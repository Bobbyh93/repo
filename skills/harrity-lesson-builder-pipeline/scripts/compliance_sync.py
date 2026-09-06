#!/usr/bin/env python3
"""Turn a release-ready lesson package into accreditation evidence (WP-5).

    compliance_sync.py SPEC [--package DIR] [--apply] [--allow-unreleased]

Reads the spec's package-level standards_refs for framework CA-BRN-ART3 and
the gated package's manifest, then builds:

  * one Evidence Registry record per req_id  (evidence_id EV-LESSON-<package_id>-<req_id>)
  * one Attachments record per package file, linked to those evidence records

Default is a dry run: the payload is written to PACKAGE/compliance_payload.json
and nothing leaves the machine. With --apply and AIRTABLE_TOKEN set, records
are created through the Airtable REST API, or updated in place when a record
with the same evidence_id / attachment_name already exists, so re-releasing
a lesson never duplicates evidence.

A package is evidence only when its manifest says release-ready. Anything
else is refused for --apply (dry run still works, so the payload can be
reviewed early). --allow-unreleased overrides that for a sandbox base only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
FRAMEWORK_FILE = HERE.parent / "references" / "frameworks" / "ca_brn_article3_requirements.json"
FRAMEWORK_ID = "CA-BRN-ART3"
API = "https://api.airtable.com/v0"


def load_framework() -> Dict[str, Any]:
    return json.loads(FRAMEWORK_FILE.read_text(encoding="utf-8"))


def package_refs(spec: Dict[str, Any]) -> List[str]:
    refs = [r.get("ref") for r in (spec.get("lesson") or {}).get("standards_refs") or [] if r.get("framework_id") == FRAMEWORK_ID]
    return [r for r in refs if r]


def build_payload(spec: Dict[str, Any], manifest: Dict[str, Any], package_dir: Path, fw: Dict[str, Any]) -> Dict[str, Any]:
    L = spec["lesson"]
    rc = (spec.get("runtime_config") or {}).get("runtime") or {}
    pkg_id = rc.get("package_id") or L.get("lesson_title", "lesson")
    status = manifest["qa"]["release_status"]
    gov = manifest.get("governance") or {}
    src = "; ".join(f"{s.get('source_id')} {s.get('title')} ({s.get('license')})" for s in spec.get("sources") or [])
    tr = manifest.get("traceability") or {}
    unmapped = tr.get("unmapped_counts") or {}
    cov = manifest.get("cjm_coverage") or {}
    problems: List[str] = []
    refs = package_refs(spec)
    if not refs:
        problems.append(f"no lesson.standards_refs for framework {FRAMEWORK_ID}; nothing to evidence")
    reqs = fw["requirements"]
    evidence = []
    for ref in refs:
        req = reqs.get(ref)
        if not req:
            problems.append(f"standards_ref {ref} not in {FRAMEWORK_FILE.name}; refresh the snapshot or fix the ref")
            continue
        desc = (f"Lesson package '{L.get('lesson_title')}' ({L.get('course_code')} · {L.get('chapter_title')}), "
                f"release status {status}, promotion state {gov.get('promotion_state')}. "
                f"Evidences {ref} ({req['ccr_section']} {req['requirement_name']}). "
                f"Source: {src}. Organizing clinical question: {L.get('organizing_clinical_question')}. "
                f"{len([s for s in manifest['slides'] if not s.get('retired')])} slides, "
                f"{len(manifest.get('assessment_items') or [])} assessment items; CJM coverage: "
                + ", ".join(f"{k} {len(v)}" for k, v in cov.items())
                + f". Traceability unmapped: {unmapped}. Package files: {', '.join(manifest.get('files') or [])}. "
                f"Generated {manifest.get('generated_at_iso')}; synced {date.today().isoformat()}.")
        evidence.append({
            "evidence_id": f"EV-LESSON-{pkg_id}-{ref}",
            "fields": {
                "Evidence Name": f"{ref} — Lesson package: {L.get('lesson_title')}",
                "evidence_id": f"EV-LESSON-{pkg_id}-{ref}",
                "req_id": ref,
                "Evidence Type": "Curriculum Evidence — Lesson Package",
                "Evidence Description": desc,
                "Evidence Status": "Received" if status == "release-ready" else "Missing",
                "requirements_link": [req["record_id"]],
            },
        })
    attachments = []
    type_map = {".pptx": "Deck", ".imscc": "LMS cartridge", ".csv": "Matrix", ".md": "Guide", ".json": "Manifest", ".html": "Web page", ".pdf": "PDF"}
    for f in manifest.get("files") or []:
        p = package_dir / f
        attachments.append({
            "attachment_name": f"{pkg_id}/{f}",
            "fields": {
                "attachment_name": f"{pkg_id}/{f}",
                "attachment_type": type_map.get(p.suffix.lower(), "File"),
                "source_url": "",
                "file": str(p.resolve()),
                "notes": f"Part of lesson package {pkg_id}; release status {status}; exists on disk: {p.exists()}",
                "ingest_status": "Linked",
                "evidence_link": [],  # filled with evidence record ids at apply time
            },
        })
    return {"package_id": pkg_id, "release_status": status, "framework": FRAMEWORK_ID, "base_id": fw["airtable"]["base_id"],
            "evidence": evidence, "attachments": attachments, "problems": problems, "dry_run": True}


# --------------------------------------------------------------------------
# Airtable REST
# --------------------------------------------------------------------------
class Airtable:
    def __init__(self, base_id: str, token: str) -> None:
        self.base, self.token = base_id, token

    def _req(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{API}/{self.base}/{path}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8") or "{}")

    def find(self, table: str, field: str, value: str) -> Optional[str]:
        safe = value.replace("'", "\\'")
        res = self._req("GET", table, query={"filterByFormula": f"{{{field}}}='{safe}'", "maxRecords": "1"})
        recs = res.get("records") or []
        return recs[0]["id"] if recs else None

    def upsert(self, table: str, key_field: str, key_value: str, fields: Dict[str, Any]) -> str:
        rid = self.find(table, key_field, key_value)
        if rid:
            self._req("PATCH", f"{table}/{rid}", {"fields": fields, "typecast": True})
            return rid
        res = self._req("POST", table, {"fields": fields, "typecast": True})
        return res["id"]


def apply(payload: Dict[str, Any], fw: Dict[str, Any], token: str) -> Dict[str, Any]:
    at = Airtable(fw["airtable"]["base_id"], token)
    ev_table = fw["airtable"]["evidence_registry_table"]
    att_table = fw["airtable"]["attachments_table"]
    ev_ids = []
    for ev in payload["evidence"]:
        rid = at.upsert(ev_table, "evidence_id", ev["evidence_id"], ev["fields"])
        ev["record_id"] = rid
        ev_ids.append(rid)
    for att in payload["attachments"]:
        fields = dict(att["fields"])
        fields["evidence_link"] = ev_ids
        att["record_id"] = at.upsert(att_table, "attachment_name", att["attachment_name"], fields)
    payload["dry_run"] = False
    payload["applied_at"] = date.today().isoformat()
    return payload


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--package", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--allow-unreleased", action="store_true")
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    pkg = a.package or (a.spec.parent / "package")
    manifest = json.loads((pkg / "lesson_manifest.json").read_text(encoding="utf-8"))
    fw = load_framework()
    payload = build_payload(spec, manifest, pkg, fw)
    if payload["problems"]:
        for p in payload["problems"]:
            print(f"[PROBLEM] {p}", file=sys.stderr)
    out = pkg / "compliance_payload.json"
    if a.apply:
        if payload["problems"]:
            print("refusing --apply: fix the problems above", file=sys.stderr)
            return 2
        if payload["release_status"] != "release-ready" and not a.allow_unreleased:
            print(f"refusing --apply: package is {payload['release_status']}, not release-ready (use --allow-unreleased only against a sandbox base)", file=sys.stderr)
            return 3
        token = os.environ.get("AIRTABLE_TOKEN", "")
        if not token:
            print("refusing --apply: AIRTABLE_TOKEN not set", file=sys.stderr)
            return 4
        payload = apply(payload, fw, token)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"package_id": payload["package_id"], "release_status": payload["release_status"], "dry_run": payload["dry_run"],
                      "evidence_records": [e["evidence_id"] for e in payload["evidence"]],
                      "attachment_records": len(payload["attachments"]), "problems": payload["problems"], "payload": str(out)}, indent=2))
    return 1 if payload["problems"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

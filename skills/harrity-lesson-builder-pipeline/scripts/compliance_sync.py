#!/usr/bin/env python3
"""File a released lesson package as accreditation evidence (WP-5).

    compliance_sync.py SPEC [--package DIR] [--apply] [--mark-received]
                            [--drive-url URL] [--allow-unreleased]

The BRN base already owns its evidence model, and this script fits into it
rather than inventing a parallel one:

  Evidence Registry  one stable "evidence pack" record per requirement,
                     keyed `EV-<req_id>` (e.g. EV-BRN-14). Pre-created.
                     This script NEVER creates one; if a pack is missing it
                     reports the fact and refuses.
  Attachments        one record per artifact, linked to the pack(s) it
                     serves through `evidence_link`, with provenance in
                     `notes` as `key: value` lines (the base's own style).

So filing a lesson means: add/refresh one Attachments record per package
file, linked to the packs for the requirements the lesson evidences.

Default is a dry run: the payload is written to PACKAGE/compliance_payload.json
and nothing leaves the machine. `--apply` needs AIRTABLE_TOKEN and a
release-ready manifest.

`--mark-received` additionally flips those packs' `Evidence Status` from
Missing to Received. That is a claim that the requirement now has evidence,
which is a faculty judgement about sufficiency, so it is off by default.

Re-running is safe: Attachments are matched by name and updated in place,
so re-releasing a lesson refreshes its records instead of duplicating them.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
FRAMEWORK_FILE = HERE.parent / "references" / "frameworks" / "ca_brn_article3_requirements.json"
FRAMEWORK_ID = "CA-BRN-ART3"
API = "https://api.airtable.com/v0"
RATE_SLEEP = 0.25          # Airtable allows 5 req/s per base; stay well under
EVIDENCE_ID_FOR = "EV-{req_id}".format

TYPE_BY_SUFFIX = {".pptx": "pptx", ".pdf": "pdf", ".imscc": "imscc", ".csv": "csv",
                  ".md": "md", ".json": "json", ".html": "html"}


def load_framework() -> Dict[str, Any]:
    return json.loads(FRAMEWORK_FILE.read_text(encoding="utf-8"))


def package_refs(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in (spec.get("lesson") or {}).get("standards_refs") or []
            if r.get("framework_id") == FRAMEWORK_ID and r.get("ref")]


# --------------------------------------------------------------------------
# Payload
# --------------------------------------------------------------------------
def build_payload(spec: Dict[str, Any], manifest: Dict[str, Any], package_dir: Path,
                  fw: Dict[str, Any], drive_url: str = "") -> Dict[str, Any]:
    L = spec["lesson"]
    rc = (spec.get("runtime_config") or {}).get("runtime") or {}
    pkg_id = rc.get("package_id") or L.get("lesson_title", "lesson")
    status = manifest["qa"]["release_status"]
    gov = manifest.get("governance") or {}
    reqs = fw["requirements"]
    problems: List[str] = []

    refs = package_refs(spec)
    if not refs:
        problems.append(f"no lesson.standards_refs for framework {FRAMEWORK_ID}; nothing to evidence")

    targets = []
    for r in refs:
        ref = r["ref"]
        req = reqs.get(ref)
        if not req:
            problems.append(f"standards_ref {ref} not in {FRAMEWORK_FILE.name}; refresh the snapshot or fix the ref")
            continue
        targets.append({"req_id": ref, "evidence_id": EVIDENCE_ID_FOR(req_id=ref),
                        "ccr_section": req["ccr_section"], "requirement_name": req["requirement_name"],
                        "requirement_record_id": req["record_id"], "basis": r.get("basis", "")})

    allowed_ingest = set(fw["airtable"].get("attachment_ingest_choices") or [])
    src = "; ".join(f"{s.get('source_id')} {s.get('title')} ({s.get('license')})" for s in spec.get("sources") or [])
    cov = manifest.get("cjm_coverage") or {}
    n_slides = len([s for s in manifest["slides"] if not s.get("retired")])
    n_items = len(manifest.get("assessment_items") or [])
    routing = ", ".join(t["evidence_id"] for t in targets)
    today = date.today().isoformat()

    listed_files = manifest.get("files") or []
    if not listed_files:
        # The loop below is the whole of the work. An empty files[] made it
        # vacuous: a run that filed nothing reported a clean dry run.
        problems.append("manifest files[] is empty; there is no artifact to file as evidence")

    attachments = []
    for f in listed_files:
        p = package_dir / f
        on_disk = p.is_file()
        if not on_disk:
            # An Attachments record names an artifact in the accreditation
            # record. Filing one for a path that does not exist is worse than
            # filing nothing, because it reads as evidence on file.
            problems.append(f"manifest files[] lists '{f}' but it is not in {package_dir}; "
                            f"regenerate the package before filing it as evidence")
        note = "\n".join([
            f"lesson_package: {pkg_id}",
            f"lesson_title: {L.get('lesson_title', '')}",
            f"course: {L.get('course_code', '')} / {L.get('chapter_title', '')}",
            f"release_status: {status}",
            f"promotion_state: {gov.get('promotion_state', '')}",
            f"source: {src}",
            f"slides: {n_slides}; assessment_items: {n_items}",
            f"cjm_coverage: " + ", ".join(f"{k} {len(v)}" for k, v in cov.items()),
            f"generated_at: {manifest.get('generated_at_iso', '')}",
            f"filed_at: {today}",
            f"route to {routing}" if routing else "route to (none)",
            "filed_by: harrity lesson builder compliance_sync",
        ])
        attachments.append({
            "match_field": "attachment_name",
            "match_value": f"{pkg_id}/{f}",
            "fields": {
                "attachment_name": f"{pkg_id}/{f}",
                "attachment_type": TYPE_BY_SUFFIX.get(p.suffix.lower(), "file"),
                "source_url": drive_url,
                "file": f"{pkg_id}/{f}",
                "notes": note,
                "ingest_status": ("Linked" if (drive_url and on_disk) else "Needs Review"),
                # The field is named for whether the artifact is missing, so it
                # must consult the artifact. It was computed from drive_url
                # alone, and read `false` for a file that was not on disk.
                "missing_file_flag": (not on_disk) or (not bool(drive_url)),
            },
        })

    for a in attachments:
        if allowed_ingest and a["fields"]["ingest_status"] not in allowed_ingest:
            problems.append(f"ingest_status '{a['fields']['ingest_status']}' is not a choice on the base "
                            f"({sorted(allowed_ingest)}); refresh the framework snapshot")
    return {"package_id": pkg_id, "release_status": status, "framework": FRAMEWORK_ID,
            "base_id": fw["airtable"]["base_id"], "evidence_targets": targets,
            "attachments": attachments, "problems": problems, "dry_run": True,
            "note": "Evidence Registry packs are looked up, never created. Attachments are "
                    "upserted by attachment_name and linked to those packs."}


# --------------------------------------------------------------------------
# Airtable REST
# --------------------------------------------------------------------------
class AirtableError(RuntimeError):
    pass


class Airtable:
    """Minimal client. Matching is done client-side on a listed page rather
    than with filterByFormula, because Airtable formula string escaping has
    no documented escape for quotes/braces and a formula that silently fails
    to match would create a duplicate record instead of updating one."""

    def __init__(self, base_id: str, token: str) -> None:
        self.base, self.token = base_id, token

    def _req(self, method: str, path: str, body: Optional[Dict[str, Any]] = None,
             query: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{API}/{self.base}/{urllib.parse.quote(path)}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                time.sleep(RATE_SLEEP)
                return json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:400]
            hint = {401: "AIRTABLE_TOKEN is invalid or expired",
                    403: "token lacks write scope on this base, or the base id is wrong",
                    404: "table or record not found; the base schema may have changed",
                    422: "Airtable rejected the field values (see detail)",
                    429: "rate limited; rerun in a minute"}.get(exc.code, "")
            raise AirtableError(f"Airtable {exc.code} on {method} {path}: {hint}. {detail}") from None
        except urllib.error.URLError as exc:
            raise AirtableError(f"cannot reach Airtable ({exc.reason}); check network access") from None

    def all_records(self, table: str, fields: List[str]) -> List[Dict[str, Any]]:
        out, offset = [], None
        while True:
            q = {"pageSize": "100"}
            for i, f in enumerate(fields):
                q[f"fields[{i}]"] = f
            if offset:
                q["offset"] = offset
            res = self._req("GET", table, query=q)
            out.extend(res.get("records") or [])
            offset = res.get("offset")
            if not offset:
                return out

    # typecast is deliberately off. With it on, Airtable silently adds a new
    # option to a singleSelect, and treats an unrecognised string on a link
    # field as a new record to create — either would mutate the base's schema
    # or its Requirements table without anyone asking.
    def create(self, table: str, fields: Dict[str, Any]) -> str:
        return self._req("POST", table, {"fields": fields, "typecast": False})["id"]

    def update(self, table: str, rid: str, fields: Dict[str, Any]) -> str:
        return self._req("PATCH", f"{table}/{rid}", {"fields": fields, "typecast": False})["id"]


def apply(payload: Dict[str, Any], fw: Dict[str, Any], token: str, mark_received: bool) -> Dict[str, Any]:
    at = Airtable(fw["airtable"]["base_id"], token)
    ev_table = fw["airtable"]["evidence_registry_table"]
    att_table = fw["airtable"]["attachments_table"]

    # 1. resolve the existing evidence packs; never create one
    packs = at.all_records(ev_table, ["evidence_id", "Evidence Name", "Evidence Status"])
    by_evidence_id: Dict[str, Dict[str, Any]] = {}
    for rec in packs:
        key = str((rec.get("fields") or {}).get("evidence_id") or "").strip()
        if key:
            by_evidence_id.setdefault(key, rec)
    missing = [t["evidence_id"] for t in payload["evidence_targets"] if t["evidence_id"] not in by_evidence_id]
    if missing:
        raise AirtableError(
            f"evidence pack(s) not found in the Evidence Registry: {', '.join(missing)}. "
            f"This script does not create packs. Create them in Airtable first, or correct "
            f"lesson.standards_refs.")
    pack_ids = []
    for t in payload["evidence_targets"]:
        rec = by_evidence_id[t["evidence_id"]]
        t["record_id"] = rec["id"]
        t["previous_status"] = ((rec.get("fields") or {}).get("Evidence Status") or {}).get("name") \
            if isinstance((rec.get("fields") or {}).get("Evidence Status"), dict) \
            else (rec.get("fields") or {}).get("Evidence Status")
        pack_ids.append(rec["id"])

    # 2. upsert one Attachments record per package file, linked to those packs
    existing = at.all_records(att_table, ["attachment_name", "evidence_link", "source_url"])
    prior = {str((r.get("fields") or {}).get("attachment_name") or "").strip(): r for r in existing}
    created = updated = 0
    for att in payload["attachments"]:
        fields = dict(att["fields"])
        rec = prior.get(att["match_value"])
        if rec:
            old = rec.get("fields") or {}
            # Airtable REPLACES a link field on PATCH rather than merging, so a
            # link someone added by hand would vanish. Union instead.
            old_links = [x if isinstance(x, str) else x.get("id") for x in (old.get("evidence_link") or [])]
            fields["evidence_link"] = sorted({*(l for l in old_links if l), *pack_ids})
            # never blank a URL a human pasted in
            if not fields.get("source_url") and old.get("source_url"):
                fields.pop("source_url")
            att["record_id"] = at.update(att_table, rec["id"], fields)
            att["action"] = "updated"
            updated += 1
        else:
            fields["evidence_link"] = pack_ids
            att["record_id"] = at.create(att_table, fields)
            att["action"] = "created"
            created += 1

    # 3. optionally mark the packs as having evidence
    for t in payload["evidence_targets"]:
        if mark_received and t.get("previous_status") != "Received":
            at.update(ev_table, t["record_id"], {"Evidence Status": "Received"})
            t["status_action"] = "set to Received"
        else:
            t["status_action"] = "left unchanged"

    payload.update({"dry_run": False, "applied_at": date.today().isoformat(),
                    "attachments_created": created, "attachments_updated": updated,
                    "marked_received": bool(mark_received)})
    return payload


# --------------------------------------------------------------------------
def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--package", type=Path)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mark-received", action="store_true",
                    help="also flip the requirement packs from Missing to Received (a sufficiency judgement)")
    ap.add_argument("--drive-url", default="", help="link to the package folder, stored on each Attachments record")
    ap.add_argument("--allow-unreleased", action="store_true", help="sandbox bases only")
    a = ap.parse_args(argv)

    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    pkg = a.package or (a.spec.parent / "package")
    manifest = json.loads((pkg / "lesson_manifest.json").read_text(encoding="utf-8"))
    fw = load_framework()
    payload = build_payload(spec, manifest, pkg, fw, a.drive_url)

    for p in payload["problems"]:
        print(f"[PROBLEM] {p}", file=sys.stderr)
    out = pkg / "compliance_payload.json"

    if a.apply:
        if payload["problems"]:
            print("refusing --apply: fix the problems above", file=sys.stderr)
            return 2
        if payload["release_status"] != "release-ready" and not a.allow_unreleased:
            print(f"refusing --apply: package is {payload['release_status']}, not release-ready "
                  f"(--allow-unreleased is for a sandbox base only)", file=sys.stderr)
            return 3
        token = os.environ.get("AIRTABLE_TOKEN", "")
        if not token:
            print("refusing --apply: AIRTABLE_TOKEN not set", file=sys.stderr)
            return 4
        try:
            payload = apply(payload, fw, token, a.mark_received)
        except AirtableError as exc:
            print(f"[AIRTABLE] {exc}", file=sys.stderr)
            payload["error"] = str(exc)
            out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"partial state written to {out}; re-running is safe (attachments match by name)", file=sys.stderr)
            return 5

    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "package_id": payload["package_id"], "release_status": payload["release_status"],
        "dry_run": payload["dry_run"],
        "evidence_packs": [f"{t['evidence_id']} ({t['ccr_section']})" for t in payload["evidence_targets"]],
        "attachment_records": len(payload["attachments"]),
        "created": payload.get("attachments_created"), "updated": payload.get("attachments_updated"),
        "marked_received": payload.get("marked_received"),
        "problems": payload["problems"], "payload": str(out),
    }, indent=2))
    return 1 if payload["problems"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

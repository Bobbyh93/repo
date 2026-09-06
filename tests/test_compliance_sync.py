"""WP-5: a gated package becomes Evidence Registry + Attachments records.
Payload shape, refusal rules, and idempotent upsert against a fake Airtable."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "harrity-lesson-builder-pipeline" / "scripts"
REF = ROOT / "lessons" / "openrn_hp_ch4"
sys.path.insert(0, str(SCRIPTS))

import compliance_sync as cs  # noqa: E402


def _load():
    spec = json.loads((REF / "lesson_spec.json").read_text(encoding="utf-8"))
    manifest = json.loads((REF / "package" / "lesson_manifest.json").read_text(encoding="utf-8"))
    return spec, manifest


def test_payload_one_evidence_record_per_req_and_one_attachment_per_file():
    spec, manifest = _load()
    fw = cs.load_framework()
    p = cs.build_payload(spec, manifest, REF / "package", fw)
    assert p["problems"] == []
    refs = cs.package_refs(spec)
    assert refs == ["BRN-14", "BRN-17"]
    assert [e["fields"]["req_id"] for e in p["evidence"]] == refs
    for e in p["evidence"]:
        assert e["fields"]["requirements_link"] == [fw["requirements"][e["fields"]["req_id"]]["record_id"]]
        assert e["fields"]["Evidence Status"] == "Missing"          # not release-ready yet
        assert "Family Dynamics" in e["fields"]["Evidence Description"]
        assert "1426" in e["fields"]["Evidence Description"]
    assert len(p["attachments"]) == len(manifest["files"])
    kinds = {a["fields"]["attachment_type"] for a in p["attachments"]}
    assert {"Deck", "LMS cartridge", "Manifest", "Matrix"} <= kinds
    assert all(a["fields"]["ingest_status"] == "Linked" for a in p["attachments"])


def test_unknown_ref_is_a_problem():
    spec, manifest = _load()
    spec["lesson"]["standards_refs"].append({"framework_id": "CA-BRN-ART3", "ref": "BRN-99"})
    p = cs.build_payload(spec, manifest, REF / "package", cs.load_framework())
    assert any("BRN-99" in x for x in p["problems"])
    assert len(p["evidence"]) == 2


def test_cli_dry_run_writes_payload_and_apply_refuses_unreleased(tmp_path, monkeypatch):
    d = tmp_path / "lesson"
    shutil.copytree(REF, d)
    r = subprocess.run([sys.executable, str(SCRIPTS / "compliance_sync.py"), str(d / "lesson_spec.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    payload = json.loads((d / "package" / "compliance_payload.json").read_text())
    assert payload["dry_run"] is True and len(payload["evidence"]) == 2
    r = subprocess.run([sys.executable, str(SCRIPTS / "compliance_sync.py"), str(d / "lesson_spec.json"), "--apply"],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "AIRTABLE_TOKEN": "x"})
    assert r.returncode == 3 and "not release-ready" in r.stderr
    r = subprocess.run([sys.executable, str(SCRIPTS / "compliance_sync.py"), str(d / "lesson_spec.json"), "--apply", "--allow-unreleased"],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 4 and "AIRTABLE_TOKEN" in r.stderr


class FakeAirtable(cs.Airtable):
    """In-memory stand-in: records keyed by table then id; find() by field value."""
    store: dict = {}
    calls: list = []

    def _req(self, method, path, body=None, query=None):
        self.calls.append((method, path))
        table, _, rid = path.partition("/")
        recs = self.store.setdefault(table, {})
        if method == "GET":
            formula = (query or {}).get("filterByFormula", "")
            field, _, value = formula.strip("{}").partition("}='")
            value = value.rstrip("'")
            hits = [{"id": k, "fields": v} for k, v in recs.items() if v.get(field) == value]
            return {"records": hits[:1]}
        if method == "POST":
            new_id = f"rec{len(recs) + 1:014d}"
            recs[new_id] = dict(body["fields"])
            return {"id": new_id, "fields": recs[new_id]}
        if method == "PATCH":
            recs[rid].update(body["fields"])
            return {"id": rid, "fields": recs[rid]}
        raise AssertionError(method)


def test_apply_is_idempotent_and_links_attachments(monkeypatch):
    spec, manifest = _load()
    manifest = dict(manifest); manifest["qa"] = dict(manifest["qa"], release_status="release-ready")
    fw = cs.load_framework()
    FakeAirtable.store.clear(); FakeAirtable.calls.clear()
    monkeypatch.setattr(cs, "Airtable", FakeAirtable)
    p1 = cs.apply(cs.build_payload(spec, manifest, REF / "package", fw), fw, "token")
    ev_table, att_table = fw["airtable"]["evidence_registry_table"], fw["airtable"]["attachments_table"]
    assert len(FakeAirtable.store[ev_table]) == 2
    assert len(FakeAirtable.store[att_table]) == len(manifest["files"])
    assert all(e["fields"]["Evidence Status"] == "Received" for e in p1["evidence"])
    ev_ids = {e["record_id"] for e in p1["evidence"]}
    assert all(set(v["evidence_link"]) == ev_ids for v in FakeAirtable.store[att_table].values())
    posts_first = sum(1 for m, _ in FakeAirtable.calls if m == "POST")
    FakeAirtable.calls.clear()
    cs.apply(cs.build_payload(spec, manifest, REF / "package", fw), fw, "token")
    assert len(FakeAirtable.store[ev_table]) == 2 and len(FakeAirtable.store[att_table]) == len(manifest["files"])
    assert sum(1 for m, _ in FakeAirtable.calls if m == "POST") == 0
    assert posts_first == 2 + len(manifest["files"])

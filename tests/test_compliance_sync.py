"""WP-5: a released package is filed as evidence the way the BRN base is
actually modelled — Evidence Registry packs are looked up, never created;
package files become Attachments linked to those packs."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "harrity-lesson-builder-pipeline" / "scripts"
REF = ROOT / "lessons" / "openrn_hp_ch4"
sys.path.insert(0, str(SCRIPTS))

import compliance_sync as cs  # noqa: E402


def _load():
    spec = json.loads((REF / "lesson_spec.json").read_text(encoding="utf-8"))
    manifest = json.loads((REF / "package" / "lesson_manifest.json").read_text(encoding="utf-8"))
    return spec, manifest


def _released(manifest):
    m = dict(manifest)
    m["qa"] = dict(m["qa"], release_status="release-ready")
    return m


# --------------------------------------------------------------------------
# payload
# --------------------------------------------------------------------------
def test_payload_targets_existing_packs_and_one_attachment_per_file():
    spec, manifest = _load()
    fw = cs.load_framework()
    p = cs.build_payload(spec, manifest, REF / "package", fw, drive_url="https://drive.example/folder")
    assert p["problems"] == []
    # evidence packs are addressed by the base's own EV-<req_id> key
    assert [t["evidence_id"] for t in p["evidence_targets"]] == ["EV-BRN-14", "EV-BRN-17"]
    assert [t["ccr_section"] for t in p["evidence_targets"]] == ["1426(b)", "1426(f)"]
    assert all(t["requirement_record_id"].startswith("rec") for t in p["evidence_targets"])
    assert all(t.get("basis") for t in p["evidence_targets"])
    # nothing in the payload proposes creating an Evidence Registry record
    assert "evidence" not in p

    assert len(p["attachments"]) == len(manifest["files"])
    kinds = {a["fields"]["attachment_type"] for a in p["attachments"]}
    assert {"pptx", "imscc", "json", "csv", "md", "html"} <= kinds
    for a in p["attachments"]:
        note = a["fields"]["notes"]
        assert "route to EV-BRN-14, EV-BRN-17" in note
        assert "lesson_package: HP-CH4-FAMILY-DYNAMICS-R1" in note
        assert a["fields"]["ingest_status"] == "Linked"      # a drive url was supplied
        assert a["fields"]["missing_file_flag"] is False


def test_without_drive_url_attachments_are_flagged_for_review():
    spec, manifest = _load()
    p = cs.build_payload(spec, manifest, REF / "package", cs.load_framework())
    assert all(a["fields"]["ingest_status"] == "Needs Review" for a in p["attachments"])
    assert all(a["fields"]["missing_file_flag"] is True for a in p["attachments"])


def test_unknown_ref_is_a_problem():
    spec, manifest = _load()
    spec["lesson"]["standards_refs"].append({"framework_id": "CA-BRN-ART3", "ref": "BRN-99"})
    p = cs.build_payload(spec, manifest, REF / "package", cs.load_framework())
    assert any("BRN-99" in x for x in p["problems"])
    assert len(p["evidence_targets"]) == 2


# --------------------------------------------------------------------------
# CLI refusals
# --------------------------------------------------------------------------
def test_cli_dry_run_writes_payload_and_apply_refuses(tmp_path):
    d = tmp_path / "lesson"
    shutil.copytree(REF, d)
    spec = d / "lesson_spec.json"
    r = subprocess.run([sys.executable, str(SCRIPTS / "compliance_sync.py"), str(spec)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    payload = json.loads((d / "package" / "compliance_payload.json").read_text())
    assert payload["dry_run"] is True and len(payload["evidence_targets"]) == 2

    r = subprocess.run([sys.executable, str(SCRIPTS / "compliance_sync.py"), str(spec), "--apply"],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "AIRTABLE_TOKEN": "x"})
    assert r.returncode == 3 and "not release-ready" in r.stderr

    r = subprocess.run([sys.executable, str(SCRIPTS / "compliance_sync.py"), str(spec), "--apply", "--allow-unreleased"],
                       capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 4 and "AIRTABLE_TOKEN" in r.stderr


# --------------------------------------------------------------------------
# apply, against an in-memory Airtable
# --------------------------------------------------------------------------
class FakeAirtable(cs.Airtable):
    """Records keyed by table then id. Seeded to mirror the real base:
    evidence packs already exist, attachments table starts empty."""
    store: dict = {}
    calls: list = []
    fail_on: tuple = ()

    def _req(self, method, path, body=None, query=None):
        self.calls.append((method, path))
        if (method, path) in self.fail_on:
            raise cs.AirtableError(f"simulated failure on {method} {path}")
        table, _, rid = path.partition("/")
        recs = self.store.setdefault(table, {})
        if method == "GET":
            return {"records": [{"id": k, "fields": v} for k, v in recs.items()]}
        if method == "POST":
            new_id = f"recNEW{len(recs) + 1:011d}"
            recs[new_id] = dict(body["fields"])
            return {"id": new_id, "fields": recs[new_id]}
        if method == "PATCH":
            recs[rid].update(body["fields"])
            return {"id": rid, "fields": recs[rid]}
        raise AssertionError(method)


@pytest.fixture
def fake(monkeypatch):
    fw = cs.load_framework()
    ev, att = fw["airtable"]["evidence_registry_table"], fw["airtable"]["attachments_table"]
    FakeAirtable.store.clear(); FakeAirtable.calls.clear(); FakeAirtable.fail_on = ()
    FakeAirtable.store[ev] = {
        "recPACK14": {"evidence_id": "EV-BRN-14", "Evidence Name": "BRN-14 Evidence Pack", "Evidence Status": "Missing"},
        "recPACK17": {"evidence_id": "EV-BRN-17", "Evidence Name": "BRN-17 Evidence Pack", "Evidence Status": "Missing"},
        "recPACK99": {"evidence_id": "EV-BRN-01", "Evidence Name": "BRN-01 Evidence Pack", "Evidence Status": "Missing"},
    }
    FakeAirtable.store[att] = {}
    monkeypatch.setattr(cs, "Airtable", FakeAirtable)
    monkeypatch.setattr(cs, "RATE_SLEEP", 0)
    return fw, ev, att


def test_apply_links_attachments_to_existing_packs_without_creating_any(fake):
    fw, ev, att = fake
    spec, manifest = _load()
    payload = cs.build_payload(spec, _released(manifest), REF / "package", fw, "https://drive.example/f")
    out = cs.apply(payload, fw, "token", mark_received=False)

    # no new Evidence Registry record was created
    assert set(FakeAirtable.store[ev]) == {"recPACK14", "recPACK17", "recPACK99"}
    assert not any(m == "POST" and p == ev for m, p in FakeAirtable.calls)
    # every attachment links to exactly the two packs
    assert len(FakeAirtable.store[att]) == len(manifest["files"])
    for rec in FakeAirtable.store[att].values():
        assert sorted(rec["evidence_link"]) == ["recPACK14", "recPACK17"]
    assert out["attachments_created"] == len(manifest["files"]) and out["attachments_updated"] == 0
    # status untouched by default
    assert all(FakeAirtable.store[ev][r]["Evidence Status"] == "Missing" for r in ("recPACK14", "recPACK17"))
    assert out["marked_received"] is False


def test_apply_is_idempotent(fake):
    fw, ev, att = fake
    spec, manifest = _load()
    m = _released(manifest)
    cs.apply(cs.build_payload(spec, m, REF / "package", fw), fw, "token", False)
    n_after_first = len(FakeAirtable.store[att])
    FakeAirtable.calls.clear()
    out = cs.apply(cs.build_payload(spec, m, REF / "package", fw), fw, "token", False)
    assert len(FakeAirtable.store[att]) == n_after_first
    assert out["attachments_created"] == 0 and out["attachments_updated"] == n_after_first
    assert not any(m_ == "POST" for m_, _ in FakeAirtable.calls)


def test_mark_received_flips_only_when_asked(fake):
    fw, ev, att = fake
    spec, manifest = _load()
    out = cs.apply(cs.build_payload(spec, _released(manifest), REF / "package", fw), fw, "token", mark_received=True)
    assert FakeAirtable.store[ev]["recPACK14"]["Evidence Status"] == "Received"
    assert FakeAirtable.store[ev]["recPACK17"]["Evidence Status"] == "Received"
    assert FakeAirtable.store[ev]["recPACK99"]["Evidence Status"] == "Missing"   # untouched requirement
    assert all(t["status_action"] == "set to Received" for t in out["evidence_targets"])


def test_apply_refuses_when_a_pack_does_not_exist(fake):
    fw, ev, att = fake
    del FakeAirtable.store[ev]["recPACK17"]
    spec, manifest = _load()
    payload = cs.build_payload(spec, _released(manifest), REF / "package", fw)
    with pytest.raises(cs.AirtableError) as exc:
        cs.apply(payload, fw, "token", False)
    assert "EV-BRN-17" in str(exc.value) and "does not create packs" in str(exc.value)
    assert FakeAirtable.store[att] == {}          # nothing written before the refusal


def test_token_never_reaches_the_payload_file(fake, tmp_path):
    fw, ev, att = fake
    spec, manifest = _load()
    out = cs.apply(cs.build_payload(spec, _released(manifest), REF / "package", fw), fw, "SECRET-TOKEN-VALUE", False)
    assert "SECRET-TOKEN-VALUE" not in json.dumps(out)


def test_http_error_is_reported_not_swallowed(fake):
    fw, ev, att = fake
    FakeAirtable.fail_on = (("POST", att),)
    spec, manifest = _load()
    payload = cs.build_payload(spec, _released(manifest), REF / "package", fw)
    with pytest.raises(cs.AirtableError):
        cs.apply(payload, fw, "token", False)


# --- D7/D8: the payload must not certify an absent artifact -----------------
# Every case above builds the payload against the real reference package, which
# is complete on disk. None of them varies the package — so a manifest that
# lists nothing, or lists a file that is not there, was never exercised.

def test_d7_empty_files_list_is_a_problem_not_a_clean_run(tmp_path):
    """D7: the attachment loop iterates manifest files[]. Empty, it produced
    zero attachments, zero problems and exit 0 — a run that filed nothing
    reported success, and --apply would have accepted it."""
    spec, manifest = _load()
    m = _released(manifest)
    m["files"] = []
    p = cs.build_payload(spec, m, REF / "package", cs.load_framework(), drive_url="https://d.example/x")
    assert p["attachments"] == []
    assert any("files[] is empty" in x for x in p["problems"])


def test_d8_file_missing_from_disk_is_a_problem(tmp_path):
    """D8: nothing in compliance_sync ever asked whether the artifact existed.
    An Attachments record naming a path that is not there reads, in the BRN
    Evidence Registry, as evidence on file."""
    spec, manifest = _load()
    pkg = tmp_path / "package"
    shutil.copytree(REF / "package", pkg)
    m = _released(manifest)
    victim = m["files"][0]
    (pkg / victim).unlink()
    p = cs.build_payload(spec, m, pkg, cs.load_framework(), drive_url="https://d.example/x")
    assert any(victim in x and "not in" in x for x in p["problems"])


def test_d8_missing_file_flag_describes_the_file_not_the_drive_url(tmp_path):
    """D8: the field is named for whether the artifact is missing and was
    computed from drive_url alone. With a drive url supplied it read `false`
    for a file that did not exist — the field's own name convicts it."""
    spec, manifest = _load()
    pkg = tmp_path / "package"
    shutil.copytree(REF / "package", pkg)
    m = _released(manifest)
    victim = m["files"][0]
    (pkg / victim).unlink()
    p = cs.build_payload(spec, m, pkg, cs.load_framework(), drive_url="https://d.example/x")
    rec = next(a for a in p["attachments"] if a["match_value"].endswith(victim))
    assert rec["fields"]["missing_file_flag"] is True
    assert rec["fields"]["ingest_status"] == "Needs Review"
    # the inverse: files that are present keep reporting present
    other = next(a for a in p["attachments"] if not a["match_value"].endswith(victim))
    assert other["fields"]["missing_file_flag"] is False


def test_d8_cli_refuses_apply_when_an_artifact_is_absent(tmp_path):
    """The control has to reach the boundary: --apply must refuse, so the
    absent artifact never becomes an Airtable write. No token is set, so a
    refusal here is the problem check, not a credential failure."""
    pkg = tmp_path / "package"
    shutil.copytree(REF / "package", pkg)
    m = json.loads((pkg / "lesson_manifest.json").read_text(encoding="utf-8"))
    m["qa"]["release_status"] = "release-ready"
    victim = m["files"][0]
    (pkg / victim).unlink()
    (pkg / "lesson_manifest.json").write_text(json.dumps(m), encoding="utf-8")
    spec = tmp_path / "lesson_spec.json"
    shutil.copy(REF / "lesson_spec.json", spec)
    r = subprocess.run([sys.executable, str(SCRIPTS / "compliance_sync.py"), str(spec),
                        "--package", str(pkg), "--drive-url", "https://d.example/x", "--apply"],
                       capture_output=True, text=True)
    assert r.returncode != 0
    # Decisive: without the D8 fix this still exits non-zero, but for the
    # missing token. The refusal must name the absent artifact, and must be
    # ordered before any credential check so the write is never attempted.
    assert "refusing --apply: fix the problems above" in r.stderr
    assert victim in r.stderr and "not in" in r.stderr


def test_d7_healthy_package_still_files_cleanly(tmp_path):
    """The inverse guard: D7/D8 must not block a package that is actually
    complete. The reference package is, and must stay at zero problems."""
    spec, manifest = _load()
    p = cs.build_payload(spec, _released(manifest), REF / "package", cs.load_framework(),
                         drive_url="https://d.example/x")
    assert p["problems"] == []
    assert len(p["attachments"]) == len(manifest["files"])
    assert all(a["fields"]["missing_file_flag"] is False for a in p["attachments"])

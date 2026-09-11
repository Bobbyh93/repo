#!/usr/bin/env python3
"""Edit lesson_spec.json and re-run the gate.

There is no sign-off workflow: no approval keys, no taxonomy lock, and no
signature needed to reach release-ready. The gate decides status from
defects alone. These commands record an edit, land it in `revision_log`,
and regenerate the package so it matches the spec.

    record_gate.py SPEC gate-pass GATE [--by NAME] [--note ...]
    record_gate.py SPEC promote SLIDE --to STATUS --evidence TEXT --by NAME
    record_gate.py SPEC set-state STATE [--by NAME]        # promotion_state
    record_gate.py SPEC set-release STATUS [--by NAME]     # qa.release_status
    record_gate.py SPEC status                             # print, no write
    common: --outdir DIR (default: <spec dir>/package)  --no-regate

`promote` keeps --by and --evidence: raising a slide to source-grounded
asserts that someone checked it against the cited source, so the spec
records who and on what basis. That is provenance, not permission.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_and_gate as gate  # noqa: E402

EVIDENCE = sorted(gate.EVIDENCE)


def load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, spec: Dict[str, Any]) -> None:
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _gov(spec: Dict[str, Any]) -> Dict[str, Any]:
    g = spec.setdefault("governance", {})
    g.setdefault("promotion_state", "intake_complete")
    return g


def _revision(spec: Dict[str, Any], changed: List[str], prev: str, new: str, reason: str, by: str, on: str) -> str:
    log = spec.setdefault("revision_log", [])
    rid = f"R{len(log) + 1:02d}"
    log.append({"revision_id": rid, "date": on, "by": by, "changed_ids": changed, "previous_summary": prev,
                "new_summary": new, "reason": reason, "downstream_effects": ["package regenerated"]})
    return rid


def cmd_gate_pass(spec, a) -> str:
    qa = spec.setdefault("qa", {})
    passed = qa.setdefault("gates_passed", [])
    if a.gate not in passed:
        passed.append(a.gate)
    qa.setdefault("gate_log", []).append({"gate": a.gate, "by": a.by, "date": a.date, "note": a.note or ""})
    return _revision(spec, ["qa.gates_passed"], "", f"gate {a.gate} passed", a.note or "", a.by, a.date)


def cmd_promote(spec, a) -> str:
    if a.to not in gate.EVIDENCE:
        raise SystemExit(f"unknown evidence status {a.to}; choose from {EVIDENCE}")
    target = next((s for s in spec["slides"] if s["slide_id"] == a.slide), None)
    if target is None:
        raise SystemExit(f"slide {a.slide} not found")
    if a.to in {"source-grounded", "source-aligned"} and not target.get("source_refs"):
        raise SystemExit(f"{a.slide} has no source_refs; cannot promote to {a.to}")
    prev = target.get("evidence_status", "")
    target["evidence_status"] = a.to
    note = f"[{a.date} {a.by}] {prev} -> {a.to}: {a.evidence}"
    target["qa_notes"] = (target.get("qa_notes", "") + ("\n" if target.get("qa_notes") else "") + note)
    target["qa_status"] = "pass" if a.to in {"source-grounded", "source-aligned"} else target.get("qa_status", "unreviewed")
    return _revision(spec, [a.slide], f"evidence_status={prev}", f"evidence_status={a.to}", a.evidence, a.by, a.date)


def cmd_set_state(spec, a) -> str:
    if a.state not in gate.PROMOTION_STATES:
        raise SystemExit(f"unknown promotion_state {a.state}; choose from {gate.PROMOTION_STATES}")
    g = _gov(spec)
    prev = g.get("promotion_state")
    g["promotion_state"] = a.state
    return _revision(spec, ["governance.promotion_state"], f"{prev}", f"{a.state}", a.note or "", a.by, a.date)


def cmd_set_release(spec, a) -> str:
    if a.status not in gate.RELEASE_STATES:
        raise SystemExit(f"unknown release_status {a.status}; choose from {sorted(gate.RELEASE_STATES)}")
    prev = spec.setdefault("qa", {}).get("release_status")
    spec["qa"]["release_status"] = a.status
    return _revision(spec, ["qa.release_status"], f"{prev}", f"{a.status}", a.note or "", a.by, a.date)


def status_summary(spec: Dict[str, Any], result: Dict[str, Any] | None = None) -> Dict[str, Any]:
    g = _gov(spec)
    ev = {}
    for s in spec["slides"]:
        ev[s.get("evidence_status", "")] = ev.get(s.get("evidence_status", ""), 0) + 1
    out = {
        "release_status_declared": spec.get("qa", {}).get("release_status"),
        "promotion_state": g["promotion_state"],
        "gates_passed": spec.get("qa", {}).get("gates_passed", []),
        "evidence_status_counts": ev,
        "revisions": len(spec.get("revision_log") or []),
    }
    if result:
        out["release_status_computed"] = result["status"]
        out["blocked"] = result.get("blocked", False)
        out["defects"] = {sev: sum(1 for d in result["defects"] if d["severity"] == sev) for sev in ("blocker", "major", "minor")}
        out["deck"] = result.get("deck")
    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--outdir", type=Path)
    ap.add_argument("--no-regate", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, by_required=False):
        p.add_argument("--by", required=by_required, default="author",
                       help="who made the edit (recorded in revision_log)")
        p.add_argument("--date", default=date.today().isoformat())
        p.add_argument("--note", default="")

    p = sub.add_parser("gate-pass"); p.add_argument("gate"); common(p)
    p = sub.add_parser("promote"); p.add_argument("slide"); p.add_argument("--to", required=True); p.add_argument("--evidence", required=True); common(p, by_required=True)
    p = sub.add_parser("set-state"); p.add_argument("state"); common(p)
    p = sub.add_parser("set-release"); p.add_argument("status"); common(p)
    sub.add_parser("status")
    a = ap.parse_args(argv)

    spec = load(a.spec)
    outdir = a.outdir or (a.spec.parent / "package")
    handlers = {"gate-pass": cmd_gate_pass, "promote": cmd_promote,
                "set-state": cmd_set_state, "set-release": cmd_set_release}
    if a.cmd != "status":
        rid = handlers[a.cmd](spec, a)
        save(a.spec, spec)
        print(f"recorded {rid}: {a.cmd} by {a.by} on {a.date}")
    result = None
    if not a.no_regate and (a.cmd != "status" or outdir.exists()):
        result = gate.run(spec, outdir, demo=False)
    print(json.dumps(status_summary(spec, result), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

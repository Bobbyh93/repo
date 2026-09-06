#!/usr/bin/env python3
"""Validate a Harrity learner-facing lesson package.

Usage:
  python scripts/validate_lesson_package.py /path/to/package
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

PROHIBITED_VISIBLE_TERMS = [
    "teaching move",
    "presenter intent",
    "script focus",
    "facilitator note",
    "production note",
    "visual production note",
    "instructor should",
    "use this slide to",
]

REQUIRED_FILES = [
    "slide_map.csv",
    "item_map.csv",
    "qa_log.csv",
    "package_manifest.json",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def warn(message: str) -> None:
    print(f"WARN: {message}")


def main() -> None:
    if len(sys.argv) != 2:
        fail("Expected package directory argument.")

    root = Path(sys.argv[1]).resolve()
    if not root.exists() or not root.is_dir():
        fail(f"Package directory not found: {root}")

    missing = [p for p in REQUIRED_FILES if not (root / p).exists()]
    if missing:
        fail("Missing required files: " + ", ".join(missing))

    slide_rows = read_csv(root / "slide_map.csv")
    item_rows = read_csv(root / "item_map.csv")
    qa_rows = read_csv(root / "qa_log.csv")

    if not slide_rows:
        fail("slide_map.csv has no rows.")

    major_concept_rows = [r for r in slide_rows if r.get("block_type") in {"concept", "exam_anchor", "trap", "item", "summary"}]
    missing_anchors = [r.get("slide_id", "<unknown>") for r in major_concept_rows if not r.get("exam_anchor")]
    if missing_anchors:
        warn("Some major concept rows lack exam_anchor: " + ", ".join(missing_anchors[:10]))

    invalid_visible = [r.get("slide_id", "<unknown>") for r in slide_rows if r.get("visible_language_check") not in {"pass", "conditional", "not_applicable"}]
    if invalid_visible:
        fail("Visible language check failed/missing for slides: " + ", ".join(invalid_visible[:10]))

    item_ids_with_rationale = {r.get("item_id") for r in item_rows if r.get("rationale")}
    item_ids = {r.get("item_id") for r in item_rows if r.get("item_id")}
    missing_rationale = sorted(item_ids - item_ids_with_rationale)
    if missing_rationale:
        fail("Items missing rationales: " + ", ".join(missing_rationale[:10]))

    p0_blockers = [r for r in qa_rows if r.get("block_level") == "P0" and r.get("status") not in {"pass", "not_applicable"}]
    if p0_blockers:
        fail(f"P0 QA blockers present: {len(p0_blockers)}")

    manifest = json.loads((root / "package_manifest.json").read_text(encoding="utf-8"))
    claimed = manifest.get("generated_artifacts", [])
    missing_claimed = []
    for item in claimed:
        rel = item.get("path") if isinstance(item, dict) else str(item)
        if rel and not (root / rel).exists():
            missing_claimed.append(rel)
    if missing_claimed:
        fail("Manifest claims missing artifacts: " + ", ".join(missing_claimed[:10]))

    print("PASS: Harrity learner-facing lesson package validation passed.")


if __name__ == "__main__":
    main()

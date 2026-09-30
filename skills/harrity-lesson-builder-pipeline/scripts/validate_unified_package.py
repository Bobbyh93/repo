#!/usr/bin/env python3
"""Validate a generated Harrity lesson package directory.

Usage:
    python validate_unified_package.py path/to/package_dir

Checks:
- required package files exist (one .pptx deck; name may carry the
  runtime filename pattern and a _DRAFT stamp)
- lesson_manifest.json is parseable and its files[] all exist
- the deck opens with python-pptx and its slide count matches the
  manifest's active (non-retired) slide count
- slide ids are present and unique
- assessment_map.csv is present and includes CJM/remediation fields
  (v1.1 columns; legacy column names also accepted)
- required CJM functions are represented or the manifest documents why not
- a manifest status of `blocked` must be paired with a _DRAFT deck name
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

REQUIRED_FILES = [
    "facilitator_guide.md",
    "learner_handout.md",
    "assessment_map.csv",
    "lesson_manifest.json",
]
OPTIONAL_V11_FILES = ["qa_log.md", "traceability_matrix.csv"]

REQUIRED_CJM = [
    "recognize cues",
    "analyze cues",
    "prioritize hypotheses",
    "generate solutions",
    "take action",
    "evaluate outcomes",
]

# v1.1 assessment_map columns; the legacy set is accepted as an alternative.
ASSESSMENT_COLUMNS_V11 = {"objective", "concept_lane", "slide", "activity", "cjm_function", "item_type", "remediation_target"}
ASSESSMENT_COLUMNS_LEGACY = {"slide_number", "slide_title", "cjm_steps", "concepts", "learner_task", "remediation_target"}


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def collect_cjm_from_manifest(manifest: Dict[str, Any]) -> Set[str]:
    found: Set[str] = set()
    for slide in manifest.get("slides", []):
        if not isinstance(slide, dict) or slide.get("retired"):
            continue
        for key in ("cjm_steps", "cjm_functions"):
            value = slide.get(key, [])
            if isinstance(value, str):
                found.add(norm(value))
            elif isinstance(value, list):
                found.update(norm(item) for item in value if norm(item))
    coverage = manifest.get("cjm_coverage")
    if isinstance(coverage, dict):
        for key, value in coverage.items():
            if value:
                found.add(norm(key))
    return found


def collect_cjm_from_assessment(path: Path) -> Set[str]:
    found: Set[str] = set()
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("cjm_steps") or row.get("cjm_function") or ""
            for part in raw.replace(";", ",").split(","):
                if norm(part):
                    found.add(norm(part))
    return found


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print(__doc__.strip())
        return 2

    root = Path(argv[1])
    errors: List[str] = []
    warnings: List[str] = []

    if not root.exists() or not root.is_dir():
        print(f"[FAIL] Package directory not found: {root}")
        return 1

    for name in REQUIRED_FILES:
        if not (root / name).exists():
            errors.append(f"missing required file: {name}")
    for name in OPTIONAL_V11_FILES:
        if not (root / name).exists():
            warnings.append(f"v1.1 file not present: {name}")

    decks = sorted(root.glob("*.pptx"))
    if not decks:
        errors.append("missing deck: no .pptx file in package directory")
    elif len(decks) > 1:
        warnings.append(f"more than one .pptx in package: {[d.name for d in decks]}")

    manifest_path = root / "lesson_manifest.json"
    manifest: Dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"lesson_manifest.json is invalid JSON: {exc}")

    listed = manifest.get("files", []) if isinstance(manifest, dict) else []
    if isinstance(manifest, dict) and not listed:
        # An empty files[] made the existence loop below vacuous: a package missing
        # every artifact passed because there was nothing to look for.
        errors.append("manifest files[] is empty; the package claims to contain nothing")
    for f in listed:
        if not (root / f).exists():
            errors.append(f"manifest files[] entry missing on disk: {f}")

    slides = manifest.get("slides", []) if isinstance(manifest, dict) else []
    active = [s for s in slides if isinstance(s, dict) and not s.get("retired")]
    if slides:
        ids = []
        for idx, slide in enumerate(slides, start=1):
            if isinstance(slide, dict):
                sid = slide.get("slide_id") or slide.get("id") or f"slide_number:{slide.get('slide_number', idx)}"
                ids.append(str(sid))
        duplicate_ids = sorted({sid for sid in ids if ids.count(sid) > 1})
        if duplicate_ids:
            errors.append(f"duplicate slide ids in manifest: {duplicate_ids}")
    else:
        # A manifest that describes no slides cannot certify a deck. Treating this as
        # a warning made the deck/manifest comparison below vacuous: a 20-slide deck
        # passed against a 0-slide manifest.
        errors.append("manifest lists no slides; nothing can be checked against the deck")

    if decks:
        try:
            from pptx import Presentation  # type: ignore
            prs = Presentation(str(decks[0]))
            n = len(prs.slides)
            if n != len(active):
                errors.append(f"deck has {n} slides but manifest lists {len(active)} active slides")
            missing_notes = [i for i, s in enumerate(prs.slides, start=1)
                             if not (s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip())]
            if missing_notes:
                warnings.append(f"{len(missing_notes)} slide(s) without speaker notes: {missing_notes[:10]}")
        except ImportError:
            warnings.append("python-pptx not installed; deck not opened")
        except Exception as exc:  # corrupt file
            errors.append(f"deck failed to open: {exc}")

    status = norm((manifest.get("qa") or {}).get("release_status")) if isinstance(manifest, dict) else ""
    if status == "blocked" and decks and "_DRAFT" not in decks[0].name:
        errors.append("manifest release_status is blocked but deck filename lacks _DRAFT stamp")
    if status and status != "blocked" and decks and "_DRAFT" in decks[0].name:
        errors.append(f"deck is stamped _DRAFT but manifest release_status is {status}")

    assessment_path = root / "assessment_map.csv"
    cjm_found: Set[str] = set()
    if assessment_path.exists():
        with assessment_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])
        if not (ASSESSMENT_COLUMNS_V11 <= headers or ASSESSMENT_COLUMNS_LEGACY <= headers):
            warnings.append(f"assessment_map.csv columns match neither v1.1 nor legacy set: {sorted(headers)}")
        try:
            cjm_found.update(collect_cjm_from_assessment(assessment_path))
        except Exception as exc:  # defensive; report but continue
            errors.append(f"could not read assessment_map.csv: {exc}")

    cjm_found.update(collect_cjm_from_manifest(manifest))
    missing_cjm = [item for item in REQUIRED_CJM if item not in cjm_found]
    if missing_cjm:
        documented = False
        if isinstance(manifest, dict):
            notes = json.dumps(manifest.get("qa_summary", {}), ensure_ascii=False).lower()
            notes += json.dumps(manifest.get("assumptions", []), ensure_ascii=False).lower()
            notes += norm(manifest.get("cjm_coverage_rationale", ""))
            documented = bool(manifest.get("cjm_coverage_rationale")) or all(
                item in notes or "short package" in notes for item in missing_cjm)
        if documented:
            warnings.append(f"missing CJM functions documented as intentional: {missing_cjm}")
        else:
            errors.append(f"missing required CJM coverage: {missing_cjm}")

    if errors:
        print("[FAIL] Validation found errors:")
        for item in errors:
            print(f"  - {item}")
    else:
        print("[PASS] No validation errors found.")

    if warnings:
        print("[WARN] Additional warnings:")
        for item in warnings:
            print(f"  - {item}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

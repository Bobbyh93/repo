#!/usr/bin/env python3
"""Extract one chapter's text from a whole-book PDF into the raw-source fallback path.

The build environment's egress proxy denies all hosts except a small allowlist
(package registries and raw.githubusercontent.com), so chapters cannot be fetched
live. A whole-book PDF committed to the repository is readable, and this script
carves a single chapter out of it.

    # see what chapter boundaries were detected, and on which pages
    python extract_chapter_text.py --pdf handoff/source/raw/book/openrn_nhp.pdf --list

    # write handoff/source/raw/ch5/chapter.md
    python extract_chapter_text.py --pdf handoff/source/raw/book/openrn_nhp.pdf --chapter 5

Boundary detection is a heuristic over page text, so `--list` exists to be checked by
a person before the output is trusted. Pass --start/--end to override it outright.
Nothing here decides licensing: SOURCE.json still carries the human attestation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
except ModuleNotFoundError:  # pragma: no cover - environment guard
    sys.exit(
        "pypdf is required. The container's system cryptography package breaks the\n"
        "system-wide install, so use a venv:\n"
        "    python3 -m venv .pdfenv && .pdfenv/bin/pip install pypdf\n"
        "    .pdfenv/bin/python skills/harrity-lesson-builder-pipeline/scripts/extract_chapter_text.py ..."
    )

# "Chapter 5", "CHAPTER 5.", "5. Family Dynamics" at the head of a page.
HEADING = re.compile(r"^\s*(?:chapter\s+)?(\d{1,2})(?:[.:]|\s|$)", re.IGNORECASE)
EXPLICIT = re.compile(r"^\s*chapter\s+(\d{1,2})\b", re.IGNORECASE)


def page_texts(pdf: Path) -> list[str]:
    reader = PdfReader(str(pdf))
    out = []
    for page in reader.pages:
        try:
            out.append(page.extract_text() or "")
        except Exception as exc:  # a single bad page should not kill the run
            out.append("")
            print(f"[warn] page {len(out)}: {exc}", file=sys.stderr)
    return out


def detect_starts(pages: list[str]) -> dict[int, int]:
    """Map chapter number -> 0-based index of the page it starts on.

    Prefers an explicit "Chapter N" line; falls back to a bare leading "N." only when
    that chapter was not found explicitly anywhere. First occurrence wins, so a
    table-of-contents mention early in the book does not shadow the real opening —
    ToC pages list many chapters at once, so they are skipped.
    """
    explicit: dict[int, int] = {}
    loose: dict[int, int] = {}
    for idx, text in enumerate(pages):
        head = "\n".join(text.strip().splitlines()[:4])
        numbers_on_page = set(EXPLICIT.findall(text))
        if len(numbers_on_page) > 2:
            continue  # a contents/index page, not a chapter opening
        m = EXPLICIT.match(head)
        if m:
            explicit.setdefault(int(m.group(1)), idx)
            continue
        m = HEADING.match(head)
        if m:
            loose.setdefault(int(m.group(1)), idx)
    merged = dict(loose)
    merged.update(explicit)
    return dict(sorted(merged.items()))


def chapter_range(starts: dict[int, int], chapter: int, total: int) -> tuple[int, int]:
    if chapter not in starts:
        raise SystemExit(
            f"[fail] chapter {chapter} not detected. Run with --list to see what was found, "
            f"then pass --start/--end explicitly."
        )

    begin = starts[chapter]
    later = [p for c, p in starts.items() if c > chapter and p > begin]
    end = min(later) if later else total
    return begin, end


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--out", type=Path, help="default: handoff/source/raw/ch<N>/chapter.md")
    ap.add_argument("--list", action="store_true", help="print detected chapter starts and exit")
    ap.add_argument("--start", type=int, help="1-based first page, overrides detection")
    ap.add_argument("--end", type=int, help="1-based last page (inclusive), overrides detection")
    args = ap.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"[fail] no such PDF: {args.pdf}")

    pages = page_texts(args.pdf)
    starts = detect_starts(pages)

    if args.list:
        print(f"{args.pdf} — {len(pages)} pages")
        for chapter, idx in starts.items():
            title = next((ln.strip() for ln in pages[idx].splitlines() if ln.strip()), "")
            print(f"  chapter {chapter:>2}  starts p.{idx + 1:<5} {title[:70]}")
        return 0

    if args.chapter is None:
        raise SystemExit("[fail] --chapter is required unless --list is given")

    if args.start and args.end:
        begin, end = args.start - 1, args.end
    else:
        begin, end = chapter_range(starts, args.chapter, len(pages))

    body = "\n\n".join(
        f"<!-- page {i + 1} -->\n{pages[i].strip()}" for i in range(begin, end) if pages[i].strip()
    )
    if not body.strip():
        raise SystemExit(f"[fail] pages {begin + 1}-{end} contain no extractable text (scanned images?)")

    out = args.out or Path(f"handoff/source/raw/ch{args.chapter}/chapter.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body + "\n", encoding="utf-8")

    words = len(re.findall(r"\b\w+\b", body))
    print(f"[ok] chapter {args.chapter}: pages {begin + 1}-{end} -> {out} ({words} words)")

    src = out.parent / "SOURCE.json"
    if not src.exists():
        print(
            f"[note] {src} does not exist yet. The lesson build refuses to run without it — "
            f"it carries the human license attestation (url, license, fetched_by, fetched_on). "
            f"See handoff/source/raw/README.md."
        )
    else:
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
            missing = [k for k in ("url", "license", "fetched_by", "fetched_on") if not data.get(k)]
            if missing:
                print(f"[warn] {src} is missing required keys: {', '.join(missing)}")
        except json.JSONDecodeError as exc:
            print(f"[warn] {src} is not valid JSON: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

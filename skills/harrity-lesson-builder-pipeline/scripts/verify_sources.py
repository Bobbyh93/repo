#!/usr/bin/env python3
"""Check every clinical slide and assessment item against its cited source text.

    verify_sources.py SPEC --out DIR [--fetch] [--html SRC_ID=FILE ...] [--text SRC_ID=FILE ...]

Source text comes from, in order: files given with --html/--text, a cached
copy in DIR/sources/<SRC_ID>.txt, or (with --fetch) the source's locator URLs
and, when the spec names a source index file, that index's section anchors.
Fetching needs network; when it fails the slide is reported as
"source text unavailable", never as verified.

Output DIR/verification_report.md and DIR/verification.json: per slide and
item, the share of content terms found in the source, the best-matching
section (by term overlap), terms not found, and a suggested action:

  keep-as-is      already source-grounded and terms found
  promote         source-aligned, >= 85% terms found -> candidate for
                  source-grounded; a human confirms with record_gate.py
  review          50-85% found; read the listed missing terms against the text
  flag            < 50% found or no source text; do not promote

The script only measures term overlap. Whether a paraphrase is faithful is a
reading judgment, which is why promotion is a separate, signed step.
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

STOP = set("""a an the and or of to in on for with by from as at is are was were be been being this that these those it its
into than then so such not no nor if but which who whom whose what when where why how all any each every both few more most
other some own same very can will just do does did done has have had having may might must shall should would could about
above after again against before below between during over under out up down off once only same too here there their they
them our we you your his her he she him one two three four five first second third per via one's client clients nurse nurses
nursing family families member members person people""".split())
TERM_RE = re.compile(r"[a-z][a-z\-']{3,}")


def terms(text: str) -> set:
    return {t for t in TERM_RE.findall(str(text).lower()) if t not in STOP}


def slide_text(s: Dict[str, Any]) -> str:
    parts = [s.get("slide_title", ""), *(s.get("on_slide_text") or [])]
    for c in (s.get("layout_spec") or {}).get("card_data") or []:
        if isinstance(c, dict):
            parts.append(json.dumps(c, ensure_ascii=False))
    return " ".join(str(p) for p in parts)


def item_text(it: Dict[str, Any]) -> str:
    return " ".join([it.get("stem", ""), *(it.get("options") or []), it.get("rationale", "")])


def html_to_text(raw: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Strip tags; also pull <table> contents out as row lists."""
    tables = []
    for m in re.finditer(r"<table.*?</table>", raw, flags=re.S | re.I):
        rows = []
        for tr in re.finditer(r"<tr.*?</tr>", m.group(0), flags=re.S | re.I):
            cells = [htmllib.unescape(re.sub(r"<[^>]+>", " ", td)).strip()
                     for td in re.findall(r"<t[dh].*?</t[dh]>", tr.group(0), flags=re.S | re.I)]
            if cells:
                rows.append(cells)
        cap = re.search(r"<caption.*?>(.*?)</caption>", m.group(0), flags=re.S | re.I)
        tables.append({"caption": htmllib.unescape(re.sub(r"<[^>]+>", " ", cap.group(1))).strip() if cap else "", "rows": rows})
    text = re.sub(r"<(script|style).*?</\1>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<h[1-6][^>]*>", "\n## ", text, flags=re.I)
    text = re.sub(r"<(p|div|li|tr|br)[^>]*>", "\n", text, flags=re.I)
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip(), tables


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "harrity-lesson-builder/1.2 (source verification)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def sections(text: str) -> List[Tuple[str, str]]:
    out, cur, buf = [], "start", []
    for line in text.splitlines():
        if line.startswith("## "):
            if buf:
                out.append((cur, "\n".join(buf)))
            cur, buf = line[3:].strip(), []
        else:
            buf.append(line)
    if buf:
        out.append((cur, "\n".join(buf)))
    return out


def load_source_text(src: Dict[str, Any], outdir: Path, overrides: Dict[str, Path], text_overrides: Dict[str, Path],
                     do_fetch: bool, spec_dir: Path) -> Tuple[str, List[Dict[str, Any]], str]:
    sid = src["source_id"]
    cache = outdir / "sources" / f"{sid}.txt"
    tcache = outdir / "sources" / f"{sid}.tables.json"
    if sid in text_overrides:
        return text_overrides[sid].read_text(encoding="utf-8"), [], f"text file {text_overrides[sid]}"
    if sid in overrides:
        text, tables = html_to_text(overrides[sid].read_text(encoding="utf-8", errors="replace"))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding="utf-8"); tcache.write_text(json.dumps(tables, indent=1), encoding="utf-8")
        return text, tables, f"html file {overrides[sid]}"
    if cache.exists():
        tables = json.loads(tcache.read_text(encoding="utf-8")) if tcache.exists() else []
        return cache.read_text(encoding="utf-8"), tables, f"cache {cache}"
    if not do_fetch:
        return "", [], "no source text (no --fetch, no file, no cache)"
    urls: List[str] = []
    idx = src.get("index_path")
    if idx and (spec_dir / idx).exists():
        index = json.loads((spec_dir / idx).read_text(encoding="utf-8"))
        urls += [s.get("pressbooks") for s in index.get("sections", []) if s.get("pressbooks")]
    urls += [u.strip() for u in re.split(r"[;\s]+", src.get("locator", "")) if u.strip().startswith("http")]
    texts, tables, errors = [], [], []
    for u in urls:
        try:
            t, tb = html_to_text(fetch(u))
            texts.append(f"## {u}\n{t}"); tables += tb
        except Exception as exc:  # network / proxy / 404
            errors.append(f"{u}: {exc}")
    if not texts:
        return "", [], "fetch failed: " + "; ".join(errors)[:500]
    text = "\n".join(texts)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8"); tcache.write_text(json.dumps(tables, indent=1), encoding="utf-8")
    return text, tables, f"fetched {len(texts)}/{len(urls)} urls" + (f"; errors: {'; '.join(errors)[:300]}" if errors else "")


def assess(content: str, src_text: str, src_terms: set, secs: List[Tuple[str, set]]) -> Dict[str, Any]:
    t = terms(content)
    if not t:
        return {"terms": 0, "found": 0, "share": 0.0, "missing": [], "best_section": ""}
    found = {x for x in t if x in src_terms}
    best, best_n = "", 0
    for name, st in secs:
        n = len(t & st)
        if n > best_n:
            best, best_n = name, n
    return {"terms": len(t), "found": len(found), "share": round(len(found) / len(t), 2),
            "missing": sorted(t - found)[:25], "best_section": best}


def suggestion(ev: str, share: float, has_text: bool) -> str:
    if not has_text:
        return "flag: source text unavailable"
    if ev == "source-grounded":
        return "keep-as-is" if share >= 0.85 else "review: grounded claim with missing terms"
    if ev in {"source-aligned", "needs-verification", "provisional", "inferred"}:
        if share >= 0.85:
            return "promote: candidate for source-grounded (human confirms)"
        if share >= 0.5:
            return "review"
        return "flag: low overlap"
    return "n/a (not a sourced claim)"


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--html", action="append", default=[], metavar="SRC_ID=FILE")
    ap.add_argument("--text", action="append", default=[], metavar="SRC_ID=FILE")
    a = ap.parse_args(argv)
    spec = json.loads(a.spec.read_text(encoding="utf-8"))
    a.out.mkdir(parents=True, exist_ok=True)
    overrides = {k: Path(v) for k, v in (x.split("=", 1) for x in a.html)}
    text_overrides = {k: Path(v) for k, v in (x.split("=", 1) for x in a.text)}
    repo_root = next((p for p in [a.spec.resolve().parent, *a.spec.resolve().parents] if (p / "handoff").exists()), a.spec.resolve().parent)

    sources: Dict[str, Dict[str, Any]] = {}
    for src in spec.get("sources") or []:
        text, tables, how = load_source_text(src, a.out, overrides, text_overrides, a.fetch, repo_root)
        secs = [(name, terms(body)) for name, body in sections(text)]
        sources[src["source_id"]] = {"text": text, "terms": terms(text), "sections": secs, "tables": tables, "how": how}

    results = []
    for s in spec["slides"]:
        if s.get("retired") or not s.get("source_refs"):
            continue
        for ref in s["source_refs"]:
            src = sources.get(ref)
            has = bool(src and src["text"])
            r = assess(slide_text(s), src["text"] if has else "", src["terms"] if has else set(), src["sections"] if has else [])
            r.update({"kind": "slide", "id": s["slide_id"], "title": s.get("slide_title", ""), "source": ref,
                      "evidence_status": s.get("evidence_status"), "suggestion": suggestion(s.get("evidence_status", ""), r["share"], has)})
            results.append(r)
    for it in spec.get("assessment_items") or []:
        for ref in it.get("source_refs") or []:
            src = sources.get(ref)
            has = bool(src and src["text"])
            r = assess(item_text(it), src["text"] if has else "", src["terms"] if has else set(), src["sections"] if has else [])
            r.update({"kind": "item", "id": it["item_id"], "title": it.get("stem", "")[:60], "source": ref,
                      "evidence_status": it.get("evidence_status"), "suggestion": suggestion(it.get("evidence_status", ""), r["share"], has)})
            results.append(r)

    summary = {"sources": {k: {"how": v["how"], "chars": len(v["text"]), "tables": len(v["tables"]),
                               "table_captions": [t["caption"] for t in v["tables"]][:20]} for k, v in sources.items()},
               "counts": {}}
    for r in results:
        key = r["suggestion"].split(":")[0]
        summary["counts"][key] = summary["counts"].get(key, 0) + 1
    (a.out / "verification.json").write_text(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [f"# Source verification — {spec['lesson'].get('lesson_title', '')}\n"]
    for k, v in summary["sources"].items():
        md.append(f"- **{k}**: {v['how']}; {v['chars']} chars; {v['tables']} tables" + (f" ({'; '.join(c for c in v['table_captions'] if c)})" if v['table_captions'] else ""))
    md.append(f"\nSuggestions: {summary['counts']}\n")
    md.append("| id | status | terms found | best section | suggestion | missing terms |")
    md.append("|---|---|---|---|---|---|")
    for r in results:
        md.append(f"| {r['id']} | {r['evidence_status']} | {r['found']}/{r['terms']} ({int(r['share'] * 100)}%) | {r['best_section'][:50]} | {r['suggestion']} | {', '.join(r['missing'][:8])} |")
    md.append("\nPromotion is a signed step: `record_gate.py SPEC promote S05 --to source-grounded --by NAME --evidence \"…\"`.")
    (a.out / "verification_report.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

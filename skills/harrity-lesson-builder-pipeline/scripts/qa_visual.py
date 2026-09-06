#!/usr/bin/env python3
"""Visual + structural QA of a gated package, and optional live LMS import.

    qa_visual.py PACKAGE_DIR [--dpi 50] [--canvas-course-id ID]

Writes PACKAGE_DIR/qa_visual/:
  slide-NN.png       one thumbnail per slide (LibreOffice + pdftoppm)
  contact_sheet.png  all thumbnails on one image, numbered, for a single Read
  report.json        what ran, what passed, what could not run and why

Structural checks always run (python-pptx round-trip, validate_unified_package,
validate_cartridge). Rendering runs only when `soffice` and `pdftoppm` exist
and succeed; otherwise report.json says so and the visual gate stays open.

Canvas import runs only when CANVAS_BASE_URL and CANVAS_TOKEN are set and a
course id is given. It uses the Content Migrations API
(common_cartridge_importer) and polls until the migration completes, then
counts quizzes/pages created. It never deletes anything. Use a sandbox course.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_lms  # noqa: E402


def structural(pkg: Path, report: Dict[str, Any]) -> None:
    from pptx import Presentation
    manifest = json.loads((pkg / "lesson_manifest.json").read_text(encoding="utf-8"))
    report["release_status"] = manifest["qa"]["release_status"]
    decks = list(pkg.glob("*.pptx"))
    report["deck"] = decks[0].name if decks else None
    prs = Presentation(str(decks[0]))
    active = [s for s in manifest["slides"] if not s.get("retired")]
    report["slide_count"] = len(prs.slides)
    report["slide_count_matches_manifest"] = len(prs.slides) == len(active)
    report["slides_without_notes"] = [i for i, s in enumerate(prs.slides, 1)
                                      if not (s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip())]
    # text overflow heuristic: any text frame whose text is long relative to its box
    overflow = []
    for i, s in enumerate(prs.slides, 1):
        for sh in s.shapes:
            if sh.has_text_frame and sh.width and sh.height:
                chars = len(sh.text_frame.text)
                area_in2 = (sh.width / 914400) * (sh.height / 914400)
                if chars > 0 and chars / max(area_in2, 0.01) > 140:   # ~140 chars per square inch at body sizes
                    overflow.append({"slide": i, "chars": chars, "area_in2": round(area_in2, 2), "text": sh.text_frame.text[:60]})
    report["possible_text_overflow"] = overflow
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("validate_unified_package.py")), str(pkg)],
                       capture_output=True, text=True)
    report["validate_unified_package"] = {"exit": r.returncode, "output": r.stdout.strip()}
    cc = list(pkg.glob("*.imscc"))
    if cc:
        errs = export_lms.validate_cartridge(cc[0], len(manifest.get("assessment_items") or []))
        report["cartridge"] = {"file": cc[0].name, "errors": errs, "pass": not errs}
    else:
        report["cartridge"] = {"file": None, "errors": ["no .imscc in package"], "pass": False}


def render(pkg: Path, out: Path, dpi: int, report: Dict[str, Any]) -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    pdftoppm = shutil.which("pdftoppm")
    try:
        import pymupdf  # noqa: F401  fallback rasterizer when poppler is absent
        have_mupdf = True
    except ImportError:
        have_mupdf = False
    if not soffice or not (pdftoppm or have_mupdf):
        report["render"] = {"ran": False, "reason": f"missing tool: soffice={bool(soffice)} pdftoppm={bool(pdftoppm)} pymupdf={have_mupdf}"}
        return
    deck = next(pkg.glob("*.pptx"))
    with tempfile.TemporaryDirectory() as tmp:
        prof = Path(tmp) / "profile"
        try:
            subprocess.run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pdf",
                            "--outdir", tmp, str(deck)], check=False, timeout=300, capture_output=True)
        except subprocess.TimeoutExpired:
            report["render"] = {"ran": False, "reason": "soffice timed out"}
            return
        pdfs = list(Path(tmp).glob("*.pdf"))
        if not pdfs:
            report["render"] = {"ran": False, "reason": "soffice produced no PDF (file could not be loaded)"}
            return
        shutil.copy(pdfs[0], out / "deck.pdf")
        for old_png in out.glob("slide-*.png"):
            old_png.unlink()
        if pdftoppm:
            subprocess.run([pdftoppm, "-r", str(dpi), "-png", str(pdfs[0]), str(out / "slide")], check=False, capture_output=True)
        else:
            import pymupdf
            doc = pymupdf.open(str(pdfs[0]))
            for i, page in enumerate(doc, 1):
                page.get_pixmap(dpi=dpi).save(str(out / f"slide-{i:02d}.png"))
    pngs = sorted(out.glob("slide-*.png"))
    report["render"] = {"ran": True, "thumbnails": [p.name for p in pngs], "pdf": "deck.pdf"}
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        report["render"]["contact_sheet"] = None
        return
    imgs = [Image.open(p) for p in pngs]
    if not imgs:
        return
    w, h = imgs[0].size
    cols = 4
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (w + 10) + 10, rows * (h + 30) + 10), "white")
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(imgs):
        x = 10 + (i % cols) * (w + 10)
        y = 10 + (i // cols) * (h + 30)
        sheet.paste(im, (x, y + 20))
        d.text((x, y + 2), f"{i + 1}", fill="black")
    sheet.save(out / "contact_sheet.png")
    report["render"]["contact_sheet"] = "contact_sheet.png"


def _canvas(method: str, url: str, token: str, data: Optional[bytes] = None, ctype: str = "application/json") -> Dict[str, Any]:
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def canvas_import(pkg: Path, course_id: str, report: Dict[str, Any]) -> None:
    base = os.environ.get("CANVAS_BASE_URL", "").rstrip("/")
    token = os.environ.get("CANVAS_TOKEN", "")
    if not base or not token:
        report["canvas_import"] = {"ran": False, "reason": "CANVAS_BASE_URL / CANVAS_TOKEN not set"}
        return
    cc = next(pkg.glob("*.imscc"), None)
    if cc is None:
        report["canvas_import"] = {"ran": False, "reason": "no .imscc"}
        return
    size = cc.stat().st_size
    body = urllib.parse.urlencode({"migration_type": "common_cartridge_importer",
                                   "pre_attachment[name]": cc.name, "pre_attachment[size]": str(size)}).encode()
    mig = _canvas("POST", f"{base}/api/v1/courses/{course_id}/content_migrations", token, body, "application/x-www-form-urlencoded")
    pre = mig.get("pre_attachment") or {}
    upload_url, params = pre.get("upload_url"), pre.get("upload_params") or {}
    if not upload_url:
        report["canvas_import"] = {"ran": False, "reason": f"no upload_url in response: {mig}"}
        return
    boundary = "----lessonrelease" + str(int(time.time()))
    parts = []
    for k, v in params.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{cc.name}\"\r\n"
                 f"Content-Type: application/zip\r\n\r\n".encode() + cc.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(upload_url, data=b"".join(parts), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    urllib.request.urlopen(req, timeout=300).read()
    mid = mig["id"]
    state = "queued"
    for _ in range(60):
        time.sleep(5)
        m = _canvas("GET", f"{base}/api/v1/courses/{course_id}/content_migrations/{mid}", token)
        state = m.get("workflow_state", state)
        if state in {"completed", "failed"}:
            break
    quizzes = _canvas("GET", f"{base}/api/v1/courses/{course_id}/quizzes?per_page=100", token)
    pages = _canvas("GET", f"{base}/api/v1/courses/{course_id}/pages?per_page=100", token)
    report["canvas_import"] = {"ran": True, "migration_id": mid, "workflow_state": state,
                               "quizzes_in_course": len(quizzes) if isinstance(quizzes, list) else None,
                               "pages_in_course": len(pages) if isinstance(pages, list) else None,
                               "pass": state == "completed"}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("package", type=Path)
    ap.add_argument("--dpi", type=int, default=50)
    ap.add_argument("--canvas-course-id")
    a = ap.parse_args(argv)
    out = a.package / "qa_visual"
    out.mkdir(parents=True, exist_ok=True)
    report: Dict[str, Any] = {"package": str(a.package)}
    structural(a.package, report)
    render(a.package, out, a.dpi, report)
    if a.canvas_course_id:
        canvas_import(a.package, a.canvas_course_id, report)
    else:
        report["canvas_import"] = {"ran": False, "reason": "no --canvas-course-id given"}
    report["visual_gate_ready"] = bool(report.get("render", {}).get("ran"))
    report["structural_pass"] = (report["validate_unified_package"]["exit"] == 0 and report["cartridge"]["pass"]
                                 and report["slide_count_matches_manifest"])
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("release_status", "slide_count", "structural_pass", "visual_gate_ready",
                                             "possible_text_overflow", "render", "canvas_import")}, indent=2))
    return 0 if report["structural_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

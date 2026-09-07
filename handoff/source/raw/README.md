# Raw chapter text (fallback source path)

The daily next-chapter Routine prefers to fetch each Open RN chapter live from
NCBI Bookshelf / Pressbooks and verify its CC BY 4.0 license from the page itself.
When the build environment's network policy blocks those hosts, the Routine
falls back to this directory. If neither is available it stops with zero commits.

To supply a chapter by hand, create `handoff/source/raw/ch<N>/` containing:

- `chapter.md` (or `chapter.txt`) — the chapter body text you fetched. Body
  sections only; leave out CC BY-NC learning activities, case studies, and
  H5P/ADAPT items (see SRC01's `license_register` for the pattern).
- `SOURCE.json`:

```json
{
  "chapter": 5,
  "url": "https://www.ncbi.nlm.nih.gov/books/NBK6153xx/",
  "pressbooks": "https://wtcs.pressbooks.pub/healthpromo/chapter/5-1-introduction/",
  "license": "CC BY 4.0",
  "license_evidence": "footer text you saw, quoted",
  "fetched_by": "Your Name",
  "fetched_on": "2026-09-07",
  "exceptions": ["4.9-style case study is CC BY-NC 4.0 — omitted", "..."]
}
```

The Routine records the resulting source index with
`license_verified.method = "human attestation"` and names `fetched_by` — it never
claims to have verified a license it could not fetch. Nothing in this directory
is ever copied verbatim into a lesson; the index stores paraphrased facts.

## Egress reality in this environment (measured 2026-09-07)

The proxy is **deny-all with a small allowlist**, not a targeted block of the
publishers. Verified with curl and WebFetch:

| Host | Result |
|---|---|
| `www.ncbi.nlm.nih.gov`, `wtcs.pressbooks.pub`, `ftp.ncbi.nlm.nih.gov` | blocked (403 at CONNECT) |
| `openstax.org`, `en.wikipedia.org`, `example.com` | blocked |
| `raw.githubusercontent.com`, PyPI/npm registries | reachable |

So the live-fetch path (Path A) cannot succeed here for *any* publisher, and picking
a different textbook will not help. Do not spend a run re-probing these hosts. Path A
stays in the Routine only because the allowlist may be widened later.

## The working route: commit the book PDF to this repository

GitHub is reachable and has no 10 MB cap (the Google Drive connector does — the
77 MB whole-book PDF cannot be pulled through it, and its text extraction returns
empty). So the whole book goes in the repo once, and every remaining chapter is
then extractable here with no further downloads:

1. Commit the NCBI whole-book PDF (`https://www.ncbi.nlm.nih.gov/books/n/openrnnhp/pdf/`)
   to `handoff/source/raw/book/openrn_nhp.pdf`. GitHub's web UI upload works; the file
   is ~77 MB, under GitHub's 100 MB per-file limit.
2. Add `handoff/source/raw/book/SOURCE.json` with `url`, `license`, `license_evidence`,
   `fetched_by`, `fetched_on`, and any `exceptions` (Open RN mixes CC BY-NC case
   studies and CC BY-SA figures into CC BY 4.0 chapters — see SRC01's
   `license_register`).
3. Per chapter, run the extractor (its heuristic boundary detection is why `--list`
   exists — eyeball it before trusting the output):

```bash
python3 -m venv .pdfenv && .pdfenv/bin/pip install pypdf   # system cryptography is broken
S=skills/harrity-lesson-builder-pipeline/scripts/extract_chapter_text.py
.pdfenv/bin/python $S --pdf handoff/source/raw/book/openrn_nhp.pdf --list
.pdfenv/bin/python $S --pdf handoff/source/raw/book/openrn_nhp.pdf --chapter 5
```

That writes `handoff/source/raw/ch5/chapter.md`. Copy the book-level `SOURCE.json`
into `ch5/` (adjusting `url` to the chapter's own page) and the daily Routine's
Path B builds the lesson on its next firing.

## Per-chapter files (also fine)

A single chapter's PDF or text dropped in as `handoff/source/raw/ch<N>/chapter.md`
plus `SOURCE.json` works too, and skips the extractor entirely. The required
`SOURCE.json` shape:

```json
{
  "chapter": 5,
  "url": "https://www.ncbi.nlm.nih.gov/books/NBK6153xx/",
  "license": "CC BY 4.0",
  "license_evidence": "footer text you saw, quoted",
  "fetched_by": "Your Name",
  "fetched_on": "2026-09-07",
  "exceptions": ["case study is CC BY-NC 4.0 - omitted", "..."]
}
```

The Routine records these as `license_verified.method = "human attestation"` naming
`fetched_by`; it never claims to have verified a page it could not reach. Nothing in
this directory is copied verbatim into a lesson — the source index stores paraphrase.


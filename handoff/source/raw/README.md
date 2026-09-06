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

## Supplying chapters via Google Drive (the practical route)

The build environment's egress proxy blocks NCBI, Pressbooks, LibreTexts, OpenStax and
the Wayback Machine (verified 2026-09-06 with curl and WebFetch: policy 403). Google Drive
is the only channel in, and its connector enforces a **10 MB per-file download cap** — the
whole-book PDF (`Bookshelf_NBK615319.pdf`, 77.6 MB) cannot be pulled, and its text
extraction returns empty.

What works: **per-chapter PDFs**. On each chapter page at
`https://www.ncbi.nlm.nih.gov/books/NBK615319/` NCBI offers a "PDF" link (top right);
those files are typically under 1 MB. Drop them in the Drive `sources` folder
(`1hFywSA2NleioUVUY25Ll9B4bQ3lVvzKP`). A Claude session with the Drive connector then
runs `pdftotext -layout`, writes `handoff/source/raw/ch<N>/chapter.md` and a `SOURCE.json`
naming the person who downloaded it as `fetched_by`, and commits — after which the daily
Routine's fallback path (Path B) builds the lesson with no further input.

`www.googleapis.com` is reachable from the container but `drive.google.com` is not; a
direct REST download would need an OAuth token or API key the session does not hold.

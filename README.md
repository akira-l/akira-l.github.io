# akira-l.github.io

Personal academic website for Yuanzhi Liang (梁远智), with bilingual
publication pages, source-checked paper summaries, and downloadable citations.

## Publication workflow

`data/publications.json` is the single source of truth for all publication
metadata and English/Chinese explanatory text. Its contract is documented by
`data/publications.schema.json`.

```powershell
python _rebuild.py
python _rebuild.py --check
```

The build uses only Python's standard library and generates:

- `/publications/` and 23 English research records;
- `/zh/publications/` and 23 Chinese research records;
- per-paper BibTeX, RIS, and CSL-JSON;
- bibliographic catalogs, update feeds, a sitemap, and discovery files; and
- `AUTHOR_REVIEW.md` and the record-by-record `CITATION_AUDIT.md`.

It also renders two connected editorial layers:

- English Research Notes from `data/research-notes.json`;
- a bilingual Research hub and Research Paths from
  `data/research-paths.json`.

The site exposes one top-level `Research` navigation item immediately after
`Publications`. Research Paths, Research Notes, and the full publication catalog
are separated inside that hub rather than competing for space on the homepage.
Generated content pages keep the top level to Biography, Publications, and
Research; the former Highlights shortcut is intentionally omitted as redundant.

Both contracts reference papers only by `paper_slug`. Titles, authors, venue,
year, abstracts, paper links, and citations always come from
`data/publications.json`; the editorial data must not maintain a second copy.
The contracts are documented in `data/research-notes.schema.json` and
`data/research-paths.schema.json`. A path relationship uses one of five roles:
`foundation`, `core`, `bridge`, `framing`, or `horizon`, together with visible
bilingual prose explaining why the paper belongs there.

The Research hub also contains a visible, bilingual research thesis. It treats
data and model scaling as a powerful driver of generalization while distinguishing
offline learning from continual learning through interaction. One arc moves from
fixed datasets to feedback-driven learning; a second separates reward-based
post-training from experience collected through actions in digital or physical
environments. These records contain only `paper_slug`
references and visible narrative; publication metadata continues to be joined
from `data/publications.json`. The same arc, horizon, methodology, and adjacent
work records are emitted in `/research/paths.json` when the hub is approved.

Tracked source files contain only author-approved `published` records. Local
`ready_for_review` material lives in ignored `.review/` files and is merged
only into an isolated preview:

```powershell
python _rebuild.py --preview
python -m http.server 8001 --directory .preview-site
```

The default build never reads `.review/`. It excludes pending titles, prose,
URLs, structured data, and relationships from public HTML, JSON, sitemap,
feed, `llms*`, and the IndexNow payload. Direct pending Note and Path URLs are
absent from the public filesystem. Preview pages are marked `noindex,nofollow`.

Do not promote a Note, Path, or homepage/Research-hub record merely because
automated checks pass. Complete `RESEARCH_NOTES_REVIEW.md` or
`RESEARCH_PATHS_REVIEW.md`, obtain the required author approval, copy only the
approved record from `.review/` into its tracked data file, set `status` to
`published`, add the real `published_on` date, and rebuild. English and Chinese
Path content is approved as a pair.

Do not hand-edit generated publication HTML or citation files; the next build
will replace them.

For a public-build check, serve the repository over HTTP instead of opening
`index.html` through `file://`:

```powershell
python -m http.server 8000
```

Then open `http://127.0.0.1:8000/`. Use the separate port and directory shown
above for the review preview. Clean directory URLs such as
`/publications/food-ingredient/` are resolved by GitHub Pages and an HTTP
server, but not by the browser's local-file URL resolver. Homepage paper
overview links use their canonical `https://akira-l.github.io/` URLs so they
also work when the homepage is opened directly as a local file.

For convenience, generated HTML also loads `dist/js/file-preview.js`. It is
inactive over HTTP/HTTPS. When `index.html` is opened through `file://`, it
adds the explicit `index.html` resolution browsers need and routes Research or
Research Notes links into the ignored `.preview-site/` review build. Generate
that preview first; HTTP remains the authoritative way to review the site.

## Accuracy and author verification

Every scientific statement in a record must be supported by the named primary
paper version. Keep the official English abstract exact, distinguish arXiv
first-posted/revised dates from final venue metadata, and do not copy numerical
claims unless the data record also identifies their table or figure.

All 23 current publication records were author-verified on 2026-07-31. For
future additions or material metadata/content changes, review the affected
items in `AUTHOR_REVIEW.md` before setting a record to:

```json
{
  "verification_status": "author-verified",
  "author_verified_on": "YYYY-MM-DD"
}
```

Then rerun the build and inspect the generated English and Chinese pages.

Published citation exports represent the version of record and deliberately do
not mix in related arXiv metadata. Forthcoming conference records cite arXiv
until a final DOI and pagination are public. Run both validation suites after
any bibliographic edit:

```powershell
python tests/validate_site.py
python tests/validate_citations.py
python tests/validate_research_notes.py
python tests/validate_research_paths.py
node tests/validate_file_preview.js
```

## Content rights

Original site commentary is CC BY 4.0. Paper abstracts, figures, titles, and
bibliographic material are expressly excluded and retain their original rights.
See `LICENSE-CONTENT.md`.

## Site maintenance

Generated output, publication data, and citation exports are checked on every
pull request and push by `.github/workflows/site-checks.yml`. Keep visible copy,
structured metadata, and source records consistent; do not add hidden text or
crawler-only scientific claims.

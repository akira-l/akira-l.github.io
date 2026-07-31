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

Do not hand-edit generated publication HTML or citation files; the next build
will replace them.

For local preview, serve the repository over HTTP instead of opening
`index.html` through `file://`:

```powershell
python -m http.server 8000
```

Then open `http://127.0.0.1:8000/`. Clean directory URLs such as
`/publications/food-ingredient/` are resolved by GitHub Pages and an HTTP
server, but not by the browser's local-file URL resolver. Homepage paper
overview links use their canonical `https://akira-l.github.io/` URLs so they
also work when the homepage is opened directly as a local file.

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

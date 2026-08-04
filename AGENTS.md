# Codex workspace rules

Before changing this repository, read these files in full:

1. `README.md` — build workflow and the publication data contract.
2. `CODEX_HANDOFF.md` — current baseline, Research Notes scope, validation, and review state.
3. `LICENSE-CONTENT.md` — what site commentary may license and what remains third-party material.

## Working boundaries

- `data/publications.json` is the only maintained source of publication metadata. Research Notes and Research Paths reference a publication by `paper_slug`; do not copy author lists, venue data, abstracts, paper URLs, or citation records into editorial data.
- Tracked `data/research-notes.json` and `data/research-paths.json` contain only approved public records. Ignored `.review/` holds `ready_for_review` source; `python _rebuild.py --preview` is the only build that may merge it into ignored `.preview-site/`.
- `_rebuild.py` owns generated HTML, citation exports, feeds, sitemaps, discovery files, and generated audits. Edit the source data or generator, never generated files by hand.
- `C:\Users\liang\Documents\pr_draft` is a read-only factual source for this repository. Do not edit its PDFs, DOCX files, Chinese platform drafts, assets, or content-library records. The only authorized cross-repository edit in the migration was the short pointer in its `CODEX_HANDOFF.md`.
- Keep every new Research Note, bilingual Research Path, and Research hub/homepage block at `ready_for_review` until Yuanzhi Liang has reviewed that item. A Path's English and Chinese content are approved together. Do not describe a draft as published, author-verified, or publicly available.
- Do not commit, push, deploy, or otherwise publish changes unless the user explicitly asks after review. Never infer publication approval from a passing build.
- Do not create X, LinkedIn, or other platform copy in the Research Notes phase.
- Do not reproduce paper figures or tables on the site without a separate rights and attribution review. Use prose descriptions and evidence locators instead.
- Preserve a coauthor's voice accurately: `we` may describe the paper's contribution, but do not imply sole or lead authorship and do not invent personal anecdotes.
- Older work must use an explicit retrospective frame. Explain what the paper established, what still holds up, and what hindsight changes; do not present a 2019–2024 paper as new.

## Required checks

Run these from the repository root after any relevant change:

```powershell
python _rebuild.py --check
python tests/validate_site.py
python tests/validate_citations.py
python tests/validate_research_notes.py
python tests/validate_research_paths.py
```

For local review, run `python _rebuild.py --preview`, serve `.preview-site/` over HTTP, inspect desktop and narrow mobile widths, and stop the server when finished. Passing automated checks does not replace the per-note checklist in `RESEARCH_NOTES_REVIEW.md` or the bilingual path checklist in `RESEARCH_PATHS_REVIEW.md`.

# Codex handoff: Research Notes and Research Paths

## Current baseline

- Repository: `C:\Users\liang\Documents\code\akira-l.github.io`
- Pre-publication comparison point: `master` at commit `687fde4`
- Date verified: 2026-08-04
- Canonical corpus: 23 author-verified bilingual publication records
- Yuanzhi Liang approved the Research hub/homepage copy, all three bilingual
  Research Paths, and all 13 Research Notes for publication on 2026-08-04.
- The approved records are tracked public data. `.review/` is empty and remains
  reserved for future `ready_for_review` work.

`C:\Users\liang\Documents\pr_draft` remains read-only and was not modified.
No X, LinkedIn, or other platform copy was created, and no paper figure or table
was reused.

## Implementation status

The approved Research organization and discoverability plan is implemented in
the public build, with the same generator retaining an isolated review workflow
for future drafts.

### Public/review separation

- Tracked `data/research-notes.json` contains 13 approved `published` Notes.
- Tracked `data/research-paths.json` contains the approved `published` Research
  hub and three approved bilingual Paths.
- Ignored `.review/research-notes.json` and `.review/research-paths.json` are
  empty review sources.
- `python _rebuild.py --preview` merges public and review records into ignored
  `.preview-site/`. The default build never reads `.review/`.
- `dist/js/file-preview.js` is inert on HTTP/HTTPS but makes direct `file://`
  clicks resolve `index.html` and routes Research/Research Notes into the local
  `.preview-site/`, avoiding browser directory listings during author review.
- Public builds include only approved Note and Path records. Any future pending
  title, summary, body, direct detail URL, structured claim, sitemap/feed entry,
  `llms*` entry, or IndexNow URL remains isolated from the public build.

### Research information architecture

The public site contains:

- `/research/` and `/zh/research/`;
- `/research/video-generation-world-models/` and its Chinese counterpart;
- `/research/trustworthy-visual-post-training/` and its Chinese counterpart;
- `/research/semantic-motion-embodied-interaction/` and its Chinese counterpart.

The homepage keeps the research profile and long-term goal inside About without
duplicating the three Path cards. Its top navigation has one `Research` item,
immediately after `Publications`; the separate `Research Notes` item was
removed. The Research hub now states a longer research thesis: scaling data and
model capacity is a powerful driver of generalization, but offline learning
remains bounded by data collected before deployment. Its first arc moves from
fixed datasets to feedback-driven learning; its second moves from post-training
to learning through interaction. Visual representations, task-relevant semantics,
dynamic scene state, and reward-based adaptation are presented as distinct
research questions rather than stages of one architecture. The hub then presents
digital and physical environments as two settings for continual interactive learning
before introducing the three Research Paths. The shared “Beyond proxy metrics” /
“不把代理指标当成真实能力” thread
remains visible. Rain One Go and Food-Ingredient remain visible as earlier and
adjacent work rather than being forced into a main Path.

Each Path uses the same visible structure: core question, research evolution,
paper relationships, boundaries that should not be collapsed, and open
questions. Relationship roles are limited to `foundation`, `core`, `bridge`,
`framing`, and `horizon`; every relation has visible English and Chinese prose.
Publication metadata continues to come only from `data/publications.json`.

The revised Path openings are intentionally framed as research interests rather
than inventories of techniques. The video path distinguishes temporally coherent
generation from action-conditioned world modeling. The post-training path studies
reward validity, uncertainty, and spatial or temporal credit assignment without
equating reward optimization with environment interaction. The semantic-motion
path studies semantic alignment, action-conditioned affordance, multi-entity
coordination, and execution verification. Their common long-term connection is
stated as a causal action–observation–update loop rather than as a list of
unrelated technical concepts.

The Research hub, Paths, publication collection, bilingual publication pages,
Research Notes collection, and Note pages link to one another where applicable.
`/research/paths.json`, `publications/records.json`, and each paper `record.json`
derive `research_paths` from the same source contract. CSL, BibTeX, and RIS are
unchanged.

### Protected Research Notes

The 13 Notes were approved after title, dek, retrospective framing, and section
heading review. Their approved editorial fields, body sections, evidence
locators, and keywords are guarded by exact per-record SHA-256 fingerprints in
`tests/validate_research_notes.py`.

Strict body word counts remain:

```text
teleboost=1100, bpgo=1105, taros=1112, vipo=1131, otca=1100,
uni-inter=1113, mhem=1100, anteval=1101, icocap=1100, maal=1100,
seeg=1100, elp=1114, vrr-vg=1130
```

Visible English Path word counts are 833, 863, and 768 respectively. The preview
`/research/paths.json` also exposes the same visible four-question arc and two
learning environments. The Research hub and Chinese pages carry equivalent visible
information rather than hidden or crawler-only text.

The visual-generative-model RL survey remains available in the complete
publication catalog, but it is intentionally absent from the four-stage personal
research arc, the homepage `Recent Work` list, and all three Path membership
lists. Primary research papers, especially ELP, VrR-VG, SEEG, and Uni-Inter,
carry the central narrative.

## Build and validation

Generate the isolated author-review site first, then check the public build:

```powershell
python _rebuild.py --preview
python _rebuild.py --check
python tests/validate_site.py
python tests/validate_citations.py
python tests/validate_research_notes.py
python tests/validate_research_paths.py
node tests/validate_file_preview.js
python _notify_updates.py --dry-run
```

Latest public-build results:

```text
Generated 173 files from 23 publication records, 13 published Research Notes, and 3 published Research Paths.
Checked 173 files from 23 publication records, 13 published Research Notes, and 3 published Research Paths.
Validated 23 bilingual research records, 71 HTML files, discovery feeds, citations, and internal links.
Validated 23 records across 69 BibTeX/RIS/CSL citation artifacts.
Validated 13 published and 0 review-only Research Notes with public/preview isolation and protected content.
Validated 3 published and 0 review-only bilingual Research Paths, relationship data, reciprocal links, and public isolation.
```

Local HTTP review covered the revised English and Chinese Research hubs and all
three bilingual Paths, including prior checks at 1440×900 and 390×844. The
four-question arc, digital/physical horizon cards, three Path cards, bilingual
labels, and return links were checked
in the rendered preview. No document-level horizontal overflow or browser
console error was found. The temporary server was stopped.

## Review and approval boundary

- `RESEARCH_NOTES_REVIEW.md` records approval of all 13 Notes.
- `RESEARCH_PATHS_REVIEW.md` records approval of the Research hub/homepage pair
  and all three bilingual Path pairs.
- Future Notes may still be promoted independently. Future Paths require both
  languages, and a future homepage/Research-hub revision remains one approval unit.
- A passing build alone is not approval; future drafts stay in `.review/` until
  Yuanzhi Liang explicitly approves them.

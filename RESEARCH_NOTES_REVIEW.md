# Research Notes author-review checklist

Automated checks establish structural consistency; they do not approve the
scientific interpretation or the author's voice. All 13 Notes below were
reviewed locally and approved by Yuanzhi Liang on 2026-08-04 before promotion
from `.review/research-notes.json` into the tracked public data.

## Per-note review

- [x] The note maps to the intended paper and does not duplicate title,
  authors, venue, year, links, abstract, or citation metadata.
- [x] The first two paragraphs state the concrete problem and the paper's
  concise answer without implying sole or lead authorship.
- [x] Method names and acronyms are expanded correctly on first use.
- [x] Every numerical claim and central method claim has been checked against
  the primary paper version named in the publication record.
- [x] Each evidence-map locator resolves to the stated page, section, figure,
  or table; reported results are distinguished from interpretation.
- [x] The note explains the nearest related approaches, the experimental
  scope, and at least one material limitation without inventing motivation or
  anecdote.
- [x] Work from 2019–2024 is explicitly framed as a retrospective and says
  what still holds up in hindsight. Online-first and volume years are not
  conflated.
- [x] The visible body is 1,100–1,500 English words and reads naturally for a
  junior researcher without removing details useful to a specialist.
- [x] The canonical URL, paper-record link, BibTeX, RIS, and CSL-JSON links are
  correct, and the corresponding publication page links back to the note.
- [x] The page has been reviewed at desktop and narrow mobile widths over a
  local HTTP server; headings, tables, navigation, long titles, and citations
  do not overflow.
- [x] The article title, dek, structured data, and visible copy describe the
  same work. No hidden, crawler-only, or keyword-stuffed scientific claim is
  present.
- [x] The author has explicitly approved publication and supplied the real
  publication date before `status` is changed to `published`.

## Current 13-note queue

| Paper | Status | Scientific review | Voice/title review | Mobile review | Publish approval |
| --- | --- | --- | --- | --- | --- |
| TeleBoost | `published` | [x] | [x] | [x] | [x] |
| ViPO | `published` | [x] | [x] | [x] | [x] |
| BPGO | `published` | [x] | [x] | [x] | [x] |
| OTCA | `published` | [x] | [x] | [x] | [x] |
| TaRoS | `published` | [x] | [x] | [x] | [x] |
| Uni-Inter | `published` | [x] | [x] | [x] | [x] |
| AntEval | `published` | [x] | [x] | [x] | [x] |
| MAAL | `published` | [x] | [x] | [x] | [x] |
| IcoCap | `published` | [x] | [x] | [x] | [x] |
| ELP | `published` | [x] | [x] | [x] | [x] |
| SEEG | `published` | [x] | [x] | [x] | [x] |
| MHEM | `published` | [x] | [x] | [x] | [x] |
| VrR-VG | `published` | [x] | [x] | [x] | [x] |

The approved Notes are tracked in `data/research-notes.json`; the review source
is empty. The public build and validation suite confirm that every Note appears
exactly once in `sitemap.xml`, `feed.xml`, `llms.txt`, `llms-full.txt`, and the
IndexNow dry-run payload.

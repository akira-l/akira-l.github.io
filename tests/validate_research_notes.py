#!/usr/bin/env python3
"""Validate public/review Research Notes without exposing review-only content."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import _rebuild  # noqa: E402
import _notify_updates  # noqa: E402
from tests.validate_site import graph_types, parse_page  # noqa: E402


EXPECTED_SLUGS = {
    "teleboost", "vipo", "bpgo", "otca", "taros", "uni-inter",
    "anteval", "maal", "icocap", "elp", "seeg", "mhem", "vrr-vg",
}
PROTECTED_KEYS = (
    "title", "dek", "retrospective", "retrospective_context", "keywords",
    "lede", "takeaway", "sections", "evidence",
)
EXPECTED_FINGERPRINTS = {
    "vipo": "eefbb4fba65211bd39f975970ba45f8db0c2f57b6e37814b300fc94daa9c568e",
    "bpgo": "2c794edb297392184e68858a57ec67b98abb73cca21aeb0e0ae8e8c879bedb8c",
    "teleboost": "23f8e2bea992ed52ef7b879d6540bfce6cc86c787f2b0a48cda0074c96b30096",
    "otca": "48fb55a370bf8e2a5c9b82e49f5f7c803226a00d3fbc2c1ec24bd7dc7d632501",
    "taros": "ea11dd327049dd2ff92cd0bf638445ef54b6c95bdb16c51bd8ab350dfbc6c17a",
    "uni-inter": "9c6658c16549f56994a046a7bf8f443ec3d6fee2d43e9250b6b2da51a0065591",
    "anteval": "d26ffd21409116a1d1365875bfde5a5a4c938faadb8a0387d1258dc4f82620e0",
    "maal": "e2b8a71b4282eaac9d18821d6edf70a1d4e113cddac6e1944a3557c2f1e63837",
    "icocap": "103c0e54b60a36d922ae4825ecdb0019a0fdb337df8632ce6d24ff2c980cb7c2",
    "elp": "efb353369cb10e6114832c4b2de8ded74c0e87ed89e3f566da010124f25e8980",
    "seeg": "32b0bf7948636944aa9d3ee9c8dcd503e51bdf9aa824a79356846cbf28e8d1d4",
    "mhem": "05b4f1846df861883c64b1d744575196a5e562963b122069c5f1678c91364b23",
    "vrr-vg": "aa6945cef99f907149325fa6887bbc73a8c3a1295e7ecfdddb3f12412081035f",
}


def fingerprint(note: dict) -> str:
    protected = {key: note[key] for key in PROTECTED_KEYS}
    payload = json.dumps(
        protected, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_note_page(
    note: dict,
    paper: dict,
    root: Path,
    expected_robots: str,
    errors: list[str],
) -> None:
    slug = note["paper_slug"]
    path = root / "research-notes" / slug / "index.html"
    if not path.exists():
        errors.append(f"{path}: generated Note page is missing")
        return
    _text, page = parse_page(path)
    if "data-local-file-preview" not in _text:
        errors.append(f"{path}: missing file-safe local navigation helper")
    relative = path.relative_to(root).as_posix()
    if " ".join(page.h1) != note["title"]:
        errors.append(f"{relative}: H1 does not match source title")
    canonical = [link.get("href") for link in page.links if link.get("rel") == "canonical"]
    if canonical != [_rebuild.research_note_url(note)]:
        errors.append(f"{relative}: canonical mismatch {canonical}")
    if page.meta_values("robots") != [expected_robots]:
        errors.append(f"{relative}: robots policy mismatch")
    types = set().union(*(graph_types(document) for document in page.jsonld))
    if not {"TechArticle", "ScholarlyArticle", "BreadcrumbList"} <= types:
        errors.append(f"{relative}: incomplete structured entities {sorted(types)}")
    links = {link.get("href", "") for link in page.links}
    required = {
        f"/publications/{slug}/",
        f"/publications/{slug}/citation.bib",
        f"/publications/{slug}/citation.ris",
        f"/publications/{slug}/citation.json",
    }
    if missing := required - links:
        errors.append(f"{relative}: missing paper/citation links {sorted(missing)}")
    if paper["title"] not in " ".join(page.body_text):
        errors.append(f"{relative}: canonical paper title is not visible")
    visible_text = " ".join(page.body_text)
    paper_authors = ", ".join(paper["authors"])
    if paper_authors not in visible_text:
        errors.append(f"{relative}: full paper author list is not visible")
    if paper["en"]["citation_ready"] not in visible_text:
        errors.append(f"{relative}: related-work summary is not visible")
    if paper["en"]["limitations"] not in visible_text:
        errors.append(f"{relative}: paper scope statement is not visible")
    required_sections = {
        "overview": "Overview",
        "in-one-sentence": "In one sentence",
        "related-work-summary": "Related-work summary",
        "evidence-map": "Evidence map",
        "cite-paper": "Cite the paper",
    }
    for section_id, label in required_sections.items():
        if f'id="{section_id}"' not in _text:
            errors.append(f"{relative}: missing stable section id #{section_id}")
        if f'href="#{section_id}"' not in _text or label not in visible_text:
            errors.append(f"{relative}: table of contents does not expose {label}")
    for index, section in enumerate(note["sections"], 1):
        section_id = _rebuild.slugify_key(section["heading"]) or f"section-{index}"
        if f'id="{section_id}"' not in _text or f'href="#{section_id}"' not in _text:
            errors.append(f"{relative}: Note section is not addressable: {section['heading']}")
    graph = next((item.get("@graph", []) for item in page.jsonld if "@graph" in item), [])
    tech_article = next(
        (item for item in graph if item.get("@type") == "TechArticle"), None
    )
    scholarly = next(
        (item for item in graph if item.get("@type") == "ScholarlyArticle"), None
    )
    paper_entity_id = f"{_rebuild.BASE_URL}/publications/{slug}/#paper"
    if not tech_article or tech_article.get("citation") != {"@id": paper_entity_id}:
        errors.append(f"{relative}: Note citation does not resolve to the paper entity")
    if not scholarly or scholarly.get("@id") != paper_entity_id:
        errors.append(f"{relative}: full scholarly paper entity is missing")
    if scholarly and {"abstract", "identifier", "sameAs"} & scholarly.keys():
        errors.append(
            f"{relative}: scholarly entity contains fields not presented on the Note page"
        )
    if "SEO" in visible_text or "GEO optimization" in visible_text:
        errors.append(f"{relative}: internal discovery terminology is visible to readers")
    if "author review pending" in visible_text.lower():
        errors.append(f"{relative}: internal review status is visible to readers")
    if "Retrospective note." in visible_text:
        errors.append(f"{relative}: editorial retrospective label is visible to readers")


def main() -> int:
    errors: list[str] = []
    papers = _rebuild.validate_data(
        json.loads((ROOT / "data" / "publications.json").read_text(encoding="utf-8"))
    )
    papers_by_slug = {paper["slug"]: paper for paper in papers}
    public_data = json.loads(
        (ROOT / "data" / "research-notes.json").read_text(encoding="utf-8")
    )
    try:
        public_notes = _rebuild.validate_research_notes(
            public_data, papers_by_slug, allowed_statuses={"published"}
        )
    except ValueError as exc:
        print(f"Public Research Note validation failed: {exc}", file=sys.stderr)
        return 1

    public_path_data = json.loads(
        (ROOT / "data" / "research-paths.json").read_text(encoding="utf-8")
    )
    public_hub, public_paths = _rebuild.validate_research_paths(
        public_path_data, papers_by_slug, allowed_statuses={"published"}
    )
    generated_public = _rebuild.build_outputs(
        papers,
        public_notes,
        public_hub,
        public_paths,
        homepage_source=(ROOT / "index.html").read_text(encoding="utf-8"),
    )
    public_output_blob = "\n".join(generated_public.values())
    public_collection_path = Path("research-notes/index.html")
    if public_notes and public_collection_path not in generated_public:
        errors.append("published Notes are missing their public collection page")
    if not public_notes and public_collection_path in generated_public:
        errors.append("empty Research Notes collection would be emitted publicly")
    if not public_notes:
        for hub_path in (Path("research/index.html"), Path("zh/research/index.html")):
            if 'href="/research-notes/"' in generated_public[hub_path]:
                errors.append(f"{hub_path}: empty Research Notes collection is linked publicly")
    notification_urls = set(_notify_updates.sitemap_urls())

    public_discovery = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("sitemap.xml", "feed.xml", "llms.txt", "llms-full.txt")
    )
    for note in public_notes:
        validate_note_page(
            note,
            papers_by_slug[note["paper_slug"]],
            ROOT,
            "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1",
            errors,
        )
        if _rebuild.research_note_url(note) not in public_discovery:
            errors.append(f"{note['paper_slug']}: published Note missing from discovery outputs")
        if _rebuild.research_note_url(note) not in notification_urls:
            errors.append(f"{note['paper_slug']}: published Note missing from IndexNow payload")

    review_path = ROOT / ".review" / "research-notes.json"
    review_notes: list[dict] = []
    if review_path.exists():
        review_data = json.loads(review_path.read_text(encoding="utf-8"))
        try:
            review_notes = _rebuild.validate_research_notes(
                review_data, papers_by_slug, allowed_statuses={"ready_for_review"}
            )
            notes = _rebuild.validate_research_notes(
                {
                    "schema_version": 1,
                    "notes": _rebuild.merge_unique_records(
                        public_notes, review_notes, "paper_slug", "Research Note"
                    ),
                },
                papers_by_slug,
                expected_count=13,
            )
        except ValueError as exc:
            print(f"Review Research Note validation failed: {exc}", file=sys.stderr)
            return 1
        if {note["paper_slug"] for note in notes} != EXPECTED_SLUGS:
            errors.append("combined public/review Note slugs differ from the protected 13-note set")
        for note in notes:
            if any(str(year) in note["title"] for year in range(1900, 2100)):
                errors.append(f"{note['paper_slug']}: Research Note title foregrounds a year")
            slug = note["paper_slug"]
            if fingerprint(note) != EXPECTED_FINGERPRINTS[slug]:
                errors.append(f"{slug}: protected Note content changed during migration")
            if not 1100 <= _rebuild.note_word_count(note) <= 1500:
                errors.append(f"{slug}: body word count is outside 1100–1500")
        preview_root = ROOT / ".preview-site"
        if not preview_root.exists():
            errors.append(".preview-site is missing; run python _rebuild.py --preview")
        else:
            _collection_text, collection_page = parse_page(
                preview_root / "research-notes" / "index.html"
            )
            collection_visible = " ".join(collection_page.body_text)
            if "author review pending" in collection_visible.lower():
                errors.append("Research Notes collection exposes internal review status")
            if "Retrospective ·" in collection_visible:
                errors.append("Research Notes collection exposes an editorial retrospective label")
        for note in review_notes:
            slug = note["paper_slug"]
            if _rebuild.research_note_url(note) in public_discovery:
                errors.append(f"{slug}: review-only URL leaked into public discovery")
            if _rebuild.research_note_url(note) in notification_urls:
                errors.append(f"{slug}: review-only URL leaked into IndexNow payload")
            public_note_dir = ROOT / "research-notes" / slug
            if public_note_dir.exists():
                errors.append(f"{slug}: review-only Note directory exists in the public build")
            if preview_root.exists():
                validate_note_page(
                    note,
                    papers_by_slug[slug],
                    preview_root,
                    "noindex,nofollow",
                    errors,
                )
                for language_path in (
                    preview_root / "publications" / slug / "index.html",
                    preview_root / "zh" / "publications" / slug / "index.html",
                ):
                    if f'href="/research-notes/{slug}/"' not in language_path.read_text(encoding="utf-8"):
                        errors.append(f"{language_path}: missing preview Note backlink")
        for note in review_notes:
            leaked = [
                value
                for value in (note["title"], note["dek"], _rebuild.research_note_url(note))
                if value in public_output_blob
            ]
            if leaked:
                errors.append(
                    f"{note['paper_slug']}: review-only title, summary, or URL leaked into public outputs"
                )

        # Exercise the eventual approval path without changing review data. Once approved,
        # every Note must become indexable and enter each public discovery surface.
        simulated_published = [
            {**note, "status": "published", "published_on": "2026-08-04"}
            for note in review_notes
        ]
        simulated_outputs = _rebuild.build_outputs(
            papers,
            [*public_notes, *simulated_published],
            public_hub,
            public_paths,
            homepage_source=(ROOT / "index.html").read_text(encoding="utf-8"),
        )
        simulated_collection = simulated_outputs[Path("research-notes/index.html")]
        discovery_outputs = {
            name: simulated_outputs[Path(name)]
            for name in ("sitemap.xml", "feed.xml", "llms.txt", "llms-full.txt")
        }
        for note in simulated_published:
            slug = note["paper_slug"]
            url = _rebuild.research_note_url(note)
            note_html = simulated_outputs[Path("research-notes") / slug / "index.html"]
            if "index,follow,max-snippet:-1" not in note_html:
                errors.append(f"{slug}: approved Note would not become indexable")
            if note["title"] not in simulated_collection:
                errors.append(f"{slug}: approved Note would be missing from the collection")
            for name, content in discovery_outputs.items():
                if url not in content:
                    errors.append(f"{slug}: approved Note would be missing from {name}")
            if note["takeaway"] not in discovery_outputs["llms-full.txt"]:
                errors.append(f"{slug}: approved Note body would be missing from llms-full.txt")

    if errors:
        print(f"{len(errors)} Research Note validation error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    counts = ", ".join(
        f"{note['paper_slug']}={_rebuild.note_word_count(note)}"
        for note in [*public_notes, *review_notes]
    )
    print(
        f"Validated {len(public_notes)} published and {len(review_notes)} review-only "
        "Research Notes with public/preview isolation and protected content."
    )
    if counts:
        print(f"Protected body word counts: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

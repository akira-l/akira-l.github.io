#!/usr/bin/env python3
"""Validate bilingual Research Paths, relationships, and public isolation."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import _rebuild  # noqa: E402
import _notify_updates  # noqa: E402
from tests.validate_site import graph_types, parse_page  # noqa: E402


EXPECTED_PATHS = {
    "video-generation-world-models": {
        "icocap", "vast", "freelong", "teleworld", "teleboost",
        "taros", "otca", "rats", "embodied-brains",
    },
    "trustworthy-visual-post-training": {
        "vrr-vg", "elp", "mhem", "icocap", "vipo",
        "bpgo", "taros", "otca", "rats", "teleboost",
    },
    "semantic-motion-embodied-interaction": {
        "seeg", "maal", "intersyn", "uni-inter", "laxmotion",
        "anteval", "embodied-brains",
    },
}

EXPECTED_ARC = {
    "perceive": {"elp", "mhem"},
    "understand": {"vrr-vg", "seeg", "icocap", "uni-inter"},
    "model-worlds": {"vast", "freelong", "teleworld"},
    "explore": {"vipo", "bpgo", "taros", "otca", "rats", "teleboost"},
}

EXPECTED_HORIZON = {
    "digital-agents": {"anteval"},
    "physical-agents": {"maal", "intersyn", "uni-inter", "embodied-brains"},
}


def validate_path_page(
    path: dict,
    root: Path,
    language: str,
    expected_robots: str,
    errors: list[str],
) -> None:
    prefix = Path() if language == "en" else Path("zh")
    page_path = prefix / "research" / path["slug"] / "index.html"
    absolute = root / page_path
    if not absolute.exists():
        errors.append(f"{absolute}: generated path page is missing")
        return
    text, page = parse_page(absolute)
    if "data-local-file-preview" not in text:
        errors.append(f"{page_path.as_posix()}: missing file-safe local navigation helper")
    local = path[language]
    if " ".join(page.h1) != local["title"]:
        errors.append(f"{page_path.as_posix()}: H1 mismatch")
    if page.meta_values("robots") != [expected_robots]:
        errors.append(f"{page_path.as_posix()}: robots mismatch")
    canonical = [link.get("href") for link in page.links if link.get("rel") == "canonical"]
    if canonical != [_rebuild.research_path_url(path, language)]:
        errors.append(f"{page_path.as_posix()}: canonical mismatch {canonical}")
    types = set().union(*(graph_types(document) for document in page.jsonld))
    if not {"CollectionPage", "ItemList", "ScholarlyArticle", "BreadcrumbList"} <= types:
        errors.append(f"{page_path.as_posix()}: incomplete structured entities {sorted(types)}")
    for member in path["members"]:
        slug = member["paper_slug"]
        expected_link = f"{'/zh' if language == 'zh' else ''}/publications/{slug}/"
        if expected_link not in text:
            errors.append(f"{page_path.as_posix()}: missing paper link {slug}")
        if member[f"{language}_relation"] not in " ".join(page.body_text):
            errors.append(f"{page_path.as_posix()}: relationship text missing for {slug}")
    return_url = f"{'' if language == 'en' else '/zh'}/research/#research-paths"
    if text.count(f'href="{return_url}"') != 2:
        errors.append(
            f"{page_path.as_posix()}: expected persistent and closing Research Path returns"
        )
    return_label = "All Research Paths" if language == "en" else "全部研究路径"
    if return_label not in " ".join(page.body_text):
        errors.append(f"{page_path.as_posix()}: visible Research Path return is missing")


def main() -> int:
    errors: list[str] = []
    papers = _rebuild.validate_data(
        json.loads((ROOT / "data" / "publications.json").read_text(encoding="utf-8"))
    )
    papers_by_slug = {paper["slug"]: paper for paper in papers}
    public_data = json.loads(
        (ROOT / "data" / "research-paths.json").read_text(encoding="utf-8")
    )
    try:
        public_hub, public_paths = _rebuild.validate_research_paths(
            public_data, papers_by_slug, allowed_statuses={"published"}
        )
    except ValueError as exc:
        print(f"Public Research Path validation failed: {exc}", file=sys.stderr)
        return 1

    public_note_data = json.loads(
        (ROOT / "data" / "research-notes.json").read_text(encoding="utf-8")
    )
    public_notes = _rebuild.validate_research_notes(
        public_note_data, papers_by_slug, allowed_statuses={"published"}
    )
    generated_public = _rebuild.build_outputs(
        papers,
        public_notes,
        public_hub,
        public_paths,
        homepage_source=(ROOT / "index.html").read_text(encoding="utf-8"),
    )
    public_output_blob = "\n".join(generated_public.values())
    notification_urls = set(_notify_updates.sitemap_urls())

    public_discovery = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("sitemap.xml", "feed.xml", "llms.txt", "llms-full.txt")
    )
    path_record = json.loads((ROOT / "research" / "paths.json").read_text(encoding="utf-8"))
    if len(path_record.get("paths", [])) != len(public_paths):
        errors.append("research/paths.json public count does not match public source")
    for path in public_paths:
        validate_path_page(
            path,
            ROOT,
            "en",
            "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1",
            errors,
        )
        validate_path_page(
            path,
            ROOT,
            "zh",
            "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1",
            errors,
        )
        if _rebuild.research_path_url(path, "en") not in public_discovery:
            errors.append(f"{path['slug']}: published path missing from discovery")
        for language in ("en", "zh"):
            if _rebuild.research_path_url(path, language) not in notification_urls:
                errors.append(
                    f"{path['slug']}: published {language} path missing from IndexNow payload"
                )
    if public_hub is None:
        for language_path in (ROOT / "research" / "index.html", ROOT / "zh" / "research" / "index.html"):
            _text, page = parse_page(language_path)
            if page.meta_values("robots") != ["noindex,nofollow"]:
                errors.append(f"{language_path}: empty public hub must be noindex,nofollow")
    else:
        for language_path in (ROOT / "research" / "index.html", ROOT / "zh" / "research" / "index.html"):
            _text, page = parse_page(language_path)
            if page.meta_values("robots") != [
                "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
            ]:
                errors.append(f"{language_path}: published hub must be indexable")
        for url in (f"{_rebuild.BASE_URL}/research/", f"{_rebuild.BASE_URL}/zh/research/"):
            if url not in public_discovery:
                errors.append("published Research hub URL is missing from discovery")
            if url not in notification_urls:
                errors.append("published Research hub URL is missing from IndexNow payload")

    review_path = ROOT / ".review" / "research-paths.json"
    review_hub: dict | None = None
    review_paths: list[dict] = []
    hub = public_hub
    paths = public_paths
    if review_path.exists():
        review_data = json.loads(review_path.read_text(encoding="utf-8"))
        try:
            review_hub, review_paths = _rebuild.validate_research_paths(
                review_data, papers_by_slug, allowed_statuses={"ready_for_review"}
            )
            if public_hub and review_hub:
                raise ValueError("hub exists in public and review sources")
            merged = _rebuild.merge_unique_records(
                public_paths, review_paths, "slug", "Research Path"
            )
            hub, paths = _rebuild.validate_research_paths(
                {
                    "schema_version": 1,
                    "hub": public_hub or review_hub,
                    "paths": merged,
                },
                papers_by_slug,
                expected_count=3,
            )
        except ValueError as exc:
            print(f"Review Research Path validation failed: {exc}", file=sys.stderr)
            return 1
        found = {path["slug"]: {member["paper_slug"] for member in path["members"]} for path in paths}
        if found != EXPECTED_PATHS:
            errors.append(f"Research Path membership differs from approved mapping: {found}")
        if [path["slug"] for path in paths] != [
            "video-generation-world-models",
            "trustworthy-visual-post-training",
            "semantic-motion-embodied-interaction",
        ]:
            errors.append("Research Path order does not match the approved homepage priority")
        active_hub = review_hub or public_hub
        if active_hub:
            adjacent = {item["paper_slug"] for item in active_hub["adjacent"]}
            if adjacent != {"rain-one-go", "food-ingredient"}:
                errors.append("Earlier and adjacent work set is incorrect")
            arc = {
                item["key"]: set(item["paper_slugs"])
                for item in active_hub["arc"]
            }
            if arc != EXPECTED_ARC:
                errors.append(f"Longer research arc mapping is incorrect: {arc}")
            horizon = {
                item["key"]: set(item["paper_slugs"])
                for item in active_hub["horizon"]
            }
            if horizon != EXPECTED_HORIZON:
                errors.append(f"Open-world research horizon mapping is incorrect: {horizon}")
            review_text = json.dumps(active_hub, ensure_ascii=False)
            for phrase in (
                "useful structure",
                "carry human meaning",
                "experimental fronts",
                "representation learning, prediction, feedback, and control",
                "producer of experience",
                "what learning signal should update the model",
                "The work expands along two connected dimensions",
                "From visual representation to learning through interaction",
                "My research asks how visual learning systems can move beyond fitting a fixed training distribution",
                "The three paths below study prerequisites for this goal",
            ):
                if phrase in review_text:
                    errors.append(f"Research hub retains an ambiguous conceptual phrase: {phrase}")
            for phrase in (
                "Modern visual models derive much of their breadth from scaling data, model capacity, and computation",
                "learning remains bounded by information collected before deployment",
                "gap between offline generalization and continued adaptation",
                "Post-training lets a model learn from evaluations of its own outputs",
                "close the loop between prediction, action, and observation",
                "requirements for learning from experience, not components of one architecture",
                "The first three themes broaden what a model represents",
                "interaction with an external environment is a separate research setting",
                "persistent digital agents",
                "observed state transitions can become reusable training experience",
            ):
                if phrase not in review_text:
                    errors.append(f"Research hub is missing a required conceptual distinction: {phrase}")

            paths_by_slug = {path["slug"]: path for path in paths}
            if "action-conditioned state transitions" not in json.dumps(
                paths_by_slug["video-generation-world-models"], ensure_ascii=False
            ):
                errors.append("Video Path does not distinguish video generation from action-conditioned world modeling")
            if "does not by itself create an agent" not in json.dumps(
                paths_by_slug["trustworthy-visual-post-training"], ensure_ascii=False
            ):
                errors.append("Post-training Path does not distinguish reward optimization from environment interaction")
            if "context-dependent validity" not in json.dumps(
                paths_by_slug["semantic-motion-embodied-interaction"], ensure_ascii=False
            ):
                errors.append("Interaction Path is missing its common research criterion")
        preview_root = ROOT / ".preview-site"
        if not preview_root.exists():
            errors.append(".preview-site is missing; run python _rebuild.py --preview")
        else:
            for language_path in (
                preview_root / "research" / "index.html",
                preview_root / "zh" / "research" / "index.html",
            ):
                text, page = parse_page(language_path)
                if page.meta_values("robots") != ["noindex,nofollow"]:
                    errors.append(f"{language_path}: review hub must be noindex,nofollow")
                language = "zh" if "zh" in language_path.relative_to(preview_root).parts else "en"
                expected_arc = hub[language]["arc_title"]
                if expected_arc not in text:
                    errors.append(f"{language_path}: longer research arc is missing")
            for path in paths:
                validate_path_page(path, preview_root, "en", "noindex,nofollow", errors)
                validate_path_page(path, preview_root, "zh", "noindex,nofollow", errors)
            for path in review_paths:
                if _rebuild.research_path_url(path, "en") in public_discovery:
                    errors.append(f"{path['slug']}: review path leaked into public discovery")
                for language in ("en", "zh"):
                    if _rebuild.research_path_url(path, language) in notification_urls:
                        errors.append(
                            f"{path['slug']}: review-only {language} URL leaked into IndexNow payload"
                        )
                    prefix = Path() if language == "en" else Path("zh")
                    public_path_dir = ROOT / prefix / "research" / path["slug"]
                    if public_path_dir.exists():
                        errors.append(f"{path['slug']}: review path directory exists in public build")
            preview_record = json.loads(
                (preview_root / "research" / "paths.json").read_text(encoding="utf-8")
            )
            if len(preview_record.get("paths", [])) != 3:
                errors.append("preview research/paths.json does not contain all three paths")
            preview_hub_record = preview_record.get("hub") or {}
            if len(preview_hub_record.get("arc", [])) != 4:
                errors.append("preview research/paths.json does not contain the longer research arc")
            if len(preview_hub_record.get("horizon", [])) != 2:
                errors.append("preview research/paths.json does not contain both open-world horizons")

        for path in review_paths:
            leaked = [
                value
                for value in (
                    path["en"]["title"],
                    path["zh"]["title"],
                    path["en"]["dek"],
                    path["zh"]["dek"],
                    _rebuild.research_path_url(path, "en"),
                    _rebuild.research_path_url(path, "zh"),
                )
                if value in public_output_blob
            ]
            if leaked:
                errors.append(
                    f"{path['slug']}: review-only title, summary, or URL leaked into public outputs"
                )
        if review_hub:
            hub_prose: list[str] = []
            for language in ("en", "zh"):
                hub_prose.extend(
                    [
                        review_hub[language]["dek"],
                        *review_hub[language]["intro"],
                        *review_hub[language]["profile_paragraphs"],
                        review_hub[language]["arc_title"],
                        review_hub[language]["arc_intro"],
                        review_hub[language]["horizon_title"],
                        review_hub[language]["horizon_intro"],
                        review_hub[language]["horizon_closing"],
                    ]
                )
            for item in [
                *review_hub["arc"],
                *review_hub["horizon"],
                *review_hub["methodology"],
            ]:
                hub_prose.extend(
                    [item["en"]["heading"], item["en"]["text"], item["zh"]["heading"], item["zh"]["text"]]
                )
            if any(value in public_output_blob for value in hub_prose):
                errors.append("review-only Research hub prose leaked into public outputs")
            for url in (f"{_rebuild.BASE_URL}/research/", f"{_rebuild.BASE_URL}/zh/research/"):
                if url in notification_urls:
                    errors.append("review-only Research hub URL leaked into IndexNow payload")

        preview_home = (ROOT / ".preview-site" / "index.html").read_text(encoding="utf-8")
        _text, preview_home_page = parse_page(ROOT / ".preview-site" / "index.html")
        if preview_home_page.meta_values("robots") != ["noindex,nofollow"]:
            errors.append("homepage review preview must be noindex,nofollow")
        if "home-research-card" in preview_home:
            errors.append("homepage preview still duplicates Research Path cards")
        if preview_home.count('href="research/"') != 1:
            errors.append("homepage must expose exactly one unified Research navigation link")
        if '>Research Notes</a>' in preview_home:
            errors.append("homepage still exposes a separate Research Notes navigation item")

    prohibited = ("SEO", "GEO optimization", "AI search optimization")
    review_blob = "\n".join(
        json.dumps(item, ensure_ascii=False)
        for item in (public_hub, *public_paths, review_hub, *review_paths)
        if item
    )
    for term in prohibited:
        if term.lower() in review_blob.lower():
            errors.append(f"visible optimization label remains in Research Path content: {term}")

    if errors:
        print(f"{len(errors)} Research Path validation error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    counts = ", ".join(
        f"{path['slug']}={_rebuild.research_path_word_count(path)}" for path in paths
    )
    print(
        f"Validated {len(public_paths)} published and {len(review_paths)} review-only bilingual "
        "Research Paths, relationship data, reciprocal links, and public isolation."
    )
    if counts:
        print(f"Visible English path word counts: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

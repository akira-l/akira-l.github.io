#!/usr/bin/env python3
"""Build the static research-record layer for akira-l.github.io.

The repository intentionally uses only Python's standard library. Publication
metadata and source-checked summaries live in data/publications.json; this
script renders every public HTML and citation artifact deterministically.

Usage:
    python _rebuild.py
    python _rebuild.py --check
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "publications.json"
RESEARCH_NOTES_PATH = ROOT / "data" / "research-notes.json"
RESEARCH_PATHS_PATH = ROOT / "data" / "research-paths.json"
REVIEW_NOTES_PATH = ROOT / ".review" / "research-notes.json"
REVIEW_PATHS_PATH = ROOT / ".review" / "research-paths.json"
PREVIEW_ROOT = ROOT / ".preview-site"
BASE_URL = "https://akira-l.github.io"
PERSON_ID = f"{BASE_URL}/#person"
WEBSITE_ID = f"{BASE_URL}/#website"
CC_BY_URL = "https://creativecommons.org/licenses/by/4.0/"
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def esc(value: Any, quote: bool = True) -> str:
    return html.escape(str(value), quote=quote)


def json_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2).replace("</", "<\\/")


def slugify_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()


def page_url(paper: dict[str, Any], language: str) -> str:
    prefix = "" if language == "en" else "/zh"
    return f"{BASE_URL}{prefix}/publications/{paper['slug']}/"


def research_note_url(note: dict[str, Any]) -> str:
    return f"{BASE_URL}/research-notes/{note['paper_slug']}/"


def local_research_note_path(note: dict[str, Any]) -> Path:
    return Path("research-notes") / note["paper_slug"] / "index.html"


def published_notes(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [note for note in notes if note["status"] == "published"]


def research_path_url(path: dict[str, Any], language: str) -> str:
    prefix = "" if language == "en" else "/zh"
    return f"{BASE_URL}{prefix}/research/{path['slug']}/"


def local_research_path(path: dict[str, Any], language: str) -> Path:
    prefix = Path() if language == "en" else Path("zh")
    return prefix / "research" / path["slug"] / "index.html"


def published_paths(paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [path for path in paths if path["status"] == "published"]


def path_memberships(
    paths: list[dict[str, Any]],
) -> dict[str, list[tuple[dict[str, Any], dict[str, Any]]]]:
    memberships: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for path in sorted(paths, key=lambda item: item["order"]):
        for member in path["members"]:
            memberships[member["paper_slug"]].append((path, member))
    return memberships


def note_word_count(note: dict[str, Any]) -> int:
    text = [*note["lede"], note["takeaway"]]
    for section in note["sections"]:
        text.extend(section["paragraphs"])
    return len(re.findall(r"\b[\w’'-]+\b", " ".join(text), flags=re.UNICODE))


def local_page_path(paper: dict[str, Any], language: str) -> Path:
    prefix = Path() if language == "en" else Path("zh")
    return prefix / "publications" / paper["slug"] / "index.html"


def primary_url(paper: dict[str, Any]) -> str:
    return paper["source"]["url"]


def citation_url(paper: dict[str, Any]) -> str:
    if paper.get("doi"):
        return f"https://doi.org/{paper['doi']}"
    return primary_url(paper)


def citation_container(paper: dict[str, Any]) -> str:
    return paper.get("citation_container_title", paper["venue"])


def publication_status(paper: dict[str, Any]) -> str:
    return paper.get(
        "publication_status",
        "preprint" if paper["kind"] == "preprint" else "published",
    )


def include_arxiv_in_citation(paper: dict[str, Any]) -> bool:
    """Keep a citation tied to one bibliographic version.

    Published DOI/proceedings entries do not inherit an arXiv identifier because
    preprint and version-of-record author lists or titles can differ. Forthcoming
    entries retain arXiv as the only stable public document identifier.
    """
    return bool(
        paper.get("arxiv_id")
        and publication_status(paper) in {"preprint", "forthcoming"}
    )


def split_person_name(name: str) -> tuple[str, str]:
    parts = name.strip().split()
    if len(parts) < 2:
        return "", name.strip()
    return " ".join(parts[:-1]), parts[-1]


def bibtex_person(name: str) -> str:
    given, family = split_person_name(name)
    return f"{family}, {given}" if given else family


def date_parts(value: str) -> list[int]:
    return [int(part) for part in value.split("-")]


def ris_date(value: str) -> str | None:
    parts = value.split("-")
    if len(parts) == 1:
        return None
    return "/".join(parts)


def bibtex_pages(value: str) -> str:
    return value.replace("-", "--", 1)


def atom_date(value: str) -> str:
    """Expand year/year-month metadata to a valid Atom timestamp date."""
    if re.fullmatch(r"\d{4}", value):
        return f"{value}-01-01"
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return f"{value}-01"
    return value


def format_authors(authors: list[str]) -> str:
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return f"{', '.join(authors[:-1])}, and {authors[-1]}"


def compact_authors(authors: list[str]) -> str:
    if len(authors) <= 3:
        return ", ".join(authors)
    return f"{authors[0]}, {authors[1]}, et al."


def venue_line(paper: dict[str, Any], language: str) -> str:
    bits = [paper["venue"], str(paper["year"])]
    if paper.get("volume"):
        volume = f"vol. {paper['volume']}" if language == "en" else f"卷 {paper['volume']}"
        if paper.get("issue"):
            volume += f"({paper['issue']})"
        bits.append(volume)
    if paper.get("pages"):
        label = "pp." if language == "en" else "页"
        bits.append(f"{label} {paper['pages']}")
    elif paper.get("article_number"):
        label = "article" if language == "en" else "文章编号"
        bits.append(f"{label} {paper['article_number']}")
    if publication_status(paper) == "forthcoming":
        bits.append("forthcoming" if language == "en" else "待正式出版")
    return " · ".join(bits)


def paper_identifiers(paper: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if paper.get("doi"):
        values.append(
            {
                "@type": "PropertyValue",
                "propertyID": "DOI",
                "value": paper["doi"],
                "url": f"https://doi.org/{paper['doi']}",
            }
        )
    if paper.get("arxiv_id"):
        values.append(
            {
                "@type": "PropertyValue",
                "propertyID": "arXiv",
                "value": paper["arxiv_id"],
                "url": f"https://arxiv.org/abs/{paper['arxiv_id']}",
            }
        )
    return values


def jsonld_graph(paper: dict[str, Any], language: str) -> dict[str, Any]:
    url = page_url(paper, language)
    paper_id = f"{BASE_URL}/publications/{paper['slug']}/#paper"
    content = paper[language]
    same_as = list(
        dict.fromkeys(
            [primary_url(paper)]
            + [link["url"] for link in paper.get("links", [])]
        )
    )
    scholarly: dict[str, Any] = {
        "@type": "ScholarlyArticle",
        "@id": paper_id,
        "name": paper["title"],
        "headline": paper["title"],
        "abstract": paper["abstract"],
        "author": [
            {
                "@type": "Person",
                "name": author,
                **({"sameAs": "https://orcid.org/0009-0008-2746-5947"} if author == "Yuanzhi Liang" else {}),
            }
            for author in paper["authors"]
        ],
        "datePublished": paper["publication_date"],
        "inLanguage": "en",
        "keywords": paper["keywords"],
        "identifier": paper_identifiers(paper),
        "sameAs": same_as,
        "url": primary_url(paper),
        "isPartOf": {
            "@type": "Periodical" if paper["kind"] == "journal" else "PublicationVolume",
            "name": citation_container(paper),
        },
    }
    if paper.get("publisher"):
        scholarly["publisher"] = {
            "@type": "Organization",
            "name": paper["publisher"],
        }
    if publication_status(paper) == "forthcoming":
        scholarly["creativeWorkStatus"] = "Forthcoming"
    if paper.get("arxiv_updated") and include_arxiv_in_citation(paper):
        scholarly["dateModified"] = paper["arxiv_updated"]
    if paper.get("pages"):
        scholarly["pagination"] = paper["pages"]
    elif paper.get("article_number"):
        scholarly["pagination"] = paper["article_number"]
    if paper.get("volume"):
        scholarly["volumeNumber"] = paper["volume"]
    if paper.get("issue"):
        scholarly["issueNumber"] = paper["issue"]

    note = {
        "@type": "Article",
        "@id": f"{url}#explainer",
        "url": url,
        "headline": (
            f"Paper explainer: {paper['title']}"
            if language == "en"
            else f"论文解读：{paper['title']}"
        ),
        "description": content["summary"],
        "inLanguage": "en" if language == "en" else "zh-CN",
        "dateModified": paper["source_checked"],
        "author": {"@id": PERSON_ID},
        "copyrightHolder": {"@id": PERSON_ID},
        "license": CC_BY_URL,
        "isBasedOn": primary_url(paper),
        "about": {"@id": paper_id},
        "mainEntity": {"@id": paper_id},
        "isPartOf": {"@id": WEBSITE_ID},
    }
    if paper["verification_status"] == "author-verified":
        note["reviewedBy"] = {"@id": PERSON_ID}
        note["dateModified"] = paper["author_verified_on"]
    breadcrumbs = {
        "@type": "BreadcrumbList",
        "@id": f"{url}#breadcrumbs",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home" if language == "en" else "主页",
                "item": f"{BASE_URL}/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Publications" if language == "en" else "论文",
                "item": f"{BASE_URL}{'' if language == 'en' else '/zh'}/publications/",
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": paper["short_title"],
                "item": url,
            },
        ],
    }
    return {"@context": "https://schema.org", "@graph": [note, scholarly, breadcrumbs]}


def highwire_meta(paper: dict[str, Any]) -> str:
    lines = [
        f'  <meta name="citation_title" content="{esc(paper["title"])}">',
        *[
            f'  <meta name="citation_author" content="{esc(author)}">'
            for author in paper["authors"]
        ],
        f'  <meta name="citation_publication_date" content="{esc(paper["publication_date"])}">',
        f'  <meta name="citation_abstract_html_url" content="{esc(page_url(paper, "en"))}">',
        f'  <meta name="citation_language" content="en">',
        f'  <meta name="citation_keywords" content="{esc("; ".join(paper["keywords"]))}">',
        f'  <meta name="citation_abstract" content="{esc(paper["abstract"])}">',
    ]
    if paper["kind"] == "journal":
        lines.append(
            f'  <meta name="citation_journal_title" content="{esc(citation_container(paper))}">'
        )
    elif paper["kind"] == "conference":
        lines.append(
            f'  <meta name="citation_conference_title" content="{esc(citation_container(paper))}">'
        )
    if paper.get("publisher"):
        lines.append(f'  <meta name="citation_publisher" content="{esc(paper["publisher"])}">')
    if paper.get("doi"):
        lines.append(f'  <meta name="citation_doi" content="{esc(paper["doi"])}">')
    if include_arxiv_in_citation(paper):
        lines.append(f'  <meta name="citation_arxiv_id" content="{esc(paper["arxiv_id"])}">')
    if paper.get("volume"):
        lines.append(f'  <meta name="citation_volume" content="{esc(paper["volume"])}">')
    if paper.get("issue"):
        lines.append(f'  <meta name="citation_issue" content="{esc(paper["issue"])}">')
    if paper.get("pages"):
        first, _, last = paper["pages"].partition("-")
        lines.append(f'  <meta name="citation_firstpage" content="{esc(first)}">')
        if last:
            lines.append(f'  <meta name="citation_lastpage" content="{esc(last)}">')
    elif paper.get("article_number"):
        lines.append(
            f'  <meta name="citation_firstpage" content="{esc(paper["article_number"])}">'
        )
    return "\n".join(lines)


def nav(language: str, active: str = "publications") -> str:
    if language == "en":
        links = [
            ("/#about", "Biography", "home"),
            ("/publications/", "Publications", "publications"),
            ("/research/", "Research", "research"),
        ]
        label = "Main navigation"
    else:
        links = [
            ("/", "个人主页", "home"),
            ("/zh/publications/", "论文与解读", "publications"),
            ("/zh/research/", "研究方向", "research"),
        ]
        label = "主导航"
    items = "".join(
        f'<li><a{" class=\"active\"" if key == active else ""} href="{href}">{esc(text)}</a></li>'
        for href, text, key in links
    )
    return f"""<nav class="pub-nav" aria-label="{esc(label)}">
  <a class="pub-nav-brand" href="/">Yuanzhi Liang</a>
  <ul class="pub-nav-links">{items}</ul>
</nav>"""


def home_return(language: str) -> str:
    is_en = language == "en"
    label = "Back to homepage" if is_en else "返回主页"
    aria_label = "Return to homepage" if is_en else "返回主页"
    return (
        f'<nav class="page-home-return" aria-label="{aria_label}">'
        f'<a href="/"><span aria-hidden="true">←</span>{label}</a></nav>'
    )


def render_paper_page(
    paper: dict[str, Any],
    language: str,
    note: dict[str, Any] | None = None,
    paper_paths: list[tuple[dict[str, Any], dict[str, Any]]] | None = None,
) -> str:
    paper_paths = paper_paths or []
    content = paper[language]
    is_en = language == "en"
    url = page_url(paper, language)
    alternate = page_url(paper, "zh" if is_en else "en")
    title = paper["title"]
    page_title = f"{title} — Paper Explainer | Yuanzhi Liang" if is_en else f"{title} 中文解读 | 梁远智"
    description = content["summary"]
    og_image = f"{BASE_URL}/{paper.get('og_image', 'img/liangyzh.jpg')}"
    links_html = "".join(
        f'<a{" class=\"primary\"" if i == 0 else ""} href="{esc(link["url"])}" '
        f'target="_blank" rel="noopener noreferrer">{esc(link["label"])}</a>'
        for i, link in enumerate(paper.get("links", []))
    )
    contribution_items = "".join(f"<li>{esc(item)}</li>" for item in content["contributions"])
    author_links = ", ".join(
        f'<a href="{PERSON_ID}" rel="author">{esc(author)}</a>' if author == "Yuanzhi Liang" else esc(author)
        for author in paper["authors"]
    )
    keyword_tags = "".join(f'<span class="tag">{esc(k)}</span>' for k in paper["keywords"])
    verified = paper["verification_status"] == "author-verified"
    if is_en:
        labels = {
            "kicker": "Paper overview · author-verified" if verified else "Paper overview · source checked",
            "authors": "Authors",
            "metadata": "Publication details",
            "dates": "Version dates",
            "posted": "arXiv first posted",
            "updated": "arXiv last revised",
            "online": "First published online",
            "print": "Print publication date",
            "checked": "Source checked",
            "status": "Verification status",
            "status_value": (
                f"Author-verified on {paper['author_verified_on']}"
                if verified
                else "Author verification pending"
            ),
            "summary": "Summary",
            "question": "Research question",
            "contributions": "What the paper contributes",
            "evidence": "Evidence and evaluation scope",
            "limits": "Scope and limitations",
            "position": "Positioning for related work",
            "sentence": "Related-work context",
            "sentence_note": "A concise, neutral description of how this paper can be situated in related work.",
            "abstract": "Official abstract",
            "abstract_note": "The abstract is reproduced for scholarly identification and remains under the paper publisher/authors’ original copyright; it is not covered by this page’s CC BY license.",
            "claims": "Evidence references",
            "claim": "What to verify",
            "locator": "Location in the paper",
            "cite": "How to cite",
            "cite_note": "Cite the paper—not this explainer—for scientific claims. Cite this page only when reusing its original commentary.",
            "paper_citation": "Recommended paper citation",
            "bibliographic_note": "Bibliographic note",
            "alternate_pagination": "Alternate-copy pagination",
            "download": "Download citation",
            "license": "Reuse policy",
            "license_text": "Original explanatory text on this page is licensed under CC BY 4.0 with attribution and a link to this page. Paper title, abstract, figures, and bibliographic metadata are excluded and retain their original rights.",
            "links": "Primary sources and resources",
            "source": "Primary source",
            "home": "Home",
            "all": "All publications",
            "switch": "中文",
            "problem_claim": "Problem statement",
            "method_claim": "Method and contributions",
            "evidence_claim": "Evaluation statement",
            "paths": "Research paths",
            "path_note": "How this paper contributes to the site's broader research map.",
        }
    else:
        labels = {
            "kicker": "论文解读 · 作者已确认" if verified else "论文解读 · 已核对来源",
            "authors": "作者",
            "metadata": "论文信息",
            "dates": "版本日期",
            "posted": "arXiv 首次提交",
            "updated": "arXiv 最近修订",
            "online": "Online 首发",
            "print": "纸质出版日期",
            "checked": "来源核验日期",
            "status": "核验状态",
            "status_value": (
                f"作者已于 {paper['author_verified_on']} 核验"
                if verified
                else "等待作者最终确认"
            ),
            "summary": "论文概要",
            "question": "研究问题",
            "contributions": "论文贡献",
            "evidence": "证据与评测范围",
            "limits": "适用范围与局限",
            "position": "Related work 定位",
            "sentence": "Related Work 表述",
            "sentence_note": "这是一段用于说明论文定位的简洁中性表述。",
            "abstract": "论文官方英文摘要",
            "abstract_note": "摘要仅用于学术识别，版权仍归论文作者或出版方所有，不属于本页 CC BY 许可范围。",
            "claims": "依据与出处",
            "claim": "核对内容",
            "locator": "论文中的位置",
            "cite": "如何引用",
            "cite_note": "科研结论应引用论文本身；只有在复用本站原创解读时才引用本页。",
            "paper_citation": "推荐论文引用",
            "bibliographic_note": "书目说明",
            "alternate_pagination": "其他版本页码",
            "download": "下载引用",
            "license": "复用许可",
            "license_text": "本页原创解读采用 CC BY 4.0：复用时须署名并链接本页。论文标题、摘要、图表和书目信息不在此许可范围内，仍保留原有权利。",
            "links": "一手来源与资源",
            "source": "主要核验来源",
            "home": "主页",
            "all": "全部论文",
            "switch": "English",
            "problem_claim": "问题陈述",
            "method_claim": "方法与贡献",
            "evidence_claim": "评测结论",
            "paths": "所属研究路径",
            "path_note": "这篇论文在本站研究脉络中的位置。",
        }

    date_bits = []
    if paper.get("arxiv_posted"):
        date_bits.append(f"<dt>{labels['posted']}</dt><dd>{esc(paper['arxiv_posted'])}</dd>")
    if paper.get("arxiv_updated"):
        date_bits.append(f"<dt>{labels['updated']}</dt><dd>{esc(paper['arxiv_updated'])}</dd>")
    if paper.get("online_date"):
        date_bits.append(f"<dt>{labels['online']}</dt><dd>{esc(paper['online_date'])}</dd>")
    if paper.get("print_date"):
        date_bits.append(f"<dt>{labels['print']}</dt><dd>{esc(paper['print_date'])}</dd>")
    date_bits.extend(
        [
            f"<dt>{labels['checked']}</dt><dd>{esc(paper['source_checked'])}</dd>",
            f"<dt>{labels['status']}</dt><dd>{labels['status_value']}</dd>",
        ]
    )
    citation_formats = (
        f'<a href="/publications/{paper["slug"]}/citation.bib">BibTeX</a>'
        f'<a href="/publications/{paper["slug"]}/citation.ris">RIS</a>'
        f'<a href="/publications/{paper["slug"]}/citation.json">CSL-JSON</a>'
    )
    note_link = ""
    if note:
        note_label = (
            "Read the long-form Research Note"
            if is_en
            else "阅读英文 Research Note 长文"
        )
        note_link = (
            '<section class="related-note">'
            f'<h2>{"Research Note" if is_en else "英文 Research Note"}</h2>'
            f'<p><a class="primary" href="/research-notes/{paper["slug"]}/">'
            f'{esc(note_label)}: {esc(note["title"])}</a></p>'
            '</section>'
        )
    role_labels = {
        "en": {
            "foundation": "Foundation",
            "core": "Core work",
            "bridge": "Bridge",
            "framing": "Field framing",
            "horizon": "Research horizon",
        },
        "zh": {
            "foundation": "基础工作",
            "core": "核心工作",
            "bridge": "衔接工作",
            "framing": "领域框架",
            "horizon": "长期方向",
        },
    }
    paths_html = ""
    if paper_paths:
        path_items = "".join(
            f'<li><a href="{research_path_url(path, language).removeprefix(BASE_URL)}">'
            f'{esc(path[language]["title"])}</a>'
            f'<span class="path-role">{esc(role_labels[language][member["role"]])}</span>'
            f'<p>{esc(member[f"{language}_relation"])}</p></li>'
            for path, member in paper_paths
        )
        paths_html = (
            '<section class="research-context">'
            f'<h2>{labels["paths"]}</h2><p>{labels["path_note"]}</p>'
            f'<ul class="path-link-list">{path_items}</ul></section>'
        )
    bibliographic_rows = ""
    if paper.get("bibliographic_note"):
        bibliographic_rows += (
            f"<dt>{labels['bibliographic_note']}</dt>"
            f"<dd>{esc(paper['bibliographic_note'])}</dd>"
        )
    if paper.get("alternate_pagination"):
        alternate_pages = paper["alternate_pagination"]
        bibliographic_rows += (
            f"<dt>{labels['alternate_pagination']}</dt>"
            f'<dd><a href="{esc(alternate_pages["url"])}" target="_blank" '
            f'rel="noopener noreferrer">{esc(alternate_pages["version"])}</a>: '
            f"{esc(alternate_pages['pages'])}</dd>"
        )
    claim_rows = [
        (labels["problem_claim"], "Abstract"),
        (labels["method_claim"], paper["source"].get("method_locator", "Abstract")),
        (labels["evidence_claim"], paper["source"].get("evidence_locator", "Abstract; Experiments section")),
    ]
    claim_table = "".join(
        f"<tr><td>{esc(claim)}</td><td>{esc(locator)}</td></tr>"
        for claim, locator in claim_rows
    )
    schema = jsonld_graph(paper, language)
    highwire = highwire_meta(paper) if is_en else ""
    date_meta = (
        paper.get("author_verified_on")
        or paper.get("arxiv_updated")
        or paper["publication_date"]
    )
    alternate_lang = "zh-CN" if is_en else "en"
    self_lang = "en" if is_en else "zh-CN"

    return f"""<!doctype html>
<html lang="{self_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(page_title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="author" content="Yuanzhi Liang">
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
  <link rel="canonical" href="{url}">
  <link rel="alternate" hreflang="{self_lang}" href="{url}">
  <link rel="alternate" hreflang="{alternate_lang}" href="{alternate}">
  <link rel="alternate" hreflang="x-default" href="{page_url(paper, 'en')}">
  <link rel="alternate" type="application/vnd.citationstyles.csl+json" title="CSL-JSON citation" href="/publications/{paper['slug']}/citation.json">
  <link rel="alternate" type="application/x-bibtex" title="BibTeX citation" href="/publications/{paper['slug']}/citation.bib">
  <link rel="alternate" type="application/x-research-info-systems" title="RIS citation" href="/publications/{paper['slug']}/citation.ris">
  <link rel="alternate" type="application/json" title="Full research record" href="/publications/{paper['slug']}/record.json">
  <link rel="license" href="{CC_BY_URL}">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{esc(page_title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{og_image}">
  <meta property="og:image:alt" content="Yuanzhi Liang">
  <meta property="og:image:width" content="1080">
  <meta property="og:image:height" content="1359">
  <meta property="article:modified_time" content="{date_meta}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(page_title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="{og_image}">
{highwire}
  <link rel="stylesheet" href="/dist/css/screen.css">
  <script type="application/ld+json">
{json_script(schema)}
  </script>
</head>
<body class="pub-page">
  <a class="skip-link" href="#main">Skip to content</a>
  {nav(language)}
  <main id="main" class="note-container">
    {home_return(language)}
    <nav class="note-breadcrumb" aria-label="Breadcrumb">
      <a href="{'' if is_en else '/zh'}/publications/">{labels['all']}</a><span aria-hidden="true">/</span>
      <span aria-current="page">{esc(paper['short_title'])}</span>
    </nav>

    <header class="note-header">
      <div class="kicker">{labels['kicker']}</div>
      <h1>{esc(title)}</h1>
      <p class="paper-authors"><strong>{labels['authors']}:</strong> {author_links}</p>
      <p class="paper-venue">{esc(venue_line(paper, language))}</p>
      <div class="note-tags" aria-label="Keywords">{keyword_tags}</div>
      <div class="record-actions">
        <a href="{alternate}" lang="{alternate_lang}" hreflang="{alternate_lang}">{labels['switch']}</a>
        {links_html}
      </div>
    </header>

    <section class="record-grid" aria-label="{labels['metadata']}">
      <div>
        <h2>{labels['metadata']}</h2>
        <dl>
          <dt>{labels['authors']}</dt><dd>{esc(format_authors(paper['authors']))}</dd>
          <dt>{labels['paper_citation']}</dt><dd>{esc(paper_citation_text(paper))}</dd>
{bibliographic_rows}
        </dl>
      </div>
      <div>
        <h2>{labels['dates']}</h2>
        <dl>{''.join(date_bits)}</dl>
      </div>
    </section>

    <article class="note-body" aria-labelledby="interpretation-heading">
      <section class="note-callout">
        <h2 id="interpretation-heading">{labels['summary']}</h2>
        <p>{esc(content['summary'])}</p>
      </section>

{note_link}

{paths_html}

      <section>
        <h2>{labels['question']}</h2>
        <p>{esc(content['problem'])}</p>
      </section>

      <section>
        <h2>{labels['contributions']}</h2>
        <ul>{contribution_items}</ul>
      </section>

      <section>
        <h2>{labels['evidence']}</h2>
        <p>{esc(content['evidence'])}</p>
      </section>

      <section>
        <h2>{labels['limits']}</h2>
        <p>{esc(content['limitations'])}</p>
      </section>

      <section>
        <h2>{labels['position']}</h2>
        <p>{esc(content['positioning'])}</p>
      </section>

      <section class="citation-ready">
        <h2>{labels['sentence']}</h2>
        <blockquote>{esc(content['citation_ready'])}</blockquote>
        <p class="fine-print">{labels['sentence_note']}</p>
      </section>

      <section>
        <h2>{labels['abstract']}</h2>
        <p lang="en">{esc(paper['abstract'])}</p>
        <p class="rights-note">{labels['abstract_note']}</p>
      </section>

      <section>
        <h2>{labels['claims']}</h2>
        <div class="table-wrap">
          <table>
            <thead><tr><th>{labels['claim']}</th><th>{labels['locator']}</th></tr></thead>
            <tbody>{claim_table}</tbody>
          </table>
        </div>
        <p><strong>{labels['source']}:</strong> <a href="{esc(paper['source']['url'])}" target="_blank" rel="noopener noreferrer">{esc(paper['source']['label'])}</a> ({esc(paper['source']['version'])}).</p>
      </section>

      <section>
        <h2>{labels['cite']}</h2>
        <p>{labels['cite_note']}</p>
        <pre class="paper-citation">{esc(paper_citation_text(paper))}</pre>
        <div class="citation-downloads" aria-label="{labels['download']}">{citation_formats}</div>
      </section>

      <section>
        <h2>{labels['license']}</h2>
        <p>{labels['license_text']} <a href="{CC_BY_URL}" rel="license">Creative Commons Attribution 4.0 International</a>.</p>
      </section>

      <section>
        <h2>{labels['links']}</h2>
        <div class="note-links">{links_html}<a href="{'' if is_en else '/zh'}/publications/">{labels['all']}</a></div>
      </section>
    </article>
  </main>
  <footer class="site-footer">
    <p>© Yuanzhi Liang · <a href="/LICENSE-CONTENT.md">Content license</a> · <a href="/feed.xml">Research feed</a></p>
  </footer>
</body>
</html>
"""


def collection_schema(papers: list[dict[str, Any]], language: str) -> dict[str, Any]:
    prefix = "" if language == "en" else "/zh"
    url = f"{BASE_URL}{prefix}/publications/"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{url}#collection",
                "url": url,
                "name": "Publications by Yuanzhi Liang" if language == "en" else "梁远智的论文与解读",
                "inLanguage": "en" if language == "en" else "zh-CN",
                "isPartOf": {"@id": WEBSITE_ID},
                "about": {"@id": PERSON_ID},
                "mainEntity": {"@id": f"{url}#papers"},
            },
            {
                "@type": "ItemList",
                "@id": f"{url}#papers",
                "numberOfItems": len(papers),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": i,
                        "url": page_url(paper, language),
                        "name": paper["title"],
                    }
                    for i, paper in enumerate(papers, 1)
                ],
            },
        ],
    }


def render_collection(
    papers: list[dict[str, Any]],
    language: str,
    notes_by_slug: dict[str, dict[str, Any]] | None = None,
    memberships: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] | None = None,
) -> str:
    notes_by_slug = notes_by_slug or {}
    memberships = memberships or {}
    is_en = language == "en"
    self_url = f"{BASE_URL}{'' if is_en else '/zh'}/publications/"
    other_url = f"{BASE_URL}{'/zh' if is_en else ''}/publications/"
    self_lang = "en" if is_en else "zh-CN"
    other_lang = "zh-CN" if is_en else "en"
    title = "Publications | Yuanzhi Liang" if is_en else "论文与解读 | 梁远智"
    desc = (
        "Publications by Yuanzhi Liang, with paper abstracts, concise summaries, related-work context, and BibTeX/RIS/CSL citation downloads."
        if is_en
        else "梁远智的论文目录与中文解读，包含论文摘要、简要介绍、Related Work 定位和 BibTeX/RIS/CSL 引用下载。"
    )
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for paper in papers:
        grouped[int(paper["year"])].append(paper)
    sections = []
    for year in sorted(grouped, reverse=True):
        cards = []
        for paper in grouped[year]:
            content = paper[language]
            search = " ".join(
                [paper["title"], *paper["authors"], paper["venue"], *paper["keywords"], content["summary"]]
            )
            links = "".join(
                f'<a href="{esc(link["url"])}" target="_blank" rel="noopener noreferrer">{esc(link["label"])}</a>'
                for link in paper.get("links", [])[:2]
            )
            record_label = "Overview" if is_en else "论文解读"
            note = notes_by_slug.get(paper["slug"])
            note_link = (
                f'<a href="/research-notes/{paper["slug"]}/">Research Note</a>'
                if note
                else ""
            )
            path_tags = "".join(
                f'<a class="path-chip" href="{research_path_url(path, language).removeprefix(BASE_URL)}">'
                f'{esc(path[language]["short_title"])}</a>'
                for path, _member in memberships.get(paper["slug"], [])
            )
            path_block = (
                f'\n  <div class="path-chips" aria-label="Research paths">{path_tags}</div>'
                if path_tags
                else ""
            )
            cards.append(
                f"""<article class="pub-item" data-search="{esc(search.lower())}">
  <h3><a href="{'' if is_en else '/zh'}/publications/{paper['slug']}/">{esc(paper['title'])}</a></h3>
  <p class="meta">{esc(compact_authors(paper['authors']))} · {esc(venue_line(paper, language))}</p>
  <p class="pub-summary">{esc(content['summary'])}</p>{path_block}
  <div class="links"><a class="primary" href="{'' if is_en else '/zh'}/publications/{paper['slug']}/">{record_label}</a>{note_link}{links}</div>
</article>"""
            )
        sections.append(
            f"""<section class="pub-year-section" id="year-{year}">
  <h2 class="pub-year-title">{year} <span class="badge">{len(cards)}</span></h2>
  <div class="pub-list">{''.join(cards)}</div>
</section>"""
        )
    labels = {
        "heading": "Publications" if is_en else "论文与解读",
        "intro": (
            "Browse publications by year. Each paper page includes the abstract, a concise overview, related-work context, sources, and citation downloads."
            if is_en
            else "按年份浏览论文。每篇论文页面包含摘要、简要解读、Related Work 定位、参考来源和引用下载。"
        ),
        "search": "Search title, author, venue, or topic" if is_en else "搜索标题、作者、会议或主题",
        "count": f"{len(papers)} records" if is_en else f"共 {len(papers)} 条",
        "switch": "中文目录" if is_en else "English catalog",
        "license": (
            "Original commentary is CC BY 4.0; paper abstracts and bibliographic material retain their original rights."
            if is_en
            else "原创解读采用 CC BY 4.0；论文摘要和书目信息仍保留原有权利。"
        ),
        "paths": "Explore by research path" if is_en else "按研究路径浏览",
    }
    schema = collection_schema(papers, language)
    return f"""<!doctype html>
<html lang="{self_lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
  <link rel="canonical" href="{self_url}">
  <link rel="alternate" hreflang="{self_lang}" href="{self_url}">
  <link rel="alternate" hreflang="{other_lang}" href="{other_url}">
  <link rel="alternate" hreflang="x-default" href="{BASE_URL}/publications/">
  <link rel="alternate" type="application/atom+xml" title="Yuanzhi Liang research updates" href="/feed.xml">
  <link rel="alternate" type="application/vnd.citationstyles.csl+json" title="Publication catalog" href="/publications/catalog.json">
  <link rel="alternate" type="application/json" title="Full research records" href="/publications/records.json">
  <link rel="alternate" type="text/plain" title="Plain-text publication index" href="/llms.txt">
  <link rel="license" href="{CC_BY_URL}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{self_url}">
  <meta property="og:image" content="{BASE_URL}/img/liangyzh.jpg">
  <meta property="og:image:alt" content="Portrait of Yuanzhi Liang">
  <meta property="og:image:width" content="1080">
  <meta property="og:image:height" content="1359">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{BASE_URL}/img/liangyzh.jpg">
  <link rel="stylesheet" href="/dist/css/screen.css">
  <script type="application/ld+json">
{json_script(schema)}
  </script>
</head>
<body class="pub-page">
  <a class="skip-link" href="#main">Skip to content</a>
  {nav(language)}
  <main id="main" class="pub-container">
    {home_return(language)}
    <header class="pub-page-header">
      <h1>{labels['heading']}</h1>
      <p>{labels['intro']}</p>
      <p class="collection-tools"><a href="{'' if is_en else '/zh'}/research/">{labels['paths']}</a></p>
      <p class="collection-tools"><a href="{other_url}" hreflang="{other_lang}">{labels['switch']}</a></p>
    </header>
    <div class="license-banner">{labels['license']}</div>
    <div class="pub-search-bar">
      <label class="sr-only" for="pub-search">{labels['search']}</label>
      <input id="pub-search" class="pub-search-input" type="search" placeholder="{labels['search']}" autocomplete="off">
      <span id="pub-count" class="pub-search-count" aria-live="polite">{labels['count']}</span>
    </div>
    {''.join(sections)}
  </main>
  <footer class="site-footer"><p>© Yuanzhi Liang · <a href="/LICENSE-CONTENT.md">Content license</a></p></footer>
  <script>
  (() => {{
    const input = document.getElementById('pub-search');
    const cards = [...document.querySelectorAll('.pub-item')];
    const count = document.getElementById('pub-count');
    input.addEventListener('input', () => {{
      const query = input.value.trim().toLowerCase();
      let visible = 0;
      cards.forEach(card => {{
        const show = !query || card.dataset.search.includes(query);
        card.hidden = !show;
        if (show) visible += 1;
      }});
      count.textContent = `${{visible}} / ${{cards.length}}`;
    }});
  }})();
  </script>
</body>
</html>
"""


def research_note_schema(
    note: dict[str, Any], paper: dict[str, Any]
) -> dict[str, Any]:
    url = research_note_url(note)
    paper_entity_id = f"{BASE_URL}/publications/{paper['slug']}/#paper"
    source_scholarly = next(
        item
        for item in jsonld_graph(paper, "en")["@graph"]
        if item.get("@type") == "ScholarlyArticle"
    )
    scholarly: dict[str, Any] = {
        "@type": "ScholarlyArticle",
        "@id": paper_entity_id,
        "url": page_url(paper, "en"),
        "name": paper["title"],
        "headline": paper["title"],
        "author": [
            {"@type": "Person", "name": name} for name in paper["authors"]
        ],
        "datePublished": source_scholarly["datePublished"],
        "inLanguage": "en",
        "keywords": note["keywords"],
        "isPartOf": {
            "@type": "CreativeWork",
            "name": venue_line(paper, "en"),
        },
    }
    if paper.get("pages"):
        scholarly["pagination"] = paper["pages"]
    article: dict[str, Any] = {
        "@type": "TechArticle",
        "@id": f"{url}#article",
        "url": url,
        "headline": note["title"],
        "description": note["dek"],
        "inLanguage": "en",
        "author": {"@id": PERSON_ID},
        "isPartOf": {"@id": WEBSITE_ID},
        "mainEntityOfPage": {"@id": f"{url}#webpage"},
        "about": {"@id": paper_entity_id},
        "citation": {"@id": paper_entity_id},
        "isBasedOn": page_url(paper, "en"),
        "dateModified": note["drafted_on"],
        "creativeWorkStatus": (
            "Published" if note["status"] == "published" else "Draft — author review pending"
        ),
        "keywords": note["keywords"],
        "license": CC_BY_URL,
    }
    if note["status"] == "published":
        article["datePublished"] = note["published_on"]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{url}#webpage",
                "url": url,
                "name": note["title"],
                "description": note["dek"],
                "inLanguage": "en",
                "isPartOf": {"@id": WEBSITE_ID},
                "mainEntity": {"@id": f"{url}#article"},
            },
            article,
            scholarly,
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumbs",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Home",
                        "item": f"{BASE_URL}/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Research Notes",
                        "item": f"{BASE_URL}/research-notes/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": note["title"],
                        "item": url,
                    },
                ],
            },
        ],
    }


def render_research_note(
    note: dict[str, Any],
    paper: dict[str, Any],
    paper_paths: list[tuple[dict[str, Any], dict[str, Any]]] | None = None,
) -> str:
    paper_paths = paper_paths or []
    url = research_note_url(note)
    review_pending = note["status"] == "ready_for_review"
    robots = "noindex,nofollow" if review_pending else "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
    status_label = "Research Note"
    retrospective = (
        '<p class="retrospective-note"><strong>Current perspective.</strong> '
        + esc(note["retrospective_context"])
        + "</p>"
        if note["retrospective"]
        else ""
    )
    lede = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in note["lede"])
    sections = []
    toc_items = [
        ("overview", "Overview"),
        ("in-one-sentence", "In one sentence"),
    ]
    used_section_ids: set[str] = set()
    for index, section in enumerate(note["sections"], 1):
        section_id = slugify_key(section["heading"]) or f"section-{index}"
        if section_id in used_section_ids:
            section_id = f"{section_id}-{index}"
        used_section_ids.add(section_id)
        toc_items.append((section_id, section["heading"]))
        paragraphs = "".join(f"<p>{esc(value)}</p>" for value in section["paragraphs"])
        sections.append(
            f'<section id="{section_id}"><h2>{esc(section["heading"])}</h2>{paragraphs}</section>'
        )
    evidence_rows = "".join(
        f'<tr><td>{esc(item["claim"])}</td><td>{esc(item["locator"])}</td></tr>'
        for item in note["evidence"]
    )
    tags = "".join(f'<span class="tag">{esc(keyword)}</span>' for keyword in note["keywords"])
    path_links = "".join(
        f'<a class="path-chip" href="/research/{path["slug"]}/">{esc(path["en"]["short_title"])}</a>'
        for path, _member in paper_paths
    )
    path_context = (
        '<aside class="note-path-context" aria-label="Research context">'
        '<strong>Research context</strong>'
        f'<div class="path-chips">{path_links}</div></aside>'
        if path_links
        else ""
    )
    schema = research_note_schema(note, paper)
    citation_formats = (
        f'<a href="/publications/{paper["slug"]}/citation.bib">BibTeX</a>'
        f'<a href="/publications/{paper["slug"]}/citation.ris">RIS</a>'
        f'<a href="/publications/{paper["slug"]}/citation.json">CSL-JSON</a>'
    )
    toc_items.extend(
        [
            ("related-work-summary", "Related-work summary"),
            ("evidence-map", "Evidence map"),
            ("cite-paper", "Cite the paper"),
        ]
    )
    toc = (
        '<nav class="note-toc" aria-label="On this page"><h2>On this page</h2><ol>'
        + "".join(
            f'<li><a href="#{section_id}">{esc(label)}</a></li>'
            for section_id, label in toc_items
        )
        + "</ol></nav>"
    )
    paper_authors = ", ".join(paper["authors"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(note['title'])} | Research Notes — Yuanzhi Liang</title>
  <meta name="description" content="{esc(note['dek'])}">
  <meta name="author" content="Yuanzhi Liang">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{url}">
  <link rel="license" href="{CC_BY_URL}">
  <link rel="alternate" type="application/x-bibtex" title="Paper citation in BibTeX" href="/publications/{paper['slug']}/citation.bib">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{esc(note['title'])}">
  <meta property="og:description" content="{esc(note['dek'])}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{BASE_URL}/img/liangyzh.jpg">
  <meta property="og:image:alt" content="Portrait of Yuanzhi Liang">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(note['title'])}">
  <meta name="twitter:description" content="{esc(note['dek'])}">
  <link rel="stylesheet" href="/dist/css/screen.css">
  <script type="application/ld+json">
{json_script(schema)}
  </script>
</head>
<body class="pub-page">
  <a class="skip-link" href="#main">Skip to content</a>
  {nav('en', 'research')}
  <main id="main" class="note-container">
    {home_return('en')}
    <nav class="note-breadcrumb" aria-label="Breadcrumb">
      <a href="/research-notes/">Research Notes</a><span aria-hidden="true">/</span>
      <span aria-current="page">{esc(paper['short_title'])}</span>
    </nav>
    <header class="note-header research-note-header">
      <div class="kicker">{status_label}</div>
      <h1>{esc(note['title'])}</h1>
      <p class="subtitle">{esc(note['dek'])}</p>
      <p class="paper-venue"><strong>Paper:</strong> <a href="/publications/{paper['slug']}/">{esc(paper['title'])}</a></p>
      <p class="paper-authors"><strong>Authors:</strong> {esc(paper_authors)}</p>
      <p class="paper-venue"><strong>Venue:</strong> {esc(venue_line(paper, 'en'))}</p>
      <div class="note-tags" aria-label="Topics">{tags}</div>
    </header>
{path_context}
{retrospective}
{toc}
    <article class="note-body research-note-body">
      <section id="overview" class="note-lede"><h2>Overview</h2>{lede}</section>
      <section id="in-one-sentence" class="note-callout"><h2>In one sentence</h2><p>{esc(note['takeaway'])}</p></section>
      {''.join(sections)}
      <section id="related-work-summary" class="citation-ready">
        <h2>Related-work summary</h2>
        <blockquote>{esc(paper['en']['citation_ready'])}</blockquote>
        <p><strong>Scope:</strong> {esc(paper['en']['limitations'])}</p>
        <p class="fine-print">Use this short summary to identify the paper's contribution and scope. Consult the primary paper before citing a specific experimental result.</p>
      </section>
      <section id="evidence-map">
        <h2>Evidence map</h2>
        <p>The locations below point to the primary paper so readers can verify the method and reported evidence directly.</p>
        <div class="table-wrap"><table><thead><tr><th>Claim to verify</th><th>Primary-paper location</th></tr></thead><tbody>{evidence_rows}</tbody></table></div>
      </section>
      <section id="cite-paper" class="citation-ready">
        <h2>Cite the paper</h2>
        <p>For scientific claims and reported results, cite the paper itself. This note provides context and interpretation.</p>
        <p><a class="primary" href="/publications/{paper['slug']}/">Open the source-checked publication record</a></p>
        <pre class="paper-citation">{esc(paper_citation_text(paper))}</pre>
        <div class="citation-downloads" aria-label="Download paper citation">{citation_formats}</div>
      </section>
      <section>
        <h2>Reuse</h2>
        <p>Original commentary in this note is licensed under <a href="{CC_BY_URL}" rel="license">CC BY 4.0</a>. The paper title and bibliographic material retain their original rights.</p>
      </section>
    </article>
  </main>
  <footer class="site-footer"><p>© Yuanzhi Liang · <a href="/LICENSE-CONTENT.md">Content license</a> · <a href="/feed.xml">Research feed</a></p></footer>
</body>
</html>
"""


def research_notes_collection_schema(
    notes: list[dict[str, Any]], papers_by_slug: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    url = f"{BASE_URL}/research-notes/"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{url}#collection",
                "url": url,
                "name": "Research Notes by Yuanzhi Liang",
                "description": "Long-form, source-linked explanations of selected research papers.",
                "inLanguage": "en",
                "isPartOf": {"@id": WEBSITE_ID},
                "about": {"@id": PERSON_ID},
                "mainEntity": {"@id": f"{url}#notes"},
            },
            {
                "@type": "ItemList",
                "@id": f"{url}#notes",
                "numberOfItems": len(notes),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "url": research_note_url(note),
                        "name": note["title"],
                    }
                    for index, note in enumerate(notes, 1)
                ],
            },
        ],
    }


def render_research_notes_collection(
    notes: list[dict[str, Any]],
    papers_by_slug: dict[str, dict[str, Any]],
    memberships: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] | None = None,
) -> str:
    memberships = memberships or {}
    has_published = bool(published_notes(notes))
    robots = "index,follow" if has_published else "noindex,nofollow"
    cards = []
    for note in notes:
        paper = papers_by_slug[note["paper_slug"]]
        path_tags = "".join(
            f'<a class="path-chip" href="/research/{path["slug"]}/">{esc(path["en"]["short_title"])}</a>'
            for path, _member in memberships.get(paper["slug"], [])
        )
        path_block = (
            f'\n  <div class="path-chips" aria-label="Research paths">{path_tags}</div>'
            if path_tags
            else ""
        )
        cards.append(
            f"""<article class="pub-item research-note-card">
  <p class="meta">{esc(venue_line(paper, 'en'))}</p>
  <h2><a href="/research-notes/{paper['slug']}/">{esc(note['title'])}</a></h2>
  <p class="pub-summary">{esc(note['dek'])}</p>{path_block}
  <div class="links"><a class="primary" href="/research-notes/{paper['slug']}/">Read note</a><a href="/publications/{paper['slug']}/">Paper record</a></div>
</article>"""
        )
    url = f"{BASE_URL}/research-notes/"
    schema = research_notes_collection_schema(notes, papers_by_slug)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Research Notes | Yuanzhi Liang</title>
  <meta name="description" content="Long-form, source-linked explanations of selected research papers by Yuanzhi Liang and collaborators.">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{url}">
  <link rel="license" href="{CC_BY_URL}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="Research Notes | Yuanzhi Liang">
  <meta property="og:description" content="Long-form, source-linked explanations of selected research papers.">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{BASE_URL}/img/liangyzh.jpg">
  <meta property="og:image:alt" content="Portrait of Yuanzhi Liang">
  <link rel="stylesheet" href="/dist/css/screen.css">
  <script type="application/ld+json">
{json_script(schema)}
  </script>
</head>
<body class="pub-page">
  <a class="skip-link" href="#main">Skip to content</a>
  {nav('en', 'research')}
  <main id="main" class="pub-container">
    {home_return('en')}
    <header class="pub-page-header">
      <h1>Research Notes</h1>
      <p>Long-form explanations for readers who want the intuition quickly and the research boundary accurately. Each note links back to the primary paper, evidence locations, and citation exports.</p>
      <p class="collection-tools"><a href="/research/">Explore the broader research paths</a></p>
    </header>
    <div class="pub-list research-notes-list">{''.join(cards)}</div>
  </main>
  <footer class="site-footer"><p>© Yuanzhi Liang · <a href="/LICENSE-CONTENT.md">Content license</a></p></footer>
</body>
</html>
"""


def research_hub_schema(
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    language: str,
) -> dict[str, Any]:
    prefix = "" if language == "en" else "/zh"
    url = f"{BASE_URL}{prefix}/research/"
    content = hub[language] if hub else None
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{url}#collection",
                "url": url,
                "name": content["title"] if content else ("Research" if language == "en" else "研究方向"),
                "description": content["dek"] if content else (
                    "Research paths by Yuanzhi Liang."
                    if language == "en"
                    else "梁远智的研究方向。"
                ),
                "inLanguage": "en" if language == "en" else "zh-CN",
                "isPartOf": {"@id": WEBSITE_ID},
                "about": {"@id": PERSON_ID},
                "mainEntity": {"@id": f"{url}#paths"},
            },
            {
                "@type": "ItemList",
                "@id": f"{url}#paths",
                "numberOfItems": len(paths),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "url": research_path_url(path, language),
                        "name": path[language]["title"],
                    }
                    for index, path in enumerate(sorted(paths, key=lambda item: item["order"]), 1)
                ],
            },
        ],
    }


def render_research_hub(
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    papers_by_slug: dict[str, dict[str, Any]],
    language: str,
    *,
    has_notes: bool = False,
    preview: bool = False,
) -> str:
    is_en = language == "en"
    lang_code = "en" if is_en else "zh-CN"
    other_language = "zh" if is_en else "en"
    other_code = "zh-CN" if is_en else "en"
    prefix = "" if is_en else "/zh"
    url = f"{BASE_URL}{prefix}/research/"
    other_url = f"{BASE_URL}{'/zh' if is_en else ''}/research/"
    review_pending = bool(hub and (preview or hub["status"] == "ready_for_review"))
    robots = (
        "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
        if hub and hub["status"] == "published" and paths and not preview
        else "noindex,nofollow"
    )
    if hub:
        content = hub[language]
        path_cards = []
        for path in sorted(paths, key=lambda item: item["order"]):
            local = path[language]
            member_titles = [papers_by_slug[item["paper_slug"]]["short_title"] for item in path["members"]]
            path_cards.append(
                f"""<article class="research-path-card path-card-{path['order']}">
  <p class="path-number">0{path['order']}</p>
  <h2><a href="{prefix}/research/{path['slug']}/">{esc(local['title'])}</a></h2>
  <p class="path-question">{esc(local['question'])}</p>
  <p>{esc(local['dek'])}</p>
  <p class="path-paper-line">{esc(' · '.join(member_titles[:6]))}{' · …' if len(member_titles) > 6 else ''}</p>
  <a class="path-arrow" href="{prefix}/research/{path['slug']}/">{'Follow this path' if is_en else '查看这条路径'} <span aria-hidden="true">→</span></a>
</article>"""
            )
        methodology_items = []
        for item in hub["methodology"]:
            label = item[language]
            links = " · ".join(
                f'<a href="{prefix}/publications/{slug}/">{esc(papers_by_slug[slug]["short_title"])}</a>'
                for slug in item["paper_slugs"]
            )
            methodology_items.append(
                f'<article class="method-card"><h3>{esc(label["heading"])}</h3>'
                f'<p>{esc(label["text"])}</p><p class="method-papers">{links}</p></article>'
            )
        arc_items = []
        for index, item in enumerate(hub["arc"], 1):
            label = item[language]
            links = " · ".join(
                f'<a href="{prefix}/publications/{slug}/">{esc(papers_by_slug[slug]["short_title"])}</a>'
                for slug in item["paper_slugs"]
            )
            arc_items.append(
                f'<article class="research-arc-step"><p class="arc-number">{index:02d}</p>'
                f'<div><h3>{esc(label["heading"])}</h3><p>{esc(label["text"])}</p>'
                f'<p class="method-papers">{links}</p></div></article>'
            )
        horizon_items = []
        for item in hub["horizon"]:
            label = item[language]
            links = " · ".join(
                f'<a href="{prefix}/publications/{slug}/">{esc(papers_by_slug[slug]["short_title"])}</a>'
                for slug in item["paper_slugs"]
            )
            horizon_items.append(
                f'<article class="research-horizon-card"><h3>{esc(label["heading"])}</h3>'
                f'<p>{esc(label["text"])}</p><p class="method-papers">{links}</p></article>'
            )
        adjacent_items = []
        for item in hub["adjacent"]:
            paper = papers_by_slug[item["paper_slug"]]
            adjacent_items.append(
                f'<article class="adjacent-item"><h3><a href="{prefix}/publications/{paper["slug"]}/">'
                f'{esc(paper["title"])}</a></h3><p>{esc(item[language])}</p></article>'
            )
        intro = "".join(f"<p>{esc(value)}</p>" for value in content["intro"])
        closing = "".join(f"<p>{esc(value)}</p>" for value in content["closing"])
        status = (
            '<p class="collection-status">Author-review preview · not publicly indexed.</p>'
            if review_pending and is_en
            else '<p class="collection-status">作者审阅预览 · 尚未进入公开索引。</p>'
            if review_pending
            else ""
        )
        notes_nav = (
            f'<a href="/research-notes/"><span>Research Notes</span><small>{"Long-form paper explanations" if is_en else "英文论文长文解读"}</small></a>'
            if has_notes
            else ""
        )
        section_nav_class = "research-section-nav" if has_notes else "research-section-nav two-sections"
        body = f"""<header class="research-hero">
  <p class="eyebrow">{'Research map' if is_en else '研究地图'}</p>
  <h1>{esc(content['title'])}</h1>
  <p class="research-dek">{esc(content['dek'])}</p>
{status}
  <p class="language-switch"><a href="{other_url}" hreflang="{other_code}">{'中文' if is_en else 'English'}</a></p>
</header>
<nav class="{section_nav_class}" aria-label="{'Research sections' if is_en else '研究内容导航'}">
  <a class="active" href="#research-paths"><span>{'Research Paths' if is_en else '研究路径'}</span><small>{'How the work connects' if is_en else '理解工作之间的关系'}</small></a>
  {notes_nav}
  <a href="{prefix}/publications/"><span>{'All Publications' if is_en else '全部论文'}</span><small>{'Records, abstracts, and citations' if is_en else '论文记录、摘要与引用'}</small></a>
</nav>
<section class="research-intro">{intro}</section>
<section class="research-arc-section" id="research-arc">
  <div class="section-heading"><p class="eyebrow">{'A longer arc' if is_en else '一条更长的脉络'}</p><h2>{esc(content['arc_title'])}</h2><p>{esc(content['arc_intro'])}</p></div>
  <div class="research-arc-list">{''.join(arc_items)}</div>
</section>
<section class="research-horizon-section">
  <div class="section-heading"><p class="eyebrow">{'Research horizon' if is_en else '长期方向'}</p><h2>{esc(content['horizon_title'])}</h2><p>{esc(content['horizon_intro'])}</p></div>
  <div class="research-horizon-grid">{''.join(horizon_items)}</div>
  <p class="research-horizon-closing">{esc(content['horizon_closing'])}</p>
</section>
<section class="research-paths-section" id="research-paths" aria-label="{'Research paths' if is_en else '研究路径'}">
  <div class="section-heading"><p class="eyebrow">{'Current research paths' if is_en else '当前研究路径'}</p><h2>{'Three research directions' if is_en else '三条研究方向'}</h2><p>{'Each path defines a specific set of problems in modeling, learning, and evaluation.' if is_en else '每条路径分别定义一组具体的建模、学习与评价问题。'}</p></div>
  <div class="research-path-grid">{''.join(path_cards)}</div>
</section>
<section class="methodology-section" id="beyond-proxy-metrics">
  <div class="section-heading"><p class="eyebrow">{'Common method' if is_en else '共同方法论'}</p><h2>{esc(content['methodology_title'])}</h2><p>{esc(content['methodology_intro'])}</p></div>
  <div class="method-grid">{''.join(methodology_items)}</div>
</section>
<section class="adjacent-section">
  <div class="section-heading"><h2>{esc(content['adjacent_title'])}</h2><p>{esc(content['adjacent_intro'])}</p></div>
  <div class="adjacent-grid">{''.join(adjacent_items)}</div>
</section>
<section class="research-closing">{closing}</section>"""
        title = f"{content['title']} | Yuanzhi Liang"
        description = content["dek"]
    else:
        title = "Research | Yuanzhi Liang" if is_en else "研究方向 | 梁远智"
        description = "Research paths by Yuanzhi Liang." if is_en else "梁远智的研究方向。"
        body = (
            "<header class=\"research-hero\"><p class=\"eyebrow\">Research map</p><h1>Research</h1>"
            "<p class=\"research-dek\">The research-path overview is under author review.</p></header>"
            if is_en
            else "<header class=\"research-hero\"><p class=\"eyebrow\">研究地图</p><h1>研究方向</h1>"
            "<p class=\"research-dek\">研究路径总览正在进行作者审阅。</p></header>"
        )
    schema = research_hub_schema(hub, paths, language)
    return f"""<!doctype html>
<html lang="{lang_code}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{url}">
  <link rel="alternate" hreflang="{lang_code}" href="{url}">
  <link rel="alternate" hreflang="{other_code}" href="{other_url}">
  <link rel="alternate" hreflang="x-default" href="{BASE_URL}/research/">
  <link rel="alternate" type="application/json" title="Research path data" href="/research/paths.json">
  <link rel="license" href="{CC_BY_URL}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{BASE_URL}/img/liangyzh.jpg">
  <link rel="stylesheet" href="/dist/css/screen.css">
  <script type="application/ld+json">
{json_script(schema)}
  </script>
</head>
<body class="pub-page research-page">
  <a class="skip-link" href="#main">{'Skip to content' if is_en else '跳到正文'}</a>
  {nav(language, 'research')}
  <main id="main" class="research-container">{home_return(language)}{body}</main>
  <footer class="site-footer"><p>© Yuanzhi Liang · <a href="/LICENSE-CONTENT.md">Content license</a> · <a href="/feed.xml">Research feed</a></p></footer>
</body>
</html>
"""


def research_path_schema(
    path: dict[str, Any],
    papers_by_slug: dict[str, dict[str, Any]],
    language: str,
) -> dict[str, Any]:
    url = research_path_url(path, language)
    prefix = "" if language == "en" else "/zh"
    local = path[language]
    article_nodes = []
    for member in path["members"]:
        paper = papers_by_slug[member["paper_slug"]]
        article_nodes.append(
            {
                "@type": "ScholarlyArticle",
                "@id": f"{page_url(paper, language)}#scholarly-article",
                "url": page_url(paper, language),
                "name": paper["title"],
                "author": [{"@type": "Person", "name": author} for author in paper["authors"]],
                "datePublished": paper["publication_date"],
            }
        )
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": f"{url}#collection",
                "url": url,
                "name": local["title"],
                "description": local["dek"],
                "inLanguage": "en" if language == "en" else "zh-CN",
                "isPartOf": {"@id": WEBSITE_ID},
                "about": {"@type": "Thing", "name": local["title"]},
                "mainEntity": {"@id": f"{url}#papers"},
            },
            {
                "@type": "ItemList",
                "@id": f"{url}#papers",
                "numberOfItems": len(path["members"]),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "url": page_url(papers_by_slug[item["paper_slug"]], language),
                        "name": papers_by_slug[item["paper_slug"]]["title"],
                    }
                    for index, item in enumerate(path["members"], 1)
                ],
            },
            {
                "@type": "BreadcrumbList",
                "@id": f"{url}#breadcrumbs",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{BASE_URL}/"},
                    {"@type": "ListItem", "position": 2, "name": "Research", "item": f"{BASE_URL}{prefix}/research/"},
                    {"@type": "ListItem", "position": 3, "name": local["title"], "item": url},
                ],
            },
            *article_nodes,
        ],
    }


def render_research_path(
    path: dict[str, Any],
    papers_by_slug: dict[str, dict[str, Any]],
    notes_by_slug: dict[str, dict[str, Any]],
    language: str,
    *,
    preview: bool = False,
) -> str:
    is_en = language == "en"
    local = path[language]
    prefix = "" if is_en else "/zh"
    lang_code = "en" if is_en else "zh-CN"
    other_code = "zh-CN" if is_en else "en"
    url = research_path_url(path, language)
    other_url = research_path_url(path, "zh" if is_en else "en")
    review_pending = preview or path["status"] == "ready_for_review"
    robots = "noindex,nofollow" if review_pending else "index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"
    role_labels = {
        "en": {"foundation": "Foundation", "core": "Core work", "bridge": "Bridge", "framing": "Field framing", "horizon": "Research horizon"},
        "zh": {"foundation": "基础工作", "core": "核心工作", "bridge": "衔接工作", "framing": "领域框架", "horizon": "长期方向"},
    }
    members_by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for member in path["members"]:
        members_by_stage[member["stage_key"]].append(member)
    stages = []
    for index, stage in enumerate(local["stages"], 1):
        stage_members = []
        for member in members_by_stage[stage["key"]]:
            paper = papers_by_slug[member["paper_slug"]]
            note = notes_by_slug.get(paper["slug"])
            note_link = ""
            if note:
                note_label = "Research Note" if is_en else "英文 Research Note"
                note_link = f'<a href="/research-notes/{paper["slug"]}/">{note_label}</a>'
            links = f'<a class="primary" href="{prefix}/publications/{paper["slug"]}/">{"Paper record" if is_en else "论文记录"}</a>{note_link}'
            stage_members.append(
                f"""<article class="path-paper-card">
  <div class="path-paper-head"><span class="path-role">{esc(role_labels[language][member['role']])}</span><span>{esc(str(paper['year']))}</span></div>
  <h3><a href="{prefix}/publications/{paper['slug']}/">{esc(paper['title'])}</a></h3>
  <p>{esc(member[f'{language}_relation'])}</p>
  <div class="links">{links}</div>
</article>"""
            )
        paragraphs = "".join(f"<p>{esc(value)}</p>" for value in stage["paragraphs"])
        stages.append(
            f"""<section class="path-stage" id="stage-{index}">
  <div class="stage-marker" aria-hidden="true">{index:02d}</div>
  <div class="stage-content"><h2>{esc(stage['heading'])}</h2>{paragraphs}<div class="path-paper-grid">{''.join(stage_members)}</div></div>
</section>"""
        )
    intro = "".join(f"<p>{esc(value)}</p>" for value in local["intro"])
    boundaries = "".join(f"<p>{esc(value)}</p>" for value in local["boundaries"]["paragraphs"])
    open_questions = "".join(f"<p>{esc(value)}</p>" for value in local["open_questions"]["paragraphs"])
    status = (
        "Research path · author review pending"
        if is_en and review_pending
        else "研究路径 · 等待作者审阅"
        if review_pending
        else "Research path"
        if is_en
        else "研究路径"
    )
    schema = research_path_schema(path, papers_by_slug, language)
    return f"""<!doctype html>
<html lang="{lang_code}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(local['title'])} | Yuanzhi Liang</title>
  <meta name="description" content="{esc(local['dek'])}">
  <meta name="robots" content="{robots}">
  <link rel="canonical" href="{url}">
  <link rel="alternate" hreflang="{lang_code}" href="{url}">
  <link rel="alternate" hreflang="{other_code}" href="{other_url}">
  <link rel="alternate" hreflang="x-default" href="{research_path_url(path, 'en')}">
  <link rel="alternate" type="application/json" title="Research path data" href="/research/paths.json">
  <link rel="license" href="{CC_BY_URL}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(local['title'])} | Yuanzhi Liang">
  <meta property="og:description" content="{esc(local['dek'])}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{BASE_URL}/img/liangyzh.jpg">
  <link rel="stylesheet" href="/dist/css/screen.css">
  <script type="application/ld+json">
{json_script(schema)}
  </script>
</head>
<body class="pub-page research-page">
  <a class="skip-link" href="#main">{'Skip to content' if is_en else '跳到正文'}</a>
  {nav(language, 'research')}
  <main id="main" class="research-container path-detail">
    {home_return(language)}
    <nav class="note-breadcrumb" aria-label="Breadcrumb"><a href="{prefix}/research/">{'Research' if is_en else '研究方向'}</a><span aria-hidden="true">/</span><span aria-current="page">{esc(local['short_title'])}</span></nav>
    <nav class="path-return-bar" aria-label="{'Research Path navigation' if is_en else '研究路径导航'}"><a href="{prefix}/research/#research-paths"><span class="path-return-arrow" aria-hidden="true">←</span><span><strong>{'All Research Paths' if is_en else '全部研究路径'}</strong><small>{'Choose another path' if is_en else '重新选择研究路径'}</small></span></a></nav>
    <header class="research-hero path-hero">
      <p class="eyebrow">{esc(status)}</p>
      <h1>{esc(local['title'])}</h1>
      <p class="research-dek">{esc(local['dek'])}</p>
      <p class="language-switch"><a href="{other_url}" hreflang="{other_code}">{'中文' if is_en else 'English'}</a></p>
    </header>
    <section class="path-question-block"><p class="eyebrow">{'Core question' if is_en else '核心问题'}</p><h2>{esc(local['question'])}</h2><p>{esc(local['thesis'])}</p></section>
    <section class="research-intro">{intro}</section>
    <div class="path-timeline">{''.join(stages)}</div>
    <section class="path-boundary"><h2>{esc(local['boundaries']['heading'])}</h2>{boundaries}</section>
    <section class="path-open"><h2>{esc(local['open_questions']['heading'])}</h2>{open_questions}</section>
    <section class="citation-ready"><h2>{'Read and cite the papers' if is_en else '阅读并引用论文'}</h2><p>{'This page connects collaborative research contributions; it does not replace the individual papers. Use each canonical paper record for evidence, source links, and citation downloads.' if is_en else '本页用于连接多项合作研究，不替代单篇论文。请通过各论文规范记录核对证据、原始来源并下载引用。'}</p></section>
    <nav class="path-return-panel" aria-label="{'Choose another Research Path' if is_en else '选择其他研究路径'}"><div><p class="eyebrow">{'Research map' if is_en else '研究地图'}</p><h2>{'Continue through another path' if is_en else '继续浏览其他研究路径'}</h2><p>{'Return to the overview to compare the three paths or choose a different line of work.' if is_en else '返回总览，对照三条研究路径，或选择另一条研究主线。'}</p></div><a href="{prefix}/research/#research-paths">{'Choose another Research Path' if is_en else '选择其他研究路径'} <span aria-hidden="true">→</span></a></nav>
  </main>
  <footer class="site-footer"><p>© Yuanzhi Liang · <a href="/LICENSE-CONTENT.md">Content license</a> · <a href="/feed.xml">Research feed</a></p></footer>
</body>
</html>
"""


def public_research_paths_record(
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    papers_by_slug: dict[str, dict[str, Any]],
    notes_by_slug: dict[str, dict[str, Any]],
    *,
    include_review: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "canonical_url": f"{BASE_URL}/research/",
        "hub": (
            {
                "urls": {"en": f"{BASE_URL}/research/", "zh-CN": f"{BASE_URL}/zh/research/"},
                "status": hub["status"],
                **({"published_on": hub["published_on"]} if hub.get("published_on") else {}),
                "content": {"en": hub["en"], "zh-CN": hub["zh"]},
                "arc": hub["arc"],
                "horizon": hub["horizon"],
                "methodology": hub["methodology"],
                "adjacent": hub["adjacent"],
            }
            if hub and (include_review or hub["status"] == "published")
            else None
        ),
        "paths": [
            {
                "slug": path["slug"],
                "order": path["order"],
                "status": path["status"],
                **({"published_on": path["published_on"]} if path.get("published_on") else {}),
                "urls": {"en": research_path_url(path, "en"), "zh-CN": research_path_url(path, "zh")},
                "content": {"en": path["en"], "zh-CN": path["zh"]},
                "papers": [
                    {
                        "paper_slug": member["paper_slug"],
                        "title": papers_by_slug[member["paper_slug"]]["title"],
                        "year": papers_by_slug[member["paper_slug"]]["year"],
                        "role": member["role"],
                        "stage_key": member["stage_key"],
                        "relationship": {"en": member["en_relation"], "zh-CN": member["zh_relation"]},
                        "paper_urls": {
                            "en": page_url(papers_by_slug[member["paper_slug"]], "en"),
                            "zh-CN": page_url(papers_by_slug[member["paper_slug"]], "zh"),
                        },
                        **(
                            {"research_note_url": research_note_url(notes_by_slug[member["paper_slug"]])}
                            if member["paper_slug"] in notes_by_slug
                            else {}
                        ),
                    }
                    for member in path["members"]
                ],
            }
            for path in sorted(paths, key=lambda item: item["order"])
            if include_review or path["status"] == "published"
        ],
    }


def paper_citation_text(paper: dict[str, Any]) -> str:
    authors = format_authors(paper["authors"])
    status = publication_status(paper)
    container = citation_container(paper)
    year = str(paper["year"])
    if status == "forthcoming":
        year = f"{year}, forthcoming"
    parts = [f"{authors}. “{paper['title']}.” {container} ({year})"]
    if paper.get("volume"):
        volume = str(paper["volume"])
        if paper.get("issue"):
            volume += f"({paper['issue']})"
        parts.append(volume)
    if paper.get("pages"):
        parts.append(f"{paper['pages']}")
    elif paper.get("article_number"):
        parts.append(f"article {paper['article_number']}")
    text = ", ".join(parts) + "."
    if paper.get("doi"):
        text += f" https://doi.org/{paper['doi']}."
    elif include_arxiv_in_citation(paper):
        text += f" arXiv:{paper['arxiv_id']}."
    return text


def bibtex(paper: dict[str, Any]) -> str:
    entry_type = {"journal": "article", "conference": "inproceedings", "preprint": "misc"}[paper["kind"]]
    fields: list[tuple[str, str]] = [
        ("title", "{" + paper["title"] + "}"),
        ("author", " and ".join(bibtex_person(author) for author in paper["authors"])),
        ("year", str(paper["year"])),
    ]
    if paper["kind"] == "journal":
        fields.append(("journal", citation_container(paper)))
    elif paper["kind"] == "conference":
        fields.append(("booktitle", citation_container(paper)))
    else:
        fields.append(("howpublished", "arXiv preprint"))
    if paper.get("editors"):
        fields.append(
            ("editor", " and ".join(bibtex_person(editor) for editor in paper["editors"]))
        )
    if paper.get("publisher"):
        fields.append(("publisher", paper["publisher"]))
    published_parts = date_parts(paper["publication_date"])
    if len(published_parts) >= 2:
        fields.append(("month", MONTH_NAMES[published_parts[1]]))
    if paper.get("volume"):
        fields.append(("volume", str(paper["volume"])))
    if paper.get("issue"):
        fields.append(("number", str(paper["issue"])))
    if paper.get("pages"):
        fields.append(("pages", bibtex_pages(str(paper["pages"]))))
    elif paper.get("article_number"):
        fields.append(("eid", str(paper["article_number"])))
    if paper.get("doi"):
        fields.append(("doi", paper["doi"]))
    if include_arxiv_in_citation(paper):
        fields.extend(
            [
                ("eprint", paper["arxiv_id"]),
                ("archivePrefix", "arXiv"),
                *(
                    [("primaryClass", paper["arxiv_primary_class"])]
                    if paper.get("arxiv_primary_class")
                    else []
                ),
            ]
        )
    if publication_status(paper) == "forthcoming":
        fields.append(("note", "Forthcoming; final DOI and pagination pending"))
    fields.append(("url", citation_url(paper)))
    body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields)
    return f"@{entry_type}{{{paper['citation_key']},\n{body}\n}}\n"


def ris(paper: dict[str, Any]) -> str:
    ris_type = {"journal": "JOUR", "conference": "CPAPER", "preprint": "RPRT"}[paper["kind"]]
    lines = [f"TY  - {ris_type}", f"TI  - {paper['title']}"]
    lines.extend(f"AU  - {bibtex_person(author)}" for author in paper["authors"])
    lines.append(f"PY  - {paper['year']}")
    exact_date = ris_date(paper["publication_date"])
    if exact_date:
        lines.append(f"DA  - {exact_date}")
    lines.append(f"T2  - {citation_container(paper)}")
    for editor in paper.get("editors", []):
        lines.append(f"ED  - {bibtex_person(editor)}")
    if paper.get("publisher"):
        lines.append(f"PB  - {paper['publisher']}")
    if paper.get("volume"):
        lines.append(f"VL  - {paper['volume']}")
    if paper.get("issue"):
        lines.append(f"IS  - {paper['issue']}")
    if paper.get("pages"):
        first, _, last = paper["pages"].partition("-")
        lines.append(f"SP  - {first}")
        if last:
            lines.append(f"EP  - {last}")
    elif paper.get("article_number"):
        lines.append(f"C7  - {paper['article_number']}")
    if paper.get("doi"):
        lines.append(f"DO  - {paper['doi']}")
    if include_arxiv_in_citation(paper):
        lines.extend(
            [
                f"AN  - arXiv:{paper['arxiv_id']}",
                "DB  - arXiv",
                f"M3  - {'Preprint' if paper['kind'] == 'preprint' else 'Forthcoming conference paper'}",
            ]
        )
    if publication_status(paper) == "forthcoming":
        lines.append("N1  - Forthcoming; final DOI and pagination pending.")
    lines.extend(
        [
            f"UR  - {citation_url(paper)}",
            f"AB  - {paper['abstract']}",
            "ER  -",
        ]
    )
    return "\n".join(lines) + "\n"


def csl_item(paper: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": paper["citation_key"],
        "type": {
            "journal": "article-journal",
            "conference": "paper-conference",
            "preprint": "article",
        }[paper["kind"]],
        "title": paper["title"],
        "author": [
            {"given": split_person_name(author)[0], "family": split_person_name(author)[1]}
            for author in paper["authors"]
        ],
        "container-title": citation_container(paper),
        "issued": {"date-parts": [date_parts(paper["publication_date"])]},
        "URL": citation_url(paper),
        "abstract": paper["abstract"],
        "keyword": ", ".join(paper["keywords"]),
    }
    if paper.get("editors"):
        item["editor"] = [
            {"given": split_person_name(editor)[0], "family": split_person_name(editor)[1]}
            for editor in paper["editors"]
        ]
    if paper.get("publisher"):
        item["publisher"] = paper["publisher"]
    if paper.get("doi"):
        item["DOI"] = paper["doi"]
    if paper.get("volume"):
        item["volume"] = str(paper["volume"])
    if paper.get("issue"):
        item["issue"] = str(paper["issue"])
    if paper.get("pages"):
        item["page"] = paper["pages"]
    elif paper.get("article_number"):
        item["page"] = str(paper["article_number"])
    if include_arxiv_in_citation(paper):
        item["archive"] = "arXiv"
        item["archive_location"] = paper["arxiv_id"]
        item["genre"] = (
            "Preprint" if paper["kind"] == "preprint" else "Forthcoming conference paper"
        )
    if publication_status(paper) == "forthcoming":
        item["status"] = "forthcoming"
    return item


def public_record(
    paper: dict[str, Any],
    paper_paths: list[tuple[dict[str, Any], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    paper_paths = paper_paths or []
    return {
        "schema_version": 1,
        "slug": paper["slug"],
        "canonical_url": page_url(paper, "en"),
        "language_urls": {
            "en": page_url(paper, "en"),
            "zh-CN": page_url(paper, "zh"),
        },
        "title": paper["title"],
        "short_title": paper["short_title"],
        "authors": paper["authors"],
        "publication": {
            "kind": paper["kind"],
            "venue": paper["venue"],
            "citation_container_title": citation_container(paper),
            "status": publication_status(paper),
            "year": paper["year"],
            "publication_date": paper["publication_date"],
            **({"online_date": paper["online_date"]} if paper.get("online_date") else {}),
            **({"print_date": paper["print_date"]} if paper.get("print_date") else {}),
            **({"publisher": paper["publisher"]} if paper.get("publisher") else {}),
            **({"editors": paper["editors"]} if paper.get("editors") else {}),
            **({"volume": paper["volume"]} if paper.get("volume") else {}),
            **({"issue": paper["issue"]} if paper.get("issue") else {}),
            **({"pages": paper["pages"]} if paper.get("pages") else {}),
            **(
                {"article_number": paper["article_number"]}
                if paper.get("article_number")
                else {}
            ),
            **(
                {"alternate_pagination": paper["alternate_pagination"]}
                if paper.get("alternate_pagination")
                else {}
            ),
        },
        "identifiers": {
            **({"doi": paper["doi"]} if paper.get("doi") else {}),
            **({"arxiv": paper["arxiv_id"]} if paper.get("arxiv_id") else {}),
            **(
                {"arxiv_primary_class": paper["arxiv_primary_class"]}
                if paper.get("arxiv_primary_class")
                else {}
            ),
        },
        "arxiv_dates": {
            **({"first_posted": paper["arxiv_posted"]} if paper.get("arxiv_posted") else {}),
            **({"last_revised": paper["arxiv_updated"]} if paper.get("arxiv_updated") else {}),
        },
        "keywords": paper["keywords"],
        "official_abstract": paper["abstract"],
        "official_abstract_rights": "Excluded from the site's CC BY 4.0 license; original paper rights apply.",
        "primary_source": paper["source"],
        "source_checked": paper["source_checked"],
        "verification_status": paper["verification_status"],
        **(
            {"bibliographic_note": paper["bibliographic_note"]}
            if paper.get("bibliographic_note")
            else {}
        ),
        **(
            {"author_verified_on": paper["author_verified_on"]}
            if paper.get("author_verified_on")
            else {}
        ),
        "commentary": {
            "license": CC_BY_URL,
            "en": paper["en"],
            "zh-CN": paper["zh"],
        },
        "research_paths": [
            {
                "slug": path["slug"],
                "role": member["role"],
                "urls": {
                    "en": research_path_url(path, "en"),
                    "zh-CN": research_path_url(path, "zh"),
                },
                "names": {
                    "en": path["en"]["title"],
                    "zh-CN": path["zh"]["title"],
                },
                "relationship": {
                    "en": member["en_relation"],
                    "zh-CN": member["zh_relation"],
                },
            }
            for path, member in paper_paths
        ],
        "citation": csl_item(paper),
        "resources": paper["links"],
    }


def llms_txt(
    papers: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    papers_by_slug: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "# Yuanzhi Liang — Research Publications",
        "",
        "> Canonical, source-checked research records for Yuanzhi Liang (梁远智; ORCID 0009-0008-2746-5947).",
        "",
        "Use the local research-record links below for structured metadata, official abstracts, source-checked explainers, claim-to-source mappings, and downloadable citations. Cite the scholarly paper for scientific claims.",
        "",
        "## Core pages",
        "",
        f"- [Homepage]({BASE_URL}/): identity, biography, affiliations, and selected work.",
        f"- [English publication catalog]({BASE_URL}/publications/): all research records.",
        f"- [中文论文目录]({BASE_URL}/zh/publications/): Chinese explainers.",
        f"- [CSL-JSON catalog]({BASE_URL}/publications/catalog.json): machine-readable bibliography.",
        f"- [Full JSON research records]({BASE_URL}/publications/records.json): metadata, abstracts, summaries, scope, and source mappings.",
        f"- [Full publication corpus]({BASE_URL}/llms-full.txt): abstracts and source-checked summaries.",
        f"- [Atom feed]({BASE_URL}/feed.xml): update discovery.",
        "",
    ]
    public_paths = published_paths(paths)
    if hub and hub["status"] == "published" and public_paths:
        lines.extend(
            [
                f"- [Research paths]({BASE_URL}/research/): {hub['en']['dek']}",
                f"- [研究方向]({BASE_URL}/zh/research/): {hub['zh']['dek']}",
                f"- [Research path data]({BASE_URL}/research/paths.json): bilingual path-to-paper relationships.",
                "",
                "## Research paths",
                "",
            ]
        )
        for path in public_paths:
            lines.append(
                f"- [{path['en']['title']}]({research_path_url(path, 'en')}) — {path['en']['dek']}"
            )
        lines.append("")
    public_notes = published_notes(notes)
    if public_notes:
        lines.extend(
            [
                f"- [Research Notes]({BASE_URL}/research-notes/): long-form, source-linked paper explanations.",
                "",
                "## Research Notes",
                "",
            ]
        )
        for note in public_notes:
            paper = papers_by_slug[note["paper_slug"]]
            lines.append(
                f"- [{note['title']}]({research_note_url(note)}) — explainer for “{paper['title']}.”"
            )
        lines.extend(["", "## Research records", ""])
    else:
        lines.extend(["## Research records", ""])
    for paper in papers:
        identifiers = []
        if paper.get("doi"):
            identifiers.append(f"DOI {paper['doi']}")
        if paper.get("arxiv_id"):
            identifiers.append(f"arXiv {paper['arxiv_id']}")
        suffix = f" — {paper['venue']} {paper['year']}"
        if identifiers:
            suffix += f"; {', '.join(identifiers)}"
        lines.append(f"- [{paper['title']}]({page_url(paper, 'en')}){suffix}.")
    lines.extend(
        [
            "",
            "## Reuse and verification",
            "",
            "- Original site commentary is CC BY 4.0 with attribution and a link to the canonical record.",
            "- Paper titles, abstracts, figures, and bibliographic metadata are excluded from that license and retain their original rights.",
            (
                f"- All {len(papers)} research records are author-verified; the verification date is exposed in each full record."
                if all(
                    paper["verification_status"] == "author-verified"
                    for paper in papers
                )
                else "- Records marked “author verification pending” have been checked against the stated primary source but are not yet labeled author-verified."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def llms_full_txt(
    papers: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    papers_by_slug: dict[str, dict[str, Any]],
) -> str:
    lines = [
        "# Yuanzhi Liang — Full Research Retrieval Corpus",
        "",
        "Canonical catalog: https://akira-l.github.io/publications/",
        "Identity: Yuanzhi Liang (梁远智), ORCID 0009-0008-2746-5947",
        "",
        "Citation rule: cite the scholarly paper for scientific claims. Cite a local explainer only when reusing its original commentary.",
        "License rule: original commentary is CC BY 4.0. Paper abstracts and bibliographic metadata retain their original rights.",
        "",
    ]
    if hub and hub["status"] == "published":
        local = hub["en"]
        lines.extend(
            [
                f"## Research map: {local['title']}",
                "",
                f"- Canonical page: {BASE_URL}/research/",
                f"- Chinese page: {BASE_URL}/zh/research/",
                "",
                local["dek"],
                *local["intro"],
                "",
                f"### {local['methodology_title']}",
                "",
                local["methodology_intro"],
            ]
        )
        for item in hub["methodology"]:
            lines.extend([f"#### {item['en']['heading']}", "", item["en"]["text"], ""])
        lines.extend([f"### {local['adjacent_title']}", "", local["adjacent_intro"], ""])
        for item in hub["adjacent"]:
            paper = papers_by_slug[item["paper_slug"]]
            lines.extend([f"- {paper['title']}: {item['en']}", ""])
        lines.extend([*local["closing"], ""])
    for path in published_paths(paths):
        local = path["en"]
        lines.extend(
            [
                f"## Research path: {local['title']}",
                "",
                f"- Canonical page: {research_path_url(path, 'en')}",
                f"- Chinese page: {research_path_url(path, 'zh')}",
                f"- Published: {path['published_on']}",
                "",
                local["dek"],
                "",
                f"Core question: {local['question']}",
                local["thesis"],
                *local["intro"],
                "",
            ]
        )
        members_by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for member in path["members"]:
            members_by_stage[member["stage_key"]].append(member)
        for stage in local["stages"]:
            lines.extend([f"### {stage['heading']}", "", *stage["paragraphs"], ""])
            for member in members_by_stage[stage["key"]]:
                paper = papers_by_slug[member["paper_slug"]]
                lines.append(
                    f"- [{paper['title']}]({page_url(paper, 'en')}) — {member['en_relation']}"
                )
            lines.append("")
        lines.extend(
            [
                f"### {local['boundaries']['heading']}",
                "",
                *local["boundaries"]["paragraphs"],
                "",
                f"### {local['open_questions']['heading']}",
                "",
                *local["open_questions"]["paragraphs"],
                "",
            ]
        )
    for note in published_notes(notes):
        paper = papers_by_slug[note["paper_slug"]]
        body = [*note["lede"], note["takeaway"]]
        for section in note["sections"]:
            body.extend([section["heading"], *section["paragraphs"]])
        lines.extend(
            [
                f"## Research Note: {note['title']}",
                "",
                f"- Canonical note: {research_note_url(note)}",
                f"- Based on paper record: {page_url(paper, 'en')}",
                f"- Published: {note['published_on']}",
                f"- Topics: {', '.join(note['keywords'])}",
                "",
                *body,
                "",
            ]
        )
    for paper in papers:
        verification = (
            f"source-checked {paper['source_checked']}; "
            f"author-verified {paper['author_verified_on']}"
            if paper["verification_status"] == "author-verified"
            else f"source-checked {paper['source_checked']}; author verification pending"
        )
        lines.extend(
            [
                f"## {paper['title']}",
                "",
                f"- Canonical record: {page_url(paper, 'en')}",
                f"- Chinese record: {page_url(paper, 'zh')}",
                f"- Authors: {format_authors(paper['authors'])}",
                f"- Venue: {venue_line(paper, 'en')}",
                f"- Primary source: {paper['source']['url']}",
                f"- Source version checked: {paper['source']['version']}",
                f"- Verification: {verification}",
                f"- Keywords: {', '.join(paper['keywords'])}",
                "",
                "Official abstract (original paper copyright):",
                paper["abstract"],
                "",
                "Source-checked English summary (CC BY 4.0):",
                paper["en"]["summary"],
                "",
                "Citation-ready neutral description (CC BY 4.0):",
                paper["en"]["citation_ready"],
                "",
                "中文来源核验摘要（CC BY 4.0）：",
                paper["zh"]["summary"],
                "",
            ]
        )
    return "\n".join(lines)


def atom_feed(
    papers: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    papers_by_slug: dict[str, dict[str, Any]],
) -> str:
    public_notes = published_notes(notes)
    dates = [p["source_checked"] for p in papers]
    dates.extend(note["published_on"] for note in public_notes)
    public_paths = published_paths(paths)
    dates.extend(path["published_on"] for path in public_paths)
    if hub and hub["status"] == "published":
        dates.append(hub["published_on"])
    updated = max(dates) + "T00:00:00+08:00"
    entries = []
    for path in public_paths:
        url = research_path_url(path, "en")
        entries.append(
            f"""  <entry>
    <title>{xml_escape(path['en']['title'])}</title>
    <id>{url}</id>
    <link href="{url}"/>
    <updated>{path['published_on']}T00:00:00+08:00</updated>
    <published>{path['published_on']}T00:00:00+08:00</published>
    <author><name>Yuanzhi Liang</name></author>
    <category term="Research Path"/>
    <summary>{xml_escape(path['en']['dek'])}</summary>
  </entry>"""
        )
    for note in public_notes:
        paper = papers_by_slug[note["paper_slug"]]
        url = research_note_url(note)
        entries.append(
            f"""  <entry>
    <title>{xml_escape(note['title'])}</title>
    <id>{url}</id>
    <link href="{url}"/>
    <updated>{note['published_on']}T00:00:00+08:00</updated>
    <published>{note['published_on']}T00:00:00+08:00</published>
    <author><name>Yuanzhi Liang</name></author>
    <category term="Research Note"/>
    <summary>{xml_escape(note['dek'])} Based on: {xml_escape(paper['title'])}.</summary>
  </entry>"""
        )
    for paper in papers[:20]:
        url = page_url(paper, "en")
        entries.append(
            f"""  <entry>
    <title>{xml_escape(paper['title'])}</title>
    <id>{url}</id>
    <link href="{url}"/>
    <updated>{paper['source_checked']}T00:00:00+08:00</updated>
    <published>{atom_date(paper['publication_date'])}T00:00:00Z</published>
    <author><name>Yuanzhi Liang</name></author>
    <summary>{xml_escape(paper['en']['summary'])}</summary>
  </entry>"""
        )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Yuanzhi Liang — Research updates</title>
  <id>{BASE_URL}/feed.xml</id>
  <link href="{BASE_URL}/feed.xml" rel="self"/>
  <link href="{BASE_URL}/publications/"/>
  <updated>{updated}</updated>
  <author><name>Yuanzhi Liang</name></author>
{''.join(entries)}
</feed>
"""


def sitemap(
    papers: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
) -> str:
    rows = [
        (
            f"{BASE_URL}/",
            max(p["source_checked"] for p in papers),
            None,
            None,
        ),
        (
            f"{BASE_URL}/publications/",
            max(p["source_checked"] for p in papers),
            f"{BASE_URL}/publications/",
            f"{BASE_URL}/zh/publications/",
        ),
        (
            f"{BASE_URL}/zh/publications/",
            max(p["source_checked"] for p in papers),
            f"{BASE_URL}/publications/",
            f"{BASE_URL}/zh/publications/",
        ),
    ]
    for paper in papers:
        rows.extend(
            [
                (page_url(paper, "en"), paper["source_checked"], page_url(paper, "en"), page_url(paper, "zh")),
                (page_url(paper, "zh"), paper["source_checked"], page_url(paper, "en"), page_url(paper, "zh")),
            ]
        )
    if hub and hub["status"] == "published":
        rows.extend(
            [
                (f"{BASE_URL}/research/", hub["published_on"], f"{BASE_URL}/research/", f"{BASE_URL}/zh/research/"),
                (f"{BASE_URL}/zh/research/", hub["published_on"], f"{BASE_URL}/research/", f"{BASE_URL}/zh/research/"),
            ]
        )
    for path in published_paths(paths):
        rows.extend(
            [
                (research_path_url(path, "en"), path["published_on"], research_path_url(path, "en"), research_path_url(path, "zh")),
                (research_path_url(path, "zh"), path["published_on"], research_path_url(path, "en"), research_path_url(path, "zh")),
            ]
        )
    public_notes = published_notes(notes)
    if public_notes:
        latest_note = max(note["published_on"] for note in public_notes)
        rows.append((f"{BASE_URL}/research-notes/", latest_note, None, None))
        rows.extend(
            (research_note_url(note), note["published_on"], None, None)
            for note in public_notes
        )
    body = []
    for loc, modified, en_url, zh_url in rows:
        alternates = ""
        if en_url and zh_url:
            alternates = (
                f'\n    <xhtml:link rel="alternate" hreflang="en" href="{en_url}"/>'
                f'\n    <xhtml:link rel="alternate" hreflang="zh-CN" href="{zh_url}"/>'
                f'\n    <xhtml:link rel="alternate" hreflang="x-default" href="{en_url}"/>'
            )
        body.append(
            f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{modified}</lastmod>{alternates}\n  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(body)
        + "\n</urlset>\n"
    )


def robots_txt() -> str:
    agents = [
        "*",
        "Googlebot",
        "Google-Extended",
        "bingbot",
        "Baiduspider",
        "OAI-SearchBot",
        "GPTBot",
        "ChatGPT-User",
        "ClaudeBot",
        "Claude-SearchBot",
        "Claude-User",
        "PerplexityBot",
        "Perplexity-User",
        "Bytespider",
    ]
    blocks = [f"User-agent: {agent}\nAllow: /" for agent in agents]
    return (
        "# Crawler access policy.\n"
        + "\n\n".join(blocks)
        + f"\n\nSitemap: {BASE_URL}/sitemap.xml\n"
    )


def replace_homepage_block(source: str, name: str, content: str | None) -> str:
    start = f"<!-- {name}_START -->"
    end = f"<!-- {name}_END -->"
    pattern = re.compile(rf"({re.escape(start)})(.*?)({re.escape(end)})", re.S)
    match = pattern.search(source)
    if not match:
        raise ValueError(f"index.html is missing {name} markers")
    replacement = match.group(2) if content is None else f"\n{content}\n\t  "
    return source[: match.start()] + match.group(1) + replacement + match.group(3) + source[match.end() :]


def de_emphasize_homepage_background_publications(source: str) -> str:
    """Keep background publications in the catalog without featuring them at home."""
    source = source.replace("Recent Preprints and Surveys", "Recent Work", 1)
    for slug in ("rl-vgm",):
        pattern = re.compile(
            rf'\s*<li\b[^>]*>(?:(?!</li>).)*?'
            rf'href="{re.escape(BASE_URL)}/publications/{re.escape(slug)}/"'
            rf'(?:(?!</li>).)*?</li>',
            re.S,
        )
        source = pattern.sub("", source, count=1)
    return source


def link_homepage_publication_titles(source: str) -> str:
    """Give each homepage paper record a descriptive, crawlable internal link."""
    pattern = re.compile(
        rf'(<li>)(?!<a class="publication-title")'
        rf'(?P<title>[^<]+)'
        rf'(?= <span class="pub-badges"><a class="badge-tldr" '
        rf'href="(?P<url>{re.escape(BASE_URL)}/publications/[^"/]+/)")'
    )

    def replace(match: re.Match[str]) -> str:
        return (
            f'{match.group(1)}<a class="publication-title" '
            f'href="{match.group("url")}">{match.group("title")}</a>'
        )

    return pattern.sub(replace, source)


def normalize_homepage_publication_venues(source: str) -> str:
    """Use the same venue-only line for accepted and published homepage papers."""
    return re.sub(
        r"(?<=<br>)\s*Accepted by (?P<venue>[^<\r\n]+?)\s*(?=<br>)",
        r" \g<venue> ",
        source,
    )


def render_homepage_research(
    source: str,
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    *,
    preview: bool = False,
) -> str:
    source = de_emphasize_homepage_background_publications(source)
    source = link_homepage_publication_titles(source)
    source = normalize_homepage_publication_venues(source)
    if not hub:
        return replace_homepage_block(source, "RESEARCH_PATHS", "")
    if preview or hub["status"] == "ready_for_review":
        public_robots = (
            '<meta name="robots" '
            'content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">'
        )
        if public_robots not in source:
            raise ValueError("index.html is missing the expected robots directive")
        source = source.replace(
            public_robots,
            '<meta name="robots" content="noindex,nofollow">',
            1,
        )
    profile = "\n\n".join(
        f'\t\t\t<p>{esc(paragraph)}</p>' for paragraph in hub["en"]["profile_paragraphs"]
    )
    source = replace_homepage_block(source, "RESEARCH_PROFILE", profile)
    return replace_homepage_block(source, "RESEARCH_PATHS", "")


def author_review(papers: list[dict[str, Any]]) -> str:
    verified_count = sum(
        paper["verification_status"] == "author-verified" for paper in papers
    )
    all_verified = verified_count == len(papers)
    lines = [
        "# Author verification checklist",
        "",
        f"Generated from `data/publications.json`. **{verified_count} of {len(papers)} records are author-verified.**",
        "",
        "For each paper, confirm: exact title and author order; venue/status/date; abstract version; method names; evaluation wording; limitations; and the citation-ready sentence. Scientific claims must cite the paper, not the explainer.",
        "",
        "Known corrections already incorporated include the current AntEval title and metrics, TaRoS v4 method description, InterSyn INS/REC formulation, VAST StoryForge/VisionForge stages, IcoCap ICS/VGC components, Rain-One-Go CCN/RainDS design, MHEM expansion and final issue metadata, and `Haibin Huang` spelling.",
        "",
    ]
    for paper in papers:
        checkbox = "x" if paper["verification_status"] == "author-verified" else " "
        identifiers = []
        if paper.get("doi"):
            identifiers.append(f"DOI `{paper['doi']}`")
        if paper.get("arxiv_id"):
            identifiers.append(f"arXiv `{paper['arxiv_id']}`")
        lines.extend(
            [
                f"## [{checkbox}] {paper['short_title']} — {paper['title']}",
                "",
                f"- Authors: {format_authors(paper['authors'])}",
                f"- Publication: {venue_line(paper, 'en')}",
                f"- Citation status/version: {publication_status(paper)}; {citation_container(paper)}",
                *([f"- Identifiers: {', '.join(identifiers)}"] if identifiers else []),
                f"- Checked source: [{paper['source']['label']}]({paper['source']['url']}) ({paper['source']['version']})",
                (
                    f"- Author verification: approved {paper['author_verified_on']}."
                    if paper["verification_status"] == "author-verified"
                    else "- Author verification: pending."
                ),
                *(
                    [f"- Bibliographic note to approve: {paper['bibliographic_note']}"]
                    if paper.get("bibliographic_note")
                    else []
                ),
                *(
                    [
                        "- Alternate-copy pagination: "
                        f"{paper['alternate_pagination']['pages']} "
                        f"({paper['alternate_pagination']['version']}); cited version uses "
                        f"{paper['pages']}."
                    ]
                    if paper.get("alternate_pagination")
                    else []
                ),
                f"- English summary: {paper['en']['summary']}",
                f"- 中文摘要：{paper['zh']['summary']}",
                f"- Citation-ready sentence: {paper['en']['citation_ready']}",
                "",
            ]
        )
    lines.extend(["## Approval action", ""])
    if all_verified:
        lines.extend(
            [
                "All current records are approved. If a paper’s bibliographic metadata or explanatory text changes later, reset that record to `pending-author-review`, update `source_checked`, obtain author approval again, and rerun `python _rebuild.py`.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "After every checkbox is approved, change each record’s `verification_status` from `pending-author-review` to `author-verified`, add `author_verified_on` in `YYYY-MM-DD` form, update `source_checked` if needed, and rerun `python _rebuild.py`. The generated pages will then display the approved status.",
                "",
            ]
        )
    return "\n".join(lines)


def citation_audit(papers: list[dict[str, Any]]) -> str:
    counts = defaultdict(int)
    for paper in papers:
        counts[publication_status(paper)] += 1
    lines = [
        "# Citation metadata audit",
        "",
        "Generated from `data/publications.json`. Last full source check: "
        f"{max(paper['source_checked'] for paper in papers)}.",
        "",
        f"Coverage: **{len(papers)} records** — {counts['published']} published, "
        f"{counts['forthcoming']} forthcoming, and {counts['preprint']} preprint records.",
        "",
        "## Audit method",
        "",
        f"- {sum(bool(paper.get('doi')) for paper in papers)} DOI records were resolved and compared with registrant/Crossref metadata for exact title, author order, container, volume/issue, pagination or article number, and publication date.",
        f"- {sum(bool(paper.get('arxiv_id')) for paper in papers)} arXiv records were compared with their official abstract pages for title, author order, first-posted/revised dates, and primary subject class.",
        "- Official CVF, NeurIPS, ACM, Springer, and IEEE records were used where applicable; no aggregator was allowed to override publisher metadata.",
        "- The four 2026 forthcoming venue acceptances are clearly labeled author-supplied because their paper-level final proceedings records were not public at the audit date.",
        "",
        "## Version policy",
        "",
        "- Published citations follow the DOI/version of record or the official proceedings record. A related arXiv identifier remains discoverable in the full research record, but is intentionally excluded from BibTeX/RIS/CSL so one citation never mixes two bibliographic versions.",
        "- Forthcoming conference papers use the public arXiv record until final proceedings metadata exists. Their exports explicitly say `forthcoming` and do not invent DOI, volume, or page fields.",
        "- Preprints cite arXiv as the publication and include the arXiv identifier and primary subject class.",
        "- Where IEEE/CVF version-of-record and CVF open-access copies carry different printed pagination, the IEEE version-of-record pagination is cited and the CVF pagination is recorded as an alternate copy.",
        "",
        "## Record-by-record results",
        "",
    ]
    for paper in papers:
        status = publication_status(paper)
        if status == "published":
            cited_version = (
                "DOI/version of record"
                if paper.get("doi")
                else "official proceedings record"
            )
        elif status == "forthcoming":
            cited_version = "forthcoming conference paper; arXiv is the stable public document"
        else:
            cited_version = "arXiv preprint"
        lines.extend(
            [
                f"### {paper['short_title']} — {paper['title']}",
                "",
                f"- Result: checked; citation status `{status}`.",
                f"- Exact author order: {format_authors(paper['authors'])}.",
                f"- Cited version: {cited_version}.",
                f"- Container/date: {citation_container(paper)}; {paper['publication_date']}.",
                f"- Primary metadata source: [{paper['source']['label']}]({paper['source']['url']}) ({paper['source']['version']}).",
            ]
        )
        identifiers = []
        if paper.get("doi"):
            identifiers.append(f"DOI `{paper['doi']}`")
        if paper.get("arxiv_id"):
            identifiers.append(f"arXiv `{paper['arxiv_id']}`")
        if identifiers:
            lines.append(f"- Identifiers in the full record: {', '.join(identifiers)}.")
        if paper.get("pages"):
            lines.append(f"- Cited pagination: {paper['pages']}.")
        elif paper.get("article_number"):
            lines.append(f"- Article number: {paper['article_number']}.")
        if paper.get("alternate_pagination"):
            alternate = paper["alternate_pagination"]
            lines.append(
                f"- Alternate-copy pagination: {alternate['pages']} in "
                f"[{alternate['version']}]({alternate['url']}); this is not used in the version-of-record citation."
            )
        if paper.get("bibliographic_note"):
            lines.append(f"- Note: {paper['bibliographic_note']}")
        lines.append("")
    lines.extend(
        [
            "## Automated checks",
            "",
            "Run `python tests/validate_citations.py` to compare every generated BibTeX, RIS, and CSL-JSON file field-by-field against the canonical data, including title, author order, date, container, DOI/arXiv version policy, volume, issue, pages/article number, publisher, and URL.",
            "",
        ]
    )
    return "\n".join(lines)


def validate_data(data: dict[str, Any]) -> list[dict[str, Any]]:
    papers = data.get("papers")
    if not isinstance(papers, list) or not papers:
        raise ValueError("data/publications.json must contain a non-empty papers array")
    required = {
        "slug",
        "short_title",
        "title",
        "citation_key",
        "authors",
        "kind",
        "venue",
        "year",
        "publication_date",
        "keywords",
        "abstract",
        "source",
        "source_checked",
        "verification_status",
        "links",
        "en",
        "zh",
    }
    slugs: set[str] = set()
    citation_keys: set[str] = set()
    dois: set[str] = set()
    for paper in papers:
        missing = sorted(required - set(paper))
        if missing:
            raise ValueError(f"{paper.get('slug', '<unknown>')}: missing fields {missing}")
        if paper["slug"] in slugs:
            raise ValueError(f"duplicate slug: {paper['slug']}")
        if paper["citation_key"] in citation_keys:
            raise ValueError(f"duplicate citation key: {paper['citation_key']}")
        slugs.add(paper["slug"])
        citation_keys.add(paper["citation_key"])
        if paper["kind"] not in {"journal", "conference", "preprint"}:
            raise ValueError(f"{paper['slug']}: invalid kind")
        status = publication_status(paper)
        if status not in {"published", "forthcoming", "preprint"}:
            raise ValueError(f"{paper['slug']}: invalid publication_status")
        if paper["kind"] == "preprint" and status != "preprint":
            raise ValueError(f"{paper['slug']}: preprint kind requires preprint status")
        if status == "forthcoming" and paper["kind"] != "conference":
            raise ValueError(f"{paper['slug']}: forthcoming status requires conference kind")
        if paper["verification_status"] not in {"pending-author-review", "author-verified"}:
            raise ValueError(f"{paper['slug']}: invalid verification_status")
        if "Yuanzhi Liang" not in paper["authors"]:
            raise ValueError(f"{paper['slug']}: Yuanzhi Liang missing from authors")
        if not paper["authors"] or any(not author.strip() for author in paper["authors"]):
            raise ValueError(f"{paper['slug']}: invalid authors")
        if not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", paper["publication_date"]):
            raise ValueError(f"{paper['slug']}: invalid publication_date")
        if int(paper["publication_date"][:4]) != int(paper["year"]):
            raise ValueError(f"{paper['slug']}: year does not match publication_date")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", paper["source_checked"]):
            raise ValueError(f"{paper['slug']}: invalid source_checked")
        if paper.get("doi"):
            doi = paper["doi"].lower()
            if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
                raise ValueError(f"{paper['slug']}: invalid DOI")
            if doi in dois:
                raise ValueError(f"{paper['slug']}: duplicate DOI {paper['doi']}")
            dois.add(doi)
        if paper.get("arxiv_id"):
            if not re.fullmatch(r"\d{4}\.\d{4,5}", paper["arxiv_id"]):
                raise ValueError(f"{paper['slug']}: invalid arXiv identifier")
            if not paper.get("arxiv_primary_class"):
                raise ValueError(f"{paper['slug']}: arXiv record missing primary class")
        if status in {"preprint", "forthcoming"} and not paper.get("arxiv_id"):
            raise ValueError(f"{paper['slug']}: {status} record requires arXiv identifier")
        if paper.get("pages") and paper.get("article_number"):
            raise ValueError(f"{paper['slug']}: use pages or article_number, not both")
        if paper.get("alternate_pagination"):
            alternate = paper["alternate_pagination"]
            if not paper.get("pages"):
                raise ValueError(f"{paper['slug']}: alternate pagination requires cited pages")
            if alternate["pages"] == paper["pages"]:
                raise ValueError(f"{paper['slug']}: alternate pagination duplicates cited pages")
        if len(paper["abstract"].split()) < 30:
            raise ValueError(f"{paper['slug']}: abstract appears incomplete")
        for language in ("en", "zh"):
            content = paper[language]
            for key in ("summary", "problem", "contributions", "evidence", "limitations", "positioning", "citation_ready"):
                if not content.get(key):
                    raise ValueError(f"{paper['slug']}.{language}: missing {key}")
        if paper["verification_status"] == "author-verified" and not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", paper.get("author_verified_on", "")
        ):
            raise ValueError(
                f"{paper['slug']}: author-verified requires author_verified_on in YYYY-MM-DD form"
            )
    return sorted(
        papers,
        key=lambda p: (p["publication_date"], p["title"]),
        reverse=True,
    )


def validate_research_notes(
    data: dict[str, Any],
    papers_by_slug: dict[str, dict[str, Any]],
    *,
    expected_count: int | None = None,
    allowed_statuses: set[str] | None = None,
) -> list[dict[str, Any]]:
    notes = data.get("notes")
    if data.get("schema_version") != 1 or not isinstance(notes, list):
        raise ValueError("data/research-notes.json must use schema_version 1 and contain notes")
    if len(notes) > 13:
        raise ValueError(f"expected at most 13 Research Notes, found {len(notes)}")
    if expected_count is not None and len(notes) != expected_count:
        raise ValueError(f"expected {expected_count} Research Notes, found {len(notes)}")
    required = {
        "paper_slug",
        "title",
        "dek",
        "status",
        "drafted_on",
        "retrospective",
        "retrospective_context",
        "keywords",
        "lede",
        "takeaway",
        "sections",
        "evidence",
    }
    forbidden_copies = {
        "authors",
        "year",
        "venue",
        "abstract",
        "citation",
        "doi",
        "arxiv_id",
        "paper_title",
        "paper_url",
    }
    seen: set[str] = set()
    for note in notes:
        slug = note.get("paper_slug", "<unknown>")
        missing = sorted(required - set(note))
        if missing:
            raise ValueError(f"Research Note {slug}: missing fields {missing}")
        copied = sorted(forbidden_copies & set(note))
        if copied:
            raise ValueError(
                f"Research Note {slug}: publication metadata must be referenced, not copied: {copied}"
            )
        if slug in seen:
            raise ValueError(f"duplicate Research Note paper_slug: {slug}")
        if slug not in papers_by_slug:
            raise ValueError(f"Research Note {slug}: publication record does not exist")
        seen.add(slug)
        if note["status"] not in {"ready_for_review", "published"}:
            raise ValueError(f"Research Note {slug}: invalid status")
        if allowed_statuses is not None and note["status"] not in allowed_statuses:
            raise ValueError(
                f"Research Note {slug}: status {note['status']} is not allowed in this data source"
            )
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", note["drafted_on"]):
            raise ValueError(f"Research Note {slug}: invalid drafted_on")
        if note["status"] == "published":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", note.get("published_on", "")):
                raise ValueError(f"Research Note {slug}: published status requires published_on")
        elif note.get("published_on"):
            raise ValueError(f"Research Note {slug}: draft cannot have published_on")
        paper = papers_by_slug[slug]
        should_be_retrospective = int(paper["year"]) <= 2024
        if bool(note["retrospective"]) != should_be_retrospective:
            raise ValueError(
                f"Research Note {slug}: retrospective must be {should_be_retrospective} for {paper['year']} work"
            )
        if note["retrospective"] and len(note["retrospective_context"].split()) < 12:
            raise ValueError(f"Research Note {slug}: retrospective_context is too short")
        if not note["retrospective"] and note["retrospective_context"]:
            raise ValueError(f"Research Note {slug}: current work should not set retrospective_context")
        if len(note["lede"]) != 2 or any(len(value.split()) < 45 for value in note["lede"]):
            raise ValueError(f"Research Note {slug}: lede must contain two substantial paragraphs")
        if not 5 <= len(note["sections"]) <= 8:
            raise ValueError(f"Research Note {slug}: expected 5–8 sections")
        for index, section in enumerate(note["sections"], 1):
            if not section.get("heading") or len(section.get("paragraphs", [])) < 2:
                raise ValueError(f"Research Note {slug}: section {index} is incomplete")
        if len(note["evidence"]) < 2:
            raise ValueError(f"Research Note {slug}: at least two evidence locators required")
        for item in note["evidence"]:
            locator = item.get("locator", "")
            if not item.get("claim") or not re.search(
                r"(?:p\.\s*\d|page\s+\d|Table|Figure|Section|Sec\.)",
                locator,
                re.I,
            ):
                raise ValueError(f"Research Note {slug}: evidence locator is not specific: {locator}")
        count = note_word_count(note)
        if not 1100 <= count <= 1500:
            raise ValueError(f"Research Note {slug}: {count} words; expected 1100–1500")
    return sorted(
        notes,
        key=lambda note: (
            papers_by_slug[note["paper_slug"]]["publication_date"],
            note["title"],
        ),
        reverse=True,
    )


def research_path_word_count(path: dict[str, Any]) -> int:
    local = path["en"]
    text = [local["dek"], local["question"], local["thesis"], *local["intro"]]
    for stage in local["stages"]:
        text.extend([stage["heading"], *stage["paragraphs"]])
    for member in path["members"]:
        text.append(member["en_relation"])
    text.extend(
        [
            local["boundaries"]["heading"],
            *local["boundaries"]["paragraphs"],
            local["open_questions"]["heading"],
            *local["open_questions"]["paragraphs"],
        ]
    )
    return len(re.findall(r"\b[\w’'-]+\b", " ".join(text), flags=re.UNICODE))


def research_hub_word_count(hub: dict[str, Any]) -> int:
    local = hub["en"]
    text = [
        local["dek"],
        *local["intro"],
        local["arc_title"],
        local["arc_intro"],
        local["horizon_title"],
        local["horizon_intro"],
        local["horizon_closing"],
        local["methodology_intro"],
    ]
    for item in [*hub["arc"], *hub["horizon"]]:
        text.extend([item["en"]["heading"], item["en"]["text"]])
    for item in hub["methodology"]:
        text.extend([item["en"]["heading"], item["en"]["text"]])
    text.extend([local["adjacent_intro"], *[item["en"] for item in hub["adjacent"]], *local["closing"]])
    return len(re.findall(r"\b[\w’'-]+\b", " ".join(text), flags=re.UNICODE))


def validate_research_paths(
    data: dict[str, Any],
    papers_by_slug: dict[str, dict[str, Any]],
    *,
    expected_count: int | None = None,
    allowed_statuses: set[str] | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if data.get("schema_version") != 1 or not isinstance(data.get("paths"), list):
        raise ValueError("data/research-paths.json must use schema_version 1 and contain paths")
    hub = data.get("hub")
    paths = data["paths"]
    if len(paths) > 3:
        raise ValueError(f"expected at most 3 Research Paths, found {len(paths)}")
    if expected_count is not None and len(paths) != expected_count:
        raise ValueError(f"expected {expected_count} Research Paths, found {len(paths)}")
    if hub is not None:
        if hub.get("status") not in {"ready_for_review", "published"}:
            raise ValueError("Research hub has invalid status")
        if allowed_statuses is not None and hub["status"] not in allowed_statuses:
            raise ValueError(f"Research hub status {hub['status']} is not allowed in this data source")
        if hub["status"] == "published":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", hub.get("published_on", "")):
                raise ValueError("published Research hub requires published_on")
        elif hub.get("published_on"):
            raise ValueError("review-pending Research hub cannot have published_on")
        for item in [
            *hub.get("arc", []),
            *hub.get("horizon", []),
            *hub.get("methodology", []),
            *hub.get("adjacent", []),
        ]:
            slugs = item.get("paper_slugs", [item.get("paper_slug")])
            for slug in slugs:
                if slug not in papers_by_slug:
                    raise ValueError(f"Research hub references unknown paper {slug}")
        count = research_hub_word_count(hub)
        if not 850 <= count <= 1300:
            raise ValueError(f"Research hub has {count} English words; expected 850–1300")
    elif paths:
        raise ValueError("Research paths require a Research hub record")
    expected_slugs = {
        "video-generation-world-models",
        "trustworthy-visual-post-training",
        "semantic-motion-embodied-interaction",
    }
    seen_slugs: set[str] = set()
    seen_orders: set[int] = set()
    roles = {"foundation", "core", "bridge", "framing", "horizon"}
    forbidden_member_fields = {"title", "authors", "year", "venue", "abstract", "paper_url", "doi", "arxiv_id"}
    for path in paths:
        slug = path.get("slug", "<unknown>")
        if slug in seen_slugs:
            raise ValueError(f"duplicate Research Path slug: {slug}")
        seen_slugs.add(slug)
        if path.get("order") in seen_orders:
            raise ValueError(f"duplicate Research Path order: {path.get('order')}")
        seen_orders.add(path.get("order"))
        if path.get("status") not in {"ready_for_review", "published"}:
            raise ValueError(f"Research Path {slug}: invalid status")
        if allowed_statuses is not None and path["status"] not in allowed_statuses:
            raise ValueError(f"Research Path {slug}: status {path['status']} is not allowed in this data source")
        if path["status"] == "published":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.get("published_on", "")):
                raise ValueError(f"Research Path {slug}: published status requires published_on")
        elif path.get("published_on"):
            raise ValueError(f"Research Path {slug}: review-pending path cannot have published_on")
        stage_keys: dict[str, set[str]] = {}
        for language in ("en", "zh"):
            local = path.get(language, {})
            stage_keys[language] = {stage.get("key") for stage in local.get("stages", [])}
            if len(stage_keys[language]) != len(local.get("stages", [])):
                raise ValueError(f"Research Path {slug}.{language}: duplicate stage key")
        if stage_keys["en"] != stage_keys["zh"]:
            raise ValueError(f"Research Path {slug}: English and Chinese stage keys differ")
        member_slugs: set[str] = set()
        for member in path.get("members", []):
            paper_slug = member.get("paper_slug")
            if forbidden_member_fields & set(member):
                raise ValueError(f"Research Path {slug}: copied publication metadata in member {paper_slug}")
            if paper_slug not in papers_by_slug:
                raise ValueError(f"Research Path {slug}: unknown paper {paper_slug}")
            if paper_slug in member_slugs:
                raise ValueError(f"Research Path {slug}: duplicate paper {paper_slug}")
            member_slugs.add(paper_slug)
            if member.get("role") not in roles:
                raise ValueError(f"Research Path {slug}: invalid role for {paper_slug}")
            if member.get("stage_key") not in stage_keys["en"]:
                raise ValueError(f"Research Path {slug}: unknown stage for {paper_slug}")
            if not member.get("en_relation") or not member.get("zh_relation"):
                raise ValueError(f"Research Path {slug}: missing bilingual relationship for {paper_slug}")
        count = research_path_word_count(path)
        if not 700 <= count <= 1000:
            raise ValueError(f"Research Path {slug}: {count} English words; expected 700–1000")
    if expected_count == 3 and seen_slugs != expected_slugs:
        raise ValueError(f"Research Path set differs: {sorted(seen_slugs ^ expected_slugs)}")
    return hub, sorted(paths, key=lambda item: item["order"])


def build_outputs(
    papers: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    hub: dict[str, Any] | None,
    paths: list[dict[str, Any]],
    *,
    preview: bool = False,
    homepage_source: str,
) -> dict[Path, str]:
    papers_by_slug = {paper["slug"]: paper for paper in papers}
    notes_by_slug = {note["paper_slug"]: note for note in notes}
    memberships = path_memberships(paths)
    outputs: dict[Path, str] = {
        Path("index.html"): render_homepage_research(
            homepage_source,
            hub,
            paths,
            preview=preview,
        ),
        Path("publications/index.html"): render_collection(papers, "en", notes_by_slug, memberships),
        Path("zh/publications/index.html"): render_collection(papers, "zh", notes_by_slug, memberships),
        Path("research/index.html"): render_research_hub(
            hub, paths, papers_by_slug, "en", has_notes=bool(notes), preview=preview
        ),
        Path("zh/research/index.html"): render_research_hub(
            hub, paths, papers_by_slug, "zh", has_notes=bool(notes), preview=preview
        ),
        Path("research/paths.json"): json.dumps(
            public_research_paths_record(
                hub,
                paths,
                papers_by_slug,
                notes_by_slug,
                include_review=preview,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        Path("publications/catalog.json"): json.dumps(
            [csl_item(paper) for paper in papers], ensure_ascii=False, indent=2
        )
        + "\n",
        Path("publications/records.json"): json.dumps(
            [public_record(paper, memberships.get(paper["slug"], [])) for paper in papers],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        Path("llms.txt"): llms_txt(papers, notes, hub, paths, papers_by_slug),
        Path("llms-full.txt"): llms_full_txt(papers, notes, hub, paths, papers_by_slug),
        Path("feed.xml"): atom_feed(papers, notes, hub, paths, papers_by_slug),
        Path("sitemap.xml"): sitemap(papers, notes, hub, paths),
        Path("robots.txt"): robots_txt(),
        Path("AUTHOR_REVIEW.md"): author_review(papers),
        Path("CITATION_AUDIT.md"): citation_audit(papers),
    }
    if notes:
        outputs[Path("research-notes/index.html")] = render_research_notes_collection(
            notes, papers_by_slug, memberships
        )
    for paper in papers:
        note = notes_by_slug.get(paper["slug"])
        paper_path_items = memberships.get(paper["slug"], [])
        outputs[local_page_path(paper, "en")] = render_paper_page(
            paper, "en", note, paper_path_items
        )
        outputs[local_page_path(paper, "zh")] = render_paper_page(
            paper, "zh", note, paper_path_items
        )
        citation_dir = Path("publications") / paper["slug"]
        outputs[citation_dir / "citation.bib"] = bibtex(paper)
        outputs[citation_dir / "citation.ris"] = ris(paper)
        outputs[citation_dir / "citation.json"] = (
            json.dumps(csl_item(paper), ensure_ascii=False, indent=2) + "\n"
        )
        outputs[citation_dir / "record.json"] = (
            json.dumps(public_record(paper, paper_path_items), ensure_ascii=False, indent=2)
            + "\n"
        )
    for note in notes:
        outputs[local_research_note_path(note)] = render_research_note(
            note,
            papers_by_slug[note["paper_slug"]],
            memberships.get(note["paper_slug"], []),
        )
    for path in paths:
        outputs[local_research_path(path, "en")] = render_research_path(
            path, papers_by_slug, notes_by_slug, "en", preview=preview
        )
        outputs[local_research_path(path, "zh")] = render_research_path(
            path, papers_by_slug, notes_by_slug, "zh", preview=preview
        )
    for relative_path, content in list(outputs.items()):
        if relative_path.suffix == ".html":
            outputs[relative_path] = inject_file_preview_script(content, relative_path)
    return outputs


def inject_file_preview_script(content: str, relative_path: Path) -> str:
    """Make local file previews resolve clean routes without changing web URLs."""
    marker = "data-local-file-preview"
    if marker in content:
        return content
    depth = len(relative_path.parent.parts)
    script_path = f'{"../" * depth}dist/js/file-preview.js'
    script = f'<script {marker} src="{script_path}"></script>'
    if "</body>" not in content:
        raise ValueError(f"{relative_path}: generated HTML is missing </body>")
    return content.replace("</body>", f"  {script}\n</body>", 1)


def merge_unique_records(
    public: list[dict[str, Any]],
    review: list[dict[str, Any]],
    key: str,
    label: str,
) -> list[dict[str, Any]]:
    public_keys = {item[key] for item in public}
    review_keys = {item[key] for item in review}
    duplicates = sorted(public_keys & review_keys)
    if duplicates:
        raise ValueError(f"{label} records exist in both public and review data: {duplicates}")
    return [*public, *review]


def write_outputs(root: Path, outputs: dict[Path, str]) -> None:
    for relative_path, content in outputs.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def build_preview_site(outputs: dict[Path, str]) -> None:
    preview_root = PREVIEW_ROOT.resolve()
    if preview_root.parent != ROOT.resolve() or preview_root.name != ".preview-site":
        raise ValueError("refusing to replace an unexpected preview directory")
    if preview_root.exists():
        shutil.rmtree(preview_root)

    def ignore(_directory: str, names: list[str]) -> set[str]:
        ignored = {name for name in names if name in {".git", ".review", ".preview-site", "__pycache__"}}
        ignored.update(name for name in names if name.endswith((".pyc", ".pyo")))
        return ignored

    shutil.copytree(ROOT, preview_root, ignore=ignore)
    write_outputs(preview_root, outputs)


def managed_detail_pages() -> set[Path]:
    pages: set[Path] = set()
    notes_collection = ROOT / "research-notes" / "index.html"
    if notes_collection.exists():
        pages.add(notes_collection.relative_to(ROOT))
    for base in (ROOT / "research-notes", ROOT / "research", ROOT / "zh" / "research"):
        if not base.exists():
            continue
        for page in base.glob("*/index.html"):
            pages.add(page.relative_to(ROOT))
    return pages


def remove_empty_managed_detail_dirs() -> None:
    """Remove empty draft directories so local public URLs resolve as 404."""
    for base in (ROOT / "research-notes", ROOT / "research", ROOT / "zh" / "research"):
        if not base.exists():
            continue
        for directory in base.iterdir():
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when generated files differ; do not write",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="merge local review data and write an isolated .preview-site tree",
    )
    args = parser.parse_args()
    if args.check and args.preview:
        parser.error("--check and --preview are mutually exclusive")
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    papers = validate_data(data)
    papers_by_slug = {paper["slug"]: paper for paper in papers}
    public_note_data = json.loads(RESEARCH_NOTES_PATH.read_text(encoding="utf-8"))
    public_notes = validate_research_notes(
        public_note_data, papers_by_slug, allowed_statuses={"published"}
    )
    public_path_data = json.loads(RESEARCH_PATHS_PATH.read_text(encoding="utf-8"))
    public_hub, public_paths = validate_research_paths(
        public_path_data, papers_by_slug, allowed_statuses={"published"}
    )
    notes = public_notes
    hub = public_hub
    paths = public_paths
    if args.preview:
        review_note_data = json.loads(REVIEW_NOTES_PATH.read_text(encoding="utf-8"))
        review_notes = validate_research_notes(
            review_note_data, papers_by_slug, allowed_statuses={"ready_for_review"}
        )
        notes = validate_research_notes(
            {"schema_version": 1, "notes": merge_unique_records(public_notes, review_notes, "paper_slug", "Research Note")},
            papers_by_slug,
            expected_count=13,
        )
        review_path_data = json.loads(REVIEW_PATHS_PATH.read_text(encoding="utf-8"))
        review_hub, review_paths = validate_research_paths(
            review_path_data, papers_by_slug, allowed_statuses={"ready_for_review"}
        )
        if public_hub is not None and review_hub is not None:
            raise ValueError("Research hub exists in both public and review data")
        hub = public_hub or review_hub
        combined_paths = merge_unique_records(public_paths, review_paths, "slug", "Research Path")
        hub, paths = validate_research_paths(
            {"schema_version": 1, "hub": hub, "paths": combined_paths},
            papers_by_slug,
            expected_count=3,
        )
    homepage_source = (ROOT / "index.html").read_text(encoding="utf-8")
    outputs = build_outputs(
        papers,
        notes,
        hub,
        paths,
        preview=args.preview,
        homepage_source=homepage_source,
    )
    if args.preview:
        build_preview_site(outputs)
        print(
            f"Generated isolated preview with {len(outputs)} files from {len(papers)} publication records, "
            f"{len(notes)} Research Notes, and {len(paths)} Research Paths."
        )
        return 0
    changed: list[str] = []
    for relative_path, content in outputs.items():
        path = ROOT / relative_path
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            changed.append(relative_path.as_posix())
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
    expected = set(outputs)
    stale_pages = sorted(managed_detail_pages() - expected)
    for relative_path in stale_pages:
        changed.append(f"stale:{relative_path.as_posix()}")
        if not args.check:
            (ROOT / relative_path).unlink()
    if not args.check:
        remove_empty_managed_detail_dirs()
    if args.check and changed:
        print("Generated files are stale:", file=sys.stderr)
        for path in changed:
            print(f"  {path}", file=sys.stderr)
        return 1
    action = "Checked" if args.check else "Generated"
    print(
        f"{action} {len(outputs)} files from {len(papers)} publication records, "
        f"{len(notes)} published Research Notes, and {len(paths)} published Research Paths."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

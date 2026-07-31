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
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "publications.json"
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
            ("/#publication", "Highlights", "highlights"),
        ]
        label = "Main navigation"
    else:
        links = [
            ("/", "个人主页", "home"),
            ("/zh/publications/", "论文与解读", "publications"),
            ("/#publication", "代表工作", "highlights"),
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


def render_paper_page(paper: dict[str, Any], language: str) -> str:
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
    <nav class="note-breadcrumb" aria-label="Breadcrumb">
      <a href="/">{labels['home']}</a><span aria-hidden="true">/</span>
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


def render_collection(papers: list[dict[str, Any]], language: str) -> str:
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
            cards.append(
                f"""<article class="pub-item" data-search="{esc(search.lower())}">
  <h3><a href="{'' if is_en else '/zh'}/publications/{paper['slug']}/">{esc(paper['title'])}</a></h3>
  <p class="meta">{esc(compact_authors(paper['authors']))} · {esc(venue_line(paper, language))}</p>
  <p class="pub-summary">{esc(content['summary'])}</p>
  <div class="links"><a class="primary" href="{'' if is_en else '/zh'}/publications/{paper['slug']}/">{record_label}</a>{links}</div>
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
    <header class="pub-page-header">
      <h1>{labels['heading']}</h1>
      <p>{labels['intro']}</p>
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


def public_record(paper: dict[str, Any]) -> dict[str, Any]:
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
        "citation": csl_item(paper),
        "resources": paper["links"],
    }


def llms_txt(papers: list[dict[str, Any]]) -> str:
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
        "## Research records",
        "",
    ]
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


def llms_full_txt(papers: list[dict[str, Any]]) -> str:
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


def atom_feed(papers: list[dict[str, Any]]) -> str:
    updated = max(p["source_checked"] for p in papers) + "T00:00:00+08:00"
    entries = []
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


def sitemap(papers: list[dict[str, Any]]) -> str:
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


def build_outputs(papers: list[dict[str, Any]]) -> dict[Path, str]:
    outputs: dict[Path, str] = {
        Path("publications/index.html"): render_collection(papers, "en"),
        Path("zh/publications/index.html"): render_collection(papers, "zh"),
        Path("publications/catalog.json"): json.dumps(
            [csl_item(paper) for paper in papers], ensure_ascii=False, indent=2
        )
        + "\n",
        Path("publications/records.json"): json.dumps(
            [public_record(paper) for paper in papers], ensure_ascii=False, indent=2
        )
        + "\n",
        Path("llms.txt"): llms_txt(papers),
        Path("llms-full.txt"): llms_full_txt(papers),
        Path("feed.xml"): atom_feed(papers),
        Path("sitemap.xml"): sitemap(papers),
        Path("robots.txt"): robots_txt(),
        Path("AUTHOR_REVIEW.md"): author_review(papers),
        Path("CITATION_AUDIT.md"): citation_audit(papers),
    }
    for paper in papers:
        outputs[local_page_path(paper, "en")] = render_paper_page(paper, "en")
        outputs[local_page_path(paper, "zh")] = render_paper_page(paper, "zh")
        citation_dir = Path("publications") / paper["slug"]
        outputs[citation_dir / "citation.bib"] = bibtex(paper)
        outputs[citation_dir / "citation.ris"] = ris(paper)
        outputs[citation_dir / "citation.json"] = (
            json.dumps(csl_item(paper), ensure_ascii=False, indent=2) + "\n"
        )
        outputs[citation_dir / "record.json"] = (
            json.dumps(public_record(paper), ensure_ascii=False, indent=2) + "\n"
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when generated files differ; do not write",
    )
    args = parser.parse_args()
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    papers = validate_data(data)
    outputs = build_outputs(papers)
    changed: list[str] = []
    for relative_path, content in outputs.items():
        path = ROOT / relative_path
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            changed.append(relative_path.as_posix())
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
    if args.check and changed:
        print("Generated files are stale:", file=sys.stderr)
        for path in changed:
            print(f"  {path}", file=sys.stderr)
        return 1
    action = "Checked" if args.check else "Generated"
    print(f"{action} {len(outputs)} files from {len(papers)} publication records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

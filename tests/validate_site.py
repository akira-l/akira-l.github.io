#!/usr/bin/env python3
"""Read-only checks for generated research records and site discovery files."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://akira-l.github.io"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.meta: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.alternates: list[dict[str, str]] = []
        self.jsonld: list[dict] = []
        self.h1: list[str] = []
        self.body_text: list[str] = []
        self.html_attrs: dict[str, str] = {}
        self._script_type = ""
        self._script_buffer = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        self.stack.append(tag)
        if tag == "html":
            self.html_attrs = values
        elif tag == "meta":
            self.meta.append(values)
        elif tag in {"a", "link"}:
            self.links.append(values)
            if tag == "link" and values.get("rel") == "alternate":
                self.alternates.append(values)
        elif tag == "img":
            self.images.append(values)
        elif tag == "script":
            self._script_type = values.get("type", "")
            self._script_buffer = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._script_type == "application/ld+json":
            self.jsonld.append(json.loads(self._script_buffer))
        if tag == "script":
            self._script_type = ""
            self._script_buffer = ""
        if tag in self.stack:
            index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            self.stack = self.stack[:index]

    def handle_data(self, data: str) -> None:
        if self._script_type == "application/ld+json":
            self._script_buffer += data
            return
        value = " ".join(data.split())
        if not value:
            return
        if "h1" in self.stack:
            self.h1.append(value)
        if "body" in self.stack:
            self.body_text.append(value)

    def meta_values(self, key: str) -> list[str]:
        return [
            item.get("content", "")
            for item in self.meta
            if item.get("name") == key or item.get("property") == key
        ]


def parse_page(path: Path) -> tuple[str, PageParser]:
    text = path.read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(text)
    return text, parser


def internal_target(source: Path, url: str) -> Path | None:
    if not url or url.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    absolute = urljoin(f"{BASE_URL}/{source.relative_to(ROOT).as_posix()}", url)
    parsed = urlparse(absolute)
    if parsed.netloc != "akira-l.github.io":
        return None
    relative = parsed.path.lstrip("/")
    target = ROOT / relative
    if not relative or parsed.path.endswith("/"):
        target = target / "index.html"
    return target


def graph_types(document: dict) -> set[str]:
    nodes = document.get("@graph", [document])
    values: set[str] = set()
    for node in nodes:
        node_type = node.get("@type")
        if isinstance(node_type, list):
            values.update(node_type)
        elif node_type:
            values.add(node_type)
    return values


def main() -> int:
    errors: list[str] = []
    file_preview_path = ROOT / "dist" / "js" / "file-preview.js"
    if not file_preview_path.exists():
        errors.append("dist/js/file-preview.js: local navigation helper is missing")
    else:
        file_preview_source = file_preview_path.read_text(encoding="utf-8")
        for required in (
            'window.location.protocol !== "file:"',
            'const previewMarker = "/.preview-site/"',
            'localPath += "index.html"',
        ):
            if required not in file_preview_source:
                errors.append(f"dist/js/file-preview.js: missing guard {required}")
    data = json.loads((ROOT / "data" / "publications.json").read_text(encoding="utf-8"))
    papers = data["papers"]
    if len(papers) != 23:
        errors.append(f"expected 23 publication records, found {len(papers)}")

    html_files = sorted(
        path
        for path in ROOT.glob("**/*.html")
        if ".preview-site" not in path.relative_to(ROOT).parts
    )
    for path in html_files:
        text, page = parse_page(path)
        relative = path.relative_to(ROOT).as_posix()
        depth = len(path.relative_to(ROOT).parent.parts)
        expected_preview_script = f'{"../" * depth}dist/js/file-preview.js'
        if (
            "data-local-file-preview" not in text
            or f'src="{expected_preview_script}"' not in text
        ):
            errors.append(f"{relative}: missing file-safe local navigation helper")
        if "\ufffd" in text or any(token in text for token in ("锛", "銆", "鈥", "闄")):
            errors.append(f"{relative}: possible mojibake")
        if re.search(r'href=["\'][^"\']*index\.html', text):
            errors.append(f"{relative}: explicit index.html internal link")
        if "http://" in text:
            errors.append(f"{relative}: insecure http:// URL")
        if not page.html_attrs.get("lang"):
            errors.append(f"{relative}: missing html lang")
        if relative != "index.html":
            home_returns = re.findall(
                r'<nav class="page-home-return"[^>]*>\s*<a href="/">',
                text,
            )
            if len(home_returns) != 1:
                errors.append(
                    f"{relative}: expected one explicit return-to-home control"
                )
        navigation_match = re.search(
            r'<nav class="pub-nav".*?</nav>', text, flags=re.S
        )
        if navigation_match:
            navigation = navigation_match.group(0)
            if page.html_attrs.get("lang") == "en":
                if navigation.count(">Research</a>") != 1:
                    errors.append(f"{relative}: expected one unified Research nav item")
                if "Research Notes" in navigation:
                    errors.append(f"{relative}: separate Research Notes nav item remains")
                if ">Highlights</a>" in navigation:
                    errors.append(f"{relative}: redundant Highlights nav item remains")
                if navigation.find(">Publications</a>") > navigation.find(">Research</a>"):
                    errors.append(f"{relative}: Research nav item must follow Publications")
            else:
                if ">代表工作</a>" in navigation:
                    errors.append(f"{relative}: redundant 代表工作 nav item remains")
                if navigation.find(">论文与解读</a>") > navigation.find(">研究方向</a>"):
                    errors.append(f"{relative}: 研究方向 nav item must follow 论文与解读")
        for image in page.images:
            if not image.get("alt"):
                errors.append(f"{relative}: image missing alt: {image.get('src', '')}")
        for link in page.links:
            target = internal_target(path, link.get("href", ""))
            if target is not None and not target.exists():
                errors.append(
                    f"{relative}: broken internal link {link.get('href')} -> "
                    f"{target.relative_to(ROOT).as_posix()}"
                )

    for paper in papers:
        slug = paper["slug"]
        en_path = ROOT / "publications" / slug / "index.html"
        zh_path = ROOT / "zh" / "publications" / slug / "index.html"
        for language, path, expected_url in (
            ("en", en_path, f"{BASE_URL}/publications/{slug}/"),
            ("zh", zh_path, f"{BASE_URL}/zh/publications/{slug}/"),
        ):
            text, page = parse_page(path)
            h1 = " ".join(page.h1)
            if h1 != paper["title"]:
                errors.append(f"{path.relative_to(ROOT)}: H1/title mismatch")
            canonical = [
                link.get("href")
                for link in page.links
                if link.get("rel") == "canonical"
            ]
            if canonical != [expected_url]:
                errors.append(f"{path.relative_to(ROOT)}: canonical mismatch {canonical}")
            alternate_map = {
                link.get("hreflang"): link.get("href")
                for link in page.alternates
                if link.get("hreflang")
            }
            if set(alternate_map) != {"en", "zh-CN", "x-default"}:
                errors.append(f"{path.relative_to(ROOT)}: incomplete hreflang cluster")
            citation_alternates = {
                link.get("type"): link.get("href")
                for link in page.alternates
                if link.get("href", "").startswith(f"/publications/{slug}/citation.")
            }
            expected_citation_alternates = {
                "application/vnd.citationstyles.csl+json": f"/publications/{slug}/citation.json",
                "application/x-bibtex": f"/publications/{slug}/citation.bib",
                "application/x-research-info-systems": f"/publications/{slug}/citation.ris",
            }
            if citation_alternates != expected_citation_alternates:
                errors.append(
                    f"{path.relative_to(ROOT)}: citation discovery links mismatch"
                )
            downloads_match = re.search(
                r'<div class="citation-downloads"[^>]*>(.*?)</div>',
                text,
                flags=re.S,
            )
            if not downloads_match or any(
                f'href="/publications/{slug}/{name}"' not in downloads_match.group(1)
                for name in ("citation.bib", "citation.ris", "citation.json")
            ):
                errors.append(
                    f"{path.relative_to(ROOT)}: visible citation downloads incomplete"
                )
            if paper["abstract"] not in " ".join(page.body_text):
                errors.append(f"{path.relative_to(ROOT)}: official abstract is not visible")
            if not page.jsonld:
                errors.append(f"{path.relative_to(ROOT)}: missing JSON-LD")
            else:
                types = set().union(*(graph_types(doc) for doc in page.jsonld))
                if not {"Article", "ScholarlyArticle", "BreadcrumbList"} <= types:
                    errors.append(f"{path.relative_to(ROOT)}: entities are not separated")
            if paper["verification_status"] == "author-verified":
                expected_status = "author-verified" if language == "en" else "作者已"
            else:
                expected_status = "verification pending" if language == "en" else "等待作者最终确认"
            if expected_status.lower() not in text.lower():
                errors.append(f"{path.relative_to(ROOT)}: verification status mismatch")
            if language == "en":
                if page.meta_values("citation_title") != [paper["title"]]:
                    errors.append(f"{path.relative_to(ROOT)}: citation_title mismatch")
                if page.meta_values("citation_author") != paper["authors"]:
                    errors.append(f"{path.relative_to(ROOT)}: citation_author order mismatch")
                if page.meta_values("citation_abstract") != [paper["abstract"]]:
                    errors.append(f"{path.relative_to(ROOT)}: citation_abstract mismatch")
                status = paper.get(
                    "publication_status",
                    "preprint" if paper["kind"] == "preprint" else "published",
                )
                container = paper.get("citation_container_title", paper["venue"])
                expected_meta: dict[str, list[str]] = {
                    "citation_publication_date": [paper["publication_date"]],
                    "citation_abstract_html_url": [expected_url],
                    "citation_language": ["en"],
                    "citation_keywords": ["; ".join(paper["keywords"])],
                    "citation_doi": [paper["doi"]] if paper.get("doi") else [],
                    "citation_arxiv_id": (
                        [paper["arxiv_id"]]
                        if paper.get("arxiv_id")
                        and status in {"preprint", "forthcoming"}
                        else []
                    ),
                    "citation_publisher": (
                        [paper["publisher"]] if paper.get("publisher") else []
                    ),
                    "citation_volume": (
                        [str(paper["volume"])] if paper.get("volume") else []
                    ),
                    "citation_issue": (
                        [str(paper["issue"])] if paper.get("issue") else []
                    ),
                }
                if paper["kind"] == "journal":
                    expected_meta["citation_journal_title"] = [container]
                    expected_meta["citation_conference_title"] = []
                elif paper["kind"] == "conference":
                    expected_meta["citation_conference_title"] = [container]
                    expected_meta["citation_journal_title"] = []
                else:
                    expected_meta["citation_journal_title"] = []
                    expected_meta["citation_conference_title"] = []
                if paper.get("pages"):
                    first, _, last = paper["pages"].partition("-")
                    expected_meta["citation_firstpage"] = [first]
                    expected_meta["citation_lastpage"] = [last] if last else []
                elif paper.get("article_number"):
                    expected_meta["citation_firstpage"] = [
                        str(paper["article_number"])
                    ]
                    expected_meta["citation_lastpage"] = []
                else:
                    expected_meta["citation_firstpage"] = []
                    expected_meta["citation_lastpage"] = []
                for key, expected in expected_meta.items():
                    actual = page.meta_values(key)
                    if actual != expected:
                        errors.append(
                            f"{path.relative_to(ROOT)}: {key} expected "
                            f"{expected!r}, found {actual!r}"
                        )
        for name in ("citation.bib", "citation.ris", "citation.json", "record.json"):
            if not (ROOT / "publications" / slug / name).exists():
                errors.append(f"publications/{slug}/{name}: missing")

    homepage_text, homepage = parse_page(ROOT / "index.html")
    if "https://akira-l.github.io/img/liangyzh.jpg" not in homepage_text:
        errors.append("index.html: portrait missing from entity/social metadata")
    if "https://orcid.org/0009-0008-2746-5947" not in homepage_text:
        errors.append("index.html: canonical ORCID missing")
    if '"mainEntity": { "@id": "https://akira-l.github.io/#person" }' not in homepage_text:
        errors.append("index.html: ProfilePage mainEntity is missing")
    if '<meta name="keywords"' in homepage_text:
        errors.append("index.html: obsolete keyword metadata remains")
    if re.search(r"\(online\s+\d{4}\)", homepage_text, flags=re.I):
        errors.append("index.html: ambiguous parenthetical online-year label remains")
    if "Accepted by" in homepage_text:
        errors.append("index.html: inconsistent Accepted by venue prefix remains")
    if "Yuanzhi (Liam) Liang" in homepage_text:
        errors.append("index.html: deprecated Liam alias remains")
    if "Browse my source-checked research records" in homepage_text:
        errors.append("index.html: promotional publication copy remains in About Me")
    if ">Research record<" in homepage_text:
        errors.append("index.html: old Research record badge label remains")
    if f'{BASE_URL}/publications/rl-vgm/' in homepage_text:
        errors.append("index.html: background RL survey remains in the homepage featured list")
    if "Recent Preprints and Surveys" in homepage_text:
        errors.append("index.html: survey-oriented homepage section heading remains")
    if 'href="/publications/' in homepage_text:
        errors.append("index.html: root-relative publication link breaks file previews")
    homepage_navigation_match = re.search(
        r'<nav class="navbar.*?</nav>', homepage_text, flags=re.S
    )
    if not homepage_navigation_match:
        errors.append("index.html: primary navigation is missing")
    else:
        homepage_navigation = homepage_navigation_match.group(0)
        if homepage_navigation.count(">Research</b></a>") != 1:
            errors.append("index.html: expected one unified Research navigation item")
        if "Research Notes" in homepage_navigation:
            errors.append("index.html: separate Research Notes navigation item remains")
        if homepage_navigation.find(">Publications</b></a>") > homepage_navigation.find(">Research</b></a>"):
            errors.append("index.html: Research navigation item must follow Publications")
    overview_links = re.findall(
        r'class="badge-tldr" href="([^"]+)">Overview</a>',
        homepage_text,
    )
    if not overview_links or any(
        not url.startswith(f"{BASE_URL}/publications/") for url in overview_links
    ):
        errors.append("index.html: publication Overview links are not production-safe")
    title_links = re.findall(
        r'class="publication-title" href="([^"]+)">([^<]+)</a>',
        homepage_text,
    )
    if len(title_links) != len(overview_links):
        errors.append("index.html: every featured publication title must link to its record")
    elif [url for url, _ in title_links] != overview_links:
        errors.append("index.html: title and Overview links disagree")

    sitemap_root = ET.parse(ROOT / "sitemap.xml").getroot()
    sitemap_ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_urls = {
        node.text
        for node in sitemap_root.findall("s:url/s:loc", sitemap_ns)
        if node.text
    }
    expected_sitemap = {
        f"{BASE_URL}/",
        f"{BASE_URL}/publications/",
        f"{BASE_URL}/zh/publications/",
        *[f"{BASE_URL}/publications/{paper['slug']}/" for paper in papers],
        *[f"{BASE_URL}/zh/publications/{paper['slug']}/" for paper in papers],
    }
    note_data = json.loads(
        (ROOT / "data" / "research-notes.json").read_text(encoding="utf-8")
    )
    expected_sitemap.update(
        f"{BASE_URL}/research-notes/{note['paper_slug']}/"
        for note in note_data["notes"]
        if note["status"] == "published"
    )
    if any(note["status"] == "published" for note in note_data["notes"]):
        expected_sitemap.add(f"{BASE_URL}/research-notes/")
    path_data = json.loads(
        (ROOT / "data" / "research-paths.json").read_text(encoding="utf-8")
    )
    if path_data.get("hub") and path_data["hub"]["status"] == "published":
        expected_sitemap.update({f"{BASE_URL}/research/", f"{BASE_URL}/zh/research/"})
    for path_record in path_data["paths"]:
        if path_record["status"] == "published":
            expected_sitemap.update(
                {
                    f"{BASE_URL}/research/{path_record['slug']}/",
                    f"{BASE_URL}/zh/research/{path_record['slug']}/",
                }
            )
    if sitemap_urls != expected_sitemap:
        errors.append(
            f"sitemap.xml: expected {len(expected_sitemap)} canonical pages, "
            f"found {len(sitemap_urls)}"
        )

    feed_root = ET.parse(ROOT / "feed.xml").getroot()
    atom_ns = {"a": "http://www.w3.org/2005/Atom"}
    for node in feed_root.findall("a:entry/a:published", atom_ns):
        try:
            datetime.fromisoformat((node.text or "").replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"feed.xml: invalid published date {node.text}")

    catalog = json.loads((ROOT / "publications" / "catalog.json").read_text(encoding="utf-8"))
    if len(catalog) != len(papers):
        errors.append("publications/catalog.json: record count mismatch")
    if [item["id"] for item in catalog] != [paper["citation_key"] for paper in sorted(
        papers, key=lambda p: (p["publication_date"], p["title"]), reverse=True
    )]:
        errors.append("publications/catalog.json: ordering or citation keys mismatch")
    records = json.loads((ROOT / "publications" / "records.json").read_text(encoding="utf-8"))
    if len(records) != len(papers):
        errors.append("publications/records.json: record count mismatch")
    for record in records:
        if record.get("official_abstract_rights", "").startswith("Excluded") is False:
            errors.append(f"publications/records.json: missing abstract rights for {record.get('slug')}")
        if record.get("commentary", {}).get("license") != "https://creativecommons.org/licenses/by/4.0/":
            errors.append(f"publications/records.json: missing CC BY commentary license for {record.get('slug')}")

    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    for agent in ("OAI-SearchBot", "GPTBot", "Claude-SearchBot", "PerplexityBot", "Bytespider", "Baiduspider"):
        if f"User-agent: {agent}\nAllow: /" not in robots:
            errors.append(f"robots.txt: missing allow policy for {agent}")
    if f"Sitemap: {BASE_URL}/sitemap.xml" not in robots:
        errors.append("robots.txt: missing canonical sitemap")

    if errors:
        print(f"{len(errors)} validation error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"Validated {len(papers)} bilingual research records, "
        f"{len(html_files)} HTML files, discovery feeds, citations, and internal links."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

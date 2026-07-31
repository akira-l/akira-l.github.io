#!/usr/bin/env python3
"""Field-by-field validation for every generated BibTeX, RIS, and CSL record."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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


def status(paper: dict) -> str:
    return paper.get(
        "publication_status",
        "preprint" if paper["kind"] == "preprint" else "published",
    )


def container(paper: dict) -> str:
    return paper.get("citation_container_title", paper["venue"])


def citation_url(paper: dict) -> str:
    if paper.get("doi"):
        return f"https://doi.org/{paper['doi']}"
    return paper["source"]["url"]


def split_name(name: str) -> tuple[str, str]:
    parts = name.split()
    return (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else ("", name)


def inverted_name(name: str) -> str:
    given, family = split_name(name)
    return f"{family}, {given}" if given else family


def parse_bibtex(path: Path) -> tuple[str, str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    header = re.match(r"@(\w+)\{([^,]+),\n", text)
    if not header:
        raise ValueError("invalid BibTeX header")
    fields: dict[str, str] = {}
    for line in text.splitlines()[1:-1]:
        match = re.fullmatch(r"\s{2}(\w+)\s*=\s*\{(.*)\},?", line)
        if not match:
            raise ValueError(f"invalid BibTeX field: {line}")
        fields[match.group(1)] = match.group(2)
    return header.group(1), header.group(2), fields


def parse_ris(path: Path) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([A-Z0-9]{2})  - ?(.*)", line)
        if not match:
            raise ValueError(f"invalid RIS field: {line}")
        fields.setdefault(match.group(1), []).append(match.group(2))
    return fields


def expect(
    errors: list[str],
    slug: str,
    artifact: str,
    field: str,
    actual: object,
    expected: object,
) -> None:
    if actual != expected:
        errors.append(
            f"{slug}/{artifact}: {field} expected {expected!r}, found {actual!r}"
        )


def expected_csl(paper: dict) -> dict:
    item = {
        "id": paper["citation_key"],
        "type": {
            "journal": "article-journal",
            "conference": "paper-conference",
            "preprint": "article",
        }[paper["kind"]],
        "title": paper["title"],
        "author": [
            {"given": split_name(author)[0], "family": split_name(author)[1]}
            for author in paper["authors"]
        ],
        "container-title": container(paper),
        "issued": {
            "date-parts": [
                [int(part) for part in paper["publication_date"].split("-")]
            ]
        },
        "URL": citation_url(paper),
        "abstract": paper["abstract"],
        "keyword": ", ".join(paper["keywords"]),
    }
    if paper.get("editors"):
        item["editor"] = [
            {"given": split_name(editor)[0], "family": split_name(editor)[1]}
            for editor in paper["editors"]
        ]
    for source, target in (
        ("publisher", "publisher"),
        ("doi", "DOI"),
        ("volume", "volume"),
        ("issue", "issue"),
    ):
        if paper.get(source):
            item[target] = str(paper[source])
    if paper.get("pages"):
        item["page"] = paper["pages"]
    elif paper.get("article_number"):
        item["page"] = str(paper["article_number"])
    if paper.get("arxiv_id") and status(paper) in {"preprint", "forthcoming"}:
        item["archive"] = "arXiv"
        item["archive_location"] = paper["arxiv_id"]
        item["genre"] = (
            "Preprint"
            if paper["kind"] == "preprint"
            else "Forthcoming conference paper"
        )
    if status(paper) == "forthcoming":
        item["status"] = "forthcoming"
    return item


def validate_bibtex(paper: dict, path: Path, errors: list[str]) -> None:
    slug = paper["slug"]
    try:
        entry_type, key, fields = parse_bibtex(path)
    except ValueError as exc:
        errors.append(f"{slug}/BibTeX: {exc}")
        return
    expected_type = {
        "journal": "article",
        "conference": "inproceedings",
        "preprint": "misc",
    }[paper["kind"]]
    expected = {
        "title": "{" + paper["title"] + "}",
        "author": " and ".join(inverted_name(author) for author in paper["authors"]),
        "year": str(paper["year"]),
        "url": citation_url(paper),
    }
    if paper["kind"] == "journal":
        expected["journal"] = container(paper)
    elif paper["kind"] == "conference":
        expected["booktitle"] = container(paper)
    else:
        expected["howpublished"] = "arXiv preprint"
    if paper.get("editors"):
        expected["editor"] = " and ".join(
            inverted_name(editor) for editor in paper["editors"]
        )
    if paper.get("publisher"):
        expected["publisher"] = paper["publisher"]
    date = paper["publication_date"].split("-")
    if len(date) >= 2:
        expected["month"] = MONTH_NAMES[int(date[1])]
    for source, target in (
        ("volume", "volume"),
        ("issue", "number"),
        ("doi", "doi"),
    ):
        if paper.get(source):
            expected[target] = str(paper[source])
    if paper.get("pages"):
        expected["pages"] = paper["pages"].replace("-", "--", 1)
    elif paper.get("article_number"):
        expected["eid"] = str(paper["article_number"])
    include_arxiv = bool(
        paper.get("arxiv_id") and status(paper) in {"preprint", "forthcoming"}
    )
    if include_arxiv:
        expected["eprint"] = paper["arxiv_id"]
        expected["archivePrefix"] = "arXiv"
        expected["primaryClass"] = paper["arxiv_primary_class"]
    if status(paper) == "forthcoming":
        expected["note"] = "Forthcoming; final DOI and pagination pending"
    expect(errors, slug, "BibTeX", "entry type", entry_type, expected_type)
    expect(errors, slug, "BibTeX", "citation key", key, paper["citation_key"])
    expect(errors, slug, "BibTeX", "complete field set", fields, expected)
    if status(paper) == "published" and any(
        field in fields for field in ("eprint", "archivePrefix", "primaryClass")
    ):
        errors.append(f"{slug}/BibTeX: published citation mixes in arXiv metadata")


def validate_ris(paper: dict, path: Path, errors: list[str]) -> None:
    slug = paper["slug"]
    try:
        fields = parse_ris(path)
    except ValueError as exc:
        errors.append(f"{slug}/RIS: {exc}")
        return
    single_expected: dict[str, str] = {
        "TY": {"journal": "JOUR", "conference": "CPAPER", "preprint": "RPRT"}[
            paper["kind"]
        ],
        "TI": paper["title"],
        "PY": str(paper["year"]),
        "T2": container(paper),
        "UR": citation_url(paper),
        "AB": paper["abstract"],
        "ER": "",
    }
    date = paper["publication_date"].split("-")
    if len(date) >= 2:
        single_expected["DA"] = "/".join(date)
    for source, target in (
        ("publisher", "PB"),
        ("volume", "VL"),
        ("issue", "IS"),
        ("doi", "DO"),
    ):
        if paper.get(source):
            single_expected[target] = str(paper[source])
    if paper.get("pages"):
        first, _, last = paper["pages"].partition("-")
        single_expected["SP"] = first
        if last:
            single_expected["EP"] = last
    elif paper.get("article_number"):
        single_expected["C7"] = str(paper["article_number"])
    include_arxiv = bool(
        paper.get("arxiv_id") and status(paper) in {"preprint", "forthcoming"}
    )
    if include_arxiv:
        single_expected["AN"] = f"arXiv:{paper['arxiv_id']}"
        single_expected["DB"] = "arXiv"
        single_expected["M3"] = (
            "Preprint"
            if paper["kind"] == "preprint"
            else "Forthcoming conference paper"
        )
    if status(paper) == "forthcoming":
        single_expected["N1"] = "Forthcoming; final DOI and pagination pending."
    expected = {key: [value] for key, value in single_expected.items()}
    expected["AU"] = [inverted_name(author) for author in paper["authors"]]
    if paper.get("editors"):
        expected["ED"] = [inverted_name(editor) for editor in paper["editors"]]
    expect(errors, slug, "RIS", "complete field set", fields, expected)
    if status(paper) == "published" and any(
        field in fields for field in ("AN", "DB", "M3")
    ):
        errors.append(f"{slug}/RIS: published citation mixes in arXiv metadata")


def validate_csl(paper: dict, path: Path, errors: list[str]) -> dict:
    slug = paper["slug"]
    item = json.loads(path.read_text(encoding="utf-8"))
    expected = expected_csl(paper)
    expect(errors, slug, "CSL-JSON", "complete record", item, expected)
    if status(paper) == "published" and any(
        field in item for field in ("archive", "archive_location", "genre")
    ):
        errors.append(f"{slug}/CSL-JSON: published citation mixes in arXiv metadata")
    return item


def main() -> int:
    errors: list[str] = []
    data = json.loads(
        (ROOT / "data" / "publications.json").read_text(encoding="utf-8")
    )
    papers = sorted(
        data["papers"],
        key=lambda paper: (paper["publication_date"], paper["title"]),
        reverse=True,
    )
    catalog = json.loads(
        (ROOT / "publications" / "catalog.json").read_text(encoding="utf-8")
    )
    csl_items: list[dict] = []
    for paper in papers:
        directory = ROOT / "publications" / paper["slug"]
        validate_bibtex(paper, directory / "citation.bib", errors)
        validate_ris(paper, directory / "citation.ris", errors)
        csl_items.append(
            validate_csl(paper, directory / "citation.json", errors)
        )
    if catalog != csl_items:
        errors.append(
            "publications/catalog.json does not exactly match the ordered per-paper CSL records"
        )
    if errors:
        print(f"{len(errors)} citation validation error(s):", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(
        f"Validated {len(papers)} records across "
        f"{len(papers) * 3} BibTeX/RIS/CSL citation artifacts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

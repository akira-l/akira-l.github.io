#!/usr/bin/env python3
"""Notify the configured discovery service after a publication update."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
HOST = "akira-l.github.io"
KEY = "97e121c0e85d6a9e589b15b45838bfaa"
ENDPOINT = "https://api.indexnow.org/indexnow"


def sitemap_urls() -> list[str]:
    root = ET.parse(ROOT / "sitemap.xml").getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [
        node.text.strip()
        for node in root.findall("s:url/s:loc", namespace)
        if node.text
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    urls = sitemap_urls()
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0
    request = Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        print(f"IndexNow accepted {len(urls)} URLs (HTTP {response.status}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

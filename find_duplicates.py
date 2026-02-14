#!/usr/bin/env python3
"""Find duplicate URLs across resources.html and news.html."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Dict, List, Set


def normalize_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r"[#?].*$", "", url)
    return url.rstrip("/")


def extract_links(html_text: str) -> List[str]:
    return re.findall(r"href=\"(https?://[^\"]+)\"", html_text, flags=re.IGNORECASE)


def load_urls(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [normalize_url(u) for u in extract_links(f.read())]
    except FileNotFoundError:
        print(f"Warning: {path} not found", file=sys.stderr)
        return []


def find_dupes(values: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return {k: v for k, v in counts.items() if v > 1}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find duplicate URLs across news and resources")
    parser.add_argument("--news", default="news.html")
    parser.add_argument("--resources", default="resources.html")
    args = parser.parse_args(argv)

    news_urls = load_urls(args.news)
    resource_urls = load_urls(args.resources)

    dupes_news = find_dupes(news_urls)
    dupes_resources = find_dupes(resource_urls)

    shared = sorted(set(news_urls) & set(resource_urls))

    print("Duplicate URLs in news.html:")
    if dupes_news:
        for url, count in sorted(dupes_news.items()):
            print(f"  {url} (x{count})")
    else:
        print("  None")

    print("\nDuplicate URLs in resources.html:")
    if dupes_resources:
        for url, count in sorted(dupes_resources.items()):
            print(f"  {url} (x{count})")
    else:
        print("  None")

    print("\nDuplicate URLs across news and resources:")
    if shared:
        for url in shared:
            print(f"  {url}")
    else:
        print("  None")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

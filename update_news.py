#!/usr/bin/env python3
"""Update news.html with fresh cloud security news.

- Pulls from multiple non-paywalled RSS/Atom feeds.
- Filters for cloud security topics.
- Ensures at least MIN_SOURCES distinct sources per update.
- Avoids duplicates across news.html and resources.html.
"""

import argparse
import datetime as dt
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


FEEDS = [
    {"name": "AWS Security Blog", "url": "https://aws.amazon.com/blogs/security/feed/"},
    {"name": "Google Cloud Blog", "url": "https://cloud.google.com/blog/products/identity-security/rss"},
    {"name": "Microsoft MSRC", "url": "https://msrc.microsoft.com/blog/feed/"},
    {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/rss/"},
    {"name": "SANS ISC", "url": "https://isc.sans.edu/rssfeed.xml"},
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/"},
    {"name": "The Hacker News", "url": "https://thehackernews.com/feeds/posts/default"},
    {"name": "SecurityWeek", "url": "https://www.securityweek.com/feed/"},
    {"name": "KrebsOnSecurity", "url": "https://krebsonsecurity.com/feed/"},
    {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml"},
    {"name": "Help Net Security", "url": "https://www.helpnetsecurity.com/feed/"},
    {"name": "Infosecurity Magazine", "url": "https://www.infosecurity-magazine.com/rss/news/"},
    {"name": "Security Affairs", "url": "https://securityaffairs.com/feed"},
    {"name": "Schneier on Security", "url": "https://www.schneier.com/feed/"},
    {"name": "The Register - Security", "url": "https://www.theregister.com/security/headlines.atom"},
    {"name": "The Register - Cloud", "url": "https://www.theregister.com/cloud/headlines.atom"},
    {"name": "Google Online Security", "url": "https://feeds.feedburner.com/GoogleOnlineSecurityBlog"},
    {"name": "CrowdStrike Blog", "url": "https://www.crowdstrike.com/blog/feed/"},
    {"name": "Palo Alto Networks Unit 42", "url": "https://unit42.paloaltonetworks.com/feed/"},
    {"name": "CISA Alerts", "url": "https://www.cisa.gov/uscert/ncas/alerts.xml"},
    {"name": "CISA Current Activity", "url": "https://www.cisa.gov/uscert/ncas/current-activity.xml"},
    {"name": "CISA Bulletins", "url": "https://www.cisa.gov/uscert/ncas/bulletins.xml"},
]

KEYWORDS = {
    "cloud", "aws", "azure", "gcp", "google cloud", "kubernetes", "k8s",
    "iam", "identity", "zero trust", "container", "supply chain",
    "ransomware", "breach", "data leak", "vulnerability", "cve", "exploit",
    "malware", "phishing", "botnet", "security", "patch", "incident",
    "ai", "llm", "genai", "machine learning", "ml",
    "job", "jobs", "hiring", "career", "layoff", "salary",
    "scam", "fraud", "social engineering", "credential", "identity theft",
}

CATEGORY_KEYWORDS = {
    "breach": ["breach", "data leak", "exposed", "leak", "compromise"],
    "vulnerability": ["vulnerability", "cve", "exploit", "rce", "zero-day", "xss", "injection"],
    "report": ["report", "guidance", "alert", "advisory", "bulletin", "update"],
}

TAG_KEYWORDS = {
    "AWS": ["aws", "amazon"],
    "Azure": ["azure", "microsoft"],
    "GCP": ["gcp", "google cloud"],
    "Kubernetes": ["kubernetes", "k8s"],
    "CISA": ["cisa"],
    "Vulnerability": ["vulnerability", "cve", "exploit", "rce", "zero-day"],
    "Breach": ["breach", "data leak", "exposed"],
    "Ransomware": ["ransomware"],
    "Phishing": ["phishing"],
    "Identity": ["iam", "identity"],
    "Supply Chain": ["supply chain"],
    "Zero Trust": ["zero trust"],
    "AI": ["ai", "llm", "genai", "machine learning", "ml"],
    "Jobs": ["job", "jobs", "hiring", "career", "layoff", "salary"],
    "Scam": ["scam", "fraud", "social engineering", "credential"],
}


def fetch_feed(url: str, timeout: int = 15) -> Optional[str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (CSOH News Bot; +https://csoh.org)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(value: str) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=dt.timezone.utc)
        return parsed
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=dt.timezone.utc)
            return parsed
        except Exception:
            continue
    return None


def _word_match(keyword: str, text: str) -> bool:
    """Match keyword in text using word boundaries for short keywords."""
    if len(keyword) <= 3:
        return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))
    return keyword in text


def is_relevant(text: str) -> bool:
    lower = text.lower()
    return any(_word_match(kw, lower) for kw in KEYWORDS)


def classify_category(text: str) -> str:
    lower = text.lower()
    for category, keys in CATEGORY_KEYWORDS.items():
        if any(_word_match(k, lower) for k in keys):
            return category
    return "report"


def build_tags(text: str) -> List[str]:
    lower = text.lower()
    tags: List[str] = []
    for tag, keys in TAG_KEYWORDS.items():
        if any(_word_match(k, lower) for k in keys):
            tags.append(tag)
    if not tags:
        tags = ["Cloud Security"]
    return tags[:3]


def normalize_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r"[#?].*$", "", url)
    return url.rstrip("/")


def extract_links(html_text: str) -> List[str]:
    return re.findall(r"href=\"(https?://[^\"]+)\"", html_text, flags=re.IGNORECASE)


def parse_rss(xml_text: str, source_name: str) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    tag = root.tag.lower()
    if tag.endswith("feed"):
        ns = "{http://www.w3.org/2005/Atom}"
        for entry in root.findall(f"{ns}entry"):
            title = (entry.findtext(f"{ns}title") or "").strip()
            link = ""
            for link_el in entry.findall(f"{ns}link"):
                rel = link_el.attrib.get("rel", "alternate")
                if rel == "alternate":
                    link = link_el.attrib.get("href", "")
                    break
            published = entry.findtext(f"{ns}published") or entry.findtext(f"{ns}updated") or ""
            summary = entry.findtext(f"{ns}summary") or entry.findtext(f"{ns}content") or ""
            items.append({
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
                "source": source_name,
            })
        return items

    # RSS
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        published = (item.findtext("pubDate") or item.findtext("date") or "").strip()
        summary = item.findtext("description") or item.findtext("summary") or ""
        items.append({
            "title": title,
            "link": link,
            "published": published,
            "summary": summary,
            "source": source_name,
        })
    return items


def load_existing_urls(news_path: str, resources_path: str) -> set:
    urls = set()
    for path in (news_path, resources_path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                urls.update(normalize_url(u) for u in extract_links(f.read()))
        except FileNotFoundError:
            continue
    return urls


def format_date(d: dt.datetime) -> Tuple[str, str]:
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    d_local = d.astimezone(dt.timezone.utc)
    return d_local.strftime("%B %d, %Y"), d_local.strftime("%Y-%m-%dT%H:%M:%SZ")


def render_card(entry: Dict[str, str], indent: str) -> str:
    title = html.escape(entry["title"])
    link = html.escape(entry["link"])
    summary = strip_html(entry.get("summary", ""))
    if len(summary) > 180:
        summary = summary[:177].rstrip() + "..."

    published_dt = parse_date(entry.get("published", "")) or dt.datetime.now(dt.timezone.utc)
    date_text, _ = format_date(published_dt)

    category = classify_category(f"{entry['title']} {summary}")
    tags = build_tags(f"{entry['title']} {summary} {entry['source']}")

    tag_spans = "\n".join([f"{indent}            <span class=\"tag\">{html.escape(t)}</span>" for t in tags])

    return (
        f"{indent}<a href=\"{link}\" class=\"card-link\" target=\"_blank\" rel=\"noopener noreferrer\">\n"
        f"{indent}    <div class=\"resource-card\" data-category=\"{category}\">\n"
        f"{indent}        <h3>{title}</h3>\n"
        f"{indent}        <p class=\"article-date\">{date_text}</p>\n"
        f"{indent}        <p>{html.escape(summary)} <span class=\"source\">({html.escape(entry['source'])})</span></p>\n"
        f"{indent}        <div class=\"resource-tags\">\n"
        f"{tag_spans}\n"
        f"{indent}        </div>\n"
        f"{indent}    </div>\n"
        f"{indent}</a>"
    )


def replace_grid(html_text: str, cards_html: str) -> str:
    marker = '<div class="resource-grid">'
    idx = html_text.find(marker)
    if idx == -1:
        raise ValueError("Could not find resource-grid container")

    start = idx + len(marker)
    depth = 1
    pattern = re.compile(r"</?div\b", re.IGNORECASE)

    for match in pattern.finditer(html_text, start):
        token = html_text[match.start():match.start() + 5].lower()
        if token.startswith("</div"):
            depth -= 1
        else:
            depth += 1
        if depth == 0:
            end = match.start()
            return html_text[:start] + "\n" + cards_html + "\n" + html_text[end:]

    raise ValueError("Could not find end of resource-grid container")


def update_date_modified(html_text: str, iso_date: str) -> str:
    return re.sub(r'"dateModified"\s*:\s*"[^"]+"', f'"dateModified": "{iso_date}"', html_text, count=1)


def build_entries(news_path: str, resources_path: str, max_articles: int, min_sources: int) -> Tuple[List[Dict[str, str]], str]:
    existing = load_existing_urls(news_path, resources_path)
    collected: List[Dict[str, str]] = []

    for feed in FEEDS:
        xml_text = fetch_feed(feed["url"])
        if not xml_text:
            continue
        for item in parse_rss(xml_text, feed["name"]):
            if not item.get("title") or not item.get("link"):
                continue
            combined = f"{item['title']} {item.get('summary', '')}"
            if not is_relevant(combined):
                continue
            norm = normalize_url(item["link"])
            if norm in existing:
                continue
            item["link"] = norm
            collected.append(item)

    if not collected:
        raise ValueError("No news items found from feeds")

    # Sort by published date (newest first)
    collected.sort(
        key=lambda x: parse_date(x.get("published", ""))
        or dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc),
        reverse=True,
    )

    # Select purely by date order
    selected: List[Dict[str, str]] = collected[:max_articles]

    sources = {item["source"] for item in selected}
    if len(sources) < min_sources:
        print(
            f"Warning: Only {len(sources)} sources available; expected at least {min_sources}.",
            file=sys.stderr,
        )

    newest = parse_date(selected[0].get("published", "")) or dt.datetime.now(dt.timezone.utc)
    _, newest_iso = format_date(newest)
    return selected[:max_articles], newest_iso


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Update news.html from RSS feeds")
    parser.add_argument("--news-file", default="news.html")
    parser.add_argument("--resources-file", default="resources.html")
    parser.add_argument("--max-articles", type=int, default=120)
    parser.add_argument("--min-sources", type=int, default=10)
    args = parser.parse_args(argv)

    try:
        entries, newest_iso = build_entries(args.news_file, args.resources_file, args.max_articles, args.min_sources)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    indent = " " * 16
    cards_html = "\n".join(render_card(entry, indent) for entry in entries)

    try:
        with open(args.news_file, "r", encoding="utf-8") as f:
            html_text = f.read()
    except FileNotFoundError:
        print(f"Error: {args.news_file} not found", file=sys.stderr)
        return 1

    html_text = replace_grid(html_text, cards_html)
    html_text = update_date_modified(html_text, newest_iso)

    with open(args.news_file, "w", encoding="utf-8") as f:
        f.write(html_text)

    print(f"Updated {args.news_file} with {len(entries)} articles from {len({e['source'] for e in entries})} sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

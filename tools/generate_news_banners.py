#!/usr/bin/env python3
"""
Generate banner images for news sources.

Captures homepage screenshots of each RSS feed source and saves them
as preview banners for use in news article cards.

Usage:
    python3 tools/generate_news_banners.py          # generate all missing
    python3 tools/generate_news_banners.py --force   # regenerate all
"""

import sys
import os
import time
from pathlib import Path

BANNER_DIR = Path(__file__).parent.parent / "img" / "news-banners"
BANNER_DIR.mkdir(parents=True, exist_ok=True)

# Unique source sites — slug to homepage URL
# Shared domains (The Register × 2, CISA × 3) map to a single slug.
SOURCES = {
    "aws-security-blog":      "https://aws.amazon.com/blogs/security/",
    "google-cloud-blog":      "https://cloud.google.com/blog/products/identity-security",
    "microsoft-msrc":         "https://msrc.microsoft.com/blog/",
    "cloudflare-blog":        "https://blog.cloudflare.com/",
    "sans-isc":               "https://isc.sans.edu/",
    "bleepingcomputer":       "https://www.bleepingcomputer.com/",
    "thehackernews":          "https://thehackernews.com/",
    "securityweek":           "https://www.securityweek.com/",
    "krebsonsecurity":        "https://krebsonsecurity.com/",
    "darkreading":            "https://www.darkreading.com/",
    "helpnetsecurity":        "https://www.helpnetsecurity.com/",
    "infosecurity-magazine":  "https://www.infosecurity-magazine.com/",
    "securityaffairs":        "https://securityaffairs.com/",
    "schneier":               "https://www.schneier.com/",
    "theregister":            "https://www.theregister.com/",
    "google-online-security": "https://security.googleblog.com/",
    "crowdstrike":            "https://www.crowdstrike.com/blog/",
    "unit42":                 "https://unit42.paloaltonetworks.com/",
    "cisa":                   "https://www.cisa.gov/",
}

VIEWPORT_W = 1280
VIEWPORT_H = 720
TIMEOUT_S = 30


def capture_banner(slug: str, url: str, force: bool = False) -> bool:
    """Capture a homepage screenshot and save as a banner image."""
    output = BANNER_DIR / f"{slug}.jpg"
    if output.exists() and not force:
        print(f"  ✔ {slug}.jpg already exists, skipping")
        return True

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: playwright not installed — pip install playwright && playwright install chromium")
        return False

    print(f"  📸 Capturing {slug} → {url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": VIEWPORT_W, "height": VIEWPORT_H},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.set_default_timeout(TIMEOUT_S * 1000)
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(2)  # let JS render

            # Take a viewport-sized screenshot (not full page)
            page.screenshot(path=str(output), full_page=False, type="jpeg", quality=85)
            browser.close()

        # Resize to match resource-preview card dimensions
        try:
            from PIL import Image
            img = Image.open(output)
            img = img.resize((400, 300), Image.LANCZOS)
            img.save(output, "JPEG", quality=85, optimize=True)
        except ImportError:
            pass  # Pillow not available — raw screenshot is fine

        size_kb = os.path.getsize(output) / 1024
        print(f"  ✔ {slug}.jpg ({size_kb:.0f} KB)")
        return True

    except Exception as e:
        print(f"  ✖ {slug} failed: {e}")
        return False


def main():
    force = "--force" in sys.argv
    print(f"Generating news source banners ({'force' if force else 'skip existing'})…\n")

    ok, fail = 0, 0
    for slug, url in SOURCES.items():
        if capture_banner(slug, url, force):
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} captured, {fail} failed, {len(SOURCES)} total sources")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Interactive News Source Submission Tool for CSOH.org.

This script helps contributors add a new RSS/Atom feed to update_news.py with:
- Interactive prompts
- URL safety validation
- Basic feed validation
- Git branch creation and commit
- PR instructions

Usage:
    python3 tools/submit_news_source.py
"""

import re
import sys
import urllib.request
from pathlib import Path
from check_url_safety import URLSafetyChecker
import subprocess

NEWS_SCRIPT = Path(__file__).parent.parent / "update_news.py"
FEEDS_VAR = "FEEDS"


def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def get_input(prompt, required=True):
    while True:
        value = input(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("This field is required. Please try again.\n")


def git_command(args, capture_output=True):
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=capture_output,
            text=True,
            check=True,
        )
        return True, result.stdout.strip() if capture_output else ""
    except subprocess.CalledProcessError as exc:
        return False, exc.stderr if capture_output else str(exc)


def check_git_status():
    success, output = git_command(["status", "--porcelain"])
    if not success:
        return False, "Not in a git repository"
    if output:
        return False, "Working directory has uncommitted changes. Please commit or stash them first."
    return True, ""


def validate_feed_url(url):
    if not url.startswith(("http://", "https://")):
        return False, "URL must start with http:// or https://"
    return True, ""


def check_url_safety(url):
    checker = URLSafetyChecker()
    return checker.check_url(url)


def fetch_feed(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (CSOH News Bot; +https://csoh.org)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def looks_like_feed(text):
    lower = text.lower()
    return "<rss" in lower or "<feed" in lower or "<rdf:rdf" in lower


def parse_existing_feeds(text):
    # Basic parse to find existing names and URLs from FEEDS list.
    match = re.search(rf"{FEEDS_VAR}\s*=\s*\[(.*?)\]", text, re.DOTALL)
    if not match:
        return [], []
    block = match.group(1)
    names = re.findall(r"\"name\"\s*:\s*\"([^\"]+)\"", block)
    urls = re.findall(r"\"url\"\s*:\s*\"([^\"]+)\"", block)
    return names, urls


def insert_feed(text, name, url):
    lines = text.splitlines(keepends=True)
    start_idx = None
    depth = 0
    for i, line in enumerate(lines):
        if start_idx is None and re.search(rf"^{FEEDS_VAR}\s*=\s*\[", line):
            start_idx = i
            depth += line.count("[") - line.count("]")
            continue
        if start_idx is not None:
            depth += line.count("[") - line.count("]")
            if depth == 0:
                insert_line = f"    {{\"name\": \"{name}\", \"url\": \"{url}\"}},\n"
                lines.insert(i, insert_line)
                return "".join(lines)
    raise ValueError("Could not locate FEEDS list in update_news.py")


def create_branch_and_commit(source_name):
    slug = re.sub(r"[^a-z0-9]+", "-", source_name.lower()).strip("-")
    branch_name = f"add-news-source-{slug}"[:60]

    success, output = git_command(["checkout", "-b", branch_name])
    if not success:
        return False, f"Failed to create branch: {output}"

    success, output = git_command(["add", "update_news.py"])
    if not success:
        return False, f"Failed to stage changes: {output}"

    commit_message = f"Add news source: {source_name}"
    success, output = git_command(["commit", "-m", commit_message])
    if not success:
        return False, f"Failed to commit: {output}"

    return True, branch_name


def main():
    print_header("CSOH News Source Submission Tool")

    print("This tool will help you add a new news source feed.")
    print("It will validate the feed URL and prepare a PR.")

    print("\n" + "=" * 70 + "\n")

    git_ok, git_msg = check_git_status()
    if not git_ok:
        print(f"Error: {git_msg}")
        print("Please resolve this before continuing.")
        return 1

    if not NEWS_SCRIPT.exists():
        print(f"Error: Could not find {NEWS_SCRIPT}")
        return 1

    source_name = get_input("Source name (e.g., AWS Security Blog)")

    while True:
        feed_url = get_input("Feed URL (RSS or Atom)")
        valid, msg = validate_feed_url(feed_url)
        if not valid:
            print(f"Error: {msg}\n")
            continue

        safety = check_url_safety(feed_url)
        if not safety["safe"]:
            print("Error: URL failed safety checks:")
            for err in safety.get("errors", []):
                print(f"  - {err}")
            retry = input("Try a different URL? (y/n): ").strip().lower()
            if retry == "y":
                continue
            return 1

        if safety.get("warnings"):
            print("Warning: URL has warnings:")
            for warn in safety["warnings"]:
                print(f"  - {warn}")
            proceed = input("Proceed anyway? (y/n): ").strip().lower()
            if proceed != "y":
                continue

        print("Checking that the feed looks valid...")
        try:
            feed_text = fetch_feed(feed_url)
        except Exception as exc:
            print(f"Warning: Could not fetch feed: {exc}")
            proceed = input("Proceed anyway? (y/n): ").strip().lower()
            if proceed != "y":
                continue
            break

        if not looks_like_feed(feed_text):
            print("Warning: Feed does not look like RSS or Atom.")
            proceed = input("Proceed anyway? (y/n): ").strip().lower()
            if proceed != "y":
                continue
        break

    with open(NEWS_SCRIPT, "r", encoding="utf-8") as f:
        news_text = f.read()

    existing_names, existing_urls = parse_existing_feeds(news_text)
    existing_names_lower = {name.lower() for name in existing_names}
    existing_urls_lower = {url.lower() for url in existing_urls}
    if source_name.lower() in existing_names_lower:
        print("Error: This source name already exists in FEEDS.")
        return 1
    if feed_url.lower() in existing_urls_lower:
        print("Error: This feed URL already exists in FEEDS.")
        return 1

    updated_text = insert_feed(news_text, source_name, feed_url)

    with open(NEWS_SCRIPT, "w", encoding="utf-8") as f:
        f.write(updated_text)

    print("Updated update_news.py with the new feed.")

    success, branch_name = create_branch_and_commit(source_name)
    if not success:
        print(branch_name)
        print("The change was written but git operations failed.")
        return 1

    print(f"Created branch: {branch_name}")
    print("Committed changes.")

    print("\nNext steps:")
    print(f"1. Push your branch: git push origin {branch_name}")
    print("2. Create a PR: https://github.com/CloudSecurityOfficeHours/csoh.org/pulls")
    print("3. Include source name and feed URL in the PR description")

    auto_push = input("Push now? (y/n): ").strip().lower()
    if auto_push == "y":
        success, output = git_command(["push", "-u", "origin", branch_name])
        if success:
            print("Push successful.")
            print("Create your PR here:")
            print(f"https://github.com/CloudSecurityOfficeHours/csoh.org/compare/{branch_name}?expand=1")
        else:
            print(f"Push failed: {output}")

    print_header("Submission Complete")
    print("Thank you for contributing to CSOH.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(1)

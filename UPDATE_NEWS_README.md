# Update News Automation

This repo includes a lightweight news updater script: `update_news.py`.

## What It Does

- Pulls cloud security news from multiple non-paywalled RSS/Atom feeds.
- Filters for cloud/security topics and avoids duplicates.
- Ensures at least 10 distinct sources per update.
- Rewrites the `news.html` article grid and updates the `dateModified` JSON-LD value.

## Requirements

- Python 3.9+ (standard library only)
- Outbound internet access

## Run It

```bash
python3 update_news.py
```

Optional arguments:

```bash
python3 update_news.py --news-file news.html --resources-file resources.html --max-articles 120 --min-sources 10
```

## Feeds Used

The script uses these sources by default:

- AWS Security Blog
- Google Cloud Blog (Identity/Security)
- Microsoft MSRC
- Cloudflare Blog
- SANS ISC
- BleepingComputer
- The Hacker News
- SecurityWeek
- KrebsOnSecurity
- CISA Alerts
- CISA Current Activity
- CISA Bulletins

You can edit the `FEEDS` list in `update_news.py` to add or remove sources.

## Duplicate Handling

The script avoids duplicates by comparing normalized URLs against:

- Existing entries in `news.html`
- Any URLs in `resources.html`

## Notes

- If fewer than 10 sources are available on a given run, the script exits with an error.
- The script does not edit structured data beyond updating `dateModified`.

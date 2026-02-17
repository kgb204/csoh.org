# Update News Automation

## How Does the News Page Stay Up to Date?

The [News page](https://csoh.org/news.html) is updated **automatically every 12 hours** — no one has to manually add articles. The script also generates an **RSS feed** (`feed.xml`) so subscribers get updates automatically. Here's how it works in plain English:

1. **GitHub Actions** (a free automation service built into GitHub) runs a Python script on a schedule — twice a day, at midnight and noon UTC.
2. The script visits **22 cloud security news sources** and checks for new articles using something called **RSS feeds**. An RSS feed is like a news wire — it's a machine-readable list of recent articles that a website publishes so other tools can easily pull in headlines, dates, and summaries.
3. The script filters those articles for **cloud security topics** (looking for keywords like "AWS", "Azure", "Kubernetes", "vulnerability", "breach", etc.) and throws out duplicates.
4. It then updates `news.html` with fresh article cards — title, date, summary, source name, and a link to the original article. It also regenerates `feed.xml` (the RSS feed) with the latest articles.
5. Instead of pushing changes directly, it **creates a Pull Request** (a proposed change) so a maintainer can review it before it goes live.
6. If the only files changed are `news.html` and `feed.xml`, the PR is **automatically merged** — no human review needed for routine news updates.
7. Once merged, the **unified site-update-deploy.yml workflow** automatically uploads the updated site to the web server via FTP.

**The end result:** the News page always has fresh, relevant cloud security articles without anyone lifting a finger.

---

## News Sources (22 feeds)

The script pulls from these trusted, non-paywalled sources:

| Source | What It Covers |
|--------|---------------|
| AWS Security Blog | Official AWS security announcements |
| Google Cloud Blog | Google Cloud identity & security updates |
| Google Online Security Blog | Google-wide security research |
| Microsoft MSRC | Microsoft Security Response Center advisories |
| Cloudflare Blog | Web security, DDoS, zero trust |
| SANS ISC | Internet Storm Center threat intelligence |
| BleepingComputer | Malware, vulnerabilities, data breaches |
| The Hacker News | Cybersecurity news and analysis |
| SecurityWeek | Enterprise security news |
| KrebsOnSecurity | Investigative cybersecurity journalism |
| Dark Reading | Enterprise security research |
| Help Net Security | Security news and expert insights |
| Infosecurity Magazine | Industry news and analysis |
| Security Affairs | Cyber crime and hacking news |
| Schneier on Security | Security commentary by Bruce Schneier |
| The Register - Security | IT security news |
| The Register - Cloud | Cloud infrastructure news |
| CrowdStrike Blog | Threat intelligence and research |
| Palo Alto Networks Unit 42 | Threat research and analysis |
| CISA Alerts | US government cybersecurity alerts |
| CISA Current Activity | Active threats and exploits |
| CISA Bulletins | Weekly vulnerability summaries |

Want to **add a new source**? You have two options:

1. Run `python3 tools/submit_news_source.py` (interactive, recommended)
2. Or edit the `FEEDS` list at the top of `update_news.py` manually

**Script guide:** [tools/SUBMIT_NEWS_SOURCE_README.md](tools/SUBMIT_NEWS_SOURCE_README.md)

### Common Errors (Submit Script)

- **`python3` not found**: Install Python from python.org and reopen your terminal
- **`git` not found**: Install Git from git-scm.com
- **Not in a git repo**: Run `cd csoh.org` before the script
- **Feed URL rejected**: Use the RSS/Atom feed URL (not the homepage)
- **Working directory not clean**: Commit or stash changes, then retry

---

## How the GitHub Actions Workflow Works

The workflow is defined in `.github/workflows/update-news.yml`. Here's what happens step by step:

```
Schedule (every 12 hours) or manual trigger
        |
        v
  Check out the latest code from the repo
        |
        v
  Run update_news.py (fetch feeds, filter, update news.html + feed.xml)
        |
        v
  Any changes?
   /         \
  No          Yes
  |            |
  Done    Create a Pull Request
              |
              v
         Only news.html + feed.xml changed?
          /         \
        Yes          No
         |            |
     Auto-merge    Wait for
     (squash)      human review
         |
         v
      Unified workflow uploads to web server
```

### Triggers

- **Scheduled:** Runs automatically at midnight and noon UTC (`0 */12 * * *` in cron syntax)
- **Manual:** You can trigger it anytime from the GitHub Actions tab (click "Run workflow")
- **On push:** Runs when `update_news.py` itself is modified and pushed to main

---

## Running Manually (for developers)

You don't need GitHub Actions to run the script. If you have Python 3.9+ installed:

```bash
python3 update_news.py
```

Optional arguments:

```bash
python3 update_news.py \
  --news-file news.html \
  --resources-file resources.html \
  --max-articles 120 \
  --min-sources 10
```

### Requirements

- Python 3.9+ (standard library only — no `pip install` needed)
- Internet access (to fetch RSS feeds)

---

## Duplicate Handling

The script avoids posting the same article twice by comparing normalized URLs against:

- Existing entries already in `news.html`
- Any URLs in `resources.html` (so news doesn't duplicate a curated resource)

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Workflow fails with "not permitted to create pull requests" | Missing or expired PAT | Create a new fine-grained PAT with Contents + Pull Requests permissions and save it as the `PAT_TOKEN` repo secret |
| Script exits with "fewer than 10 sources" | Too many feeds are down or unreachable | Usually temporary — wait for the next scheduled run |
| No PR created | No new articles found since last run | Normal — means news is already up to date |
| PR not auto-merging | Files other than `news.html` changed | Review the PR manually — the script may have been updated |
| Site not deployed after merge | Unified workflow failed or was skipped | Check Actions tab for site-update-deploy.yml run and resolve any errors |

---

## Setup Requirements

The workflow uses a **Personal Access Token (PAT)** stored as a GitHub repo secret called `PAT_TOKEN`. This is needed because the GitHub organization restricts what the default `GITHUB_TOKEN` can do.

To set up or rotate the token:

1. Go to [GitHub Token Settings](https://github.com/settings/tokens) and create a **fine-grained token**
2. Grant it access to the `CloudSecurityOfficeHours/csoh.org` repository
3. Give it **Contents** (read/write) and **Pull requests** (read/write) permissions
4. Go to the repo's **Settings > Secrets and variables > Actions** and save it as `PAT_TOKEN`

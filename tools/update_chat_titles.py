#!/usr/bin/env python3
import re
from urllib.parse import urlparse, unquote

#!/usr/bin/env python3
import re
import time
import html
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

INPUT = 'chat-resources.html'
BACKUP = INPUT + '.fetch.bak'


def humanize_path(path):
    if not path or path == '/':
        return ''
    parts = [p for p in path.split('/') if p]
    if parts and re.search(r'\.(html|htm|php|aspx|jsp)$', parts[-1]):
        parts[-1] = re.sub(r'\.(html|htm|php|aspx|jsp)$', '', parts[-1])
    parts = [re.sub(r'[-_]+', ' ', p) for p in parts]
    return ' – '.join([p.replace('%20', ' ') for p in parts])


def title_from_url(url):
    try:
        parsed = urlparse(url)
    except Exception:
        return url
    host = parsed.netloc.replace('www.', '')
    host = host.split(':')[0]
    path_h = humanize_path(unquote(parsed.path))
    special = {
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'github.com': 'GitHub',
        'en.wikipedia.org': 'Wikipedia',
        'gemini.google.com': 'Gemini Share',
        'a.co': 'Amazon',
    }
    if host in special and path_h:
        return f"{special[host]}: {path_h}"
    if host in special:
        return special[host]
    if path_h:
        return f"{host} — {path_h.title()}"
    return host


def fetch_title(url, timeout=6):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CSOH-bot/1.0)'} )
        with urlopen(req, timeout=timeout) as r:
            # read a reasonable chunk
            raw = r.read(131072)
            try:
                text = raw.decode('utf-8', errors='replace')
            except Exception:
                text = raw.decode('latin-1', errors='replace')
            m = re.search(r'<title[^>]*>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
            if m:
                t = html.unescape(m.group(1)).strip()
                # collapse whitespace
                t = re.sub(r'\s+', ' ', t)
                return t
    except (URLError, HTTPError, ValueError, Exception):
        return None
    return None


def make_backup(content):
    with open(BACKUP, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    with open(INPUT, 'r', encoding='utf-8') as f:
        html_doc = f.read()

    make_backup(html_doc)

    pattern = re.compile(r'(<a[^>]+href="([^"]+)"[^>]*>\s*<div class="resource-card"[\s\S]*?<h3>)(.*?)(</h3>)', re.IGNORECASE)

    changes = 0

    def repl(m):
        nonlocal changes
        prefix = m.group(1)
        href = m.group(2)
        old = m.group(3).strip()
        suffix = m.group(4)
        # try fetching
        title = None
        try:
            title = fetch_title(href)
        except Exception:
            title = None
        if not title:
            title = title_from_url(href)
        changes += 1
        return prefix + title + suffix

    new_html = pattern.sub(repl, html_doc)

    with open(INPUT, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f"Updated {changes} titles in {INPUT}, backup saved to {BACKUP}")


if __name__ == '__main__':
    main()

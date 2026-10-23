"""Read one web page as plain text: for the website in the work list, which web_fetch will not open (web_fetch only opens
addresses that appeared in a web_search result or in a page it fetched).

Usage: python3 read_page.py URL [--max 12000]
Prints the final address, the page title, up to --max characters of readable text (scripts, styles and tags removed)
and the same-site links worth opening next (about, team, services). Personal social media is refused.
Exit 0 = read, 1 = could not be read, 2 = refused.
"""
import argparse
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BLOCKED = ("instagram.com", "tiktok.com")


def text_of(page):
    t = re.sub(r"(?is)<(script|style|noscript|svg|template)[^>]*>.*?</\1>", " ", page)
    t = re.sub(r"(?i)<br\s*/?>|</(p|h[1-6]|li|div|section|article|tr|header|footer)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r\f\v\xa0]+", " ", t)
    return re.sub(r"\n\s*(\n\s*)+", "\n", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--max", type=int, default=12000)
    a = ap.parse_args()
    url = a.url if re.match(r"^https?://", a.url, re.I) else "https://" + a.url
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    if any(host == b or host.endswith("." + b) for b in BLOCKED):
        print("REFUSED: %s is personal social media (see references/safety.md)" % host)
        sys.exit(2)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; meeting-brief-agent/1.0)",
                                               "Accept": "text/html,application/xhtml+xml"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read(3_000_000)
            final = r.geturl()
            charset = r.headers.get_content_charset() or "utf-8"
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("COULD NOT READ %s: %s" % (url, e))
        sys.exit(1)
    page = raw.decode(charset, "replace")
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", page)
    body = text_of(page)
    print("URL: %s" % final)
    print("TITLE: %s" % (html.unescape(title.group(1)).strip() if title else ""))
    print("TEXT (%d characters%s):" % (len(body), ", cut at %d" % a.max if len(body) > a.max else ""))
    print(body[:a.max])
    base = urllib.parse.urlparse(final)
    skip_ext = re.compile(r"\.(png|jpe?g|gif|svg|webp|css|js|pdf|ico|xml|json|woff2?|ttf|otf|eot|webmanifest|mp4|mp3|zip)$", re.I)
    skip_path = re.compile(r"/(wp-json|wp-content|wp-includes|wp-admin|wp|app/uploads|themes|feed|cdn-cgi)(/|$)|xmlrpc|/tag/|/author/", re.I)
    links, seen = [], set()
    for href in re.findall(r"""href=["']([^"'#]+)""", page, re.I):
        full = urllib.parse.urljoin(final, href.strip()).split("?")[0]
        p = urllib.parse.urlparse(full)
        key = p.path.rstrip("/").lower()
        if p.scheme not in ("http", "https") or p.netloc != base.netloc or key in ("", base.path.rstrip("/").lower()):
            continue
        if skip_ext.search(p.path) or skip_path.search(p.path) or key in seen:
            continue
        seen.add(key)
        links.append(full)
    if links:
        links.sort(key=lambda u: (len(urllib.parse.urlparse(u).path), u))
        print("SAME-SITE LINKS: " + " ".join(links[:30]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

#!/usr/bin/env python3
"""Builds news.json for Deckwright's News tab from Daily MTG (magic.wizards.com/en/news).

The news page lists article links. Each article page carries standard share tags (og:title, og:image,
og:description, and a publish date), which are far steadier than the page layout, so the headline,
picture and date are read from those. Only the newest articles are kept.

Usage: python3 build_news.py news.json
"""
import html
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://magic.wizards.com"
INDEX = BASE + "/en/news"
MAX_ITEMS = 20
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 Deckwright-news"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


ARTICLE = re.compile(r'href="((?:https://magic\.wizards\.com)?/en/news/([a-z0-9-]+)/([a-z0-9-]+))(?:[?#][^"]*)?"', re.I)


def article_links(page):
    """Article URLs on the news page, in page order (newest first), with their section ("announcements", ...)."""
    seen, out = set(), []
    for m in ARTICLE.finditer(page):
        path, section = m.group(1), m.group(2)
        url = path if path.startswith("http") else BASE + path
        if url in seen:
            continue
        seen.add(url)
        out.append((url, section))
    # also catch links that only appear inside embedded page data (JSON with escaped slashes)
    for m in re.finditer(r'\\?/en\\?/news\\?/([a-z0-9-]+)\\?/([a-z0-9-]+)', page):
        url = f"{BASE}/en/news/{m.group(1)}/{m.group(2)}"
        if url not in seen:
            seen.add(url)
            out.append((url, m.group(1)))
    return out


def meta(page, *names):
    for n in names:
        for pat in (rf'<meta[^>]+(?:property|name|itemprop)=["\']{re.escape(n)}["\'][^>]*content=["\']([^"\']*)["\']',
                    rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name|itemprop)=["\']{re.escape(n)}["\']'):
            m = re.search(pat, page, re.I)
            if m and m.group(1).strip():
                return html.unescape(m.group(1).strip())
    return ""


def published(page):
    d = meta(page, "article:published_time", "og:article:published_time", "datePublished", "date", "publish-date")
    if not d:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', page) or re.search(r'<time[^>]+datetime=["\']([^"\']+)["\']', page, re.I)
        d = m.group(1) if m else ""
    try:
        return datetime.fromisoformat(d.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d")
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", d)
        return m.group(1) if m else ""


def tidy_title(t):
    return re.sub(r"\s*[|–-]\s*Magic: The Gathering\s*$", "", t).strip()


def main(out_path):
    links = article_links(get(INDEX))
    if not links:
        raise SystemExit("No article links found on the news page; its layout may have changed.")
    items = []
    for url, section in links[: MAX_ITEMS + 10]:
        try:
            page = get(url)
        except Exception as e:  # one bad article shouldn't stop the rest
            print("skip", url, e)
            continue
        title = tidy_title(meta(page, "og:title", "twitter:title"))
        if not title:
            m = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
            title = tidy_title(html.unescape(m.group(1).strip())) if m else ""
        if not title:
            continue
        img = meta(page, "og:image", "twitter:image")
        if img.startswith("//"):
            img = "https:" + img
        items.append({
            "title": title,
            "url": url,
            "section": section.replace("-", " ").title(),
            "date": published(page),
            "summary": meta(page, "og:description", "description", "twitter:description")[:240],
            "image": img,
        })
        if len(items) >= MAX_ITEMS:
            break
        time.sleep(0.5)  # be polite
    if not items:
        raise SystemExit("Found links but couldn't read any articles.")
    items.sort(key=lambda x: x["date"], reverse=True)  # dated newest first; undated keep page order at the end
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "source": INDEX, "items": items}, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(items)} articles to {out_path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "news.json")

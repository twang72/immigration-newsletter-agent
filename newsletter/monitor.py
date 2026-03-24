"""
Monitors official IRCC sources for the latest Canadian immigration news.
Only official government sources — no third-party or social media content.
"""

import httpx
from bs4 import BeautifulSoup

IRCC_NEWS_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/news.html"
IRCC_NOTICES_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals.html"


def fetch_ircc_news() -> list[dict]:
    """Fetch latest news releases from IRCC."""
    stories = []
    try:
        resp = httpx.get(IRCC_NEWS_URL, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = (
            soup.select("li.item article")
            or soup.select("article.news-item")
            or soup.select(".views-row")
            or soup.select("li.item")
        )
        for item in items[:6]:
            title_tag = item.find(["h3", "h2", "a"])
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            if not title:
                continue
            link_tag = item.find("a", href=True)
            link = link_tag["href"] if link_tag else ""
            if link and not link.startswith("http"):
                link = "https://www.canada.ca" + link
            stories.append({"source": "IRCC News", "title": title, "url": link})
    except Exception as e:
        print(f"[monitor] IRCC news fetch error: {e}")
    return stories


def fetch_ircc_notices() -> list[dict]:
    """Fetch latest operational bulletins and policy notices from IRCC."""
    stories = []
    try:
        resp = httpx.get(IRCC_NOTICES_URL, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = (
            soup.select("li.item article")
            or soup.select("li.item")
            or soup.select(".views-row")
        )
        for item in items[:4]:
            title_tag = item.find(["h3", "h2", "a"])
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            if not title:
                continue
            link_tag = item.find("a", href=True)
            link = link_tag["href"] if link_tag else ""
            if link and not link.startswith("http"):
                link = "https://www.canada.ca" + link
            stories.append({"source": "IRCC Policy Notice", "title": title, "url": link})
    except Exception as e:
        print(f"[monitor] IRCC notices fetch error: {e}")
    return stories


def gather_stories() -> list[dict]:
    print("[monitor] Gathering official IRCC news and notices...")
    stories = []
    stories.extend(fetch_ircc_news())
    stories.extend(fetch_ircc_notices())
    print(f"[monitor] Found {len(stories)} official stories")
    return stories

"""
Monitors official IRCC sources for the latest Canadian immigration news.
Only official government sources — no third-party or social media content.
"""

import httpx
from bs4 import BeautifulSoup

# IRCC advanced news search — reliable source of news releases
IRCC_RELEASES_URL = (
    "https://www.canada.ca/en/news/advanced-news-search/news-results.html"
    "?typ=newsreleases&dprtmnt=departmentofcitizenshipandimmigration&start=2025-01-01"
)
IRCC_NOTICES_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/news/notices.html"


def fetch_ircc_releases() -> list[dict]:
    """Fetch latest IRCC news releases via the advanced search page."""
    stories = []
    try:
        resp = httpx.get(IRCC_RELEASES_URL, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        # News items are <a> tags linking to ircc news URLs
        links = soup.find_all("a", href=True)
        seen = set()
        for a in links:
            href = a["href"]
            title = a.get_text(strip=True)
            if (
                "/immigration-refugees-citizenship/news/" in href
                and title
                and len(title) > 20
                and href not in seen
            ):
                if not href.startswith("http"):
                    href = "https://www.canada.ca" + href
                stories.append({"source": "IRCC News Release", "title": title, "url": href})
                seen.add(href)
            if len(stories) >= 6:
                break
    except Exception as e:
        print(f"[monitor] IRCC releases fetch error: {e}")
    return stories


def fetch_ircc_notices() -> list[dict]:
    """Fetch latest IRCC policy notices."""
    stories = []
    try:
        resp = httpx.get(IRCC_NOTICES_URL, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.find_all("a", href=True)
        seen = set()
        for a in links:
            href = a["href"]
            title = a.get_text(strip=True)
            if (
                "/immigration-refugees-citizenship/" in href
                and title
                and len(title) > 20
                and href not in seen
                and "notice" in href.lower()
            ):
                if not href.startswith("http"):
                    href = "https://www.canada.ca" + href
                stories.append({"source": "IRCC Notice", "title": title, "url": href})
                seen.add(href)
            if len(stories) >= 4:
                break
    except Exception as e:
        print(f"[monitor] IRCC notices fetch error: {e}")
    return stories


def gather_stories() -> list[dict]:
    print("[monitor] Gathering official IRCC news and notices...")
    stories = []
    stories.extend(fetch_ircc_releases())
    stories.extend(fetch_ircc_notices())
    print(f"[monitor] Found {len(stories)} official stories")
    return stories

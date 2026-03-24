"""
Monitors IRCC and Reddit for the latest Canadian immigration news.
Returns a list of raw story dicts for the newsletter writer to process.
"""

import os
import httpx
import praw
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

IRCC_NEWS_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/news.html"
IRCC_NOTICES_URL = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/publications-manuals/operational-bulletins-manuals.html"
REDDIT_SUBS = ["ImmigrationCanada", "ExpressEntry", "CanadaVisa"]


def fetch_ircc_news() -> list[dict]:
    stories = []
    try:
        resp = httpx.get(IRCC_NEWS_URL, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Try multiple selectors for IRCC's news page structure
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
            stories.append({"source": "IRCC", "title": title, "url": link})
    except Exception as e:
        print(f"[monitor] IRCC news fetch error: {e}")
    return stories


def fetch_reddit_posts() -> list[dict]:
    stories = []
    try:
        reddit = praw.Reddit(
            client_id=os.environ["REDDIT_CLIENT_ID"],
            client_secret=os.environ["REDDIT_CLIENT_SECRET"],
            user_agent=os.environ.get("REDDIT_USER_AGENT", "immigration-newsletter-bot/1.0"),
        )
        for sub_name in REDDIT_SUBS:
            sub = reddit.subreddit(sub_name)
            for post in sub.hot(limit=3):
                if post.score > 50:
                    stories.append({
                        "source": f"r/{sub_name}",
                        "title": post.title,
                        "url": f"https://reddit.com{post.permalink}",
                        "score": post.score,
                    })
    except Exception as e:
        print(f"[monitor] Reddit fetch error: {e}")
    return stories


def gather_stories() -> list[dict]:
    print("[monitor] Gathering Canadian immigration stories...")
    stories = []
    stories.extend(fetch_ircc_news())
    stories.extend(fetch_reddit_posts())
    print(f"[monitor] Found {len(stories)} stories")
    return stories

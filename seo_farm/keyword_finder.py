"""
Keyword discovery for the global immigration SEO farm.

Sources (all free, no paid API required):
1. Seed keywords — curated high-value immigration topics by country
2. Reddit — top posts from immigration subreddits (JSON API, no auth needed)
3. Google Trends RSS — what's trending in immigration searches

Output: list of {keyword, country, source, priority} dicts
"""

import re
import httpx
from bs4 import BeautifulSoup

# ── Seed Keywords ────────────────────────────────────────────────────────────
# priority 1 = highest (evergreen, high search volume)
# priority 3 = trending/topical

SEED_KEYWORDS: list[dict] = [
    # Canada
    {"keyword": "express entry draw 2026", "country": "Canada", "source": "seed", "priority": 1},
    {"keyword": "canada pr requirements 2026", "country": "Canada", "source": "seed", "priority": 1},
    {"keyword": "canada study permit application guide", "country": "Canada", "source": "seed", "priority": 1},
    {"keyword": "canada open work permit eligibility", "country": "Canada", "source": "seed", "priority": 1},
    {"keyword": "canada post graduation work permit guide", "country": "Canada", "source": "seed", "priority": 1},
    {"keyword": "provincial nominee program streams 2026", "country": "Canada", "source": "seed", "priority": 2},
    {"keyword": "canada spouse sponsorship processing time", "country": "Canada", "source": "seed", "priority": 2},
    {"keyword": "canada citizenship application requirements", "country": "Canada", "source": "seed", "priority": 2},
    {"keyword": "canada visitor visa requirements 2026", "country": "Canada", "source": "seed", "priority": 2},
    {"keyword": "canadian experience class eligibility", "country": "Canada", "source": "seed", "priority": 2},

    # Australia
    {"keyword": "australia skilled migration visa 2026", "country": "Australia", "source": "seed", "priority": 1},
    {"keyword": "australia 189 visa requirements", "country": "Australia", "source": "seed", "priority": 1},
    {"keyword": "australia 190 visa state nomination guide", "country": "Australia", "source": "seed", "priority": 1},
    {"keyword": "australia partner visa processing time", "country": "Australia", "source": "seed", "priority": 2},
    {"keyword": "australia student visa requirements 2026", "country": "Australia", "source": "seed", "priority": 2},
    {"keyword": "australia points test calculator guide", "country": "Australia", "source": "seed", "priority": 2},
    {"keyword": "australia 482 tss visa employer sponsorship", "country": "Australia", "source": "seed", "priority": 2},
    {"keyword": "australia citizenship requirements 2026", "country": "Australia", "source": "seed", "priority": 2},

    # UK
    {"keyword": "uk skilled worker visa requirements 2026", "country": "UK", "source": "seed", "priority": 1},
    {"keyword": "uk spouse visa requirements 2026", "country": "UK", "source": "seed", "priority": 1},
    {"keyword": "uk student visa application guide", "country": "UK", "source": "seed", "priority": 1},
    {"keyword": "uk indefinite leave to remain guide", "country": "UK", "source": "seed", "priority": 2},
    {"keyword": "uk global talent visa requirements", "country": "UK", "source": "seed", "priority": 2},
    {"keyword": "uk naturalisation citizenship requirements", "country": "UK", "source": "seed", "priority": 2},

    # Germany
    {"keyword": "germany job seeker visa requirements 2026", "country": "Germany", "source": "seed", "priority": 1},
    {"keyword": "germany eu blue card requirements", "country": "Germany", "source": "seed", "priority": 1},
    {"keyword": "germany work visa application process", "country": "Germany", "source": "seed", "priority": 1},
    {"keyword": "germany permanent residence requirements", "country": "Germany", "source": "seed", "priority": 2},
    {"keyword": "germany family reunification visa guide", "country": "Germany", "source": "seed", "priority": 2},

    # Portugal
    {"keyword": "portugal d7 visa requirements 2026", "country": "Portugal", "source": "seed", "priority": 1},
    {"keyword": "portugal golden visa alternatives 2026", "country": "Portugal", "source": "seed", "priority": 1},
    {"keyword": "portugal digital nomad visa guide", "country": "Portugal", "source": "seed", "priority": 1},
    {"keyword": "portugal nhr tax regime guide", "country": "Portugal", "source": "seed", "priority": 2},
    {"keyword": "portugal residency by investment 2026", "country": "Portugal", "source": "seed", "priority": 2},

    # UAE
    {"keyword": "dubai work visa requirements 2026", "country": "UAE", "source": "seed", "priority": 1},
    {"keyword": "uae golden visa eligibility 2026", "country": "UAE", "source": "seed", "priority": 1},
    {"keyword": "dubai freelance visa requirements", "country": "UAE", "source": "seed", "priority": 2},
    {"keyword": "uae retirement visa requirements", "country": "UAE", "source": "seed", "priority": 2},

    # USA (long-tail only — avoid head terms)
    {"keyword": "h1b visa transfer process on opt 2026", "country": "USA", "source": "seed", "priority": 2},
    {"keyword": "eb2 niw self petition guide 2026", "country": "USA", "source": "seed", "priority": 2},
    {"keyword": "us green card through marriage process", "country": "USA", "source": "seed", "priority": 2},
    {"keyword": "o1 visa requirements extraordinary ability", "country": "USA", "source": "seed", "priority": 2},
    {"keyword": "us citizenship naturalization requirements 2026", "country": "USA", "source": "seed", "priority": 3},
]

# ── Reddit Subreddits ────────────────────────────────────────────────────────
SUBREDDITS = [
    ("r/ImmigrationCanada", "Canada"),
    ("r/immigration", "USA"),
    ("r/AusVisa", "Australia"),
    ("r/ukvisa", "UK"),
    ("r/germany", "Germany"),
    ("r/expats", "Global"),
    ("r/digitalnomad", "Portugal"),
]


def fetch_reddit_keywords(limit_per_sub: int = 10) -> list[dict]:
    """
    Scrape top posts from immigration subreddits via Reddit's public JSON API.
    No authentication required.
    """
    keywords = []
    headers = {"User-Agent": "immigration-seo-research/1.0"}

    for subreddit, country in SUBREDDITS:
        sub_name = subreddit.lstrip("r/")
        url = f"https://www.reddit.com/r/{sub_name}/hot.json?limit={limit_per_sub}"
        try:
            resp = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
            if resp.status_code != 200:
                continue
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                title = post["data"].get("title", "").strip()
                if len(title) < 15 or len(title) > 120:
                    continue
                # Convert post title to a keyword-style phrase
                kw = _title_to_keyword(title)
                if kw:
                    keywords.append({
                        "keyword": kw,
                        "country": country,
                        "source": f"reddit/{sub_name}",
                        "priority": 3,
                    })
        except Exception as e:
            print(f"[keyword_finder] Reddit fetch error ({subreddit}): {e}")

    print(f"[keyword_finder] Reddit: found {len(keywords)} keyword candidates")
    return keywords


def fetch_google_trends_keywords() -> list[dict]:
    """
    Fetch trending immigration searches from Google Trends RSS feeds.
    Uses daily trending searches RSS — free, no API key.
    """
    keywords = []
    country_codes = [("CA", "Canada"), ("AU", "Australia"), ("GB", "UK"), ("DE", "Germany")]
    immigration_terms = {"visa", "immigration", "permit", "pr ", "residency", "citizenship",
                         "work permit", "study permit", "refugee", "asylum", "green card"}

    for geo, country in country_codes:
        url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}"
        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            soup = BeautifulSoup(resp.text, "xml")
            items = soup.find_all("item")
            for item in items[:20]:
                title_tag = item.find("title")
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True).lower()
                if any(term in title for term in immigration_terms):
                    keywords.append({
                        "keyword": title + f" {country.lower()} 2026",
                        "country": country,
                        "source": "google_trends",
                        "priority": 2,
                    })
        except Exception as e:
            print(f"[keyword_finder] Google Trends error ({geo}): {e}")

    print(f"[keyword_finder] Google Trends: found {len(keywords)} immigration keywords")
    return keywords


def _title_to_keyword(title: str) -> str | None:
    """Convert a Reddit post title into a searchable keyword phrase."""
    # Remove common Reddit noise
    noise = ["[question]", "[help]", "[update]", "rant:", "psa:", "eli5:", "?", "!"]
    kw = title.lower()
    for n in noise:
        kw = kw.replace(n, "")
    kw = re.sub(r"\s+", " ", kw).strip()
    # Skip if too short or looks like a rant
    if len(kw) < 15:
        return None
    # Truncate to reasonable keyword length
    words = kw.split()[:10]
    return " ".join(words)


def discover_keywords(include_reddit: bool = True, include_trends: bool = True) -> list[dict]:
    """
    Combine all keyword sources and return deduplicated list.
    Seeds always included. Reddit and Trends are optional (may be slow).
    """
    all_keywords = list(SEED_KEYWORDS)

    if include_reddit:
        all_keywords.extend(fetch_reddit_keywords())

    if include_trends:
        all_keywords.extend(fetch_google_trends_keywords())

    # Deduplicate by (keyword, country)
    seen = set()
    unique = []
    for kw in all_keywords:
        key = (kw["keyword"].lower().strip(), kw["country"])
        if key not in seen:
            seen.add(key)
            unique.append(kw)

    print(f"[keyword_finder] Total unique keywords: {len(unique)}")
    return unique

"""
WordPress REST API publisher.

Setup:
1. In your WordPress admin: Users → Profile → Application Passwords
2. Create a new app password and copy it
3. Set WP_URL, WP_USERNAME, WP_APP_PASSWORD in your .env

The publisher creates/updates posts as drafts by default.
Pass publish=True to publish immediately.
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WP_URL", "").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")


def _headers() -> dict:
    import base64
    credentials = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
    token = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _get_or_create_tag(name: str) -> int | None:
    """Get tag ID by name, creating it if it doesn't exist."""
    try:
        # Search for existing tag
        resp = httpx.get(
            f"{WP_URL}/wp-json/wp/v2/tags",
            params={"search": name},
            headers=_headers(),
            timeout=10,
        )
        tags = resp.json()
        if tags and isinstance(tags, list):
            return tags[0]["id"]

        # Create new tag
        resp = httpx.post(
            f"{WP_URL}/wp-json/wp/v2/tags",
            json={"name": name},
            headers=_headers(),
            timeout=10,
        )
        return resp.json().get("id")
    except Exception:
        return None


def _get_or_create_category(name: str) -> int | None:
    """Get category ID by name, creating it if it doesn't exist."""
    try:
        resp = httpx.get(
            f"{WP_URL}/wp-json/wp/v2/categories",
            params={"search": name},
            headers=_headers(),
            timeout=10,
        )
        cats = resp.json()
        if cats and isinstance(cats, list):
            return cats[0]["id"]

        resp = httpx.post(
            f"{WP_URL}/wp-json/wp/v2/categories",
            json={"name": name},
            headers=_headers(),
            timeout=10,
        )
        return resp.json().get("id")
    except Exception:
        return None


def publish_article(article: dict, publish: bool = False) -> dict:
    """
    Publish an article to WordPress.

    Args:
        article: dict from article_writer.write_article()
        publish: True to publish immediately, False for draft

    Returns:
        {"post_id": int, "url": str, "status": str}
    """
    if not WP_URL or not WP_USERNAME or not WP_APP_PASSWORD:
        print("[wp_publisher] WordPress credentials not configured — skipping publish")
        return {"post_id": None, "url": None, "status": "skipped"}

    status = "publish" if publish else "draft"

    # Resolve tag IDs
    tag_ids = []
    for tag_name in article.get("tags", []):
        tid = _get_or_create_tag(tag_name)
        if tid:
            tag_ids.append(tid)

    # Resolve category (country name)
    category_id = _get_or_create_category(article["country"])

    payload = {
        "title": article["title"],
        "content": article["html"],
        "slug": article["slug"],
        "status": status,
        "tags": tag_ids,
        "categories": [category_id] if category_id else [],
        "excerpt": article.get("meta_description", ""),
        # Yoast SEO fields (if Yoast REST API plugin is active)
        "meta": {
            "_yoast_wpseo_title": article["title"],
            "_yoast_wpseo_metadesc": article.get("meta_description", ""),
            "_yoast_wpseo_focuskw": article["keyword"],
        },
    }

    try:
        resp = httpx.post(
            f"{WP_URL}/wp-json/wp/v2/posts",
            json=payload,
            headers=_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        post_id = data.get("id")
        url = data.get("link", "")
        print(f"[wp_publisher] Published post #{post_id}: {url}")
        return {"post_id": post_id, "url": url, "status": status}
    except httpx.HTTPStatusError as e:
        print(f"[wp_publisher] HTTP error: {e.response.status_code} — {e.response.text[:300]}")
        return {"post_id": None, "url": None, "status": "error"}
    except Exception as e:
        print(f"[wp_publisher] Error: {e}")
        return {"post_id": None, "url": None, "status": "error"}

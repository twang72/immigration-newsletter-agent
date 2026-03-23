"""
Publishes the newsletter issue to Beehiiv via their API.
Docs: https://developers.beehiiv.com/docs/v2
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

BEEHIIV_API_BASE = "https://api.beehiiv.com/v2"


def publish_to_beehiiv(subject: str, body: str, send_now: bool = False) -> dict:
    api_key = os.environ["BEEHIIV_API_KEY"]
    publication_id = os.environ["BEEHIIV_PUBLICATION_ID"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Create the post (draft)
    payload = {
        "subject": subject,
        "content": {
            "type": "html",
            "value": body,
        },
        "status": "draft",
        "audience": "free",
    }

    url = f"{BEEHIIV_API_BASE}/publications/{publication_id}/posts"
    print(f"[publisher] Creating post in Beehiiv: \"{subject}\"")

    resp = httpx.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    post = resp.json().get("data", {})
    post_id = post.get("id")
    print(f"[publisher] Draft created: post_id={post_id}")

    if send_now and post_id:
        send_url = f"{BEEHIIV_API_BASE}/publications/{publication_id}/posts/{post_id}/send"
        send_resp = httpx.post(send_url, headers=headers, timeout=30)
        send_resp.raise_for_status()
        print(f"[publisher] Newsletter sent to subscribers.")

    return post

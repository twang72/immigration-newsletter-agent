"""
Main orchestrator for the newsletter agent.
Run this file to execute one full newsletter cycle:
  1. Monitor: gather stories from IRCC, USCIS, Reddit
  2. Write: Claude generates the newsletter
  3. Publish: post to Beehiiv as a draft (or send immediately)

Usage:
  python -m newsletter.agent              # creates a draft in Beehiiv
  python -m newsletter.agent --send       # sends immediately to subscribers
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from newsletter.monitor import gather_stories
from newsletter.writer import write_newsletter
from newsletter.publisher import publish_to_beehiiv


def run(send_now: bool = False):
    print("=" * 50)
    print("Newsletter Agent Starting")
    print("=" * 50)

    # Step 1: Monitor
    stories = gather_stories()
    if not stories:
        print("[agent] No stories found. Aborting.")
        return

    # Step 2: Write
    newsletter = write_newsletter(stories)

    # Step 3: Publish
    result = publish_to_beehiiv(
        subject=newsletter["subject"],
        body=newsletter["body"],
        send_now=send_now,
    )

    print("=" * 50)
    status = "Sent" if send_now else "Draft saved"
    print(f"[agent] Done. {status}: \"{newsletter['subject']}\"")
    print(f"[agent] Beehiiv post ID: {result.get('id', 'unknown')}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Send immediately instead of saving as draft")
    args = parser.parse_args()
    run(send_now=args.send)

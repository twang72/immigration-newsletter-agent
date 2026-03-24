"""
Main orchestrator for the newsletter agent.
Run this file to execute one full newsletter cycle:
  1. Scrape: collect latest EE draw data into SQLite
  2. Analyze: generate proprietary data insights
  3. Monitor: gather news stories from IRCC, USCIS, Reddit
  4. Write: Claude generates the full newsletter
  5. Publish: post to Beehiiv as a draft (or send immediately)

Usage:
  python -m newsletter.agent              # creates a draft in Beehiiv
  python -m newsletter.agent --send       # sends immediately to subscribers
  python -m newsletter.agent --scrape-only  # only update the database, don't publish
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ee_scraper import run_scraper
from data.analyzer import generate_insights
from newsletter.monitor import gather_stories
from newsletter.writer import write_newsletter
from newsletter.publisher import publish_to_beehiiv


def run(send_now: bool = False, scrape_only: bool = False):
    print("=" * 50)
    print("Newsletter Agent Starting")
    print("=" * 50)

    # Step 1: Scrape latest EE draws into database
    print("\n[agent] Step 1/5: Updating Express Entry draw database...")
    draw_count = run_scraper()
    print(f"[agent] {draw_count} draws in database.")

    if scrape_only:
        print("[agent] --scrape-only flag set. Done.")
        return

    # Step 2: Analyze draw data for proprietary insights
    print("\n[agent] Step 2/5: Generating data insights...")
    insights = generate_insights()
    if insights.get("error"):
        print(f"[agent] Insights unavailable: {insights['error']}")
        insights = None

    # Step 3: Gather news stories
    print("\n[agent] Step 3/5: Monitoring news sources...")
    stories = gather_stories()
    if not stories:
        print("[agent] No stories found from IRCC — continuing with data insights only.")
        stories = []

    # Step 4: Write newsletter (news + data insights combined)
    print("\n[agent] Step 4/5: Writing newsletter...")
    newsletter = write_newsletter(stories, insights=insights)

    # Step 5: Publish to Beehiiv
    print("\n[agent] Step 5/5: Publishing to Beehiiv...")
    result = publish_to_beehiiv(
        subject=newsletter["subject"],
        body=newsletter["body"],
        send_now=send_now,
    )

    print("\n" + "=" * 50)
    status = "Sent to subscribers" if send_now else "Draft saved in Beehiiv"
    print(f"[agent] Done. {status}")
    print(f"[agent] Subject: \"{newsletter['subject']}\"")
    print(f"[agent] Beehiiv post ID: {result.get('id', 'unknown')}")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Send immediately instead of saving as draft")
    parser.add_argument("--scrape-only", action="store_true", help="Only update the database, skip publishing")
    args = parser.parse_args()
    run(send_now=args.send, scrape_only=args.scrape_only)

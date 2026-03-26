"""
SEO Farm Agent — main orchestrator.

Pipeline:
  1. Discover: find keyword opportunities from Reddit, Google Trends, seeds
  2. Queue: load new keywords into SQLite tracker
  3. Write: generate SEO articles via Claude for top N keywords
  4. Publish: push to WordPress as draft (or live with --publish)

Usage:
  python -m seo_farm.agent                        # discover + write 3 articles (drafts)
  python -m seo_farm.agent --publish              # publish immediately
  python -m seo_farm.agent --articles 10         # write 10 articles
  python -m seo_farm.agent --discover-only       # only refresh keyword queue
  python -m seo_farm.agent --country Canada      # filter to one country
  python -m seo_farm.agent --no-reddit           # skip Reddit (faster)
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo_farm.tracker import init_db, add_keywords, get_next_keywords, mark_keyword_used, record_article, get_published_count
from seo_farm.keyword_finder import discover_keywords
from seo_farm.article_writer import write_article
from seo_farm.wp_publisher import publish_article


def run(
    articles: int = 3,
    publish: bool = False,
    discover_only: bool = False,
    country_filter: str | None = None,
    include_reddit: bool = True,
    include_trends: bool = True,
):
    print("=" * 55)
    print("SEO Farm Agent Starting")
    print("=" * 55)

    # Step 1: Init database
    init_db()
    print(f"\n[agent] Articles published so far: {get_published_count()}")

    # Step 2: Discover and queue new keywords
    print("\n[agent] Step 1/3: Discovering keyword opportunities...")
    keywords = discover_keywords(include_reddit=include_reddit, include_trends=include_trends)

    if country_filter:
        keywords = [k for k in keywords if k["country"].lower() == country_filter.lower()]
        print(f"[agent] Filtered to {country_filter}: {len(keywords)} keywords")

    add_keywords(keywords)
    print(f"[agent] Keyword queue updated with {len(keywords)} candidates")

    if discover_only:
        print("[agent] --discover-only flag set. Done.")
        return

    # Step 3: Pick top unwritten keywords
    print(f"\n[agent] Step 2/3: Selecting top {articles} unwritten keywords...")
    queue = get_next_keywords(limit=articles)
    if not queue:
        print("[agent] No new keywords to write. Queue exhausted or all already published.")
        return

    # Step 4: Write and publish articles
    print(f"\n[agent] Step 3/3: Writing {len(queue)} articles...")
    results = []

    for i, kw in enumerate(queue, 1):
        keyword = kw["keyword"]
        country = kw["country"]
        print(f"\n[agent] Article {i}/{len(queue)}: '{keyword}' ({country})")

        try:
            article = write_article(keyword, country)
            wp_result = publish_article(article, publish=publish)

            record_article(
                keyword=keyword,
                country=country,
                slug=article["slug"],
                title=article["title"],
                wp_post_id=wp_result.get("post_id"),
                wp_url=wp_result.get("url"),
                status=wp_result.get("status", "draft"),
            )
            mark_keyword_used(keyword, country)

            results.append({
                "title": article["title"],
                "url": wp_result.get("url"),
                "status": wp_result.get("status"),
            })

        except Exception as e:
            print(f"[agent] Error processing '{keyword}': {e}")
            continue

    # Summary
    print("\n" + "=" * 55)
    print(f"[agent] Done. {len(results)} articles processed.")
    for r in results:
        status_label = "LIVE" if r["status"] == "publish" else "DRAFT"
        url_display = r["url"] or "(WordPress not configured)"
        print(f"  [{status_label}] {r['title']}")
        print(f"          {url_display}")
    print(f"\n[agent] Total published: {get_published_count()}")
    print("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Immigration SEO Farm Agent")
    parser.add_argument("--publish", action="store_true", help="Publish immediately (default: draft)")
    parser.add_argument("--articles", type=int, default=3, help="Number of articles to write (default: 3)")
    parser.add_argument("--discover-only", action="store_true", help="Only refresh keyword queue, skip writing")
    parser.add_argument("--country", type=str, default=None, help="Filter to one country (e.g. Canada)")
    parser.add_argument("--no-reddit", action="store_true", help="Skip Reddit keyword discovery")
    parser.add_argument("--no-trends", action="store_true", help="Skip Google Trends discovery")
    args = parser.parse_args()

    run(
        articles=args.articles,
        publish=args.publish,
        discover_only=args.discover_only,
        country_filter=args.country,
        include_reddit=not args.no_reddit,
        include_trends=not args.no_trends,
    )

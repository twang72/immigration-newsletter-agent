"""
Analyzes Express Entry draw data using Claude to produce proprietary insights.

Uses both draw history AND score band distributions (dd1-dd18) to answer
questions like:
- How many people are ahead of you in the pool?
- Is the pool growing or shrinking?
- Which score band is most at-risk of waiting too long?
- Which categories are overdue?
"""

import json
import statistics
from datetime import datetime
from data.db import (
    get_recent_ee_draws, get_ee_draws_by_type, get_all_draw_types,
    get_score_band_distribution, get_pool_size_trend
)
from shared.claude_client import generate

ANALYST_SYSTEM = """You are a senior immigration data analyst specializing in Canada's
Express Entry system. You have access to proprietary historical draw data AND candidate
pool distribution data that most people cannot easily find or interpret.

Your job is to produce sharp, data-driven insights — not generic summaries. Every claim
must be backed by the numbers provided. Be specific: use actual scores, dates, counts, and
percentages.

Your audience is serious Canadian immigration applicants who want an edge. Give them one.
Never mention the US immigration system."""


def compute_basic_stats(draws: list[dict]) -> dict:
    if not draws:
        return {}

    scores = [d["cutoff_score"] for d in draws if d["cutoff_score"] > 0]
    invites = [d["invitations"] for d in draws if d["invitations"] > 0]

    recent_5 = scores[:5] if len(scores) >= 5 else scores
    prev_5 = scores[5:10] if len(scores) >= 10 else []
    score_trend = None
    if recent_5 and prev_5:
        score_trend = round(statistics.mean(recent_5) - statistics.mean(prev_5), 1)

    dates = []
    for d in draws:
        for fmt in ("%Y-%m-%d", "%B %d, %Y", "%B %d, %Y"):
            try:
                dates.append(datetime.strptime(d["draw_date"], fmt))
                break
            except Exception:
                continue

    avg_days_between = None
    days_since_last = None
    if len(dates) >= 2:
        gaps = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
        avg_days_between = round(statistics.mean(gaps), 1)
    if dates:
        days_since_last = (datetime.now() - dates[0]).days

    return {
        "total_draws_analyzed": len(draws),
        "latest_cutoff": scores[0] if scores else None,
        "avg_cutoff_last_10": round(statistics.mean(scores[:10]), 1) if len(scores) >= 10 else None,
        "min_cutoff_ever": min(scores) if scores else None,
        "max_cutoff_ever": max(scores) if scores else None,
        "score_trend_vs_prev_5": score_trend,
        "avg_invitations_last_10": round(statistics.mean(invites[:10]), 0) if len(invites) >= 10 else None,
        "avg_days_between_draws": avg_days_between,
        "days_since_last_draw": days_since_last,
    }


def compute_category_stats(draw_types: list[str]) -> dict:
    category_stats = {}
    for dt in draw_types:
        draws = get_ee_draws_by_type(dt, limit=10)
        if not draws:
            continue

        dates = []
        for d in draws:
            for fmt in ("%Y-%m-%d", "%B %d, %Y"):
                try:
                    dates.append(datetime.strptime(d["draw_date"], fmt))
                    break
                except Exception:
                    continue

        days_since = (datetime.now() - dates[0]).days if dates else None
        avg_gap = None
        if len(dates) >= 2:
            gaps = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
            avg_gap = round(sum(gaps) / len(gaps), 1)

        scores = [d["cutoff_score"] for d in draws if d["cutoff_score"] > 0]
        invites = [d["invitations"] for d in draws if d["invitations"] > 0]

        category_stats[dt] = {
            "days_since_last_draw": days_since,
            "avg_days_between_draws": avg_gap,
            "overdue": days_since > avg_gap * 1.5 if (days_since and avg_gap) else False,
            "latest_cutoff": scores[0] if scores else None,
            "avg_cutoff": round(sum(scores) / len(scores), 1) if scores else None,
            "avg_invitations": round(sum(invites) / len(invites), 0) if invites else None,
            "total_draws_tracked": len(draws),
        }
    return category_stats


def compute_pool_insights(draws: list[dict]) -> dict:
    """
    Analyzes the candidate pool using score band distributions.
    Tells applicants how many people are ahead of them and whether
    the pool is growing or shrinking.
    """
    if not draws:
        return {}

    latest_draw = draws[0]
    latest_dist = get_score_band_distribution(latest_draw["draw_number"])
    pool_trend = get_pool_size_trend(limit=8)

    # Calculate cumulative pool above each band
    # (how many people have a HIGHER score than you)
    cumulative = {}
    running_total = 0
    for band, count in sorted(latest_dist.items(), reverse=True):
        cumulative[band] = running_total
        running_total += count

    total_pool = sum(latest_dist.values())

    # Pool size trend
    pool_sizes = [r["total_pool"] for r in pool_trend if r["total_pool"]]
    pool_growing = None
    if len(pool_sizes) >= 3:
        recent_avg = statistics.mean(pool_sizes[:3])
        older_avg = statistics.mean(pool_sizes[3:6]) if len(pool_sizes) >= 6 else None
        if older_avg:
            pool_growing = recent_avg > older_avg

    return {
        "latest_draw_number": latest_draw["draw_number"],
        "total_pool_size": total_pool,
        "score_band_distribution": latest_dist,
        "candidates_above_each_band": cumulative,
        "pool_trend": pool_trend,
        "pool_growing": pool_growing,
    }


def generate_insights() -> dict:
    print("[analyzer] Computing Express Entry insights...")

    draws = get_recent_ee_draws(limit=50)
    if not draws:
        return {"error": "No draw data available yet. Run the scraper first."}

    stats = compute_basic_stats(draws)
    draw_types = get_all_draw_types()
    category_stats = compute_category_stats(draw_types)
    pool_insights = compute_pool_insights(draws)

    data_summary = {
        "overall_stats": stats,
        "recent_draws": draws[:15],
        "category_analysis": category_stats,
        "pool_analysis": pool_insights,
    }

    user_prompt = f"""Here is our proprietary Express Entry database analysis for this week's newsletter:

{json.dumps(data_summary, indent=2)}

Please produce a newsletter section called "📊 Draw Intelligence Report" with these sub-sections:

1. **CRS Score Trend** — Is the cutoff rising, falling, or volatile? By how much across the last 5 draws? What does this mean for applicants in the 450-500 range specifically?

2. **Who's In The Pool Right Now** — Use the score band distribution data to tell applicants how many people are competing in different score ranges. Is the pool growing or shrinking? Which bands are most congested?

3. **Category Draw Watch** — Which categories are overdue based on historical frequency? Which have the lowest cutoff scores (best chance)?

4. **The Insight Most People Miss** — One sharp, specific observation from the data that the average applicant wouldn't notice on their own. Make it genuinely useful.

5. **Your Number This Week** — One specific CRS score threshold applicants should watch, with data-backed reasoning why.

HTML formatting rules:
- Use inline CSS only
- All tables must have style="width:100%; border-collapse:collapse; font-family:sans-serif;"
- Table header cells: style="background:#1a6bb5; color:white; padding:8px 12px; text-align:left;"
- Table data cells: style="padding:8px 12px; border-bottom:1px solid #eee;"
- Section headings: style="color:#1a6bb5; font-size:16px; margin:24px 0 8px 0;"
- Do NOT include <html>, <head>, <body> tags — start directly with content
- Focus entirely on Canada immigration — no US content

This section is what makes our newsletter worth subscribing to."""

    analysis = generate(system=ANALYST_SYSTEM, user=user_prompt, max_tokens=8192)

    # Strip any accidental markdown fences
    import re
    analysis = re.sub(r"^```[a-z]*\n?", "", analysis.strip())
    analysis = re.sub(r"\n?```$", "", analysis.strip())

    return {
        "stats": stats,
        "category_stats": category_stats,
        "pool_insights": pool_insights,
        "html_section": analysis,
    }

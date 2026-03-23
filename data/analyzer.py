"""
Analyzes Express Entry draw data using Claude to produce proprietary insights
that go far beyond what canada.ca publishes.

Generates:
- CRS score trend (rising/falling/volatile)
- Category draw frequency and which categories are overdue
- Score band wait-time estimates
- Draw cadence analysis
- Plain-English prediction commentary
"""

import json
import statistics
from datetime import datetime, timedelta
from data.db import get_recent_ee_draws, get_ee_draws_by_type, get_all_draw_types
from shared.claude_client import generate

ANALYST_SYSTEM = """You are a senior immigration data analyst specializing in Canada's
Express Entry system. You have access to historical draw data that most people cannot easily
find or interpret.

Your job is to produce sharp, data-driven insights — not generic summaries. Every claim
must be backed by the numbers provided. Be specific: use actual scores, dates, counts, and
percentages. Avoid vague language like "scores may rise" — say "scores have risen 12 points
over the last 6 draws" if that's what the data shows.

Your audience is serious immigration applicants who want an edge. Give them one."""


def compute_basic_stats(draws: list[dict]) -> dict:
    """Compute raw statistics from draw records."""
    if not draws:
        return {}

    scores = [d["cutoff_score"] for d in draws if d["cutoff_score"] > 0]
    invites = [d["invitations"] for d in draws if d["invitations"] > 0]

    # Score trend: compare last 5 vs previous 5
    recent_5 = scores[:5] if len(scores) >= 5 else scores
    prev_5 = scores[5:10] if len(scores) >= 10 else []

    score_trend = None
    if recent_5 and prev_5:
        delta = statistics.mean(recent_5) - statistics.mean(prev_5)
        score_trend = round(delta, 1)

    # Draw cadence: average days between draws
    dates = []
    for d in draws:
        try:
            dates.append(datetime.strptime(d["draw_date"], "%B %d, %Y"))
        except Exception:
            try:
                dates.append(datetime.strptime(d["draw_date"], "%Y-%m-%d"))
            except Exception:
                pass

    avg_days_between = None
    if len(dates) >= 2:
        gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
        avg_days_between = round(statistics.mean(gaps), 1)

    # Days since last draw
    days_since_last = None
    if dates:
        days_since_last = (datetime.now() - dates[0]).days

    return {
        "total_draws_analyzed": len(draws),
        "latest_cutoff": scores[0] if scores else None,
        "avg_cutoff_last_10": round(statistics.mean(scores[:10]), 1) if len(scores) >= 10 else None,
        "min_cutoff": min(scores) if scores else None,
        "max_cutoff": max(scores) if scores else None,
        "score_trend_vs_prev_5_draws": score_trend,
        "avg_invitations": round(statistics.mean(invites), 0) if invites else None,
        "avg_days_between_draws": avg_days_between,
        "days_since_last_draw": days_since_last,
    }


def compute_category_stats(draw_types: list[str]) -> dict:
    """For each category, compute how long since last draw and frequency."""
    category_stats = {}
    for dt in draw_types:
        draws = get_ee_draws_by_type(dt, limit=10)
        if not draws:
            continue

        dates = []
        for d in draws:
            try:
                dates.append(datetime.strptime(d["draw_date"], "%B %d, %Y"))
            except Exception:
                try:
                    dates.append(datetime.strptime(d["draw_date"], "%Y-%m-%d"))
                except Exception:
                    pass

        days_since = (datetime.now() - dates[0]).days if dates else None

        avg_gap = None
        if len(dates) >= 2:
            gaps = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
            avg_gap = round(sum(gaps) / len(gaps), 1)

        scores = [d["cutoff_score"] for d in draws if d["cutoff_score"] > 0]
        category_stats[dt] = {
            "days_since_last_draw": days_since,
            "avg_days_between_draws": avg_gap,
            "overdue": days_since > avg_gap * 1.5 if (days_since and avg_gap) else False,
            "latest_cutoff": scores[0] if scores else None,
            "avg_cutoff": round(sum(scores) / len(scores), 1) if scores else None,
            "total_draws_tracked": len(draws),
        }

    return category_stats


def generate_insights() -> dict:
    """Main entry point — returns a dict with stats + Claude's analysis."""
    print("[analyzer] Computing Express Entry insights...")

    draws = get_recent_ee_draws(limit=50)
    if not draws:
        return {"error": "No draw data available yet. Run the scraper first."}

    stats = compute_basic_stats(draws)
    draw_types = get_all_draw_types()
    category_stats = compute_category_stats(draw_types)

    # Build the data payload for Claude
    data_summary = {
        "overall_stats": stats,
        "recent_draws": draws[:15],  # last 15 draws in detail
        "category_analysis": category_stats,
    }

    user_prompt = f"""Here is our proprietary Express Entry draw database analysis:

{json.dumps(data_summary, indent=2)}

Please produce a newsletter section called "📊 Draw Intelligence Report" with:

1. **CRS Score Trend** — Is the cutoff rising, falling, or volatile? By how much? What does this mean for applicants in the 450-500 range?

2. **Category Draw Watch** — Which category draws are overdue based on historical frequency? Which categories have been most active lately?

3. **Invitation Volume Analysis** — Is IRCC issuing more or fewer invitations than usual? What does the volume signal?

4. **The Insight Most People Miss** — One sharp observation from the data that the average applicant wouldn't notice on their own.

5. **What To Watch Next Week** — A specific, data-backed prediction or thing to monitor.

Format as clean HTML for a newsletter. Be specific with numbers. This section is the reason people subscribe — make it worth reading."""

    analysis = generate(system=ANALYST_SYSTEM, user=user_prompt)

    return {
        "stats": stats,
        "category_stats": category_stats,
        "html_section": analysis,
    }

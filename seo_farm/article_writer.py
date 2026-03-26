"""
Generates long-form, SEO-optimized immigration articles using Claude.
Output is HTML ready for WordPress, plus meta fields for Yoast SEO.
"""

import re
from datetime import date
from shared.claude_client import generate

SYSTEM_PROMPT = """You are a senior immigration content strategist and journalist.
You write authoritative, SEO-optimized guides for people navigating immigration worldwide.

Your writing style:
- Clear, practical, and reassuring — like a knowledgeable friend who happens to be a licensed immigration consultant
- Always accurate about processes, timelines, and requirements
- Never gives specific legal advice — always recommend consulting a licensed immigration professional
- Uses current year references for freshness signals

SEO rules you always follow:
- Use the exact target keyword in the H1, first 100 words, and naturally throughout
- Write at least 1800 words
- Include H2 and H3 subheadings with related keywords
- Add a FAQ section with 5–7 questions (schema-friendly format)
- End with a clear call to action
"""


def _build_prompt(keyword: str, country: str) -> str:
    year = date.today().year
    return f"""Write a comprehensive, SEO-optimized immigration guide for this target keyword:

**Target keyword:** {keyword}
**Target country:** {country}
**Current year:** {year}

Return ONLY valid HTML starting with <article> — no markdown, no code fences, no explanations.

Use this exact structure:

<article>
  <h1>[SEO title containing the exact keyword]</h1>

  <p>[Hook intro: 2–3 sentences. What the reader will learn. Use the keyword in first 100 words.]</p>

  <h2>What Is [topic]?</h2>
  <p>[Clear definition and context. 150–200 words.]</p>

  <h2>Who Is Eligible?</h2>
  <p>[Eligibility criteria in plain language. Use a <ul> list for requirements.]</p>

  <h2>Step-by-Step Application Process</h2>
  <p>[Numbered steps using <ol>. Be specific and actionable.]</p>

  <h2>Processing Times and Timeline</h2>
  <p>[Current processing times. What to expect at each stage.]</p>

  <h2>Fees and Costs</h2>
  <p>[Government fees + realistic total cost estimate including supporting documents.]</p>

  <h2>Common Mistakes to Avoid</h2>
  <ul>[5–6 common pitfalls with brief explanation of why they matter.]</ul>

  <h2>Frequently Asked Questions</h2>
  [5–7 Q&As using <details><summary> tags for each question]

  <h2>Final Thoughts</h2>
  <p>[2–3 sentence conclusion. Soft CTA: recommend consulting a licensed immigration professional for case-specific advice.]</p>
</article>
"""


def _extract_title(html: str) -> str:
    """Extract H1 text from generated HTML."""
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"<[^>]+>", "", match.group(1)).strip()
    return ""


def _build_meta_description(keyword: str, country: str) -> str:
    """Generate a 150-char meta description via Claude."""
    year = date.today().year
    prompt = f"""Write a compelling meta description (max 155 characters) for an immigration guide about:
Keyword: {keyword}
Country: {country}
Year: {year}

Return ONLY the meta description text. No quotes, no labels."""
    desc = generate(system=SYSTEM_PROMPT, user=prompt, max_tokens=80).strip().strip('"')
    return desc[:155]


def _keyword_to_slug(keyword: str) -> str:
    """Convert keyword to a URL-friendly slug."""
    slug = keyword.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]


def write_article(keyword: str, country: str) -> dict:
    """
    Generate a full SEO article for the given keyword and country.

    Returns:
        {
            "keyword": str,
            "country": str,
            "title": str,
            "slug": str,
            "meta_description": str,
            "html": str,       # full article HTML
            "tags": list[str],
        }
    """
    print(f"[article_writer] Writing article: '{keyword}' ({country})")

    prompt = _build_prompt(keyword, country)
    html = generate(system=SYSTEM_PROMPT, user=prompt, max_tokens=6000)

    # Strip accidental markdown fences
    html = re.sub(r"^```[a-z]*\n?", "", html.strip())
    html = re.sub(r"\n?```$", "", html.strip())

    title = _extract_title(html) or keyword.title()
    slug = _keyword_to_slug(keyword)
    meta_description = _build_meta_description(keyword, country)

    tags = [country, "immigration", "visa guide", str(date.today().year)]
    country_tags = {
        "Canada": ["express entry", "ircc", "canadian immigration"],
        "Australia": ["home affairs", "skilled migration"],
        "UK": ["ukvi", "home office"],
        "Germany": ["german immigration", "blue card"],
        "Portugal": ["portuguese visa", "residency portugal"],
        "UAE": ["dubai visa", "emirates"],
        "USA": ["uscis", "us immigration"],
    }
    tags.extend(country_tags.get(country, []))

    # Remove the H1 from content — WordPress renders the post title as H1 already
    html = re.sub(r"<h1[^>]*>.*?</h1>", "", html, count=1, flags=re.IGNORECASE | re.DOTALL).strip()

    print(f"[article_writer] Done: '{title}' ({len(html)} chars)")

    return {
        "keyword": keyword,
        "country": country,
        "title": title,
        "slug": slug,
        "meta_description": meta_description,
        "html": html,
        "tags": tags,
    }

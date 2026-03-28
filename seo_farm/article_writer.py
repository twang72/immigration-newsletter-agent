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


def _apply_inline_styles(html: str) -> str:
    """
    Apply inline styles directly to each HTML element.
    Bypasses WordPress stripping class attributes from post content.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("h2"):
        tag["style"] = "color:#1a4fa0;font-size:1.45em;margin:2em 0 0.6em;padding-bottom:0.3em;border-bottom:2px solid #e8f0fe;"

    for tag in soup.find_all("h3"):
        tag["style"] = "color:#2d6bc4;font-size:1.15em;margin:1.5em 0 0.4em;"

    for tag in soup.find_all("ul"):
        tag["style"] = "margin:0.5em 0 1.2em 1.5em;padding-left:1em;"

    for tag in soup.find_all("ol"):
        tag["style"] = "margin:0.5em 0 1.2em 1.5em;padding-left:1em;"

    for tag in soup.find_all("li"):
        tag["style"] = "margin-bottom:0.5em;"

    for tag in soup.find_all("table"):
        tag["style"] = "width:100%;border-collapse:collapse;margin:1.2em 0;font-size:0.95em;"

    for tag in soup.find_all("th"):
        tag["style"] = "background:#1a4fa0;color:#fff;padding:0.7em 1em;text-align:left;"

    for i, row in enumerate(soup.find_all("tr")):
        for td in row.find_all("td"):
            bg = "#f8faff" if i % 2 == 0 else "#fff"
            td["style"] = f"padding:0.65em 1em;border-bottom:1px solid #e2e8f0;background:{bg};"

    for tag in soup.find_all("details"):
        tag["style"] = "border:1px solid #e2e8f0;border-radius:8px;margin:0.6em 0;overflow:hidden;"

    for tag in soup.find_all("summary"):
        tag["style"] = "padding:0.9em 1.1em;cursor:pointer;font-weight:600;color:#1a4fa0;background:#f8faff;display:flex;justify-content:space-between;align-items:center;"

    for tag in soup.find_all("div", class_="callout"):
        tag["style"] = "background:#e8f0fe;border-left:4px solid #1a4fa0;border-radius:0 8px 8px 0;padding:1em 1.2em;margin:1.5em 0;"
        del tag["class"]

    for tag in soup.find_all("div", class_="warning"):
        tag["style"] = "background:#fff8e1;border-left:4px solid #f59e0b;border-radius:0 8px 8px 0;padding:1em 1.2em;margin:1.5em 0;"
        del tag["class"]

    for tag in soup.find_all("div", class_="cta-box"):
        tag["style"] = "background:linear-gradient(135deg,#1a4fa0 0%,#2d6bc4 100%);color:#fff;border-radius:10px;padding:1.5em 1.8em;margin:2em 0 1em;text-align:center;"
        del tag["class"]

    wrapper = f'<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;color:#1a1a2e;line-height:1.8;">{soup}</div>'
    return wrapper


def _wrap_article(html: str) -> str:
    return _apply_inline_styles(html)


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

    # Wrap with professional styling
    html = _wrap_article(html)

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

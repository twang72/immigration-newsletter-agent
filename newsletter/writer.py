"""
Takes raw stories from the monitor and uses Claude to write a professional
weekly immigration newsletter issue in HTML format ready for Beehiiv.
"""

import json
from datetime import date
from shared.claude_client import generate

SYSTEM_PROMPT = """You are the editor of "Canada Immigration Weekly", a trusted newsletter
for people navigating Canadian and US immigration. Your tone is clear, professional, and
helpful — like a knowledgeable friend who happens to be an immigration expert.

You write concise, scannable newsletters with:
- A warm subject line
- A brief intro (2-3 sentences)
- 3-5 story summaries with key takeaways
- A practical tip of the week
- A disclaimer footer

You always link back to official sources. You never give legal advice — only information.
Format your output as valid HTML suitable for an email newsletter.
"""

DISCLAIMER = """
<hr>
<p style="font-size:12px; color:#888;">
<strong>Disclaimer:</strong> This newsletter is for informational purposes only and does
not constitute legal or immigration advice. Always consult a licensed immigration
professional (RCIC or immigration lawyer) for advice specific to your situation.
<br><br>
© Canada Immigration Weekly. You are receiving this because you subscribed.
<a href="{{unsubscribe_url}}">Unsubscribe</a>
</p>
"""


def write_newsletter(stories: list[dict]) -> dict:
    today = date.today().strftime("%B %d, %Y")
    stories_json = json.dumps(stories, indent=2)

    user_prompt = f"""Today is {today}.

Here are this week's immigration stories gathered from IRCC, USCIS, and Reddit:

{stories_json}

Please write this week's newsletter issue. Include:
1. A compelling subject line (for the email)
2. The full newsletter body in HTML

Return your response as JSON with two keys:
- "subject": the email subject line
- "body": the full HTML body of the newsletter
"""

    print("[writer] Generating newsletter with Claude...")
    response = generate(system=SYSTEM_PROMPT, user=user_prompt)

    # Parse JSON from Claude's response
    try:
        # Strip markdown code fences if present
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean.strip())
    except Exception:
        # Fallback: treat entire response as body
        result = {
            "subject": f"Canada Immigration Weekly — {today}",
            "body": response,
        }

    # Append disclaimer
    result["body"] = result["body"] + DISCLAIMER
    print(f"[writer] Newsletter written: \"{result['subject']}\"")
    return result

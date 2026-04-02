"""
Takes raw stories from the monitor and uses Claude to write a professional
weekly immigration newsletter issue in HTML format ready for Beehiiv.
"""

import re
from datetime import date
from shared.claude_client import generate

SYSTEM_PROMPT = """You are the editor of "Canada Immigration Insider", a trusted weekly newsletter
for people navigating Canadian immigration — Express Entry, PNP, study permits, work permits, and PR.

Your tone is clear, professional, and helpful — like a knowledgeable friend who happens to be
a licensed Canadian immigration consultant (RCIC).

Rules:
- Focus exclusively on Canadian immigration. Never include US immigration content.
- Always link back to official IRCC sources where available.
- Never give legal advice — only factual information and analysis.
- Be specific and actionable. Applicants want to know what to DO, not just what happened.
"""

HEADER = """
<div style="font-family:sans-serif; max-width:680px; margin:0 auto; padding:16px 0 8px 0;">
  <h1 style="color:#1a6bb5; font-size:22px; margin:0 0 4px 0;">Canada Immigration Insider</h1>
  <p style="color:#888; font-size:13px; margin:0;">Your weekly briefing on Canadian immigration</p>
  <hr style="border:none; border-top:2px solid #1a6bb5; margin:12px 0 24px 0;">
</div>
"""

DISCLAIMER = """
<div style="font-family:sans-serif; max-width:680px; margin:0 auto;">
  <hr style="border:none; border-top:1px solid #ddd; margin:32px 0 16px 0;">
  <p style="font-size:12px; color:#888; line-height:1.6;">
    <strong>Disclaimer:</strong> This newsletter is for informational purposes only and does
    not constitute legal or immigration advice. Always consult a licensed immigration
    professional (RCIC or immigration lawyer) for advice specific to your situation.
    <br><br>
    © Canada Immigration Insider. You are receiving this because you subscribed.
  </p>
</div>
"""


def write_newsletter(stories: list[dict], insights: dict | None = None) -> dict:
    today = date.today().strftime("%B %d, %Y")

    stories_text = ""
    for s in stories:
        stories_text += f"- [{s['source']}] {s['title']} — {s.get('url', '')}\n"

    subject_prompt = f"""Today is {today}.

Based on these Canadian immigration stories, write ONE compelling email subject line (max 60 chars).
Return ONLY the subject line text, nothing else.

Stories:
{stories_text}"""

    body_prompt = f"""Today is {today}.

Write a complete HTML email newsletter for "Canada Immigration Insider" using these stories:

{stories_text}

Structure:
1. Brief intro paragraph (2-3 sentences)
2. News summaries — for each story: headline, 2-3 sentence summary, key takeaway, link
3. Practical tip of the week

Rules:
- Return ONLY valid HTML — no markdown, no JSON, no code fences
- Use inline CSS for styling (email clients strip external CSS)
- Keep it clean and readable
- Start directly with <div> or <table>, do NOT include <html>, <head>, or <body> tags
"""

    print("[writer] Generating subject line...")
    subject = generate(system=SYSTEM_PROMPT, user=subject_prompt, max_tokens=100).strip().strip('"')

    print("[writer] Generating newsletter body...")
    body = generate(system=SYSTEM_PROMPT, user=body_prompt, max_tokens=4096)

    # Strip any accidental markdown code fences
    body = re.sub(r"^```[a-z]*\n?", "", body.strip())
    body = re.sub(r"\n?```$", "", body.strip())

    # Directly inject insights HTML — never pass through Claude
    # Wrapped in a closed div to prevent disclaimer bleeding into tables
    if insights and insights.get("html_section"):
        print("[writer] Injecting data insights section...")
        insights_wrapped = (
            '<div style="font-family:sans-serif; max-width:680px; margin:24px auto 0 auto;">'
            + insights["html_section"]
            + "</div>"
        )
        body = body + "\n" + insights_wrapped

    # Safety-close any unclosed table elements before the disclaimer.
    # Orphaned closing tags are harmless if the table is already closed,
    # but prevent the disclaimer from being swallowed into the last <td>.
    table_closer = "\n</td></tr></tbody></table>\n"
    body = HEADER + body + table_closer + DISCLAIMER

    print(f"[writer] Newsletter written: \"{subject}\"")
    return {"subject": subject, "body": body}

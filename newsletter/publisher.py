"""
Sends the finished newsletter to your own email address as HTML.
You then copy/paste it into Beehiiv's editor and click send.

Uses Gmail SMTP — free, no extra API needed.
Setup: enable 2FA on Gmail, then create an App Password at
https://myaccount.google.com/apppasswords
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()


def publish_to_beehiiv(subject: str, body: str, send_now: bool = False) -> dict:
    """
    Sends the newsletter HTML to your email for manual Beehiiv paste.
    The send_now flag is ignored — email is always sent immediately.
    Returns a dict mimicking the Beehiiv post response for compatibility.
    """
    gmail_user = os.environ["GMAIL_USER"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ.get("NEWSLETTER_RECIPIENT_EMAIL", gmail_user)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Newsletter Ready] {subject}"
    msg["From"] = gmail_user
    msg["To"] = recipient

    # Plain text fallback
    plain = (
        f"Your newsletter is ready to paste into Beehiiv.\n\n"
        f"Subject: {subject}\n\n"
        f"Open the HTML version of this email to copy the content."
    )

    # Instructions header prepended to the HTML body
    instructions = f"""
<div style="background:#fffbea;border:1px solid #f0c040;padding:16px;margin-bottom:24px;font-family:sans-serif;">
  <strong>Action needed:</strong> Copy everything below this box and paste it into your
  <a href="https://app.beehiiv.com">Beehiiv</a> editor, then click Send.<br>
  <strong>Subject line:</strong> {subject}
</div>
"""
    full_html = instructions + body

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(full_html, "html"))

    print(f"[publisher] Sending newsletter to {recipient} via Gmail...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_app_password)
        smtp.sendmail(gmail_user, recipient, msg.as_string())

    print(f"[publisher] Email sent. Open your inbox and paste into Beehiiv.")
    return {"id": "email-delivery", "subject": subject}

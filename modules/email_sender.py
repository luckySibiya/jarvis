"""Send emails via Gmail SMTP.

Requires a Gmail App Password (not your regular password).
Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.command_router import register
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD
from utils.logger import get_logger

logger = get_logger(__name__)


@register("system", "send_email")
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail SMTP."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        return (
            "Email is not configured. Add GMAIL_ADDRESS and "
            "GMAIL_APP_PASSWORD to your .env file."
        )

    try:
        msg = MIMEMultipart()
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

        return f"Email sent to {to} with subject '{subject}'."
    except Exception as e:
        logger.error(f"Email error: {e}")
        return f"Failed to send email: {e}"

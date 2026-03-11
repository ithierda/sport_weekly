"""SMTP email sender."""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import Config

logger = logging.getLogger(__name__)
cfg = Config()


def send_mail(html_body: str, subject: str, recipients: list[str]):
    """Send HTML email via SMTP to a list of recipients."""
    if not cfg.MAIL_SMTP_HOST or not cfg.MAIL_SMTP_USER or not cfg.MAIL_SMTP_PASSWORD:
        raise ValueError("SMTP configuration incomplete (MAIL_SMTP_HOST/USER/PASSWORD)")

    if not recipients:
        raise ValueError("No recipients provided")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.MAIL_SMTP_USER
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html"))

    try:
        logger.info("Connecting to %s:%s", cfg.MAIL_SMTP_HOST, cfg.MAIL_SMTP_PORT)
        s = smtplib.SMTP(cfg.MAIL_SMTP_HOST, cfg.MAIL_SMTP_PORT)
        s.starttls()
        s.login(cfg.MAIL_SMTP_USER, cfg.MAIL_SMTP_PASSWORD)
        s.sendmail(cfg.MAIL_SMTP_USER, recipients, msg.as_string())
        s.quit()
        logger.info("Email sent to %s", ", ".join(recipients))
    except smtplib.SMTPAuthenticationError as e:
        logger.error("SMTP auth failed: %s", e)
        raise
    except Exception as e:
        logger.error("Email send failed: %s", e)
        raise

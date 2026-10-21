"""SMTP email abstraction. Never logs tokens or passwords."""
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via SMTP; return True if sent, False if skipped or failed.

    If SMTP_HOST is empty the email is skipped and only that fact is logged.
    The body is never logged because it may contain secrets.
    """
    if not settings.SMTP_HOST:
        logger.info("SMTP not configured; email skipped (subject=%s)", subject)
        return False
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError):
        logger.error("Failed to send email (subject=%s)", subject)
        return False
    return True


def send_password_reset_email(to: str, token: str) -> bool:
    """Send a password reset link containing the raw token."""
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    body = (
        "A password reset was requested for your GradNexa account.\n\n"
        f"Reset your password: {link}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutes. "
        "If you did not request it, ignore this email."
    )
    return send_email(to, "Reset your GradNexa password", body)

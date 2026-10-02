"""Outgoing email with pluggable backends.

console  writes each message to backend/outbox/<timestamp>-<to>.html (+ .txt) and logs it  (development)
smtp     sends through any SMTP provider: Resend, Brevo, Amazon SES, Postmark, Gmail app password…  (production)
memory   appends to `SENT` (tests)
"""

import logging
import re
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path

from ..config import PROJECT_ROOT, settings

log = logging.getLogger("burnoutai.email")
OUTBOX = PROJECT_ROOT / "backend" / "outbox"
SENT: list[dict] = []


def send_email(to: str, subject: str, html: str, text: str) -> None:
    backend = settings.email_backend
    if backend == "memory":
        SENT.append({"to": to, "subject": subject, "html": html, "text": text})
        return
    if backend == "console":
        OUTBOX.mkdir(parents=True, exist_ok=True)
        stem = f"{datetime.now():%Y%m%d-%H%M%S-%f}-{re.sub(r'[^a-zA-Z0-9]+', '_', to)}"
        (OUTBOX / f"{stem}.html").write_text(html, encoding="utf-8")
        (OUTBOX / f"{stem}.txt").write_text(f"To: {to}\nSubject: {subject}\n\n{text}", encoding="utf-8")
        log.warning("EMAIL (console backend) to=%s subject=%r saved to %s", to, subject, OUTBOX / f"{stem}.html")
        return
    if backend == "smtp":
        _send_smtp(to, subject, html, text)
        return
    raise RuntimeError(f"Unknown EMAIL_BACKEND {backend!r}")


def _send_smtp(to: str, subject: str, html: str, text: str) -> None:
    if not settings.smtp_host:
        raise RuntimeError("EMAIL_BACKEND=smtp but SMTP_HOST is not set")
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=settings.email_from.split("@")[-1].strip("> "))
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    if settings.smtp_security == "ssl":
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=20)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
    with server:
        if settings.smtp_security == "starttls":
            server.starttls(context=context)
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def send_safely(to: str, subject: str, html: str, text: str) -> None:
    """For background tasks: never let a mail-server hiccup crash the request that triggered it."""
    try:
        send_email(to, subject, html, text)
    except Exception:  # noqa: BLE001
        log.exception("Failed to send email to %s (%s)", to, subject)


def outbox_dir() -> Path:
    return OUTBOX

"""Send one test email with the settings in .env, to check your email setup.

Usage (from backend/):  python -m scripts.test_email you@example.com
"""

import sys

from app.config import settings
from app.email import templates
from app.email.sender import send_email


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.test_email you@example.com")
    to = sys.argv[1]
    print(f"Backend: {settings.email_backend} | From: {settings.email_from} | Host: {settings.smtp_host or '-'}:{settings.smtp_port}")
    subject, html, text = templates.verify_code("Test", "123456")
    try:
        send_email(to, "[Test] " + subject, html, text)
    except Exception as e:  # noqa: BLE001
        raise SystemExit(f"FAILED: {type(e).__name__}: {e}")
    if settings.email_backend == "console":
        print("Saved to backend/outbox/ (EMAIL_BACKEND=console). Set EMAIL_BACKEND=smtp to send for real.")
    else:
        print(f"Sent. Check the inbox (and spam folder) of {to}.")


if __name__ == "__main__":
    main()

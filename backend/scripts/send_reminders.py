"""Send the daily check-in reminder email.

Run every hour (cron, systemd timer, Windows Task Scheduler, or your host's scheduler):

    python -m scripts.send_reminders          # from backend/

Each verified user with reminders on gets at most one email per local day, once it's past
REMINDER_HOUR in their timezone, and only if they haven't checked in yet today.
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal, User
from app.email import templates
from app.email.sender import send_safely
from app.security import unsubscribe_token
from app.services import safe_zone, today_status, user_member

REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "9"))


def run(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    sent = 0
    with SessionLocal() as session:
        users = session.scalars(select(User).where(User.reminders.is_(True), User.email_verified_at.is_not(None))).all()
        for user in users:
            local = now.astimezone(ZoneInfo(safe_zone(user.timezone)))
            today = local.date().isoformat()
            if local.hour < REMINDER_HOUR or user.last_reminded_on == today:
                continue
            if today_status(session, user, user_member(session, user), now).done:
                continue
            unsubscribe = f"{settings.api_url}/unsubscribe?token={unsubscribe_token(user)}"
            send_safely(user.email, *templates.reminder(user.name, unsubscribe))
            user.last_reminded_on = today
            session.commit()
            sent += 1
    return sent


if __name__ == "__main__":
    print(f"Sent {run()} reminder(s)")

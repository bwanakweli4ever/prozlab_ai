"""Daily automatic 'finish your profile' reminders.

Run by the prozlab-reminders systemd timer. Sends only when PROFILE_REMINDERS_AUTO=true in .env,
to verified professionals with an unfinished profile whose account is at least a day old,
at most once a week and three times in total per person.

    ./venv/bin/python -m app.scripts.send_profile_reminders            # send
    ./venv/bin/python -m app.scripts.send_profile_reminders --dry-run  # list who would get it
"""
import sys

import app.main  # noqa: F401  (registers every model with SQLAlchemy)
from app.config.database import SessionLocal
from app.config.settings import settings
from app.services import profile_reminder
from app.services.email_service import EmailService


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    if not settings.PROFILE_REMINDERS_AUTO and not dry_run:
        print("Automatic profile reminders are off (set PROFILE_REMINDERS_AUTO=true to turn them on).")
        return 0
    email_service = EmailService()
    if not dry_run and not (email_service.mailtrap_api_key or email_service.smtp_configured):
        print("No email provider is configured; nothing sent.")
        return 1
    db = SessionLocal()
    try:
        recipients, recent = profile_reminder.find_recipients(
            db, min_account_age_days=profile_reminder.MIN_ACCOUNT_AGE_DAYS
        )
        if dry_run:
            print(f"Would send to {len(recipients)} (skipping {recent} reminded in the last {profile_reminder.REMINDER_INTERVAL_DAYS} days):")
            for r in recipients:
                print(f"  - {r.user.email}: {r.done}/{len(r.steps)} steps, {r.user.profile_reminder_count or 0} sent before")
            return 0
        sent, failed = profile_reminder.send_to(db, recipients, email_service)
        print(f"Profile reminders: {sent} sent, {failed} failed, {recent} skipped as recently reminded.")
        return 0 if failed == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

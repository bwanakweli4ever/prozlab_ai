"""Admin tools for the 'finish your profile' reminder email."""
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_superuser
from app.config.settings import settings
from app.services import profile_reminder
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)
router = APIRouter()
email_service = EmailService()


class RecipientOut(BaseModel):
    name: str
    email: str
    steps_done: int
    steps_total: int
    missing: List[str]
    last_reminded_at: Optional[datetime] = None
    reminders_sent: int = 0


class AutoReminderInfo(BaseModel):
    enabled: bool
    schedule: str
    interval_days: int
    max_reminders: int
    min_account_age_days: int


class ReminderOverview(BaseModel):
    subject: str
    eligible_count: int
    recently_reminded_count: int
    skip_recent_days: int
    recipients: List[RecipientOut]
    preview_html: str
    auto: AutoReminderInfo


class ReminderTestRequest(BaseModel):
    email: Optional[EmailStr] = None


class ReminderSendRequest(BaseModel):
    confirm: bool = False
    skip_recent_days: int = 7


class ReminderResult(BaseModel):
    success: bool
    message: str
    count: int = 0


def _provider_ready() -> bool:
    return bool(email_service.mailtrap_api_key or email_service.smtp_configured)


@router.get("", response_model=ReminderOverview)
def overview(
    skip_recent_days: int = Query(7, ge=0, le=90),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """Who would get the reminder now, and a preview of the email."""
    recipients, recent = profile_reminder.find_recipients(db, skip_recent_days)
    subject, preview_html, _ = profile_reminder.render(current_user.first_name, profile_reminder.sample_steps())
    return ReminderOverview(
        subject=subject,
        eligible_count=len(recipients),
        recently_reminded_count=recent,
        skip_recent_days=skip_recent_days,
        recipients=[
            RecipientOut(
                name=" ".join(filter(None, [r.user.first_name, r.user.last_name])) or r.user.email,
                email=r.user.email,
                steps_done=r.done,
                steps_total=len(r.steps),
                missing=[s.label for s in r.steps if not s.done],
                last_reminded_at=r.user.profile_reminder_sent_at,
                reminders_sent=r.user.profile_reminder_count or 0,
            )
            for r in recipients[:200]
        ],
        preview_html=preview_html,
        auto=AutoReminderInfo(
            enabled=bool(getattr(settings, "PROFILE_REMINDERS_AUTO", False)),
            schedule=profile_reminder.AUTO_SCHEDULE,
            interval_days=profile_reminder.REMINDER_INTERVAL_DAYS,
            max_reminders=profile_reminder.MAX_REMINDERS,
            min_account_age_days=profile_reminder.MIN_ACCOUNT_AGE_DAYS,
        ),
    )


@router.post("/test", response_model=ReminderResult)
def send_test(
    body: ReminderTestRequest = Body(default_factory=ReminderTestRequest),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """Send the reminder (with a sample checklist) to the admin or a given address."""
    if not _provider_ready():
        return ReminderResult(success=False, message="No email provider is configured.")
    to_email = str(body.email or current_user.email)
    subject, html_body, text_body = profile_reminder.render(current_user.first_name, profile_reminder.sample_steps())
    try:
        email_service.send_email(to_email=to_email, subject=f"[Test] {subject}", html_body=html_body, text_body=text_body)
    except Exception as e:
        return ReminderResult(success=False, message=f"Send failed: {str(e)[:300]}")
    return ReminderResult(success=True, message=f"Test sent to {to_email}.", count=1)


def _send_all(user_ids: List[str]) -> None:
    db = SessionLocal()
    try:
        wanted = set(user_ids)
        # Re-check eligibility at send time (same limits as the overview), then send.
        recipients, _ = profile_reminder.find_recipients(db)
        sent, failed = profile_reminder.send_to(db, [r for r in recipients if str(r.user.id) in wanted], email_service)
        logger.info(f"Profile reminders finished: {sent} sent, {failed} failed")
    finally:
        db.close()


@router.post("/send", response_model=ReminderResult)
def send_to_all(
    background_tasks: BackgroundTasks,
    body: ReminderSendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """Email every eligible professional. Requires confirm=true; skips anyone reminded in the last N days."""
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Set confirm to true to send.")
    if not _provider_ready():
        return ReminderResult(success=False, message="No email provider is configured.")
    recipients, _ = profile_reminder.find_recipients(db, max(0, body.skip_recent_days))
    if not recipients:
        return ReminderResult(success=True, message="Nobody needs a reminder right now.", count=0)
    background_tasks.add_task(_send_all, [str(r.user.id) for r in recipients])
    return ReminderResult(success=True, message=f"Sending to {len(recipients)} professional{'' if len(recipients) == 1 else 's'} now.", count=len(recipients))

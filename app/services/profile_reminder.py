"""'Finish your profile' reminder emails for professionals with incomplete profiles."""
import html
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile

# Bios the sign-up wizard writes automatically; they don't count as the person's own bio.
_AUTO_BIO_PREFIXES = ("Professional with ", "Professional looking to provide quality services")
_MIN_BIO_CHARS = 120


@dataclass
class Step:
    key: str
    label: str
    hint: str
    done: bool


def checklist(profile: Optional[ProzProfile]) -> List[Step]:
    bio = ((profile.bio if profile else None) or "").strip()
    own_bio = len(bio) >= _MIN_BIO_CHARS and not bio.startswith(_AUTO_BIO_PREFIXES)
    evidences = (profile.verification_evidences if profile else None) or []
    verifying = bool(profile) and (
        (profile.skill_verification_status or "not_started") != "not_started" or len(evidences) > 0
    )
    return [
        Step("cv", "Upload your CV", "We can fill in most of your profile from it.", bool(profile and profile.resume_filename)),
        Step("bio", "Write a short bio", "Two or three sentences on the work you do best.", own_bio),
        Step("skills", "List your skills", "Clients and our team search by skill.", bool(profile and (profile.skills or []))),
        Step("photo", "Add a profile photo", "A clear photo builds trust before the first call.", bool(profile and profile.profile_image_url)),
        Step("verify", "Verify your skills", "Share GitHub, work samples or references.", verifying),
    ]


def profile_for(db: Session, user: User) -> Optional[ProzProfile]:
    return (
        db.query(ProzProfile)
        .filter((ProzProfile.user_id == user.id) | (ProzProfile.email == user.email))
        .first()
    )


@dataclass
class Recipient:
    user: User
    profile: Optional[ProzProfile]
    steps: List[Step]

    @property
    def done(self) -> int:
        return sum(1 for s in self.steps if s.done)


def find_recipients(db: Session, skip_recent_days: int = 7) -> Tuple[List[Recipient], int]:
    """Verified, active professionals with at least one step left. Also returns how many were skipped as recently reminded."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=skip_recent_days)
    users = (
        db.query(User)
        .filter(User.is_active.is_(True), User.is_verified.is_(True), User.is_superuser.is_(False))
        .order_by(User.created_at.asc())
        .all()
    )
    recipients: List[Recipient] = []
    recently_reminded = 0
    for user in users:
        if getattr(user, "is_banned", False):
            continue
        profile = profile_for(db, user)
        steps = checklist(profile)
        if all(s.done for s in steps):
            continue
        sent_at = user.profile_reminder_sent_at
        if sent_at is not None:
            if sent_at.tzinfo is None:
                sent_at = sent_at.replace(tzinfo=timezone.utc)
            if sent_at > cutoff:
                recently_reminded += 1
                continue
        recipients.append(Recipient(user, profile, steps))
    return recipients, recently_reminded


def sample_steps() -> List[Step]:
    """A realistic half-finished checklist for test sends and the admin preview."""
    steps = checklist(None)
    for s in steps:
        s.done = s.key in ("photo", "skills")
    return steps


SUBJECT = "Opportunities are waiting: finish your Prozlab profile"


def render(first_name: Optional[str], steps: List[Step]) -> Tuple[str, str, str]:
    """Returns (subject, html_body, text_body)."""
    name = (first_name or "").strip() or "there"
    app_url = getattr(settings, "APP_URL", "https://prozlab.com").rstrip("/")
    logo = getattr(settings, "BRAND_LOGO_URL", "") or f"{app_url}/images/prozlab-logo.png"
    login_url = f"{app_url}/login"
    done = sum(1 for s in steps if s.done)
    total = len(steps)
    pct = int(round(100 * done / total)) if total else 0
    esc = html.escape

    rows = []
    for s in steps:
        if s.done:
            badge = '<td width="28" valign="top" style="padding:14px 0 14px 0;"><div style="width:22px;height:22px;border-radius:11px;background:#10B981;color:#ffffff;font:700 13px/22px Arial,Helvetica,sans-serif;text-align:center;">&#10003;</div></td>'
            label_style = "color:#64748B;text-decoration:line-through;"
            hint = "Done"
        else:
            badge = '<td width="28" valign="top" style="padding:14px 0 14px 0;"><div style="width:18px;height:18px;border-radius:11px;border:2px solid #C7D2FE;background:#ffffff;"></div></td>'
            label_style = "color:#0F172A;"
            hint = esc(s.hint)
        rows.append(
            f'<tr>{badge}<td style="padding:12px 0 12px 12px;border-bottom:1px solid #EEF2F7;">'
            f'<div style="font:600 15px/1.4 Arial,Helvetica,sans-serif;{label_style}">{esc(s.label)}</div>'
            f'<div style="font:400 13px/1.5 Arial,Helvetica,sans-serif;color:#64748B;margin-top:2px;">{hint}</div></td></tr>'
        )
    bar_done = max(pct, 4)

    html_body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(SUBJECT)}</title></head>
<body style="margin:0;padding:0;background:#F1F5F9;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">Clients are sending IT, web and software work. Finish your profile so we can match you.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
  <tr><td style="padding:0 4px 18px 4px;"><img src="{esc(logo)}" alt="Prozlab" height="34" style="display:block;height:34px;width:auto;border:0;"></td></tr>
  <tr><td style="background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #E2E8F0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
      <tr><td style="background:#0F172A;background-image:linear-gradient(135deg,#0F172A 0%,#312E81 100%);padding:36px 36px 32px 36px;">
        <div style="font:700 12px/1 Arial,Helvetica,sans-serif;letter-spacing:2px;text-transform:uppercase;color:#FDBA74;">Opportunities are waiting</div>
        <div style="font:800 28px/1.2 Arial,Helvetica,sans-serif;color:#ffffff;margin-top:14px;">{esc(name)}, finish your profile and get matched to client work.</div>
        <div style="font:400 15px/1.6 Arial,Helvetica,sans-serif;color:#C7D2FE;margin-top:14px;">Businesses across the US come to Prozlab for IT support, networks, security, websites and custom software. We match each request to professionals with complete, verified profiles.</div>
      </td></tr>
      <tr><td style="padding:28px 36px 8px 36px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
          <td style="font:700 15px/1.4 Arial,Helvetica,sans-serif;color:#0F172A;">Your profile</td>
          <td align="right" style="font:600 13px/1.4 Arial,Helvetica,sans-serif;color:#4F46E5;">{done} of {total} steps done</td>
        </tr></table>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:10px;background:#EEF2FF;border-radius:6px;"><tr>
          <td width="{bar_done}%" style="height:10px;background:#4F46E5;border-radius:6px;font-size:0;line-height:0;">&nbsp;</td><td style="font-size:0;line-height:0;">&nbsp;</td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:8px 36px 0 36px;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{''.join(rows)}</table></td></tr>
      <tr><td style="padding:28px 36px 8px 36px;">
        <a href="{esc(login_url)}" style="display:inline-block;background:#4F46E5;color:#ffffff;text-decoration:none;font:700 15px/1 Arial,Helvetica,sans-serif;padding:16px 26px;border-radius:12px;">Finish my profile &rarr;</a>
        <span style="display:inline-block;margin-left:12px;font:600 13px/1.4 Arial,Helvetica,sans-serif;color:#4F46E5;">Takes a few minutes with AI</span>
      </td></tr>
      <tr><td style="padding:10px 36px 32px 36px;font:400 13px/1.6 Arial,Helvetica,sans-serif;color:#64748B;">Upload your CV and our AI assistant fills in most of your profile for you. You just check it and save.</td></tr>
    </table>
  </td></tr>
  <tr><td style="padding:20px 8px 0 8px;font:400 12px/1.6 Arial,Helvetica,sans-serif;color:#94A3B8;text-align:center;">
    You're receiving this because you created a Prozlab professional account.<br>
    Prozlab Consulting &middot; <a href="{esc(app_url)}" style="color:#64748B;text-decoration:underline;">prozlab.com</a>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""

    lines = [
        f"Hi {name},",
        "",
        "Businesses across the US come to Prozlab for IT support, networks, security, websites and custom software.",
        "We match each request to professionals with complete, verified profiles.",
        "",
        f"Your profile: {done} of {total} steps done",
    ]
    lines += [f"  [{'x' if s.done else ' '}] {s.label}" + ("" if s.done else f" - {s.hint}") for s in steps]
    lines += [
        "",
        f"Finish your profile: {login_url}",
        "It only takes a few minutes: upload your CV and our AI assistant fills in most of your profile for you to check.",
        "",
        "You're receiving this because you created a Prozlab professional account.",
        "Prozlab Consulting - prozlab.com",
    ]
    return SUBJECT, html_body, "\n".join(lines)

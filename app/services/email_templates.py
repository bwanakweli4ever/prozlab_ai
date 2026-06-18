"""Shared Prozlab transactional email layouts (table-based, client-safe HTML)."""

from __future__ import annotations

import html
from datetime import datetime
from typing import Optional

from app.config.settings import settings


def _esc(value: Optional[str]) -> str:
    return html.escape(str(value or ""), quote=True)


def _brand() -> dict[str, str]:
    return {
        "name": getattr(settings, "PROJECT_NAME", "Prozlab Team"),
        "logo_url": getattr(
            settings,
            "BRAND_LOGO_URL",
            "https://prozlab.com/images/prozlab-logo.png",
        ),
        "green": getattr(settings, "BRAND_GREEN", "#2EAD5C"),
        "green_light": "#E8F7EE",
        "navy": "#0F172A",
        "muted": "#64748B",
        "border": "#E2E8F0",
        "bg": "#F1F5F9",
        "app_url": getattr(settings, "APP_URL", "https://prozlab.com").rstrip("/"),
        "support": getattr(settings, "MAIL_SUPPORT", None) or "support@prozlab.com",
    }


def _hero_svg(hero: str) -> str:
    green = _brand()["green"]
    if hero == "verify":
        return f"""
        <svg width="120" height="96" viewBox="0 0 120 96" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Verify email">
          <rect x="18" y="24" width="72" height="52" rx="8" fill="{green}" fill-opacity="0.15"/>
          <path d="M24 32 L60 56 L96 32" stroke="{green}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          <rect x="24" y="32" width="72" height="44" rx="6" fill="white" stroke="{green}" stroke-width="2"/>
          <circle cx="84" cy="28" r="14" fill="{green}"/>
          <path d="M78 28 L82.5 32.5 L90 24" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """
    if hero == "lock":
        return f"""
        <svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Password reset">
          <rect x="24" y="42" width="48" height="36" rx="8" fill="{green}" fill-opacity="0.15" stroke="{green}" stroke-width="2"/>
          <path d="M34 42 V34 C34 26.268 40.268 20 48 20 C55.732 20 62 26.268 62 34 V42" stroke="{green}" stroke-width="3" stroke-linecap="round"/>
          <circle cx="48" cy="58" r="4" fill="{green}"/>
        </svg>
        """
    if hero == "check":
        return f"""
        <svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Approved">
          <circle cx="48" cy="48" r="34" fill="{green}" fill-opacity="0.15"/>
          <circle cx="48" cy="48" r="28" fill="{green}"/>
          <path d="M36 48 L44 56 L62 38" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """
    if hero == "bell":
        return f"""
        <svg width="96" height="96" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Notification">
          <path d="M48 18 C38 18 32 26 32 36 V52 L26 60 H70 L64 52 V36 C64 26 58 18 48 18Z" fill="{green}" fill-opacity="0.15" stroke="{green}" stroke-width="2"/>
          <path d="M40 68 C40 72.418 43.582 76 48 76 C52.418 76 56 72.418 56 68" stroke="{green}" stroke-width="2" stroke-linecap="round"/>
        </svg>
        """
    return ""


def render_email_layout(content_html: str, *, preheader: str = "") -> str:
    b = _brand()
    year = datetime.now().year
    preheader_html = (
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{_esc(preheader)}</div>'
        if preheader
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
  <title>{_esc(b["name"])}</title>
</head>
<body style="margin:0;padding:0;background:{b['bg']};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  {preheader_html}
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:{b['bg']};padding:32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(15,23,42,0.08);">
          <tr>
            <td align="center" style="padding:32px 32px 8px;">
              <img src="{_esc(b['logo_url'])}" alt="Prozlab" width="160" style="display:block;height:auto;max-width:160px;border:0;"/>
            </td>
          </tr>
          <tr>
            <td style="padding:8px 32px 24px;">
              {content_html}
            </td>
          </tr>
        </table>
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:600px;margin-top:24px;">
          <tr>
            <td align="center" style="padding:0 16px 8px;font-size:13px;line-height:1.6;color:{b['muted']};">
              <strong style="color:{b['navy']};">Need help? We&apos;re here for you.</strong><br/>
              Email us at <a href="mailto:{_esc(b['support'])}" style="color:{b['green']};text-decoration:none;font-weight:600;">{_esc(b['support'])}</a>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:8px 16px 24px;font-size:12px;line-height:1.6;color:#94A3B8;">
              &copy; {year} Prozlab. All rights reserved.<br/>
              Prozlab Technologies Ltd. &nbsp;|&nbsp; Empowering connections, building futures.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_cta_email(
    *,
    subject: str,
    title: str,
    greeting_name: str,
    intro_html: str,
    cta_label: Optional[str] = None,
    cta_url: Optional[str] = None,
    fallback_url: Optional[str] = None,
    expiry_note: Optional[str] = None,
    security_note: Optional[str] = None,
    extra_html: str = "",
    hero: str = "verify",
    text_body: Optional[str] = None,
) -> tuple[str, str, str]:
    b = _brand()
    display_name = (greeting_name or "").strip() or "there"
    hero_html = _hero_svg(hero)
    hero_block = (
        f'<div style="text-align:center;margin:8px 0 20px;">{hero_html}</div>'
        if hero_html
        else ""
    )

    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
        <div style="text-align:center;margin:28px 0 8px;">
          <a href="{_esc(cta_url)}" style="display:inline-block;background:{b['green']};color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;padding:14px 28px;border-radius:10px;">
            &#9993;&nbsp; {_esc(cta_label)}
          </a>
        </div>
        """

    expiry_block = ""
    if expiry_note:
        expiry_block = f"""
        <p style="margin:16px 0 0;text-align:center;font-size:13px;color:{b['muted']};">
          &#9201;&nbsp; {expiry_note}
        </p>
        """

    fallback_block = ""
    link = fallback_url or cta_url
    if link:
        fallback_block = f"""
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-top:28px;border-top:1px solid {b['border']};padding-top:24px;">
          <tr>
            <td style="font-size:13px;line-height:1.6;color:{b['muted']};">
              <strong style="color:{b['navy']};">&#128279; Button not working?</strong><br/>
              Copy and paste this link into your browser:
              <div style="margin-top:10px;padding:12px 14px;background:#F8FAFC;border:1px solid {b['border']};border-radius:8px;word-break:break-all;font-size:12px;color:#334155;">
                {_esc(link)}
              </div>
            </td>
          </tr>
        </table>
        """

    security_block = ""
    if security_note:
        security_block = f"""
        <div style="margin-top:24px;padding:14px 16px;background:{b['green_light']};border-radius:10px;font-size:13px;line-height:1.6;color:#166534;">
          &#128737;&nbsp; {security_note}
        </div>
        """

    content = f"""
      {hero_block}
      <h1 style="margin:0 0 16px;font-size:24px;line-height:1.3;font-weight:800;color:{b['navy']};text-align:center;">
        {_esc(title)}
      </h1>
      <p style="margin:0 0 12px;font-size:15px;line-height:1.7;color:#334155;">
        Hi <strong style="color:{b['green']};">{_esc(display_name)}</strong>,
      </p>
      <div style="font-size:15px;line-height:1.7;color:#334155;">{intro_html}</div>
      {extra_html}
      {cta_block}
      {expiry_block}
      {fallback_block}
      {security_block}
    """

    html_body = render_email_layout(content, preheader=title)
    if text_body is None:
        text_body = (
            f"{title}\n\nHi {display_name},\n\n"
            f"{html.unescape(intro_html.replace('<br/>', chr(10)).replace('<br>', chr(10)))}\n"
        )
        if cta_url:
            text_body += f"\n{cta_label or 'Open link'}: {cta_url}\n"
        if expiry_note:
            text_body += f"\n{expiry_note}\n"
        if security_note:
            text_body += f"\n{security_note}\n"
        text_body += f"\n{b['name']}\n{b['support']}\n"

    return subject, html_body, text_body


def build_verification_email(
    email: str,
    token: str,
    user_name: Optional[str] = None,
    verification_url: Optional[str] = None,
) -> tuple[str, str, str]:
    del email, token  # URL is built by caller when needed
    b = _brand()
    subject = f"Verify your email for {b['name']}"
    first = (user_name or "").strip().split()[0] if user_name else "there"
    intro = (
        f"Thanks for joining Prozlab! &#127881;<br/><br/>"
        "To activate your account and start exploring opportunities, "
        "please verify your email address by clicking the button below."
    )
    return build_cta_email(
        subject=subject,
        title="Verify Your Email Address",
        greeting_name=first,
        intro_html=intro,
        cta_label="Verify Email Address",
        cta_url=verification_url,
        fallback_url=verification_url,
        expiry_note="This link will expire in <strong style=\"color:#2EAD5C;\">24 hours</strong>.",
        security_note="If you didn't create a Prozlab account, you can safely ignore this email.",
        hero="verify",
    )


def build_password_reset_email(user_name: str, reset_url: str) -> tuple[str, str, str]:
    first = (user_name or "").strip().split()[0] if user_name else "there"
    extra = """
      <div style="margin-top:16px;padding:14px 16px;background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;font-size:13px;line-height:1.6;color:#9A3412;">
        <strong>Important:</strong>
        <ul style="margin:8px 0 0;padding-left:18px;">
          <li>This link will expire in 1 hour</li>
          <li>If you didn't request this reset, you can ignore this email</li>
          <li>Your password stays the same until you create a new one</li>
        </ul>
      </div>
    """
    return build_cta_email(
        subject="Reset your Prozlab password",
        title="Reset Your Password",
        greeting_name=first,
        intro_html="We received a request to reset your password. Click the button below to choose a new one.",
        cta_label="Reset Password",
        cta_url=reset_url,
        fallback_url=reset_url,
        expiry_note="This reset link expires in <strong style=\"color:#2EAD5C;\">1 hour</strong>.",
        security_note="If you didn't request a password reset, you can safely ignore this email.",
        extra_html=extra,
        hero="lock",
    )


def build_profile_status_email(
    user_name: str,
    *,
    subject: str,
    status_message: str,
    next_steps: str,
    admin_notes: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    hero: str = "check",
) -> tuple[str, str, str]:
    b = _brand()
    extra_parts = []
    if admin_notes:
        extra_parts.append(
            f'<div style="margin-top:16px;padding:14px 16px;background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;">'
            f'<strong style="color:{b["navy"]};">Administrative notes</strong>'
            f'<p style="margin:8px 0 0;font-size:14px;line-height:1.6;color:#334155;">{_esc(admin_notes)}</p></div>'
        )
    if rejection_reason:
        extra_parts.append(
            '<div style="margin-top:16px;padding:14px 16px;background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;">'
            f'<strong style="color:#991B1B;">Reason for review</strong>'
            f'<p style="margin:8px 0 0;font-size:14px;line-height:1.6;color:#7F1D1D;">{_esc(rejection_reason)}</p></div>'
        )
    extra = "".join(extra_parts)
    dashboard_url = f"{b['app_url']}/dashboard"
    return build_cta_email(
        subject=subject,
        title="Profile Verification Update",
        greeting_name=user_name,
        intro_html=(
            f"<strong>{_esc(status_message)}</strong><br/><br/>{_esc(next_steps)}"
        ),
        cta_label="View Your Dashboard",
        cta_url=dashboard_url,
        fallback_url=dashboard_url,
        extra_html=extra,
        hero=hero,
    )


def build_simple_notification_email(
    *,
    subject: str,
    title: str,
    greeting_name: str,
    body_html: str,
    cta_label: Optional[str] = None,
    cta_url: Optional[str] = None,
    hero: str = "bell",
) -> tuple[str, str, str]:
    return build_cta_email(
        subject=subject,
        title=title,
        greeting_name=greeting_name,
        intro_html=body_html,
        cta_label=cta_label,
        cta_url=cta_url,
        fallback_url=cta_url,
        hero=hero,
    )

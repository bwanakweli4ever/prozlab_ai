from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile
from app.modules.proz.services.verification_helpers import evidences

DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "guerrillamail.com",
    "tempmail.com",
    "10minutemail.com",
    "yopmail.com",
    "throwaway.email",
    "sharklasers.com",
}

SEVERITY_WEIGHTS = {"low": 10, "medium": 20, "high": 35, "critical": 50}
AUTO_FLAG_THRESHOLD = 55
HIGH_RISK_THRESHOLD = 40


def _risk_level(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= HIGH_RISK_THRESHOLD:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def _get_profile(db: Session, user: User) -> Optional[ProzProfile]:
    return (
        db.query(ProzProfile)
        .filter((ProzProfile.user_id == user.id) | (ProzProfile.email == user.email))
        .first()
    )


def _signal(code: str, severity: str, message: str) -> Dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "score": SEVERITY_WEIGHTS.get(severity, 10),
    }


def _duplicate_urls(db: Session, profile: ProzProfile, user_id: UUID) -> List[Dict[str, Any]]:
    signals: List[Dict[str, Any]] = []
    urls: set[str] = set()

    for field in ("linkedin", "website"):
        val = getattr(profile, field, None)
        if val and val.startswith("http"):
            urls.add(val.strip().lower())

    for item in evidences(profile):
        url = item.get("url")
        if url and url.startswith("http"):
            urls.add(url.strip().lower())

    for url in urls:
        others = (
            db.query(ProzProfile)
            .filter(ProzProfile.id != profile.id)
            .filter(
                (ProzProfile.linkedin.ilike(f"%{url}%"))
                | (ProzProfile.website.ilike(f"%{url}%"))
            )
            .count()
        )
        if others > 0:
            signals.append(
                _signal(
                    "duplicate_profile_link",
                    "high",
                    f"Profile link also used by {others} other candidate(s): {url}",
                )
            )
    return signals


def scan_user(db: Session, user: User) -> Tuple[int, List[Dict[str, Any]]]:
    """Return fraud score and signal list for a user."""
    if user.is_superuser:
        return 0, []

    signals: List[Dict[str, Any]] = []
    profile = _get_profile(db, user)

    domain = (user.email or "").split("@")[-1].lower()
    if domain in DISPOSABLE_DOMAINS:
        signals.append(
            _signal("disposable_email", "high", f"Registration uses disposable email domain: {domain}")
        )

    if profile:
        if profile.email and user.email and profile.email.lower() != user.email.lower():
            signals.append(
                _signal(
                    "email_mismatch",
                    "critical",
                    f"Account email ({user.email}) does not match profile email ({profile.email})",
                )
            )

        if profile.verification_status == "rejected":
            signals.append(
                _signal("profile_verification_rejected", "high", "Profile verification was rejected by admin")
            )

        if profile.skill_verification_status in {"rejected", "needs_revision"}:
            signals.append(
                _signal(
                    "skill_verification_failed",
                    "medium",
                    f"Skills assessment status: {profile.skill_verification_status}",
                )
            )

        items = evidences(profile)
        rejected_items = [e for e in items if e.get("status") == "rejected"]
        if len(rejected_items) >= 2:
            signals.append(
                _signal(
                    "multiple_rejected_evidence",
                    "high",
                    f"{len(rejected_items)} verification evidence items were rejected",
                )
            )

        if profile.years_experience and profile.years_experience > 15:
            account_age_days = (datetime.now(timezone.utc) - user.created_at.replace(tzinfo=timezone.utc)).days
            if account_age_days < 14 and len(items) < 2:
                signals.append(
                    _signal(
                        "experience_inconsistency",
                        "medium",
                        f"Claims {profile.years_experience}+ years experience but account is only {account_age_days} days old with little proof",
                    )
                )

        if not profile.bio and profile.years_experience and profile.years_experience > 5:
            signals.append(
                _signal(
                    "thin_profile_high_experience",
                    "low",
                    "High experience claimed with minimal profile information",
                )
            )

        signals.extend(_duplicate_urls(db, profile, user.id))

    if user.is_flagged:
        signals.append(_signal("manually_flagged", "medium", "Previously flagged by an administrator"))

    score = min(sum(s["score"] for s in signals), 100)
    return score, signals


def apply_scan_result(db: Session, user: User, auto_flag: bool = True) -> Tuple[int, List[Dict[str, Any]], bool]:
    score, signals = scan_user(db, user)
    user.fraud_score = score
    user.fraud_signals = signals
    user.fraud_scanned_at = datetime.now(timezone.utc)

    auto_flagged = False
    if auto_flag and score >= AUTO_FLAG_THRESHOLD and not user.is_banned and not user.is_superuser:
        user.is_flagged = True
        user.flagged_at = datetime.now(timezone.utc)
        auto_flagged = True

    db.commit()
    db.refresh(user)
    return score, signals, auto_flagged


def to_candidate_item(db: Session, user: User) -> Dict[str, Any]:
    profile = _get_profile(db, user)
    signals = user.fraud_signals if isinstance(user.fraud_signals, list) else []
    score = user.fraud_score or 0
    return {
        "user_id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_flagged": user.is_flagged or False,
        "is_banned": user.is_banned or False,
        "fraud_score": score,
        "fraud_signals": signals,
        "ban_reason": user.ban_reason,
        "fraud_notes": user.fraud_notes,
        "flagged_at": user.flagged_at,
        "banned_at": user.banned_at,
        "fraud_scanned_at": user.fraud_scanned_at,
        "profile_id": profile.id if profile else None,
        "profile_verification_status": profile.verification_status if profile else None,
        "skill_verification_status": profile.skill_verification_status if profile else None,
        "risk_level": _risk_level(score),
    }

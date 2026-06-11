import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_user
from app.modules.proz.models.proz import ProzProfile
from app.modules.proz.schemas.verification import (
    EvidenceCreate,
    EvidenceItem,
    GitHubValidateRequest,
    GitHubValidateResponse,
    VerificationStatusResponse,
)
from app.modules.proz.services.verification_helpers import (
    compute_score,
    evidences,
    get_meta,
    requirements_met,
    save_evidences,
    utc_now_iso,
)

router = APIRouter(prefix="/verification", tags=["skill-verification"])

GITHUB_PATTERN = re.compile(r"^https?://(www\.)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/?$")
LINKEDIN_PATTERN = re.compile(r"^https?://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?")


def _get_profile(db: Session, user: User) -> ProzProfile:
    profile = (
        db.query(ProzProfile)
        .filter((ProzProfile.user_id == user.id) | (ProzProfile.email == user.email))
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Complete your profile first.",
        )
    if not profile.user_id:
        profile.user_id = user.id
    return profile


def _status_response(profile: ProzProfile) -> VerificationStatusResponse:
    items = evidences(profile)
    reqs = requirements_met(items)
    meta = get_meta(profile)
    return VerificationStatusResponse(
        skill_verification_status=profile.skill_verification_status or "not_started",
        verification_score=compute_score(items),
        evidences=[EvidenceItem(**e) for e in items],
        requirements_met=reqs,
        can_submit=all(reqs.values()) and profile.skill_verification_status not in {
            "pending_review",
            "verified",
        },
        admin_notes=meta.get("admin_notes"),
        reviewed_at=meta.get("reviewed_at"),
    )


def _validate_evidence(payload: EvidenceCreate) -> None:
    if payload.type == "github":
        if not payload.url or not GITHUB_PATTERN.match(payload.url.strip()):
            raise HTTPException(status_code=400, detail="Valid GitHub profile URL required")
    elif payload.type == "linkedin":
        if not payload.url or not LINKEDIN_PATTERN.match(payload.url.strip()):
            raise HTTPException(status_code=400, detail="Valid LinkedIn profile URL required")
    elif payload.type in {"portfolio", "work_sample", "certification", "identity_document"}:
        if not payload.url or not payload.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Valid URL required")
    elif payload.type == "recommendation":
        if not payload.referrer_name or not payload.referrer_email:
            raise HTTPException(status_code=400, detail="Referrer name and email required")
        if not payload.referrer_message or len(payload.referrer_message.strip()) < 20:
            raise HTTPException(status_code=400, detail="Recommendation message must be at least 20 characters")
    elif payload.type == "previous_employer":
        if not payload.title or not payload.description:
            raise HTTPException(status_code=400, detail="Employer name and role description required")


@router.get("", response_model=VerificationStatusResponse)
async def get_verification_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = _get_profile(db, current_user)
    return _status_response(profile)


@router.post("/evidence", response_model=EvidenceItem)
async def add_evidence(
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_evidence(payload)
    profile = _get_profile(db, current_user)
    items = evidences(profile)
    meta = get_meta(profile)

    metadata: Optional[Dict[str, Any]] = None
    if payload.type == "github" and payload.url:
        gh = await _validate_github_url(payload.url)
        if not gh.valid:
            raise HTTPException(status_code=400, detail=gh.message or "GitHub profile could not be verified")
        metadata = {
            "username": gh.username,
            "public_repos": gh.public_repos,
            "followers": gh.followers,
        }

    item = {
        "id": str(uuid.uuid4()),
        "type": payload.type,
        "title": payload.title.strip(),
        "url": payload.url.strip() if payload.url else None,
        "description": payload.description.strip() if payload.description else None,
        "referrer_name": payload.referrer_name,
        "referrer_email": str(payload.referrer_email) if payload.referrer_email else None,
        "referrer_relationship": payload.referrer_relationship,
        "referrer_message": payload.referrer_message,
        "status": "submitted",
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    items.append(item)

    if profile.skill_verification_status in {"not_started", "needs_revision", "rejected"}:
        profile.skill_verification_status = "in_progress"

    save_evidences(profile, items, meta if meta else None)
    db.commit()
    db.refresh(profile)
    return EvidenceItem(**item)


@router.delete("/evidence/{evidence_id}")
async def delete_evidence(
    evidence_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = _get_profile(db, current_user)
    items = evidences(profile)
    meta = get_meta(profile)
    filtered = [e for e in items if e.get("id") != evidence_id]
    if len(filtered) == len(items):
        raise HTTPException(status_code=404, detail="Evidence not found")

    save_evidences(profile, filtered, meta if meta else None)
    if not filtered:
        profile.skill_verification_status = "not_started"
    db.commit()
    return {"success": True}


@router.post("/submit", response_model=VerificationStatusResponse)
async def submit_for_review(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = _get_profile(db, current_user)
    items = evidences(profile)
    reqs = requirements_met(items)
    if not all(reqs.values()):
        raise HTTPException(
            status_code=400,
            detail="Complete identity, work experience, and at least 2 evidence items before submitting.",
        )

    meta = get_meta(profile)
    meta["submitted_at"] = utc_now_iso()
    meta.pop("admin_notes", None)
    meta.pop("reviewed_at", None)
    meta.pop("decision", None)

    profile.skill_verification_status = "pending_review"
    save_evidences(profile, items, meta)
    db.commit()
    db.refresh(profile)
    return _status_response(profile)


@router.post("/github/validate", response_model=GitHubValidateResponse)
async def validate_github(
    payload: GitHubValidateRequest,
    current_user: User = Depends(get_current_user),
):
    return await _validate_github_url(payload.url)


async def _validate_github_url(url: str) -> GitHubValidateResponse:
    match = GITHUB_PATTERN.match(url.strip())
    if not match:
        return GitHubValidateResponse(valid=False, message="Invalid GitHub profile URL")

    username = match.group(2)
    try:
        res = requests.get(
            f"https://api.github.com/users/{username}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=8,
        )
        if res.status_code == 404:
            return GitHubValidateResponse(valid=False, message="GitHub user not found")
        if res.status_code != 200:
            return GitHubValidateResponse(valid=False, message="Could not reach GitHub API")
        data = res.json()
        return GitHubValidateResponse(
            valid=True,
            username=data.get("login"),
            public_repos=data.get("public_repos"),
            followers=data.get("followers"),
            profile_url=data.get("html_url"),
            message="GitHub profile verified",
        )
    except requests.RequestException:
        return GitHubValidateResponse(
            valid=False,
            message="Network error while validating GitHub profile",
        )

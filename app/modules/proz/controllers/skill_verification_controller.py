import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_user
from app.modules.proz.models.proz import ProzProfile
from app.modules.proz.schemas.files import FileUploadResponse
from app.modules.proz.schemas.verification import (
    EvidenceCreate,
    EvidenceItem,
    GitHubRepoPreview,
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
from app.services.file_service import FileService

router = APIRouter(prefix="/verification", tags=["skill-verification"])
file_service = FileService()

GITHUB_PATTERN = re.compile(r"^https?://(www\.)?github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?)/?$")
LINKEDIN_PATTERN = re.compile(r"^https?://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?")


def _is_valid_evidence_url(url: Optional[str]) -> bool:
    if not url:
        return False
    value = url.strip()
    return value.startswith(("http://", "https://", "/static/", "/uploads/"))


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
    elif payload.type in {"portfolio", "work_sample", "certification"}:
        if not _is_valid_evidence_url(payload.url):
            raise HTTPException(status_code=400, detail="Enter a valid link starting with https://")
    elif payload.type == "identity_document":
        if not _is_valid_evidence_url(payload.url):
            raise HTTPException(status_code=400, detail="Upload your government ID or passport before continuing")
        if not payload.description or len(payload.description.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Tell us which document you uploaded (e.g. Passport, National ID)",
            )
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
            "name": gh.name,
            "public_repos": gh.public_repos,
            "account_created_at": gh.account_created_at,
            "top_repos": [repo.model_dump() for repo in (gh.top_repos or [])],
            "profile_url": gh.profile_url,
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


@router.post("/identity-document/upload", response_model=FileUploadResponse)
async def upload_identity_document(
    file: UploadFile = File(..., description="Government ID or passport (PDF, JPG, PNG)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    profile = _get_profile(db, current_user)
    result = file_service.upload_verification_document(file, profile.id)

    if not result["success"]:
        if result.get("error_code") == "INVALID_FILE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
        if result.get("error_code") == "FILE_TOO_LARGE":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["message"])
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result["message"])

    return FileUploadResponse(
        success=True,
        message=result["message"],
        file_url=result["primary_url"],
        file_name=result["file_name"],
        file_size=result["file_size"],
    )


@router.post("/github/validate", response_model=GitHubValidateResponse)
async def validate_github(
    payload: GitHubValidateRequest,
    current_user: User = Depends(get_current_user),
):
    return await _validate_github_url(payload.url)


async def _validate_github_url(url: str) -> GitHubValidateResponse:
    match = GITHUB_PATTERN.match(url.strip())
    if not match:
        return GitHubValidateResponse(valid=False, message="Enter a public GitHub profile URL, e.g. https://github.com/your-username")

    username = match.group(2)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Prozlab-Verification"}
    try:
        res = requests.get(
            f"https://api.github.com/users/{username}",
            headers=headers,
            timeout=8,
        )
        if res.status_code == 404:
            return GitHubValidateResponse(valid=False, message="GitHub user not found. Check the username and try again.")
        if res.status_code != 200:
            return GitHubValidateResponse(valid=False, message="Could not reach GitHub. Try again in a moment.")
        data = res.json()

        top_repos: list[GitHubRepoPreview] = []
        repos_res = requests.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 5, "type": "owner"},
            headers=headers,
            timeout=8,
        )
        if repos_res.status_code == 200:
            for repo in repos_res.json()[:5]:
                if repo.get("fork"):
                    continue
                top_repos.append(
                    GitHubRepoPreview(
                        name=repo.get("name") or "repository",
                        language=repo.get("language"),
                        description=(repo.get("description") or "")[:140] or None,
                        url=repo.get("html_url"),
                        stars=repo.get("stargazers_count"),
                        updated_at=repo.get("updated_at"),
                    )
                )
                if len(top_repos) >= 3:
                    break

        public_repos = data.get("public_repos") or 0
        if public_repos == 0 and not top_repos:
            return GitHubValidateResponse(
                valid=False,
                username=data.get("login"),
                profile_url=data.get("html_url"),
                message="This GitHub profile has no public repositories. Add public work samples before verifying.",
            )

        return GitHubValidateResponse(
            valid=True,
            username=data.get("login"),
            name=data.get("name") or data.get("login"),
            bio=(data.get("bio") or "")[:200] or None,
            avatar_url=data.get("avatar_url"),
            public_repos=public_repos,
            account_created_at=data.get("created_at"),
            profile_url=data.get("html_url"),
            top_repos=top_repos or None,
            followers=data.get("followers"),
            message="GitHub profile linked — public repositories found.",
        )
    except requests.RequestException:
        return GitHubValidateResponse(
            valid=False,
            message="Network error while contacting GitHub. Check your connection and try again.",
        )

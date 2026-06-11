import math
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_superuser
from app.modules.proz.models.proz import ProzProfile
from app.modules.proz.schemas.skill_verification_admin import (
    SkillVerificationDetailResponse,
    SkillVerificationListItem,
    SkillVerificationListResponse,
    SkillVerificationReviewRequest,
)
from app.modules.proz.schemas.verification import EvidenceItem
from app.modules.proz.services.verification_helpers import (
    IDENTITY_TYPES,
    WORK_EXPERIENCE_TYPES,
    compute_score,
    evidences,
    get_meta,
    requirements_met,
    save_evidences,
    utc_now_iso,
)

router = APIRouter()


def _to_list_item(profile: ProzProfile) -> SkillVerificationListItem:
    items = evidences(profile)
    meta = get_meta(profile)
    types = {e.get("type") for e in items}
    return SkillVerificationListItem(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        profile_image_url=profile.profile_image_url,
        location=profile.location,
        years_experience=profile.years_experience,
        verification_status=profile.verification_status or "pending",
        skill_verification_status=profile.skill_verification_status or "not_started",
        verification_score=compute_score(items),
        evidence_count=len(items),
        identity_items=len([e for e in items if e.get("type") in IDENTITY_TYPES]),
        work_experience_items=len([e for e in items if e.get("type") in WORK_EXPERIENCE_TYPES]),
        submitted_at=meta.get("submitted_at"),
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/skill-verifications", response_model=SkillVerificationListResponse)
async def list_skill_verifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    skill_status: Optional[str] = Query(
        None, description="Filter: pending_review, in_progress, verified, rejected, needs_revision"
    ),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(
        None, description="identity, work_experience, assessment"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    query = db.query(ProzProfile)

    if skill_status:
        query = query.filter(ProzProfile.skill_verification_status == skill_status)
    else:
        query = query.filter(
            ProzProfile.skill_verification_status.in_(
                ["pending_review", "in_progress", "verified", "rejected", "needs_revision"]
            )
        )

    if search:
        query = query.filter(
            or_(
                ProzProfile.first_name.ilike(f"%{search}%"),
                ProzProfile.last_name.ilike(f"%{search}%"),
                ProzProfile.email.ilike(f"%{search}%"),
            )
        )

    profiles = query.order_by(ProzProfile.updated_at.desc()).all()

    if category == "identity":
        profiles = [p for p in profiles if any(e.get("type") in IDENTITY_TYPES for e in evidences(p))]
    elif category == "work_experience":
        profiles = [
            p for p in profiles if any(e.get("type") in WORK_EXPERIENCE_TYPES for e in evidences(p))
        ]
    elif category == "assessment":
        profiles = [p for p in profiles if len(evidences(p)) >= 2]

    total = len(profiles)
    offset = (page - 1) * page_size
    page_profiles = profiles[offset : offset + page_size]

    return SkillVerificationListResponse(
        profiles=[_to_list_item(p) for p in page_profiles],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)) if total else 0,
    )


@router.get("/skill-verifications/{profile_id}", response_model=SkillVerificationDetailResponse)
async def get_skill_verification_detail(
    profile_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    items = evidences(profile)
    meta = get_meta(profile)
    return SkillVerificationDetailResponse(
        profile=_to_list_item(profile),
        evidences=[EvidenceItem(**e) for e in items],
        requirements_met=requirements_met(items),
        admin_notes=meta.get("admin_notes"),
        reviewed_at=meta.get("reviewed_at"),
        reviewed_by=meta.get("reviewed_by"),
    )


@router.post("/skill-verifications/{profile_id}/review", response_model=SkillVerificationDetailResponse)
async def review_skill_verification(
    profile_id: UUID,
    payload: SkillVerificationReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    user_items = evidences(profile)
    review_map = {r.evidence_id: r for r in payload.evidence_reviews}

    updated_items: List[dict] = []
    for item in user_items:
        review = review_map.get(item.get("id", ""))
        if review:
            item = {**item, "status": review.status, "admin_notes": review.admin_notes}
        updated_items.append(item)

    profile.skill_verification_status = payload.decision

    meta = {
        "admin_notes": payload.admin_notes,
        "reviewed_at": utc_now_iso(),
        "reviewed_by": current_user.email,
        "decision": payload.decision,
        "submitted_at": get_meta(profile).get("submitted_at"),
    }
    save_evidences(profile, updated_items, meta)

    db.commit()
    db.refresh(profile)

    items = evidences(profile)
    meta = get_meta(profile)
    return SkillVerificationDetailResponse(
        profile=_to_list_item(profile),
        evidences=[EvidenceItem(**e) for e in items],
        requirements_met=requirements_met(items),
        admin_notes=meta.get("admin_notes"),
        reviewed_at=meta.get("reviewed_at"),
        reviewed_by=meta.get("reviewed_by"),
    )

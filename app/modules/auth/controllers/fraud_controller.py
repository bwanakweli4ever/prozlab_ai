from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.schemas.fraud import (
    FraudActionRequest,
    FraudActionResponse,
    FraudCandidateItem,
    FraudCandidateListResponse,
    FraudScanResponse,
    FraudSignal,
)
from app.modules.auth.services.auth_service import get_current_superuser
from app.modules.auth.services.fraud_detection_service import (
    AUTO_FLAG_THRESHOLD,
    apply_scan_result,
    scan_user,
    to_candidate_item,
    _risk_level,
)

router = APIRouter(prefix="/fraud", tags=["Admin - Fraud Detection"])


def _get_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Cannot apply fraud actions to superuser accounts")
    return user


@router.get("/candidates", response_model=FraudCandidateListResponse)
async def list_fraud_candidates(
    filter: Optional[str] = Query(None, description="flagged, banned, high_risk, all"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    query = db.query(User).filter(User.is_superuser == False)  # noqa: E712

    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%"))
            | (User.first_name.ilike(f"%{search}%"))
            | (User.last_name.ilike(f"%{search}%"))
        )

    users: List[User] = query.order_by(User.fraud_score.desc(), User.updated_at.desc()).all()

    candidates = [to_candidate_item(db, u) for u in users]

    if filter == "flagged":
        candidates = [c for c in candidates if c["is_flagged"] and not c["is_banned"]]
    elif filter == "banned":
        candidates = [c for c in candidates if c["is_banned"]]
    elif filter == "high_risk":
        candidates = [c for c in candidates if c["fraud_score"] >= AUTO_FLAG_THRESHOLD and not c["is_banned"]]

    flagged_count = sum(1 for c in candidates if c["is_flagged"] and not c["is_banned"])
    banned_count = sum(1 for c in candidates if c["is_banned"])
    high_risk_count = sum(1 for c in candidates if c["fraud_score"] >= AUTO_FLAG_THRESHOLD)

    return FraudCandidateListResponse(
        candidates=[FraudCandidateItem(**c) for c in candidates],
        total=len(candidates),
        flagged_count=flagged_count,
        banned_count=banned_count,
        high_risk_count=high_risk_count,
    )


@router.post("/scan", response_model=List[FraudScanResponse])
async def scan_candidates(
    user_id: Optional[UUID] = Query(None, description="Scan single user; omit to scan all non-admin users"),
    auto_flag: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    if user_id:
        users = [_get_user_or_404(db, user_id)]
    else:
        users = db.query(User).filter(User.is_superuser == False).all()  # noqa: E712

    results: List[FraudScanResponse] = []
    for user in users:
        score, signals, auto_flagged = apply_scan_result(db, user, auto_flag=auto_flag)
        results.append(
            FraudScanResponse(
                user_id=user.id,
                fraud_score=score,
                risk_level=_risk_level(score),
                signals=[FraudSignal(**s) for s in signals],
                auto_flagged=auto_flagged,
            )
        )
    return results


@router.post("/users/{user_id}/flag", response_model=FraudActionResponse)
async def flag_candidate(
    user_id: UUID,
    payload: FraudActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    user = _get_user_or_404(db, user_id)
    user.is_flagged = True
    user.flagged_at = datetime.now(timezone.utc)
    user.fraud_notes = payload.notes or payload.reason
    db.commit()
    db.refresh(user)
    return FraudActionResponse(
        success=True,
        message="Candidate flagged for review",
        user_id=user.id,
        is_flagged=True,
        is_banned=user.is_banned or False,
        is_active=user.is_active,
    )


@router.post("/users/{user_id}/unflag", response_model=FraudActionResponse)
async def unflag_candidate(
    user_id: UUID,
    payload: FraudActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    user = _get_user_or_404(db, user_id)
    user.is_flagged = False
    user.fraud_notes = payload.notes or payload.reason
    db.commit()
    db.refresh(user)
    return FraudActionResponse(
        success=True,
        message="Flag removed",
        user_id=user.id,
        is_flagged=False,
        is_banned=user.is_banned or False,
        is_active=user.is_active,
    )


@router.post("/users/{user_id}/ban", response_model=FraudActionResponse)
async def ban_candidate(
    user_id: UUID,
    payload: FraudActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    user = _get_user_or_404(db, user_id)
    user.is_banned = True
    user.is_active = False
    user.is_flagged = True
    user.ban_reason = payload.reason
    user.fraud_notes = payload.notes or payload.reason
    user.banned_at = datetime.now(timezone.utc)
    if not user.flagged_at:
        user.flagged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return FraudActionResponse(
        success=True,
        message="Candidate banned and deactivated",
        user_id=user.id,
        is_flagged=True,
        is_banned=True,
        is_active=False,
    )


@router.post("/users/{user_id}/unban", response_model=FraudActionResponse)
async def unban_candidate(
    user_id: UUID,
    payload: FraudActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    user = _get_user_or_404(db, user_id)
    user.is_banned = False
    user.is_active = True
    user.ban_reason = None
    user.banned_at = None
    user.fraud_notes = payload.notes or "Ban lifted by admin"
    db.commit()
    db.refresh(user)
    return FraudActionResponse(
        success=True,
        message="Ban lifted — candidate can sign in again",
        user_id=user.id,
        is_flagged=user.is_flagged or False,
        is_banned=False,
        is_active=True,
    )


@router.get("/users/{user_id}/scan", response_model=FraudScanResponse)
async def scan_single_candidate(
    user_id: UUID,
    auto_flag: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    user = _get_user_or_404(db, user_id)
    score, signals, auto_flagged = apply_scan_result(db, user, auto_flag=auto_flag)
    return FraudScanResponse(
        user_id=user.id,
        fraud_score=score,
        risk_level=_risk_level(score),
        signals=[FraudSignal(**s) for s in signals],
        auto_flagged=auto_flagged,
    )

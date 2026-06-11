from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_user
from app.modules.onboarding.schemas.onboarding import (
    OnboardingCompleteResponse,
    OnboardingStatusResponse,
    OnboardingStepPayload,
)
from app.modules.onboarding.services.onboarding_service import OnboardingService

router = APIRouter()
service = OnboardingService()


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's onboarding progress."""
    progress = service.get_status(db, current_user)
    return OnboardingStatusResponse(
        user_id=progress.user_id,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps or [],
        step_data=progress.step_data or {},
        is_complete=progress.is_complete,
        created_at=progress.created_at,
        updated_at=progress.updated_at,
    )


@router.post("/start", response_model=OnboardingStatusResponse)
async def start_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Initialize onboarding for the authenticated user."""
    progress = service.get_or_create(db, current_user)
    return OnboardingStatusResponse(
        user_id=progress.user_id,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps or [],
        step_data=progress.step_data or {},
        is_complete=progress.is_complete,
        created_at=progress.created_at,
        updated_at=progress.updated_at,
    )


@router.patch("/step", response_model=OnboardingStatusResponse)
async def save_onboarding_step(
    payload: OnboardingStepPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save data for an onboarding step and advance progress."""
    progress = service.save_step(db, current_user, payload.step, payload.data)
    return OnboardingStatusResponse(
        user_id=progress.user_id,
        current_step=progress.current_step,
        completed_steps=progress.completed_steps or [],
        step_data=progress.step_data or {},
        is_complete=progress.is_complete,
        created_at=progress.created_at,
        updated_at=progress.updated_at,
    )


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Finalize onboarding and sync data to the candidate profile."""
    profile = service.complete(db, current_user)
    return OnboardingCompleteResponse(
        message="Onboarding complete. Your profile is ready for matching.",
        profile_id=profile.id,
    )

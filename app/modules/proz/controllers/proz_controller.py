from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.services.auth_service import auth_service, get_current_user, get_current_superuser
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile, Specialty
from app.modules.proz.schemas.proz import ProzProfileCreate, ProzProfileResponse, ProzProfileUpdate
from app.modules.proz.services.proz_service import ProzService

router = APIRouter()
# Get auth service for user authentication
# auth_service = AuthService()  # Using global instance

@router.post("/register", response_model=ProzProfileResponse, status_code=status.HTTP_201_CREATED)
async def register_profile(
    profile_data: ProzProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Register a candidate profile linked to the authenticated user.
    """
    existing_profile = (
        db.query(ProzProfile)
        .filter(
            (ProzProfile.user_id == current_user.id) | (ProzProfile.email == profile_data.email)
        )
        .first()
    )
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A profile already exists for this user or email",
        )

    profile = ProzProfile(
        user_id=current_user.id,
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        email=profile_data.email,
        phone_number=profile_data.phone_number,
        bio=profile_data.bio,
        location=profile_data.location,
        years_experience=profile_data.years_experience,
        hourly_rate=profile_data.hourly_rate,
        availability=profile_data.availability,
        experience_level=profile_data.experience_level,
        work_types=profile_data.work_types,
        skills=profile_data.skills,
        portfolio_links=profile_data.portfolio_links,
        skill_verification_status=profile_data.skill_verification_status or "not_started",
        onboarding_completed=profile_data.onboarding_completed or False,
        predicted_success_score=profile_data.predicted_success_score,
        education=profile_data.education,
        certifications=profile_data.certifications,
        website=profile_data.website,
        linkedin=profile_data.linkedin,
        preferred_contact_method=profile_data.preferred_contact_method,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile

@router.get("/profile", response_model=ProzProfileResponse)
async def get_own_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get your own professional profile.
    """
    profile = (
        db.query(ProzProfile)
        .filter(
            (ProzProfile.user_id == current_user.id) | (ProzProfile.email == current_user.email)
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Complete onboarding or register first.",
        )

    if not profile.user_id:
        profile.user_id = current_user.id
        db.commit()
        db.refresh(profile)

    return profile

@router.put("/profile", response_model=ProzProfileResponse)
async def update_own_profile(
    profile_data: ProzProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update your own candidate profile."""
    proz_service = ProzService()
    return proz_service.update_profile_by_email(db=db, email=current_user.email, profile_data=profile_data)

@router.patch("/profile", response_model=ProzProfileResponse)
async def patch_own_profile(
    profile_data: ProzProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Partially update your own professional profile using PATCH method.
    Only provided fields will be updated.
    """
    proz_service = ProzService()
    
    try:
        updated_profile = proz_service.update_profile_by_email(
            db=db,
            email=current_user.email,
            profile_data=profile_data
        )
        return updated_profile
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile. Please try again later."
        )
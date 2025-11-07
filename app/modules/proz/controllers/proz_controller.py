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
    db: Session = Depends(get_db)
):
    """
    Register a professional profile.
    """
    # Check if profile already exists
    existing_profile = db.query(ProzProfile).filter(ProzProfile.email == profile_data.email).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A profile with this email already exists"
        )
    
    # Create new profile
    profile = ProzProfile(
        first_name=profile_data.first_name,
        last_name=profile_data.last_name,
        email=profile_data.email,
        phone_number=profile_data.phone_number,
        bio=profile_data.bio,
        location=profile_data.location,
        years_experience=profile_data.years_experience,
        hourly_rate=profile_data.hourly_rate,
        availability=profile_data.availability
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
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found. Please register first."
        )
    
    return profile

@router.put("/profile", response_model=ProzProfileResponse)
async def update_own_profile(
    profile_data: ProzProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update your own professional profile.
    """
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found. Please register first."
        )
    
    # Update fields
    if profile_data.first_name is not None:
        profile.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        profile.last_name = profile_data.last_name
    if profile_data.phone_number is not None:
        profile.phone_number = profile_data.phone_number
    if profile_data.bio is not None:
        profile.bio = profile_data.bio
    if profile_data.location is not None:
        profile.location = profile_data.location
    if profile_data.years_experience is not None:
        profile.years_experience = profile_data.years_experience
    if profile_data.hourly_rate is not None:
        profile.hourly_rate = profile_data.hourly_rate
    if profile_data.availability is not None:
        profile.availability = profile_data.availability
    
    db.commit()
    db.refresh(profile)
    
    return profile

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
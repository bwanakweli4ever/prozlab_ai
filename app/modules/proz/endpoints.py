"""
Endpoints for Proz Profile module.
File location: app/modules/proz/endpoints.py
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.services.auth_service import AuthService
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile, VerificationStatus
from app.modules.proz.schemas.proz import ProzProfileCreate, ProzProfileResponse, ProzProfileUpdate
from app.modules.proz.routes import router

# Get auth service for user authentication
auth_service = AuthService()

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
    current_user: User = Depends(auth_service.get_current_user)
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
    current_user: User = Depends(auth_service.get_current_user)
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
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Partially update your own professional profile (PATCH).
    """
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found. Please register first."
        )
    
    # Only update fields that are provided (exclude_unset=True)
    update_data = profile_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile

# Add to app/modules/proz/endpoints.py

@router.get("/specialties", response_model=List[str])
async def get_specialties(
    db: Session = Depends(get_db)
):
    """
    Get all available specialties.
    """
    # For simplicity, return a hardcoded list of specialties for now
    specialties = [
        "Computer Repair",
        "Network Installation",
        "Web Development",
        "Mobile App Development",
        "Graphic Design",
        "IT Consulting",
        "Data Recovery",
        "Cloud Migration",
        "Cybersecurity"
    ]
    return specialties

# Add to app/modules/proz/endpoints.py

@router.patch("/admin/verify/{profile_id}", response_model=ProzProfileResponse)
async def verify_profile(
    profile_id: str,
    verification_status: VerificationStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_superuser)  # Ensure only admins can verify
):
    """
    Verify or reject a professional profile.
    """
    profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Professional profile not found"
        )
    
    profile.verification_status = verification_status
    db.commit()
    db.refresh(profile)
    
    return profile
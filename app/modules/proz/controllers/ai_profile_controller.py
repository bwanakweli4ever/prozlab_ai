from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import os
import tempfile
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.database.session import get_db
from app.modules.auth.services.auth_service import get_current_user
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile
from app.modules.proz.schemas.proz import ProzProfileUpdate, ProzProfileResponse
from app.services.ai_profile_service import AIProfileService

router = APIRouter(prefix="/ai")

@router.get("/status")
async def ai_status():
    ai = AIProfileService()
    return {"success": True, **ai.status()}

@router.post("/parse-resume")
async def parse_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        ai = AIProfileService()
        result = ai.analyze_resume(tmp_path)
        return {"success": True, **result}
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

@router.post("/apply-suggestions", response_model=ProzProfileResponse)
async def apply_suggestions(
    update: ProzProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    if not profile:
        # Create a new profile for this user using provided fields
        if not update.first_name or not update.last_name:
            # fallback from user record if names not provided
            first_name = getattr(current_user, 'first_name', None) or getattr(current_user, 'first_name', '') or ""
            last_name = getattr(current_user, 'last_name', None) or getattr(current_user, 'last_name', '') or ""
        else:
            first_name = update.first_name
            last_name = update.last_name

        if not first_name or not last_name:
            raise HTTPException(status_code=400, detail="first_name and last_name are required to create profile")

        profile = ProzProfile(
            user_id=current_user.id,
            first_name=first_name,
            last_name=last_name,
            email=current_user.email,
            phone_number=update.phone_number or None,
            bio=update.bio or None,
            location=update.location or None,
            years_experience=update.years_experience or None,
            hourly_rate=update.hourly_rate or None,
            availability=update.availability or None,
            education=update.education or None,
            certifications=update.certifications or None,
            website=update.website or None,
            linkedin=update.linkedin or None,
            preferred_contact_method=update.preferred_contact_method or None,
            profile_image_url=update.profile_image_url or None,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    # Apply provided updates
    if update.first_name is not None:
        profile.first_name = update.first_name
    if update.last_name is not None:
        profile.last_name = update.last_name
    if update.phone_number is not None:
        profile.phone_number = update.phone_number
    if update.bio is not None:
        profile.bio = update.bio
    if update.location is not None:
        profile.location = update.location
    if update.years_experience is not None:
        profile.years_experience = update.years_experience
    if update.hourly_rate is not None:
        profile.hourly_rate = update.hourly_rate
    if update.availability is not None:
        profile.availability = update.availability
    if update.education is not None:
        profile.education = update.education
    if update.certifications is not None:
        profile.certifications = update.certifications
    if update.website is not None:
        profile.website = update.website
    if update.linkedin is not None:
        profile.linkedin = update.linkedin
    if update.preferred_contact_method is not None:
        profile.preferred_contact_method = update.preferred_contact_method
    if update.profile_image_url is not None:
        profile.profile_image_url = update.profile_image_url

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/review-profile")
async def review_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Professional profile not found")
    ai = AIProfileService()
    payload = {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "phone_number": profile.phone_number,
        "location": profile.location,
        "years_experience": profile.years_experience,
        "hourly_rate": profile.hourly_rate,
        "availability": profile.availability,
        "bio": profile.bio,
        "education": profile.education,
        "certifications": profile.certifications,
        "website": profile.website,
        "linkedin": profile.linkedin,
        "preferred_contact_method": profile.preferred_contact_method,
    }
    result = ai.review_profile(payload)
    return {"success": True, **result}


class RephraseApplyRequest(BaseModel):
    fields: Optional[List[str]] = None  # which fields to auto-apply; defaults to ['bio']

@router.post("/rephrase-apply", response_model=ProzProfileResponse)
async def rephrase_and_apply(
    payload: RephraseApplyRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.query(ProzProfile).filter(ProzProfile.email == current_user.email).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Professional profile not found")

    ai = AIProfileService()
    curr = {
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "phone_number": profile.phone_number,
        "location": profile.location,
        "years_experience": profile.years_experience,
        "hourly_rate": profile.hourly_rate,
        "availability": profile.availability,
        "bio": profile.bio,
        "education": profile.education,
        "certifications": profile.certifications,
        "website": profile.website,
        "linkedin": profile.linkedin,
        "preferred_contact_method": profile.preferred_contact_method,
    }
    review = ai.review_profile(curr)
    suggested = review.get("suggested_updates", {}) if isinstance(review, dict) else {}

    to_apply = set((payload.fields if payload and payload.fields else ["bio"]))
    if "bio" in to_apply and not suggested.get("bio"):
        rephrased = review.get("rephrased_bio") if isinstance(review, dict) else None
        if isinstance(rephrased, list) and rephrased:
            suggested["bio"] = rephrased[0]

    # Apply selected fields
    if "bio" in to_apply and "bio" in suggested:
        profile.bio = suggested["bio"]
    if "location" in to_apply and "location" in suggested:
        profile.location = suggested["location"]
    if "years_experience" in to_apply and "years_experience" in suggested:
        try:
            profile.years_experience = int(suggested["years_experience"]) if suggested["years_experience"] is not None else None
        except Exception:
            pass
    if "hourly_rate" in to_apply and "hourly_rate" in suggested:
        try:
            profile.hourly_rate = float(suggested["hourly_rate"]) if suggested["hourly_rate"] is not None else None
        except Exception:
            pass
    if "availability" in to_apply and "availability" in suggested:
        profile.availability = suggested["availability"]
    if "education" in to_apply and "education" in suggested:
        profile.education = suggested["education"]
    if "certifications" in to_apply and "certifications" in suggested:
        profile.certifications = suggested["certifications"]
    if "website" in to_apply and "website" in suggested:
        profile.website = suggested["website"]
    if "linkedin" in to_apply and "linkedin" in suggested:
        profile.linkedin = suggested["linkedin"]
    if "preferred_contact_method" in to_apply and "preferred_contact_method" in suggested:
        profile.preferred_contact_method = suggested["preferred_contact_method"]

    db.commit()
    db.refresh(profile)
    return profile

class DraftProfile(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    hourly_rate: Optional[float] = None
    availability: Optional[str] = None
    bio: Optional[str] = None
    education: Optional[str] = None
    certifications: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    preferred_contact_method: Optional[str] = None

@router.post("/review-draft")
async def review_draft(
    draft: DraftProfile,
    current_user: User = Depends(get_current_user),
):
    ai = AIProfileService()
    # Merge user defaults for missing email/name to improve AI context
    payload = {
        "first_name": draft.first_name or getattr(current_user, 'first_name', None),
        "last_name": draft.last_name or getattr(current_user, 'last_name', None),
        "email": draft.email or current_user.email,
        "phone_number": draft.phone_number,
        "location": draft.location,
        "years_experience": draft.years_experience,
        "hourly_rate": draft.hourly_rate,
        "availability": draft.availability,
        "bio": draft.bio,
        "education": draft.education,
        "certifications": draft.certifications,
        "website": draft.website,
        "linkedin": draft.linkedin,
        "preferred_contact_method": draft.preferred_contact_method,
    }
    result = ai.review_profile(payload)
    return {"success": True, **result}



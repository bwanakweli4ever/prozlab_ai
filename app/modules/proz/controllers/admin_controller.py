# app/modules/proz/controllers/admin_controller.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
from datetime import datetime, timedelta
import math

from app.database.session import get_db
from app.modules.auth.services.auth_service import auth_service, get_current_user, get_current_superuser
from app.modules.auth.models.user import User
from app.modules.proz.models.proz import ProzProfile, Specialty, ProzSpecialty, Review
from app.modules.proz.services.proz_service import resolve_profile_by_identifier
from app.services.notification_service import NotificationService
from app.modules.proz.schemas.admin import (
    ProfileVerificationRequest,
    ProfileVerificationResponse,
    AdminProfileListItem,
    AdminProfileDetailResponse,
    BulkVerificationRequest,
    BulkVerificationResponse,
    VerificationStatsAdmin,
    VerificationHistoryItem,
    AdminDashboardResponse,
    ProfileSearchFiltersAdmin
)

router = APIRouter()
# auth_service = AuthService()  # Using global instance


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get admin dashboard overview with verification statistics.
    """
    # Calculate stats
    total_profiles = db.query(ProzProfile).count()
    pending_verification = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "pending"
    ).count()
    verified_profiles = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "verified"
    ).count()
    rejected_profiles = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "rejected"
    ).count()
    
    # Profiles created this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    profiles_this_week = db.query(ProzProfile).filter(
        ProzProfile.created_at >= week_ago
    ).count()
    
    # Verifications this week (profiles that changed from pending to verified/rejected)
    verifications_this_week = db.query(ProzProfile).filter(
        and_(
            ProzProfile.updated_at >= week_ago,
            ProzProfile.verification_status.in_(["verified", "rejected"])
        )
    ).count()
    
    # Average verification time (simplified - could be enhanced with history tracking)
    avg_verification_time_hours = 24.0  # Placeholder - would need verification history table
    
    # Oldest pending profile
    oldest_pending = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "pending"
    ).order_by(ProzProfile.created_at.asc()).first()
    
    pending_oldest_date = oldest_pending.created_at if oldest_pending else None

    pending_skill_reviews = db.query(ProzProfile).filter(
        ProzProfile.skill_verification_status == "pending_review"
    ).count()
    verified_skills = db.query(ProzProfile).filter(
        ProzProfile.skill_verification_status == "verified"
    ).count()
    rejected_skills = db.query(ProzProfile).filter(
        ProzProfile.skill_verification_status.in_(["rejected", "needs_revision"])
    ).count()
    
    stats = VerificationStatsAdmin(
        total_profiles=total_profiles,
        pending_verification=pending_verification,
        verified_profiles=verified_profiles,
        rejected_profiles=rejected_profiles,
        profiles_this_week=profiles_this_week,
        verifications_this_week=verifications_this_week,
        avg_verification_time_hours=avg_verification_time_hours,
        pending_oldest_date=pending_oldest_date,
        pending_skill_reviews=pending_skill_reviews,
        verified_skills=verified_skills,
        rejected_skills=rejected_skills,
    )
    
    # Recent submissions (last 10 profiles)
    recent_submissions = db.query(ProzProfile).order_by(
        desc(ProzProfile.created_at)
    ).limit(10).all()
    
    # Pending reviews (oldest first)
    pending_reviews = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "pending"
    ).order_by(ProzProfile.created_at.asc()).limit(10).all()
    
    # Recent verifications (would need history table for real implementation)
    recent_verifications = []  # Placeholder
    
    return AdminDashboardResponse(
        stats=stats,
        recent_submissions=[AdminProfileListItem.model_validate(p) for p in recent_submissions],
        pending_reviews=[AdminProfileListItem.model_validate(p) for p in pending_reviews],
        recent_verifications=recent_verifications
    )


@router.get("/profiles", response_model=dict)
async def get_profiles_for_verification(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    search: Optional[str] = Query(None, description="Search in name, email"),
    sort_by: str = Query("created_at", description="Sort by: created_at, updated_at, verification_status"),
    sort_order: str = Query("desc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get paginated list of profiles for admin verification.
    """
    # Build query
    query_obj = db.query(ProzProfile)
    
    # Apply filters
    if verification_status:
        query_obj = query_obj.filter(ProzProfile.verification_status == verification_status)
    
    if search:
        search_filter = or_(
            ProzProfile.first_name.ilike(f"%{search}%"),
            ProzProfile.last_name.ilike(f"%{search}%"),
            ProzProfile.email.ilike(f"%{search}%")
        )
        query_obj = query_obj.filter(search_filter)
    
    # Apply sorting
    sort_column = getattr(ProzProfile, sort_by, ProzProfile.created_at)
    if sort_order.lower() == "desc":
        query_obj = query_obj.order_by(sort_column.desc())
    else:
        query_obj = query_obj.order_by(sort_column.asc())
    
    # Get total count
    total_count = query_obj.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    profiles = query_obj.offset(offset).limit(page_size).all()
    
    # Calculate pagination info
    total_pages = math.ceil(total_count / page_size)
    
    return {
        "profiles": [AdminProfileListItem.model_validate(p) for p in profiles],
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }


@router.get("/profiles/{profile_id}", response_model=AdminProfileDetailResponse)
async def get_profile_for_verification(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get detailed profile information for verification review.
    """
    profile = resolve_profile_by_identifier(db, profile_id)

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )

    # Get specialties
    specialties = db.query(Specialty.name).join(ProzSpecialty).filter(
        ProzSpecialty.proz_id == profile.id
    ).all()

    # Build detailed response
    profile_data = AdminProfileDetailResponse.model_validate(profile)
    profile_data.specialties = [s.name for s in specialties]
    profile_data.verification_history = []  # Would come from history table
    
    return profile_data


@router.post("/profiles/{profile_id}/verify", response_model=ProfileVerificationResponse)
async def verify_profile(
    profile_id: str,
    request: ProfileVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Update profile verification status.
    """
    profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    old_status = profile.verification_status
    new_status = request.verification_status.value
    
    # Update profile
    profile.verification_status = new_status
    profile.updated_at = datetime.utcnow()
    
    # TODO: Store verification history in a separate table
    # verification_history = VerificationHistory(
    #     profile_id=profile.id,
    #     old_status=old_status,
    #     new_status=new_status,
    #     admin_user_id=current_user.id,
    #     admin_notes=request.admin_notes,
    #     rejection_reason=request.rejection_reason
    # )
    # db.add(verification_history)
    
    db.commit()
    db.refresh(profile)
    
    # Send notification email to user about verification status change
    # Use profile email directly since user relationship might not be loaded
    user_email = profile.email
    user_name = f"{profile.first_name} {profile.last_name}".strip() or "Professional"
    
    background_tasks.add_task(
        send_verification_notification,
        user_email,
        user_name,
        new_status,
        old_status,
        request.admin_notes,
        request.rejection_reason
    )
    
    return ProfileVerificationResponse(
        success=True,
        message=f"Profile verification status updated to {new_status}",
        profile_id=profile.id,
        old_status=old_status,
        new_status=new_status,
        admin_notes=request.admin_notes,
        updated_by=current_user.email,
        updated_at=datetime.utcnow()
    )


@router.post("/profiles/bulk-verify", response_model=BulkVerificationResponse)
async def bulk_verify_profiles(
    request: BulkVerificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Bulk update verification status for multiple profiles.
    """
    updated_count = 0
    failed_updates = []
    
    for profile_id in request.profile_ids:
        try:
            profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
            
            if profile:
                old_status = profile.verification_status
                profile.verification_status = request.verification_status.value
                profile.updated_at = datetime.utcnow()
                updated_count += 1
                
                # Queue email notification per profile update (no admin notes/rejection reason in bulk)
                user_email = profile.email
                user_name = f"{profile.first_name} {profile.last_name}".strip() or "Professional"
                background_tasks.add_task(
                    send_verification_notification,
                    user_email,
                    user_name,
                    request.verification_status.value,
                    old_status,
                    None,
                    None
                )
            else:
                failed_updates.append({
                    "profile_id": str(profile_id),
                    "error": "Profile not found"
                })
        except Exception as e:
            failed_updates.append({
                "profile_id": str(profile_id),
                "error": str(e)
            })
    
    db.commit()
    
    summary = {
        "total_requested": len(request.profile_ids),
        "successfully_updated": updated_count,
        "failed": len(failed_updates),
        "new_status": request.verification_status.value
    }
    
    return BulkVerificationResponse(
        success=updated_count > 0,
        message=f"Bulk verification completed. Updated {updated_count} profiles.",
        updated_count=updated_count,
        failed_updates=failed_updates,
        summary=summary
    )


@router.post("/profiles/{profile_id}/feature", response_model=dict)
async def toggle_profile_featured(
    profile_id: str,
    featured: bool = Query(..., description="Set featured status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Toggle profile featured status.
    """
    profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Only verified profiles can be featured
    if featured and profile.verification_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only verified profiles can be featured"
        )
    
    profile.is_featured = featured
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    
    return {
        "success": True,
        "message": f"Profile {'featured' if featured else 'unfeatured'} successfully",
        "profile_id": profile.id,
        "is_featured": profile.is_featured
    }


@router.get("/stats", response_model=VerificationStatsAdmin)
async def get_verification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Get detailed verification statistics for admin dashboard.
    """
    total_profiles = db.query(ProzProfile).count()
    pending_verification = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "pending"
    ).count()
    verified_profiles = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "verified"
    ).count()
    rejected_profiles = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "rejected"
    ).count()
    
    # This week stats
    week_ago = datetime.utcnow() - timedelta(days=7)
    profiles_this_week = db.query(ProzProfile).filter(
        ProzProfile.created_at >= week_ago
    ).count()
    verifications_this_week = db.query(ProzProfile).filter(
        and_(
            ProzProfile.updated_at >= week_ago,
            ProzProfile.verification_status.in_(["verified", "rejected"])
        )
    ).count()
    
    # Oldest pending profile
    oldest_pending = db.query(ProzProfile).filter(
        ProzProfile.verification_status == "pending"
    ).order_by(ProzProfile.created_at.asc()).first()
    
    return VerificationStatsAdmin(
        total_profiles=total_profiles,
        pending_verification=pending_verification,
        verified_profiles=verified_profiles,
        rejected_profiles=rejected_profiles,
        profiles_this_week=profiles_this_week,
        verifications_this_week=verifications_this_week,
        avg_verification_time_hours=24.0,  # Placeholder
        pending_oldest_date=oldest_pending.created_at if oldest_pending else None
    )


@router.delete("/profiles/{profile_id}", response_model=dict)
async def delete_profile(
    profile_id: str,
    reason: str = Query(..., description="Reason for deletion"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
) -> Any:
    """
    Delete a profile (admin only, for policy violations, etc.).
    """
    profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    # Store deletion info before deleting (you might want to log this)
    profile_info = {
        "profile_id": str(profile.id),
        "email": profile.email,
        "name": f"{profile.first_name} {profile.last_name}",
        "deleted_by": current_user.email,
        "deletion_reason": reason,
        "deleted_at": datetime.utcnow().isoformat()
    }
    
    # Delete related records first (due to foreign key constraints)
    db.query(ProzSpecialty).filter(ProzSpecialty.proz_id == profile.id).delete()
    db.query(Review).filter(Review.proz_id == profile.id).delete()
    
    # Delete the profile
    db.delete(profile)
    db.commit()
    
    return {
        "success": True,
        "message": "Profile deleted successfully",
        "deleted_profile": profile_info
    }


def send_verification_notification(
    user_email: str,
    user_name: str,
    new_status: str,
    old_status: str,
    admin_notes: Optional[str] = None,
    rejection_reason: Optional[str] = None
):
    """
    Send verification status change notification to user.
    """
    try:
        notification_service = NotificationService()
        
        if new_status == "verified":
            notification_service.send_profile_verification_notification(
                user_email=user_email,
                user_name=user_name,
                is_approved=True,
                admin_notes=admin_notes
            )
        elif new_status == "rejected":
            notification_service.send_profile_verification_notification(
                user_email=user_email,
                user_name=user_name,
                is_approved=False,
                admin_notes=admin_notes,
                rejection_reason=rejection_reason
            )
        else:
            # For other status changes (pending, etc.)
            notification_service.send_profile_verification_notification(
                user_email=user_email,
                user_name=user_name,
                is_approved=None,  # Status change notification
                admin_notes=admin_notes,
                new_status=new_status,
                old_status=old_status
            )
            
        print(f"✅ Profile verification email sent to {user_email}")
        
    except Exception as e:
        print(f"❌ Failed to send verification email to {user_email}: {str(e)}")


# ---- Message a professional (email + in-app notification) ----
from pydantic import BaseModel as _BaseModel, Field as _Field


class AdminMessageRequest(_BaseModel):
    subject: str = _Field(..., min_length=2, max_length=150)
    message: str = _Field(..., min_length=2, max_length=4000)
    send_email: bool = True


class AdminMessageResult(_BaseModel):
    success: bool
    emailed: bool
    message: str


def _message_email(first_name: str, subject: str, body: str) -> tuple:
    import html as _html
    from app.config.settings import settings as _settings
    app_url = getattr(_settings, "APP_URL", "https://prozlab.com").rstrip("/")
    logo = getattr(_settings, "BRAND_LOGO_URL", "") or f"{app_url}/images/prozlab-logo.png"
    paragraphs = "".join(
        f'<p style="margin:0 0 14px 0;">{_html.escape(p)}</p>' for p in body.split("\n") if p.strip()
    )
    html_body = f"""<!doctype html><html><body style="margin:0;padding:0;background:#F1F5F9;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F1F5F9;"><tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
<tr><td style="padding:0 4px 18px 4px;"><img src="{_html.escape(logo)}" alt="Prozlab" height="34" style="display:block;height:34px;width:auto;border:0;"></td></tr>
<tr><td style="background:#ffffff;border:1px solid #E2E8F0;border-radius:18px;padding:32px 36px;font:400 15px/1.65 Arial,Helvetica,sans-serif;color:#0F172A;">
<p style="margin:0 0 14px 0;">Hi {_html.escape(first_name or "there")},</p>
{paragraphs}
<p style="margin:22px 0 0 0;"><a href="{app_url}/login" style="display:inline-block;background:#4F46E5;color:#ffffff;text-decoration:none;font:700 14px/1 Arial,Helvetica,sans-serif;padding:14px 22px;border-radius:12px;">Open my dashboard</a></p>
<p style="margin:22px 0 0 0;color:#64748B;font-size:13px;">The Prozlab team &middot; reply to this email to reach us</p>
</td></tr>
<tr><td style="padding:18px 8px 0 8px;font:400 12px/1.6 Arial,Helvetica,sans-serif;color:#94A3B8;text-align:center;">Prozlab Consulting &middot; <a href="{app_url}" style="color:#64748B;">prozlab.com</a></td></tr>
</table></td></tr></table></body></html>"""
    text_body = f"Hi {first_name or 'there'},\n\n{body}\n\nOpen your dashboard: {app_url}/login\n\nThe Prozlab team (reply to this email to reach us)"
    return subject, html_body, text_body


@router.post("/profiles/{profile_id}/message", response_model=AdminMessageResult)
def message_professional(
    profile_id: str,
    payload: AdminMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """Admin only: send a professional a message. It always appears in their Notifications; by default it's emailed too."""
    import logging as _logging
    from app.modules.tasks.models.task import TaskNotification
    from app.services.email_service import EmailService

    profile = db.query(ProzProfile).filter(ProzProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    subject = payload.subject.strip()
    body = payload.message.strip()

    db.add(TaskNotification(proz_id=profile.id, title=subject[:200], message=body, notification_type="admin_message"))
    db.commit()

    emailed = False
    note = "Saved to their notifications."
    if payload.send_email:
        service = EmailService()
        if not (service.mailtrap_api_key or service.smtp_configured):
            note = "Saved to their notifications. Email isn't set up, so no email was sent."
        else:
            subj, html_body, text_body = _message_email(profile.first_name, subject, body)
            try:
                service.send_email(
                    to_email=profile.email,
                    to_name=" ".join(filter(None, [profile.first_name, profile.last_name])) or None,
                    subject=subj,
                    html_body=html_body,
                    text_body=text_body,
                )
                emailed = True
                note = f"Emailed to {profile.email} and saved to their notifications."
            except Exception as e:
                _logging.getLogger(__name__).error(f"Admin message email to {profile.email} failed: {e}")
                note = "Saved to their notifications, but the email failed to send."
    return AdminMessageResult(success=True, emailed=emailed, message=note)


class AdminProfileUpdate(_BaseModel):
    """Fields an admin may change on a professional's profile. Only fields that are sent are changed."""
    first_name: Optional[str] = _Field(None, max_length=100)
    last_name: Optional[str] = _Field(None, max_length=100)
    phone_number: Optional[str] = _Field(None, max_length=20)
    bio: Optional[str] = _Field(None, max_length=5000)
    location: Optional[str] = _Field(None, max_length=255)
    years_experience: Optional[int] = _Field(None, ge=0, le=70)
    hourly_rate: Optional[float] = _Field(None, ge=0, le=10000)
    availability: Optional[str] = _Field(None, max_length=50)
    education: Optional[str] = _Field(None, max_length=5000)
    certifications: Optional[str] = _Field(None, max_length=5000)
    website: Optional[str] = _Field(None, max_length=255)
    linkedin: Optional[str] = _Field(None, max_length=255)
    preferred_contact_method: Optional[str] = _Field(None, max_length=50)
    skills: Optional[List[str]] = None
    verification_status: Optional[str] = _Field(None, pattern="^(pending|verified|rejected)$")
    is_featured: Optional[bool] = None


_ADMIN_TEXT_FIELDS = (
    "phone_number", "bio", "location", "availability", "education", "certifications",
    "website", "linkedin", "preferred_contact_method",
)


@router.put("/profiles/{profile_id}", response_model=AdminProfileDetailResponse)
def admin_update_profile(
    profile_id: str,
    payload: AdminProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """Admin only: edit a professional's profile. Only verified profiles can be featured."""
    profile = resolve_profile_by_identifier(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    changes = payload.model_dump(exclude_unset=True)

    for name_field in ("first_name", "last_name"):
        if name_field in changes:
            value = (changes[name_field] or "").strip()
            if not value:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="First and last name are required")
            changes[name_field] = value

    for field in _ADMIN_TEXT_FIELDS:
        if field in changes and isinstance(changes[field], str):
            changes[field] = changes[field].strip() or None

    if "skills" in changes and changes["skills"] is not None:
        seen, cleaned = set(), []
        for skill in changes["skills"]:
            text = str(skill).strip()[:60]
            if text and text.lower() not in seen:
                seen.add(text.lower())
                cleaned.append(text)
        changes["skills"] = cleaned[:40]

    new_status = changes.get("verification_status", profile.verification_status)
    if changes.get("is_featured") and new_status != "verified":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only verified profiles can be featured")
    if new_status != "verified":
        # A profile that is no longer verified drops off the public /proz page
        changes["is_featured"] = False

    for field, value in changes.items():
        setattr(profile, field, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)

    specialties = db.query(Specialty.name).join(ProzSpecialty).filter(ProzSpecialty.proz_id == profile.id).all()
    detail = AdminProfileDetailResponse.model_validate(profile)
    detail.specialties = [s.name for s in specialties]
    return detail

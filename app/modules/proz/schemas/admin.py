# app/modules/proz/schemas/admin.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
from enum import Enum


class VerificationAction(str, Enum):
    APPROVE = "verified"
    REJECT = "rejected"
    PENDING = "pending"


class ProfileVerificationRequest(BaseModel):
    """Request to update profile verification status"""
    verification_status: VerificationAction
    admin_notes: Optional[str] = Field(None, description="Admin notes for the verification decision")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection (if applicable)")


class ProfileVerificationResponse(BaseModel):
    """Response after updating verification status"""
    success: bool
    message: str
    profile_id: uuid.UUID
    old_status: str
    new_status: str
    admin_notes: Optional[str] = None
    updated_by: str
    updated_at: datetime


class AdminProfileListItem(BaseModel):
    """Profile item for admin list view"""
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    profile_image_url: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    verification_status: str
    is_featured: bool
    rating: float
    review_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AdminProfileDetailResponse(BaseModel):
    """Detailed profile view for admin verification"""
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    hourly_rate: Optional[float] = None
    availability: Optional[str] = None
    education: Optional[str] = None
    certifications: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    verification_status: str
    is_featured: bool
    rating: float
    review_count: int
    email_verified: bool
    specialties: List[str] = []
    verification_history: List[dict] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BulkVerificationRequest(BaseModel):
    """Request to bulk update verification status"""
    profile_ids: List[uuid.UUID] = Field(..., description="List of profile IDs to update")
    verification_status: VerificationAction
    admin_notes: Optional[str] = None


class BulkVerificationResponse(BaseModel):
    """Response for bulk verification update"""
    success: bool
    message: str
    updated_count: int
    failed_updates: List[dict] = []
    summary: dict


class VerificationStatsAdmin(BaseModel):
    """Admin verification statistics"""
    total_profiles: int
    pending_verification: int
    verified_profiles: int
    rejected_profiles: int
    profiles_this_week: int
    verifications_this_week: int
    avg_verification_time_hours: float
    pending_oldest_date: Optional[datetime] = None


class VerificationHistoryItem(BaseModel):
    """Verification history entry"""
    id: uuid.UUID
    profile_id: uuid.UUID
    old_status: str
    new_status: str
    admin_user_id: Optional[str] = None
    admin_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AdminDashboardResponse(BaseModel):
    """Admin dashboard overview"""
    stats: VerificationStatsAdmin
    recent_submissions: List[AdminProfileListItem]
    pending_reviews: List[AdminProfileListItem]
    recent_verifications: List[VerificationHistoryItem]


class ProfileSearchFiltersAdmin(BaseModel):
    """Advanced search filters for admin"""
    verification_status: Optional[str] = None
    is_featured: Optional[bool] = None
    email_verified: Optional[bool] = None
    has_profile_image: Optional[bool] = None
    min_rating: Optional[float] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    location: Optional[str] = None
    specialty: Optional[str] = None
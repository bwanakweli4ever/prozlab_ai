# app/modules/proz/schemas/public.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class PublicProzProfileResponse(BaseModel):
    """Public profile response - only shows public information"""
    id: uuid.UUID
    first_name: str
    last_name: str
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
    verification_status: str
    is_featured: bool
    rating: float
    review_count: int
    specialties: List[str] = []
    created_at: datetime
    
    class Config:
        from_attributes = True


class PublicProzProfileCard(BaseModel):
    """Compact profile card for listings"""
    id: uuid.UUID
    first_name: str
    last_name: str
    profile_image_url: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    hourly_rate: Optional[float] = None
    availability: Optional[str] = None
    verification_status: str
    is_featured: bool
    rating: float
    review_count: int
    specialties: List[str] = []
    
    class Config:
        from_attributes = True


class PublicReviewResponse(BaseModel):
    """Public review response"""
    id: uuid.UUID
    client_name: str
    rating: int
    review_text: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PublicProzProfileWithReviews(PublicProzProfileResponse):
    """Full profile with reviews"""
    reviews: List[PublicReviewResponse] = []


class ProfileSearchRequest(BaseModel):
    """Search filters for profiles"""
    query: Optional[str] = Field(None, description="Search in name, bio, location")
    location: Optional[str] = None
    specialty: Optional[str] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_hourly_rate: Optional[float] = Field(None, ge=0)
    min_experience: Optional[int] = Field(None, ge=0)
    availability: Optional[str] = None
    is_featured: Optional[bool] = None
    verification_status: Optional[str] = Field(None, description="verified, pending, rejected")
    show_unverified: Optional[bool] = Field(False, description="Include unverified profiles")


class ProfileSearchResponse(BaseModel):
    """Search results response"""
    profiles: List[PublicProzProfileCard]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters_applied: ProfileSearchRequest


class FeaturedProfilesResponse(BaseModel):
    """Featured profiles response"""
    featured_profiles: List[PublicProzProfileCard]
    total_featured: int


class ProfileCategoriesResponse(BaseModel):
    """Available categories and filters"""
    specialties: List[str]
    locations: List[str]
    availability_options: List[str]
    experience_ranges: List[dict]
    rating_ranges: List[dict]


class ProfileStatsResponse(BaseModel):
    """Public statistics"""
    total_profiles: int
    verified_profiles: int
    pending_profiles: int
    rejected_profiles: int
    featured_profiles: int
    specialties_count: int
    average_rating: float
    locations_count: int


class VerificationStatusInfo(BaseModel):
    """Verification status information"""
    status: str
    label: str
    description: str
    badge_color: str
    show_publicly: bool


class VerificationStatsResponse(BaseModel):
    """Verification statistics for admin/public view"""
    verification_statuses: List[VerificationStatusInfo]
    stats_by_status: dict
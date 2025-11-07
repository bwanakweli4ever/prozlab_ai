# app/modules/proz/schemas/files.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None


class ProfileImageUpdateRequest(BaseModel):
    """For updating profile image via URL (if using external storage)"""
    image_url: str = Field(..., description="URL of the uploaded image")


class ProfileImageResponse(BaseModel):
    success: bool
    message: str
    profile_image_url: Optional[str] = None


class FileInfo(BaseModel):
    original_name: str
    saved_name: str
    file_path: str
    file_url: str
    file_size: int
    mime_type: str
    uploaded_at: datetime


# Update the existing ProzProfileResponse to include image info
class ProzProfileResponseWithImage(BaseModel):
    id: str
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
    created_at: datetime
    
    class Config:
        from_attributes = True
# app/modules/proz/schemas/proz.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from datetime import datetime
import uuid
import enum


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ProzProfileBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
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


class ProzProfileCreate(ProzProfileBase):
    pass


class ProzProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
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
    profile_image_url: Optional[str] = None
    
    # Validation for numeric fields
    @field_validator('years_experience')
    @classmethod
    def validate_years_experience(cls, v):
        if v is not None and v < 0:
            raise ValueError('Years of experience cannot be negative')
        return v
    
    @field_validator('hourly_rate')
    @classmethod
    def validate_hourly_rate(cls, v):
        if v is not None and v < 0:
            raise ValueError('Hourly rate cannot be negative')
        return v
    
    @field_validator('availability')
    @classmethod
    def validate_availability(cls, v):
        if v is not None and v not in ['full-time', 'part-time', 'contract', 'freelance']:
            raise ValueError('Availability must be one of: full-time, part-time, contract, freelance')
        return v
    
    @field_validator('preferred_contact_method')
    @classmethod
    def validate_contact_method(cls, v):
        if v is not None and v not in ['email', 'phone', 'linkedin', 'website']:
            raise ValueError('Preferred contact method must be one of: email, phone, linkedin, website')
        return v


class ProzProfileResponse(ProzProfileBase):
    id: uuid.UUID  # Change from str to uuid.UUID
    user_id: Optional[uuid.UUID] = None  # Add user_id field
    profile_image_url: Optional[str] = None
    verification_status: str = "pending"  # Changed from enum to str for simplicity
    is_featured: bool = False
    rating: float = 0.0
    review_count: int = 0
    email_verified: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
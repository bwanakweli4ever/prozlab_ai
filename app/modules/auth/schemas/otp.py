# app/modules/auth/schemas/otp.py
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class OTPPurpose(str, Enum):
    """OTP purpose enumeration"""
    PHONE_VERIFICATION = "phone_verification"
    PASSWORD_RESET = "password_reset"
    LOGIN_VERIFICATION = "login_verification"
    PROFILE_UPDATE = "profile_update"


class OTPRequest(BaseModel):
    """Schema for OTP request"""
    phone_number: str = Field(..., description="Phone number in international format (+1234567890)")
    purpose: OTPPurpose = Field(default=OTPPurpose.PHONE_VERIFICATION, description="Purpose of OTP")
    
    class Config:
        json_encoders = {
            OTPPurpose: lambda v: v.value
        }


class OTPVerification(BaseModel):
    """Schema for OTP verification"""
    phone_number: str = Field(..., description="Phone number in international format")
    otp_code: str = Field(..., min_length=4, max_length=8, description="OTP code")
    purpose: OTPPurpose = Field(default=OTPPurpose.PHONE_VERIFICATION, description="Purpose of OTP")
    
    class Config:
        json_encoders = {
            OTPPurpose: lambda v: v.value
        }


class OTPResponse(BaseModel):
    """Schema for OTP response"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    expires_at: Optional[str] = Field(None, description="OTP expiration time")
    attempts_remaining: Optional[int] = Field(None, description="Number of attempts remaining")
    
    
class OTPStatus(BaseModel):
    """Schema for OTP status"""
    phone_number: str
    is_verified: bool
    attempts_used: int
    max_attempts: int
    expires_at: Optional[str] = None
    created_at: str
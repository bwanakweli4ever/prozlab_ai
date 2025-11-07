# app/modules/auth/schemas/email.py - COMPLETE VERSION
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class EmailVerificationRequest(BaseModel):
    """Schema for email verification request"""
    email: EmailStr = Field(..., description="Email address to verify")


class EmailVerifyTokenRequest(BaseModel):
    """Schema for email token verification request"""
    token: str = Field(..., min_length=1, description="Verification token")


class EmailResendRequest(BaseModel):
    """Schema for resending email verification"""
    email: Optional[EmailStr] = Field(None, description="Email address (optional if user is authenticated)")


class EmailVerificationResponse(BaseModel):
    """Schema for email verification response"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    token: Optional[str] = Field(None, description="Verification token (if applicable)")
    expires_at: Optional[str] = Field(None, description="Token expiration time")
    email: Optional[str] = Field(None, description="Email address that was processed")


class EmailVerificationStatus(BaseModel):
    """Schema for email verification status"""
    email: EmailStr
    is_verified: bool
    verification_sent_at: Optional[str] = None
    verified_at: Optional[str] = None
    token_expires_at: Optional[str] = None


class EmailServiceStatus(BaseModel):
    """Schema for email service status"""
    service: str
    status: str
    provider: str
    message: str
    smtp_configured: Optional[bool] = None
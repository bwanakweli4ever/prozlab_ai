# app/modules/auth/schemas/password_reset.py
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr = Field(..., description="Email address to send reset OTP to")


class VerifyOTPRequest(BaseModel):
    """Schema for OTP verification request"""
    email: EmailStr = Field(..., description="Email address")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class ResetPasswordWithOTPRequest(BaseModel):
    """Schema for reset password with OTP request"""
    email: EmailStr = Field(..., description="Email address")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

    @field_validator('otp_code')
    @classmethod
    def validate_otp_format(cls, v):
        if not v.isdigit():
            raise ValueError('OTP code must contain only digits')
        if len(v) != 6:
            raise ValueError('OTP code must be exactly 6 digits')
        return v

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    @field_validator('confirm_password')
    @classmethod
    def validate_passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


# Legacy token-based schemas (kept for backward compatibility)
class ResetPasswordRequest(BaseModel):
    """Schema for reset password request (legacy token-based)"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

    @field_validator('new_password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

    @field_validator('confirm_password')
    @classmethod
    def validate_passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


class PasswordResetResponse(BaseModel):
    """Schema for password reset response"""
    success: bool
    message: str
    error_code: Optional[str] = None


class ForgotPasswordResponse(BaseModel):
    """Schema for forgot password response"""
    success: bool
    message: str
    error_code: Optional[str] = None
    development_mode: Optional[bool] = None
    otp_code: Optional[str] = None  # Only returned in development mode
    expires_at: Optional[str] = None  # OTP expiration time


class VerifyOTPResponse(BaseModel):
    """Schema for OTP verification response"""
    success: bool
    message: str
    error_code: Optional[str] = None
    attempts_remaining: Optional[int] = None
    email: Optional[str] = None
    user_id: Optional[str] = None


class PasswordResetTokenResponse(BaseModel):
    """Schema for password reset token response"""
    id: str
    user_id: str
    token: str
    is_used: bool
    expires_at: datetime
    created_at: datetime
    used_at: Optional[datetime] = None
    is_expired: bool
    is_valid: bool

    model_config = {"from_attributes": True}

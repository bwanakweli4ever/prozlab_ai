# app/modules/auth/schemas/__init__.py
from .user import User, UserCreate, UserUpdate, Token, TokenPayload, UserLogin
from .otp import OTPRequest, OTPVerification, OTPResponse, OTPStatus, OTPPurpose
from .email import EmailVerificationRequest, EmailVerificationResponse
from .password_reset import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PasswordResetResponse,
    ForgotPasswordResponse,
    PasswordResetTokenResponse
)

__all__ = [
    "User", "UserCreate", "UserUpdate", "Token", "TokenPayload", "UserLogin",
    "OTPRequest", "OTPVerification", "OTPResponse", "OTPStatus", "OTPPurpose",
    "EmailVerificationRequest", "EmailVerificationResponse",
    "ForgotPasswordRequest", "ResetPasswordRequest", "PasswordResetResponse",
    "ForgotPasswordResponse", "PasswordResetTokenResponse"
]

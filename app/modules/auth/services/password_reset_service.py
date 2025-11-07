# app/modules/auth/services/password_reset_service.py
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import logging

from app.modules.auth.models.user import User
from app.modules.auth.models.password_reset import PasswordResetToken
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.repositories.password_reset_repository import PasswordResetRepository
from app.modules.auth.services.otp_service import OTPService
from app.core.security import get_password_hash, verify_password
from app.services.email_service import EmailService
from app.core.exceptions import NotFoundException, AuthenticationException

logger = logging.getLogger(__name__)


class PasswordResetService:
    def __init__(self):
        self.user_repository = UserRepository()
        self.password_reset_repository = PasswordResetRepository()
        self.otp_service = OTPService()
        self.email_service = EmailService()
    
    def _create_reset_email(self, email: str, token: str, user_name: str = None) -> tuple:
        """Create password reset email content"""
        # Create reset URL
        reset_url = f"http://localhost:8000/api/v1/auth/password/reset?token={token}"
        
        # Email subject
        subject = "Reset Your Password"
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #dc3545;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #dc3545;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #666;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <h2>Reset Your Password</h2>
                <p>Hello{' ' + user_name if user_name else ''},</p>
                <p>We received a request to reset your password. Click the button below to reset it:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #fff; padding: 10px; border-radius: 3px;">
                    {reset_url}
                </p>
                
                <div class="warning">
                    <strong>Important:</strong>
                    <ul>
                        <li>This link will expire in 1 hour</li>
                        <li>If you didn't request this password reset, please ignore this email</li>
                        <li>Your password will remain unchanged until you create a new one</li>
                    </ul>
                </div>
                
                <p>If you didn't request a password reset, you can safely ignore this email.</p>
            </div>
            <div class="footer">
                <p>This email was sent from your account security system</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
        Password Reset Request
        
        Hello{' ' + user_name if user_name else ''},
        
        We received a request to reset your password. Please visit this link to reset it:
        {reset_url}
        
        Important:
        - This link will expire in 1 hour
        - If you didn't request this password reset, please ignore this email
        - Your password will remain unchanged until you create a new one
        
        If you didn't request a password reset, you can safely ignore this email.
        
        Best regards,
        Your Account Security Team
        """
        
        return subject, html_body, text_body
    
    def send_reset_otp(self, db: Session, email: str) -> Dict[str, Any]:
        """Send password reset OTP via email"""
        try:
            # Check if user exists
            user = self.user_repository.get_by_email(db, email)
            if not user:
                # Don't reveal if email exists or not for security
                return {
                    "success": True,
                    "message": "If an account with that email exists, a password reset OTP has been sent.",
                    "development_mode": self.email_service.development_mode
                }
            
            # Check if user is active
            if not user.is_active:
                return {
                    "success": False,
                    "message": "Account is inactive. Please contact support.",
                    "error_code": "ACCOUNT_INACTIVE"
                }
            
            # Send OTP via email
            result = self.otp_service.send_password_reset_otp(db, email)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "development_mode": result.get("development_mode"),
                    "otp_code": result.get("otp_code"),
                    "expires_at": result.get("expires_at")
                }
            else:
                return {
                    "success": False,
                    "message": result["message"],
                    "error_code": result.get("error_code"),
                    "error_details": result.get("error_details")
                }
            
        except Exception as e:
            logger.error(f"Error sending password reset OTP to {email}: {str(e)}")
            return {
                "success": False,
                "message": "Failed to send password reset OTP",
                "error_code": "OTP_SEND_FAILED",
                "error_details": str(e)
            }
    
    def reset_password_with_otp(self, db: Session, email: str, otp_code: str, new_password: str) -> Dict[str, Any]:
        """Reset password using OTP"""
        try:
            # Verify OTP first
            otp_result = self.otp_service.verify_password_reset_otp(db, email, otp_code)
            if not otp_result["success"]:
                return {
                    "success": False,
                    "message": otp_result["message"],
                    "error_code": otp_result.get("error_code"),
                    "attempts_remaining": otp_result.get("attempts_remaining")
                }
            
            # Get user
            user = self.user_repository.get_by_email(db, email)
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error_code": "USER_NOT_FOUND"
                }
            
            # Check if user is active
            if not user.is_active:
                return {
                    "success": False,
                    "message": "Account is inactive",
                    "error_code": "ACCOUNT_INACTIVE"
                }
            
            # Hash new password
            hashed_password = get_password_hash(new_password)
            
            # Update user password
            user.hashed_password = hashed_password
            db.commit()
            
            # Clean up all OTPs for this email
            self.otp_service.password_reset_otp_repo.delete_otps_for_email(db, email)
            
            logger.info(f"✅ Password reset successful for user: {user.email}")
            
            return {
                "success": True,
                "message": "Password reset successfully",
                "user_id": str(user.id),
                "email": user.email
            }
            
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "message": "Failed to reset password",
                "error_code": "RESET_FAILED",
                "error_details": str(e)
            }
    
    def verify_reset_otp(self, db: Session, email: str, otp_code: str) -> Dict[str, Any]:
        """Verify password reset OTP without resetting password"""
        try:
            result = self.otp_service.verify_password_reset_otp(db, email, otp_code)
            
            if result["success"]:
                # Get user info
                user = self.user_repository.get_by_email(db, email)
                if user:
                    return {
                        "success": True,
                        "message": "OTP verified successfully",
                        "email": email,
                        "user_id": str(user.id)
                    }
                else:
                    return {
                        "success": False,
                        "message": "User not found",
                        "error_code": "USER_NOT_FOUND"
                    }
            else:
                return {
                    "success": False,
                    "message": result["message"],
                    "error_code": result.get("error_code"),
                    "attempts_remaining": result.get("attempts_remaining")
                }
                
        except Exception as e:
            logger.error(f"Error verifying reset OTP: {str(e)}")
            return {
                "success": False,
                "message": "Failed to verify OTP",
                "error_code": "VERIFICATION_FAILED",
                "error_details": str(e)
            }
    
    def validate_reset_token(self, db: Session, token: str) -> Dict[str, Any]:
        """Validate a password reset token"""
        try:
            token_obj = self.password_reset_repository.get_by_token(db, token)
            if not token_obj:
                return {
                    "success": False,
                    "message": "Invalid reset token",
                    "error_code": "INVALID_TOKEN"
                }
            
            if not token_obj.is_valid:
                if token_obj.is_used:
                    return {
                        "success": False,
                        "message": "Reset token has already been used",
                        "error_code": "TOKEN_USED"
                    }
                elif token_obj.is_expired:
                    return {
                        "success": False,
                        "message": "Reset token has expired",
                        "error_code": "TOKEN_EXPIRED"
                    }
            
            # Get user info
            user = self.user_repository.get_by_id(db, str(token_obj.user_id))
            if not user:
                return {
                    "success": False,
                    "message": "User not found",
                    "error_code": "USER_NOT_FOUND"
                }
            
            return {
                "success": True,
                "message": "Token is valid",
                "user_id": str(user.id),
                "email": user.email,
                "expires_at": token_obj.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating reset token: {str(e)}")
            return {
                "success": False,
                "message": "Failed to validate token",
                "error_code": "VALIDATION_FAILED",
                "error_details": str(e)
            }

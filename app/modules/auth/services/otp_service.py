# app/modules/auth/services/otp_service.py
from typing import Dict, Any
from sqlalchemy.orm import Session
import random
import string
from datetime import datetime, timedelta
import logging

from app.modules.auth.repositories.password_reset_otp_repository import PasswordResetOTPRepository
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class OTPService:
    """OTP service for phone and email verification"""
    
    def __init__(self):
        # In-memory storage for development (use Redis/database in production)
        self.otp_storage = {}
        self.password_reset_otp_repo = PasswordResetOTPRepository()
        self.email_service = EmailService()
        
    def get_service_status(self) -> Dict[str, Any]:
        """Get OTP service status"""
        return {
            "service": "OTP Service",
            "status": "active",
            "provider": "development",
            "message": "OTP service is running in development mode"
        }
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    def send_otp(self, db: Session, phone_number: str, purpose: str = "phone_verification") -> Dict[str, Any]:
        """Send OTP to phone number (simulated for development)"""
        try:
            # Generate OTP
            otp_code = self.generate_otp()
            expires_at = datetime.utcnow() + timedelta(minutes=5)
            
            # Store OTP (in production, use Redis or database)
            self.otp_storage[phone_number] = {
                "code": otp_code,
                "purpose": purpose,
                "expires_at": expires_at,
                "attempts": 0,
                "max_attempts": 3
            }
            
            # In development, just log the OTP (in production, send SMS)
            print(f"🔐 OTP for {phone_number}: {otp_code} (expires in 5 minutes)")
            
            return {
                "success": True,
                "message": f"OTP sent to {phone_number}",
                "expires_at": expires_at.isoformat(),
                "attempts_remaining": 3
            }
            
        except Exception as e:
            print(f"Error sending OTP: {str(e)}")
            return {
                "success": False,
                "message": "Failed to send OTP"
            }
    
    def verify_otp(self, db: Session, phone_number: str, otp_code: str, purpose: str = "phone_verification") -> Dict[str, Any]:
        """Verify OTP code"""
        try:
            stored_otp = self.otp_storage.get(phone_number)
            
            if not stored_otp:
                return {
                    "success": False,
                    "message": "No OTP found for this phone number"
                }
            
            # Check if OTP expired
            if datetime.utcnow() > stored_otp["expires_at"]:
                del self.otp_storage[phone_number]
                return {
                    "success": False,
                    "message": "OTP has expired"
                }
            
            # Check attempts
            if stored_otp["attempts"] >= stored_otp["max_attempts"]:
                del self.otp_storage[phone_number]
                return {
                    "success": False,
                    "message": "Maximum attempts exceeded"
                }
            
            # Verify OTP
            if stored_otp["code"] == otp_code and stored_otp["purpose"] == purpose:
                del self.otp_storage[phone_number]
                return {
                    "success": True,
                    "message": "OTP verified successfully"
                }
            else:
                # Increment attempts
                stored_otp["attempts"] += 1
                attempts_remaining = stored_otp["max_attempts"] - stored_otp["attempts"]
                
                return {
                    "success": False,
                    "message": "Invalid OTP code",
                    "attempts_remaining": attempts_remaining
                }
                
        except Exception as e:
            print(f"Error verifying OTP: {str(e)}")
            return {
                "success": False,
                "message": "Failed to verify OTP"
            }
    
    def resend_otp(self, db: Session, phone_number: str, purpose: str = "phone_verification") -> Dict[str, Any]:
        """Resend OTP"""
        # Clear existing OTP and send new one
        if phone_number in self.otp_storage:
            del self.otp_storage[phone_number]
        
        return self.send_otp(db, phone_number, purpose)
    
    def verify_and_update_profile(self, db: Session, user_id: str, phone_number: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP and update user profile"""
        # First verify OTP
        verification_result = self.verify_otp(db, phone_number, otp_code, "phone_verification")
        
        if not verification_result["success"]:
            return verification_result
        
        # TODO: Update user profile with verified phone number
        # This would typically update the user's phone number in the database
        print(f"📱 Phone number {phone_number} verified for user {user_id}")
        
        return {
            "success": True,
            "message": "Phone number verified and profile updated"
        }
    
    def send_password_reset_otp(self, db: Session, email: str) -> Dict[str, Any]:
        """Send password reset OTP via email"""
        try:
            # Create OTP in database
            otp_obj = self.password_reset_otp_repo.create(db, email, expires_in_minutes=10)
            if not otp_obj:
                return {
                    "success": False,
                    "message": "Failed to create OTP. Please try again.",
                    "error_code": "OTP_CREATION_FAILED"
                }
            
            # Create email content
            subject, html_body, text_body = self._create_password_reset_otp_email(email, otp_obj.otp_code)
            
            # If Mailtrap or SMTP is configured, send email; otherwise log in dev mode
            if self.email_service.mailtrap_api_key:
                self.email_service._send_mailtrap_email(
                    to_email=email,
                    to_name=email,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                )
                message = "Password reset OTP sent successfully"
            elif self.email_service.smtp_configured and not self.email_service.development_mode:
                self.email_service._send_smtp_email(email, subject, html_body, text_body)
                message = "Password reset OTP sent successfully"
            else:
                # Development fallback
                logger.info(f"🔐 DEVELOPMENT MODE - Password reset OTP for {email}: {otp_obj.otp_code}")
                print(f"🔐 DEVELOPMENT MODE - Password reset OTP for {email}: {otp_obj.otp_code}")
                message = "Password reset OTP sent (development mode). Check console for OTP."
            
            return {
                "success": True,
                "message": message,
                "development_mode": self.email_service.development_mode,
                "otp_code": otp_obj.otp_code if self.email_service.development_mode else None,
                "expires_at": otp_obj.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending password reset OTP to {email}: {str(e)}")
            return {
                "success": False,
                "message": "Failed to send password reset OTP",
                "error_code": "OTP_SEND_FAILED",
                "error_details": str(e)
            }
    
    def verify_password_reset_otp(self, db: Session, email: str, otp_code: str) -> Dict[str, Any]:
        """Verify password reset OTP"""
        try:
            # Get OTP from database
            otp_obj = self.password_reset_otp_repo.get_by_email_and_code(db, email, otp_code)
            if not otp_obj:
                return {
                    "success": False,
                    "message": "Invalid OTP code",
                    "error_code": "INVALID_OTP"
                }
            
            # Check if OTP is valid
            if not otp_obj.is_valid:
                if otp_obj.is_verified:
                    return {
                        "success": False,
                        "message": "OTP has already been used",
                        "error_code": "OTP_USED"
                    }
                elif otp_obj.is_expired:
                    return {
                        "success": False,
                        "message": "OTP has expired",
                        "error_code": "OTP_EXPIRED"
                    }
            
            # Check attempts
            if otp_obj.attempts >= 3:
                return {
                    "success": False,
                    "message": "Maximum attempts exceeded",
                    "error_code": "MAX_ATTEMPTS_EXCEEDED"
                }
            
            # Verify OTP
            if otp_obj.otp_code == otp_code:
                # Mark as verified
                self.password_reset_otp_repo.mark_as_verified(db, email, otp_code)
                
                # Clean up expired OTPs
                self.password_reset_otp_repo.delete_expired_otps(db)
                
                return {
                    "success": True,
                    "message": "OTP verified successfully",
                    "email": email
                }
            else:
                # Increment attempts
                self.password_reset_otp_repo.increment_attempts(db, email, otp_code)
                attempts_remaining = 3 - (otp_obj.attempts + 1)
                
                return {
                    "success": False,
                    "message": "Invalid OTP code",
                    "error_code": "INVALID_OTP",
                    "attempts_remaining": max(0, attempts_remaining)
                }
                
        except Exception as e:
            logger.error(f"Error verifying password reset OTP: {str(e)}")
            return {
                "success": False,
                "message": "Failed to verify OTP",
                "error_code": "VERIFICATION_FAILED",
                "error_details": str(e)
            }
    
    def _create_password_reset_otp_email(self, email: str, otp_code: str) -> tuple:
        """Create password reset OTP email content"""
        # Email subject
        subject = "Password Reset OTP"
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset OTP</title>
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
                .otp-code {{
                    background-color: #fff;
                    border: 2px solid #dc3545;
                    color: #dc3545;
                    font-size: 32px;
                    font-weight: bold;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin: 20px 0;
                    letter-spacing: 5px;
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
                <h1>Password Reset OTP</h1>
            </div>
            <div class="content">
                <h2>Your Password Reset Code</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password. Use the following code to reset your password:</p>
                
                <div class="otp-code">{otp_code}</div>
                
                <div class="warning">
                    <strong>Important:</strong>
                    <ul>
                        <li>This code will expire in 10 minutes</li>
                        <li>If you didn't request this password reset, please ignore this email</li>
                        <li>Do not share this code with anyone</li>
                        <li>You have 3 attempts to enter the correct code</li>
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
        Password Reset OTP
        
        Hello,
        
        We received a request to reset your password. Use the following code to reset your password:
        
        {otp_code}
        
        Important:
        - This code will expire in 10 minutes
        - If you didn't request this password reset, please ignore this email
        - Do not share this code with anyone
        - You have 3 attempts to enter the correct code
        
        If you didn't request a password reset, you can safely ignore this email.
        
        Best regards,
        Your Account Security Team
        """
        
        return subject, html_body, text_body
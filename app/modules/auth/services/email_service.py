# app/services/email_service.py
import smtplib
import ssl
import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

from app.config.settings import settings

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory storage for email verification.")

# In-memory storage for development mode
email_storage = {}
rate_limit_storage = {}


class EmailService:
    def __init__(self):
        self.smtp_configured = self._check_smtp_configuration()
        self.development_mode = not self.smtp_configured
        
        # Set up storage (Redis or in-memory)
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
                self.redis_client.ping()
                self.use_redis = True
                logger.info("Redis connection established for email service")
            except Exception as e:
                logger.error(f"Redis connection failed: {str(e)}. Using in-memory storage.")
                self.redis_client = None
                self.use_redis = False
        else:
            self.redis_client = None
            self.use_redis = False
            logger.info("Using in-memory storage for email verification")
        
        if self.development_mode:
            logger.info("Email service running in DEVELOPMENT MODE")
        else:
            logger.info("Email service configured for production")
    
    def _check_smtp_configuration(self) -> bool:
        """Check if SMTP is properly configured"""
        return all([
            hasattr(settings, 'SMTP_HOST') and settings.SMTP_HOST,
            hasattr(settings, 'SMTP_PORT') and settings.SMTP_PORT,
            hasattr(settings, 'SMTP_USER') and settings.SMTP_USER,
            hasattr(settings, 'SMTP_PASSWORD') and settings.SMTP_PASSWORD,
            hasattr(settings, 'EMAIL_FROM') and settings.EMAIL_FROM
        ])
    
    def generate_verification_token(self) -> str:
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)
    
    def _get_rate_limit_key(self, email: str) -> str:
        """Get key for rate limiting"""
        return f"email_rate_limit:{email}"
    
    def _get_verification_key(self, token: str) -> str:
        """Get key for verification token storage"""
        return f"email_verification:{token}"
    
    def _store_data(self, key: str, data: dict, expire_seconds: int = None):
        """Store data in Redis or in-memory"""
        if self.use_redis:
            self.redis_client.setex(key, expire_seconds or 3600, json.dumps(data))
        else:
            # In-memory storage with expiration
            expire_at = datetime.utcnow() + timedelta(seconds=expire_seconds or 3600)
            if key.startswith("email_rate_limit:"):
                rate_limit_storage[key] = {"data": data, "expires_at": expire_at}
            else:
                email_storage[key] = {"data": data, "expires_at": expire_at}
    
    def _get_data(self, key: str) -> Optional[dict]:
        """Get data from Redis or in-memory"""
        if self.use_redis:
            data_str = self.redis_client.get(key)
            return json.loads(data_str) if data_str else None
        else:
            # In-memory storage with expiration check
            storage = rate_limit_storage if key.startswith("email_rate_limit:") else email_storage
            if key in storage:
                stored = storage[key]
                if datetime.utcnow() < stored["expires_at"]:
                    return stored["data"]
                else:
                    # Expired, remove it
                    del storage[key]
            return None
    
    def _delete_data(self, key: str):
        """Delete data from Redis or in-memory"""
        if self.use_redis:
            self.redis_client.delete(key)
        else:
            # Remove from appropriate storage
            if key.startswith("email_rate_limit:") and key in rate_limit_storage:
                del rate_limit_storage[key]
            elif key in email_storage:
                del email_storage[key]
    
    def _check_rate_limit(self, email: str) -> bool:
        """Check if email has exceeded rate limit"""
        key = self._get_rate_limit_key(email)
        data = self._get_data(key)
        
        if not data:
            return True  # No previous requests
        
        return data.get("count", 0) < 3  # Max 3 emails per hour
    
    def _increment_rate_limit(self, email: str):
        """Increment rate limit counter"""
        key = self._get_rate_limit_key(email)
        current_data = self._get_data(key) or {"count": 0}
        current_data["count"] += 1
        self._store_data(key, current_data, 3600)  # 1 hour expiry
    
    def _create_verification_email(self, email: str, token: str, user_name: str = None) -> tuple:
        """Create verification email content"""
        # Create verification URL
        verification_url = f"http://localhost:8000/api/v1/auth/email/verify?token={token}"
        
        # Email subject
        subject = f"Verify your email for {settings.PROJECT_NAME}"
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Email Verification</title>
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
                    background-color: #4CAF50;
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
                    background-color: #4CAF50;
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
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Welcome to {settings.PROJECT_NAME}</h1>
            </div>
            <div class="content">
                <h2>Verify Your Email Address</h2>
                <p>Hello{' ' + user_name if user_name else ''},</p>
                <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
                
                <div style="text-align: center;">
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background-color: #fff; padding: 10px; border-radius: 3px;">
                    {verification_url}
                </p>
                
                <p><strong>This verification link will expire in 24 hours.</strong></p>
                
                <p>If you didn't sign up for an account, you can safely ignore this email.</p>
            </div>
            <div class="footer">
                <p>This email was sent from {settings.PROJECT_NAME}</p>
                <p>Please do not reply to this email.</p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version for email clients that don't support HTML
        text_body = f"""
        Welcome to {settings.PROJECT_NAME}!
        
        Please verify your email address by visiting this link:
        {verification_url}
        
        This verification link will expire in 24 hours.
        
        If you didn't sign up for an account, you can safely ignore this email.
        
        Best regards,
        The {settings.PROJECT_NAME} Team
        """
        
        return subject, html_body, text_body
    
    def send_verification_email(self, email: str, user_name: str = None, user_id: int = None) -> Dict[str, Any]:
        """Send verification email"""
        try:
            # Check rate limiting
            if not self._check_rate_limit(email):
                return {
                    "success": False,
                    "message": "Too many verification emails sent. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                }
            
            # Generate verification token
            token = self.generate_verification_token()
            
            # Store verification data
            verification_data = {
                "email": email,
                "user_name": user_name,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                "verified": False
            }
            
            verification_key = self._get_verification_key(token)
            self._store_data(verification_key, verification_data, 24 * 3600)  # 24 hours
            
            # Create email content
            subject, html_body, text_body = self._create_verification_email(email, token, user_name)
            
            if self.development_mode:
                # Development mode - log verification link
                verification_url = f"http://localhost:8000/api/v1/auth/email/verify?token={token}"
                logger.info(f"📧 DEVELOPMENT MODE - Email verification for {email}")
                logger.info(f"🔗 Verification URL: {verification_url}")
                print(f"📧 DEVELOPMENT MODE - Email verification for {email}")
                print(f"🔗 Verification URL: {verification_url}")
                
                message = f"Verification email sent (development mode). Check console for verification link."
                
            else:
                # Production mode - send actual email
                self._send_smtp_email(email, subject, html_body, text_body)
                message = "Verification email sent successfully"
            
            # Increment rate limit
            self._increment_rate_limit(email)
            
            return {
                "success": True,
                "message": message,
                "expires_in_hours": 24,
                "development_mode": self.development_mode,
                "token": token if self.development_mode else None  # Only return token in dev mode
            }
            
        except Exception as e:
            logger.error(f"Error sending verification email to {email}: {str(e)}")
            return {
                "success": False,
                "message": "Failed to send verification email",
                "error_code": "EMAIL_SEND_FAILED",
                "error_details": str(e)
            }
    
    def _send_smtp_email(self, to_email: str, subject: str, html_body: str, text_body: str):
        """Send email via SMTP"""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings.EMAIL_FROM
        msg['To'] = to_email
        
        # Create text and HTML parts
        text_part = MIMEText(text_body, 'plain')
        html_part = MIMEText(html_body, 'html')
        
        # Add parts to message
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Create secure connection and send email
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    
    def verify_email_token(self, token: str) -> Dict[str, Any]:
        """Verify email token"""
        try:
            verification_key = self._get_verification_key(token)
            verification_data = self._get_data(verification_key)
            
            if not verification_data:
                return {
                    "success": False,
                    "message": "Invalid or expired verification token",
                    "error_code": "TOKEN_NOT_FOUND"
                }
            
            # Check if already verified
            if verification_data.get("verified"):
                return {
                    "success": False,
                    "message": "Email already verified",
                    "error_code": "ALREADY_VERIFIED"
                }
            
            # Check if expired
            expires_at = datetime.fromisoformat(verification_data["expires_at"])
            if datetime.utcnow() > expires_at:
                self._delete_data(verification_key)
                return {
                    "success": False,
                    "message": "Verification token has expired",
                    "error_code": "TOKEN_EXPIRED"
                }
            
            # Mark as verified
            verification_data["verified"] = True
            verification_data["verified_at"] = datetime.utcnow().isoformat()
            self._store_data(verification_key, verification_data, 3600)  # Keep for 1 hour after verification
            
            logger.info(f"✅ Email verified successfully: {verification_data['email']}")
            return {
                "success": True,
                "message": "Email verified successfully",
                "email_verified": True,
                "email": verification_data["email"],
                "user_id": verification_data.get("user_id")
            }
            
        except Exception as e:
            logger.error(f"Error verifying email token: {str(e)}")
            return {
                "success": False,
                "message": "An error occurred during verification",
                "error_code": "VERIFICATION_ERROR"
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get email service status"""
        return {
            "email_configured": self.smtp_configured,
            "smtp_available": self.smtp_configured,
            "redis_available": self.use_redis,
            "development_mode": self.development_mode,
            "storage_type": "redis" if self.use_redis else "in-memory",
            "rate_limiting_enabled": True,
            "templates_available": True
        }
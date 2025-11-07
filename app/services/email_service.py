# app/services/email_service.py
import smtplib
import ssl
import secrets
import json
from datetime import datetime, timedelta
import os
import http.client
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

from app.config.settings import settings

# Optional .env loader so server runs pick up root .env without process-level export
try:
    from dotenv import load_dotenv  # type: ignore
    DOTENV_AVAILABLE = True
except Exception:
    DOTENV_AVAILABLE = False

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
        # Best-effort load of .env files if Mailtrap/SMTP envs not already present
        if DOTENV_AVAILABLE:
            try:
                # Load from CWD and project root (two levels up from this file: app/services/.. -> project root)
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                load_dotenv(os.path.join(project_root, '.env'), override=False)
                load_dotenv(os.path.join(project_root, '.env.production'), override=False)
                load_dotenv(os.path.join(os.getcwd(), '.env'), override=False)
            except Exception:
                pass

        self.smtp_configured = self._check_smtp_configuration()
        
        # Mailtrap API availability (load early to compute mode)
        # Prefer settings, fall back to environment variables
        self.mailtrap_api_key = getattr(settings, 'MAILTRAP_APIKEY', None) or os.getenv('MAILTRAP_APIKEY')
        self.mailtrap_from_email = (
            getattr(settings, 'MAILTRAP_FROM_EMAIL', None)
            or os.getenv('MAILTRAP_FROM_EMAIL')
            or getattr(settings, 'EMAIL_FROM', None)
        )
        self.mailtrap_from_name = (
            getattr(settings, 'MAILTRAP_FROM_NAME', None)
            or os.getenv('MAILTRAP_FROM_NAME')
            or getattr(settings, 'PROJECT_NAME', 'ProzLab')
        )
        self.mailtrap_reply_email = getattr(settings, 'MAILTRAP_REPLY_EMAIL', None) or os.getenv('MAILTRAP_REPLY_EMAIL')
        self.mailtrap_reply_name = getattr(settings, 'MAILTRAP_REPLY_NAME', None) or os.getenv('MAILTRAP_REPLY_NAME')

        # Treat Mailtrap as production-capable as well
        self.development_mode = not (self.smtp_configured or self.mailtrap_api_key)

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
        # Dynamic Reply-To if configured via settings/env
        reply_email = getattr(self, 'mailtrap_reply_email', None)
        reply_name = getattr(self, 'mailtrap_reply_name', None)
        if reply_email:
            msg['Reply-To'] = f"{reply_name} <{reply_email}>" if reply_name else reply_email
        
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

    def _send_mailtrap_email(self, to_email: str, to_name: str, subject: str, text_body: str, html_body: Optional[str] = None, cc: Optional[list] = None, bcc: Optional[list] = None):
        """Send email using Mailtrap Send API if configured."""
        if not self.mailtrap_api_key:
            raise RuntimeError("MAILTRAP_APIKEY not configured")

        # Build payload
        payload = {
            "to": [{"email": to_email, "name": to_name or to_email}],
            "from": {
                "email": self.mailtrap_from_email,
                "name": self.mailtrap_from_name,
            },
            "subject": subject,
            "text": text_body or "",
            "category": settings.PROJECT_NAME if hasattr(settings, 'PROJECT_NAME') else "App Email",
        }

        if html_body:
            payload["html"] = html_body
        if self.mailtrap_reply_email:
            payload["reply_to"] = {"email": self.mailtrap_reply_email, "name": self.mailtrap_reply_name or self.mailtrap_reply_email}
        if cc:
            payload["cc"] = cc
        if bcc:
            payload["bcc"] = bcc

        conn = http.client.HTTPSConnection("send.api.mailtrap.io")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Api-Token': self.mailtrap_api_key,
        }
        try:
            conn.request("POST", "/api/send", json.dumps(payload), headers)
            res = conn.getresponse()
            data = res.read()
            if res.status >= 400:
                raise RuntimeError(f"Mailtrap send failed: {res.status} {data.decode('utf-8')}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def send_email_to_proz_profile(self, proz_profile, subject: str, text_body: str, html_body: Optional[str] = None) -> Dict[str, Any]:
        """Send an email to a Proz profile using Mailtrap if available, else SMTP.

        proz_profile: instance with 'email', 'first_name', 'last_name'
        """
        try:
            to_email = getattr(proz_profile, 'email', None)
            first_name = getattr(proz_profile, 'first_name', '') or ''
            last_name = getattr(proz_profile, 'last_name', '') or ''
            to_name = (first_name + ' ' + last_name).strip() or to_email

            if not to_email:
                return {"success": False, "message": "Profile has no email"}

            if self.mailtrap_api_key:
                self._send_mailtrap_email(to_email=to_email, to_name=to_name, subject=subject, text_body=text_body, html_body=html_body)
            else:
                # Fallback to SMTP (build minimal bodies)
                html_content = html_body or f"<p>{text_body}</p>"
                self._send_smtp_email(to_email=to_email, subject=subject, html_body=html_content, text_body=text_body)

            return {"success": True, "message": "Email sent"}

        except Exception as e:
            logger.error(f"Error sending email to proz profile {getattr(proz_profile, 'email', 'unknown')}: {str(e)}")
            return {"success": False, "message": "Failed to send email", "error": str(e)}

    def send_ceo_welcome_email(self, proz_profile) -> Dict[str, Any]:
        """Send 'Welcome Message from the CEO' to a newly registered user (proz profile).

        Uses Mailtrap if configured, otherwise SMTP. Safely handles missing name fields.
        """
        first_name = (getattr(proz_profile, 'first_name', '') or '').strip()
        last_name = (getattr(proz_profile, 'last_name', '') or '').strip()
        full_name = (first_name + ' ' + last_name).strip()
        to_email = getattr(proz_profile, 'email', None)

        if not to_email:
            return {"success": False, "message": "Profile has no email"}

        display_name = full_name if full_name else 'there'
        subject = "Welcome Message from the CEO"

        text_body = (
            f"Dear {display_name},\n\n"
            "On behalf of the entire Proz Lab family, I warmly welcome you into our community of passionate professionals. "
            "At Proz Lab, we are more than just a platform—we are a living lab of creativity, innovation, and purpose.\n\n"
            "We exist with a zeal to design, build, develop, and deliver excellence in technology, not only for progress "
            "but also for the greater good of the communities we serve. We believe that technology is a bridge to a better "
            "tomorrow—a tool that makes life easier, empowers people, and sparks meaningful change.\n\n"
            "As you begin your journey with us, know that you are not just joining a platform—you are becoming part of a movement. "
            "A movement driven by passion, fueled by collaboration, and inspired by the belief that together, we can shape a brighter, better world through innovation.\n\n"
            "Welcome aboard. Let’s create, let’s innovate, and let’s build change that matters.\n\n"
            "With enthusiasm and gratitude,\n"
            "Fabrice Rugogwe\n"
            "CEO, Proz Lab\n"
        )

        # Light theme, elegant layout (inline styles for email client compatibility)
        primary = getattr(settings, 'BRAND_PRIMARY_COLOR', '#1F7A8C')
        accent = getattr(settings, 'BRAND_ACCENT_COLOR', '#EC625F')
        logo = getattr(settings, 'BRAND_LOGO_URL', '')
        app_url = getattr(settings, 'APP_URL', 'https://prozlab.com')

        # Build logo/header HTML separately to avoid backslashes in f-string expressions
        if logo:
            logo_html = f'<img src="{logo}" alt="Proz Lab" style="height:32px;display:block;"/>'
        else:
            logo_html = '<div style="font-family:Arial,Helvetica,sans-serif;font-weight:700;font-size:18px;letter-spacing:.3px;">Proz Lab</div>'

        html_body = f"""
        <!doctype html>
        <html>
          <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
            <title>{subject}</title>
          </head>
          <body style="margin:0;padding:0;background:#f3f4f6;">
            <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:#f3f4f6;">
              <tr>
                <td align="center" style="padding:32px 16px;">
                  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="max-width:680px;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.08);">
                    <tr>
                      <td align="left" style="background:{primary};padding:24px 28px;color:#ffffff;">
                        {logo_html}
                        <div style="font-family:Arial,Helvetica,sans-serif;font-weight:800;font-size:22px;margin-top:8px;">Welcome to the Proz Lab community</div>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:28px;">
                        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                          <tr>
                            <td style="font-family:Arial,Helvetica,sans-serif;color:#1f2937;font-size:16px;line-height:1.8;">
                              <p style="margin:0 0 16px 0;color:#374151;">Dear {display_name},</p>
                              <p style="margin:0 0 14px 0;">On behalf of the entire <strong>Proz Lab</strong> family, I warmly welcome you into our community of passionate professionals. At Proz Lab, we are more than just a platform—we are a living lab of creativity, innovation, and purpose.</p>
                              <div style="margin:16px 0;padding:14px 16px;border-left:4px solid {accent};background:#f9fafb;border-radius:8px;color:#374151;">
                                We exist with a zeal to design, build, develop, and deliver excellence in technology, not only for progress but also for the greater good of the communities we serve. We believe that technology is a bridge to a better tomorrow—a tool that makes life easier, empowers people, and sparks meaningful change.
                              </div>
                              <p style="margin:0 0 14px 0;">As you begin your journey with us, know that you are not just joining a platform—you are becoming part of a movement. A movement driven by passion, fueled by collaboration, and inspired by the belief that together, we can shape a brighter, better world through innovation.</p>
                              <p style="margin:0 0 18px 0;">Welcome aboard. Let’s create, let’s innovate, and let’s build change that matters.</p>
                              <div style="margin-top:24px;color:#111827;">
                                <strong>With enthusiasm and gratitude,</strong><br/>
                                Fabrice Rugogwe<br/>
                                CEO, Proz Lab
                              </div>
                              <p style="margin:22px 0 0 0;">
                                <a href="{app_url}" style="display:inline-block;background:{accent};color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:700;">Explore your dashboard</a>
                              </p>
                              <p style="margin:12px 0 0 0;color:#6b7280;font-size:13px;">If the button doesn't work, copy and paste this link:<br/>
                                <a href="{app_url}" style="color:{primary};text-decoration:none;">{app_url}</a>
                              </p>
                            </td>
                          </tr>
                        </table>
                      </td>
                    </tr>
                    <tr>
                      <td style="background:#f9fafb;padding:16px 28px;color:#6b7280;font-family:Arial,Helvetica,sans-serif;font-size:12px;">
                        © {datetime.utcnow().year} Proz Lab. All rights reserved.
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </body>
        </html>
        """

        return self.send_email_to_proz_profile(
            proz_profile=proz_profile,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    
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
# app/modules/auth/controllers/email_controller.py - FIXED IMPORTS
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.repositories.user_repository import UserRepository
from app.modules.auth.services.auth_service import get_current_user_allow_unverified
from app.modules.auth.schemas.email import (
    EmailVerificationRequest,
    EmailVerificationResponse,
    EmailVerifyTokenRequest,
    EmailResendRequest,
    EmailServiceStatus,
)
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from app.config.settings import settings

router = APIRouter()
email_service = EmailService()
notification_service = NotificationService()
user_repository = UserRepository()


class ProfileVerificationNotificationRequest(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    verification_status: Literal["verified", "rejected", "pending"]
    admin_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


@router.get("/status", response_model=EmailServiceStatus)
def get_email_service_status() -> Any:
    """Get email service status"""
    try:
        raw = email_service.get_service_status()
        smtp_host = settings.SMTP_HOST or "unknown"
        provider = "Mailtrap" if email_service.mailtrap_api_key else (
            "Mailgun" if isinstance(smtp_host, str) and "mailgun" in smtp_host else str(smtp_host)
        )
        is_configured = bool(raw.get("email_configured") or email_service.mailtrap_api_key)
        message = "Email service running in development mode" if raw.get("development_mode") else "Email service configured for production"
        status_text = "operational" if is_configured else "not_configured"
        return {
            "service": "email",
            "status": status_text,
            "provider": provider,
            "message": message,
            "smtp_configured": is_configured,
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email service status"
        )


@router.post("/send-verification", response_model=EmailVerificationResponse)
def send_verification_email(
    *,
    db: Session = Depends(get_db),
    email_request: EmailVerificationRequest,
    current_user: User = Depends(get_current_user_allow_unverified),
) -> Any:
    """Send email verification"""
    try:
        result = email_service.send_verification_email(
            email=email_request.email,
            user_name=current_user.first_name,
            user_id=str(current_user.id),
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error sending verification email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.post("/request-verification", response_model=EmailVerificationResponse)
def request_verification_email(
    *,
    db: Session = Depends(get_db),
    email_request: EmailVerificationRequest,
) -> Any:
    """Public endpoint to request a verification email without logging in."""
    user = user_repository.get_by_email(db, email_request.email)
    if not user:
        return {
            "success": True,
            "message": "If an account exists for that email, a verification link has been sent.",
        }
    if user.is_verified:
        return {
            "success": True,
            "message": "This email address is already verified.",
        }

    user_name = " ".join(filter(None, [user.first_name, user.last_name])).strip() or None
    return email_service.send_verification_email(
        email=user.email,
        user_name=user_name,
        user_id=str(user.id),
    )


@router.post("/send-verification-notification")
def send_profile_verification_notification(
    request: ProfileVerificationNotificationRequest,
) -> Any:
    """Send profile approval/rejection notification (used by admin dashboard)."""
    user_name = f"{request.first_name} {request.last_name}".strip() or "Professional"
    is_approved = None
    if request.verification_status == "verified":
        is_approved = True
    elif request.verification_status == "rejected":
        is_approved = False

    result = notification_service.send_profile_verification_notification(
        user_email=request.email,
        user_name=user_name,
        is_approved=is_approved,
        admin_notes=request.admin_notes,
        rejection_reason=request.rejection_reason,
        new_status=request.verification_status if is_approved is None else None,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("message", "Failed to send notification email"),
        )
    return result


@router.get("/verify")
def verify_email_from_link(
    token: str = Query(..., description="Verification token"),
) -> Any:
    """Redirect legacy API verify links to the dashboard verify page."""
    app_url = getattr(settings, "APP_URL", "https://prozlab.com").rstrip("/")
    return RedirectResponse(
        url=f"{app_url}/verify-email?token={token}",
        status_code=302,
    )


@router.post("/verify-token", response_model=EmailVerificationResponse)
def verify_email_token(
    *,
    db: Session = Depends(get_db),
    verify_request: EmailVerifyTokenRequest = Body(...)
) -> Any:
    """Verify email token (API endpoint)"""
    try:
        result = email_service.verify_email_from_token(db=db, token=verify_request.token)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error verifying token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email token"
        )


@router.post("/resend-verification", response_model=EmailVerificationResponse)
def resend_verification_email(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_allow_unverified),
    resend_request: EmailResendRequest = Body(default=EmailResendRequest())
) -> Any:
    """Resend verification email to current user"""
    try:
        email_to_verify = resend_request.email or current_user.email
        user_name = " ".join(filter(None, [current_user.first_name, current_user.last_name])).strip() or None
        result = email_service.send_verification_email(
            email=email_to_verify,
            user_name=user_name,
            user_id=str(current_user.id),
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error resending verification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email"
        )


@router.get("/resend-form", response_class=HTMLResponse)
def resend_verification_form(request: Request) -> Any:
    """Show form to resend verification email"""
    return """
    <html>
        <head>
            <title>Resend Email Verification</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    max-width: 600px; 
                    margin: 50px auto; 
                    padding: 20px; 
                    background-color: #f8f9fa;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .form-group { margin-bottom: 20px; }
                label { 
                    display: block; 
                    margin-bottom: 8px; 
                    font-weight: bold;
                    color: #333;
                }
                input { 
                    width: 100%; 
                    padding: 12px; 
                    border: 1px solid #ddd; 
                    border-radius: 4px; 
                    font-size: 16px;
                    box-sizing: border-box;
                }
                button { 
                    background: #007bff; 
                    color: white; 
                    padding: 12px 24px; 
                    border: none; 
                    border-radius: 4px; 
                    cursor: pointer; 
                    font-size: 16px;
                    width: 100%;
                }
                button:hover { background: #0056b3; }
                .note {
                    background: #e9ecef;
                    padding: 15px;
                    border-radius: 4px;
                    margin-bottom: 20px;
                    color: #6c757d;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>📧 Resend Email Verification</h2>
                
                <div class="note">
                    <strong>Note:</strong> Enter the email address you used to register.
                </div>
                
                <form method="post" action="/api/v1/auth/email/request-verification">
                    <div class="form-group">
                        <label for="email">Email Address:</label>
                        <input type="email" id="email" name="email" 
                               placeholder="Enter your email address" required>
                    </div>
                    <button type="submit">📤 Resend Verification Email</button>
                </form>
            </div>
        </body>
    </html>
    """

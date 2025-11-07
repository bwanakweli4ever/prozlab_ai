# app/modules/auth/controllers/email_controller.py - FIXED IMPORTS
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.models.user import User
from app.modules.auth.services.auth_service import get_current_user
from app.modules.auth.schemas.email import (
    EmailVerificationRequest, 
    EmailVerificationResponse, 
    EmailVerifyTokenRequest,
    EmailResendRequest,
    EmailServiceStatus
)
from app.modules.auth.services.email_service import EmailService
from app.config.settings import settings

router = APIRouter()
email_service = EmailService()


@router.get("/status", response_model=EmailServiceStatus)
def get_email_service_status() -> Any:
    """Get email service status"""
    try:
        raw = email_service.get_service_status()
        # Map raw service dict to the response model expected fields
        smtp_host = settings.SMTP_HOST or "unknown"
        provider = "Mailgun" if isinstance(smtp_host, str) and "mailgun" in smtp_host else smtp_host
        is_configured = bool(raw.get("email_configured"))
        message = "Email service running in development mode" if raw.get("development_mode") else "Email service configured for production"
        status_text = "operational" if is_configured else "not_configured"
        return {
            "service": "email",
            "status": status_text,
            "provider": provider,
            "message": message,
            "smtp_configured": is_configured,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get email service status"
        )


@router.post("/send-verification", response_model=EmailVerificationResponse)
def send_verification_email(
    *,
    db: Session = Depends(get_db),
    email_request: EmailVerificationRequest,
    current_user: User = Depends(get_current_user)
) -> Any:
    """Send email verification"""
    try:
        result = email_service.send_verification_email(
            db=db,
            user_id=str(current_user.id),
            email=email_request.email
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


@router.get("/verify", response_class=HTMLResponse)
def verify_email_from_link(
    token: str = Query(..., description="Verification token"),
    db: Session = Depends(get_db)
) -> Any:
    """Verify email from link (typically clicked in email)"""
    try:
        result = email_service.verify_email_from_token(db=db, token=token)
        
        if result["success"]:
            return """
            <html>
                <head>
                    <title>Email Verified</title>
                    <style>
                        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                        .success { color: #28a745; }
                        .container { border: 1px solid #ddd; border-radius: 8px; padding: 40px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2 class="success">✅ Email Verified Successfully!</h2>
                        <p>Your email has been verified. You can now close this window.</p>
                        <p><small>You may now use all features of your account.</small></p>
                    </div>
                </body>
            </html>
            """
        else:
            return f"""
            <html>
                <head>
                    <title>Email Verification Failed</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                        .error {{ color: #dc3545; }}
                        .container {{ border: 1px solid #ddd; border-radius: 8px; padding: 40px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2 class="error">❌ Email Verification Failed</h2>
                        <p>Error: {result.get('message', 'Unknown error')}</p>
                        <p><small>Please try requesting a new verification email.</small></p>
                    </div>
                </body>
            </html>
            """
            
    except Exception as e:
        print(f"❌ Error in email verification: {str(e)}")
        return f"""
        <html>
            <head>
                <title>Email Verification Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }}
                    .error {{ color: #dc3545; }}
                    .container {{ border: 1px solid #ddd; border-radius: 8px; padding: 40px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2 class="error">❌ Email Verification Error</h2>
                    <p>An error occurred: {str(e)}</p>
                    <p><small>Please contact support if this problem persists.</small></p>
                </div>
            </body>
        </html>
        """


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
    current_user: User = Depends(get_current_user),
    resend_request: EmailResendRequest = Body(default=EmailResendRequest())
) -> Any:
    """Resend verification email to current user"""
    try:
        # Use the email from request or fall back to current user's email
        email_to_verify = resend_request.email or current_user.email
        
        result = email_service.send_verification_email(
            db=db,
            user_id=str(current_user.id),
            email=email_to_verify
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
                    <strong>Note:</strong> If you're already logged in, we'll send the verification to your account email. 
                    Otherwise, enter the email address below.
                </div>
                
                <form method="post" action="/api/v1/auth/email/resend-verification">
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
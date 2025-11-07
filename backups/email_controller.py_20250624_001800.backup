# app/modules/auth/controllers/email_controller.py
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.auth.schemas.email import (
    EmailVerificationRequest, EmailVerificationResponse,
    EmailVerifyTokenRequest, EmailVerifyTokenResponse,
    ResendVerificationRequest, EmailStatusResponse
)
from app.services.email_service import EmailService
from app.modules.auth.models.user import User

router = APIRouter()
email_service = EmailService()


@router.get("/status", response_model=EmailStatusResponse)
async def get_email_service_status() -> Any:
    """
    Get the current status of the email service.
    """
    status_info = email_service.get_service_status()
    return EmailStatusResponse(**status_info)


@router.post("/send-verification", response_model=EmailVerificationResponse)
async def send_verification_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Send verification email to the specified email address.
    """
    # Optional: Check if user exists with this email
    # user = db.query(User).filter(User.email == request.email).first()
    
    result = email_service.send_verification_email(
        email=request.email,
        user_name=None,  # Can be passed if user exists
        user_id=None     # Can be passed if user exists
    )
    
    if not result["success"]:
        if result.get("error_code") == "RATE_LIMIT_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
    
    return EmailVerificationResponse(
        success=result["success"],
        message=result["message"],
        expires_in_hours=result.get("expires_in_hours")
    )


@router.get("/verify", response_class=HTMLResponse)
async def verify_email_from_link(
    token: str = Query(..., description="Email verification token"),
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify email using token from email link.
    Returns an HTML response for better user experience.
    """
    result = email_service.verify_email_token(token)
    
    if result["success"]:
        # Success HTML page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Verified</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                }}
                .success {{
                    color: #4CAF50;
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                .message {{
                    font-size: 18px;
                    margin-bottom: 30px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #4CAF50;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="success">✅ Email Verified Successfully!</div>
            <div class="message">
                Your email address has been verified. You can now continue using our services.
            </div>
            <a href="http://localhost:3000/login" class="button">Continue to App</a>
        </body>
        </html>
        """
    else:
        # Error HTML page
        error_messages = {
            "TOKEN_NOT_FOUND": "Invalid or expired verification link",
            "ALREADY_VERIFIED": "This email has already been verified",
            "TOKEN_EXPIRED": "Verification link has expired",
        }
        
        error_message = error_messages.get(
            result.get("error_code"), 
            "An error occurred during verification"
        )
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verification Error</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                }}
                .error {{
                    color: #f44336;
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                .message {{
                    font-size: 18px;
                    margin-bottom: 30px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #2196F3;
                    color: white;
                    padding: 12px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="error">❌ Verification Failed</div>
            <div class="message">{error_message}</div>
            <a href="http://localhost:8000/api/v1/auth/email/resend-form" class="button">Request New Verification</a>
        </body>
        </html>
        """
    
    return html_content


@router.post("/verify-token", response_model=EmailVerifyTokenResponse)
async def verify_email_token(
    request: EmailVerifyTokenRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify email token via API (for programmatic access).
    """
    result = email_service.verify_email_token(request.token)
    
    if not result["success"]:
        error_codes = ["TOKEN_NOT_FOUND", "TOKEN_EXPIRED", "ALREADY_VERIFIED"]
        if result.get("error_code") in error_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    return EmailVerifyTokenResponse(
        success=result["success"],
        message=result["message"],
        email_verified=result.get("email_verified", False),
        user_id=result.get("user_id")
    )


@router.post("/resend-verification", response_model=EmailVerificationResponse)
async def resend_verification_email(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db)
) -> Any:
    """
    Resend verification email.
    """
    result = email_service.send_verification_email(
        email=request.email,
        user_name=None,
        user_id=None
    )
    
    if not result["success"]:
        if result.get("error_code") == "RATE_LIMIT_EXCEEDED":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=result["message"]
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
    
    return EmailVerificationResponse(
        success=result["success"],
        message=result["message"],
        expires_in_hours=result.get("expires_in_hours")
    )


@router.get("/resend-form", response_class=HTMLResponse)
async def resend_verification_form() -> Any:
    """
    HTML form for requesting new verification email.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Resend Verification Email</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            input[type="email"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            button:hover {
                background-color: #45a049;
            }
        </style>
    </head>
    <body>
        <h1>Resend Verification Email</h1>
        <form action="/api/v1/auth/email/resend-verification" method="post">
            <div class="form-group">
                <label for="email">Email Address:</label>
                <input type="email" id="email" name="email" required>
            </div>
            <button type="submit">Send Verification Email</button>
        </form>
    </body>
    </html>
    """
    return html_content
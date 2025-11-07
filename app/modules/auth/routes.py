# app/modules/auth/routes.py - CORRECTED
from fastapi import APIRouter
from app.modules.auth.controllers import auth_controller, otp_controller, email_controller, password_reset_controller

# Create the main auth router
router = APIRouter()

# Include auth controller WITHOUT any prefix (base auth routes)
router.include_router(auth_controller.router, tags=["Authentication"])

# # Include OTP controller with /otp prefix
# router.include_router(otp_controller.router, prefix="/otp", tags=["OTP Verification"]) we don

# # Include email controller with /email prefix  
router.include_router(email_controller.router, prefix="/email", tags=["Email Verification"])

# Include password reset controller with /password prefix
router.include_router(password_reset_controller.router, prefix="/password", tags=["Password Reset"])
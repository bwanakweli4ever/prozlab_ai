# app/routes.py - CORRECTED
from fastapi import APIRouter

from app.config.settings import settings
from app.modules.auth.routes import router as auth_router
from app.modules.proz.routes import router as proz_router
from app.modules.proz.controllers.admin_controller import router as admin_router
from app.modules.tasks.routes import router as task_router

# Create main API router
api_router = APIRouter()

# Include auth router with /auth prefix (this will give you /api/v1/auth/*)
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# Include email verification router with /email prefix
api_router.include_router(auth_router, prefix="/email", tags=["Email Verification"])

# Include other routers with their prefixes
api_router.include_router(proz_router, prefix="/proz", tags=["Professional Profiles"])
api_router.include_router(admin_router, prefix="/admin/proz", tags=["Admin - Profile Verification"])
api_router.include_router(task_router, prefix="/tasks", tags=["Task Management"])
from fastapi import APIRouter

from app.modules.onboarding.controllers.onboarding_controller import router as onboarding_router

router = APIRouter()
router.include_router(onboarding_router, tags=["Candidate Onboarding"])

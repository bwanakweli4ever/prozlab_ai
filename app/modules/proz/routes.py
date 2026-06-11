# app/modules/proz/routes.py
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.modules.proz.models.proz import Specialty

# Import controllers
from app.modules.proz.controllers.public_controller import router as public_router
from app.modules.proz.controllers.media_controller import router as media_router
from app.modules.proz.controllers.proz_controller import router as proz_router
from app.modules.proz.controllers.file_access_controller import router as file_access_router
from app.modules.proz.controllers.ai_profile_controller import router as ai_router
from app.modules.proz.controllers.skill_verification_controller import router as verification_router


# Create the main router for the proz module
router = APIRouter()

# Include public routes (no authentication required)
router.include_router(public_router, prefix="/public", tags=["public-profiles"])

# Include media/file upload routes (authentication required)
router.include_router(media_router, prefix="/media", tags=["profile-media"])

router.include_router(proz_router, prefix="/proz", tags=["proz-profiles"])

router.include_router(file_access_router, prefix="/files", tags=["file-access"])

# AI-powered profile assistance (mounted under /api/v1/proz/...)
router.include_router(ai_router, prefix="", tags=["proz-ai"])
router.include_router(verification_router, prefix="", tags=["skill-verification"])


@router.get("/specialties", response_model=List[str], tags=["proz-profiles"])
async def get_specialties(db: Session = Depends(get_db)) -> List[str]:
    """All specialty names from the database, for onboarding and profile forms."""
    rows = db.query(Specialty.name).order_by(Specialty.name.asc()).all()
    return [row.name for row in rows]
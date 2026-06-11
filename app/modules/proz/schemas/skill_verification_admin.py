from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.proz.schemas.verification import EvidenceItem


class EvidenceReviewItem(BaseModel):
    evidence_id: str
    status: Literal["approved", "rejected", "pending"]
    admin_notes: Optional[str] = None


class SkillVerificationReviewRequest(BaseModel):
    decision: Literal["verified", "rejected", "needs_revision"]
    admin_notes: Optional[str] = None
    evidence_reviews: List[EvidenceReviewItem] = Field(default_factory=list)


class SkillVerificationListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    profile_image_url: Optional[str] = None
    location: Optional[str] = None
    years_experience: Optional[int] = None
    verification_status: str
    skill_verification_status: str
    verification_score: int
    evidence_count: int
    identity_items: int
    work_experience_items: int
    submitted_at: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SkillVerificationDetailResponse(BaseModel):
    profile: SkillVerificationListItem
    evidences: List[EvidenceItem]
    requirements_met: Dict[str, bool]
    admin_notes: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[str] = None


class SkillVerificationListResponse(BaseModel):
    profiles: List[SkillVerificationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int

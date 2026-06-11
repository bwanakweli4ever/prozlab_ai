from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FraudSignal(BaseModel):
    code: str
    severity: Literal["low", "medium", "high", "critical"]
    message: str
    score: int = 0


class FraudCandidateItem(BaseModel):
    user_id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_flagged: bool
    is_banned: bool
    fraud_score: int
    fraud_signals: List[FraudSignal] = []
    ban_reason: Optional[str] = None
    fraud_notes: Optional[str] = None
    flagged_at: Optional[datetime] = None
    banned_at: Optional[datetime] = None
    fraud_scanned_at: Optional[datetime] = None
    profile_id: Optional[UUID] = None
    profile_verification_status: Optional[str] = None
    skill_verification_status: Optional[str] = None
    risk_level: str = "low"

    class Config:
        from_attributes = True


class FraudCandidateListResponse(BaseModel):
    candidates: List[FraudCandidateItem]
    total: int
    flagged_count: int
    banned_count: int
    high_risk_count: int


class FraudScanResponse(BaseModel):
    user_id: UUID
    fraud_score: int
    risk_level: str
    signals: List[FraudSignal]
    auto_flagged: bool = False


class FraudActionRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)
    notes: Optional[str] = None


class FraudActionResponse(BaseModel):
    success: bool
    message: str
    user_id: UUID
    is_flagged: bool
    is_banned: bool
    is_active: bool

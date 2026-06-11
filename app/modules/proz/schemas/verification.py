from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


EvidenceType = Literal[
    "github",
    "portfolio",
    "work_sample",
    "recommendation",
    "linkedin",
    "certification",
    "previous_employer",
    "identity_document",
]


class EvidenceCreate(BaseModel):
    type: EvidenceType
    title: str = Field(..., min_length=2, max_length=200)
    url: Optional[str] = None
    description: Optional[str] = None
    referrer_name: Optional[str] = None
    referrer_email: Optional[EmailStr] = None
    referrer_relationship: Optional[str] = None
    referrer_message: Optional[str] = None


class EvidenceItem(BaseModel):
    id: str
    type: EvidenceType
    title: str
    url: Optional[str] = None
    description: Optional[str] = None
    referrer_name: Optional[str] = None
    referrer_email: Optional[str] = None
    referrer_relationship: Optional[str] = None
    referrer_message: Optional[str] = None
    status: str = "submitted"
    admin_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


class VerificationStatusResponse(BaseModel):
    skill_verification_status: str
    verification_score: int
    evidences: List[EvidenceItem]
    requirements_met: Dict[str, bool]
    can_submit: bool
    admin_notes: Optional[str] = None
    reviewed_at: Optional[str] = None


class GitHubValidateRequest(BaseModel):
    url: str


class GitHubValidateResponse(BaseModel):
    valid: bool
    username: Optional[str] = None
    public_repos: Optional[int] = None
    followers: Optional[int] = None
    profile_url: Optional[str] = None
    message: Optional[str] = None

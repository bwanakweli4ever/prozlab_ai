from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

OnboardingStepName = Literal[
    "welcome",
    "expertise",
    "experience",
    "preferences",
    "portfolio",
    "skills_verification",
    "profile",
]


class OnboardingStepPayload(BaseModel):
    step: OnboardingStepName
    data: Dict[str, Any] = Field(default_factory=dict)


class OnboardingStatusResponse(BaseModel):
    user_id: uuid.UUID
    current_step: int
    total_steps: int = 7
    completed_steps: List[str]
    step_data: Dict[str, Any]
    is_complete: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OnboardingCompleteResponse(BaseModel):
    message: str
    profile_id: uuid.UUID
    onboarding_completed: bool = True

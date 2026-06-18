from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SpecialtyAdminResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    profiles_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("id", mode="before")
    @classmethod
    def _id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = {"from_attributes": True}


class SpecialtyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class SpecialtyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

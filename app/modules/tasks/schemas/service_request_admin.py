from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.tasks.schemas.task import ServiceRequestResponse, TaskAssignmentResponse


class ProposalLineItem(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(1, ge=0)
    unit_price: float = Field(..., ge=0)
    days: Optional[int] = Field(None, ge=0)


class ServiceRequestMessageCreate(BaseModel):
    body: str = Field(..., min_length=1)
    message_type: str = Field("question", description="question, reply, note")
    subject: Optional[str] = None
    requested_budget_min: Optional[float] = Field(None, ge=0)
    requested_budget_max: Optional[float] = Field(None, ge=0)
    requested_days: Optional[int] = Field(None, ge=0)
    send_email_to_client: bool = True


class ServiceRequestMessageResponse(BaseModel):
    id: str
    service_request_id: str
    author_type: str
    author_name: str
    author_email: Optional[str] = None
    message_type: str
    subject: Optional[str] = None
    body: str
    requested_budget_min: Optional[float] = None
    requested_budget_max: Optional[float] = None
    requested_days: Optional[int] = None
    email_sent: bool = False
    created_at: datetime

    @field_validator("id", "service_request_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = {"from_attributes": True}


class ServiceRequestProposalCreate(BaseModel):
    proposal_type: str = Field("dynamic", description="dynamic or uploaded")
    title: str = Field(..., min_length=3, max_length=255)
    introduction: Optional[str] = None
    line_items: Optional[List[ProposalLineItem]] = None
    tax_rate: float = Field(0, ge=0, le=100)
    estimated_days: Optional[int] = Field(None, ge=0)
    budget_amount: Optional[float] = Field(None, ge=0)
    currency: str = "USD"
    notes: Optional[str] = None
    valid_until: Optional[datetime] = None
    document_url: Optional[str] = None


class ServiceRequestProposalResponse(BaseModel):
    id: str
    service_request_id: str
    proposal_type: str
    title: str
    introduction: Optional[str] = None
    line_items: Optional[List[dict]] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    total: Optional[float] = None
    estimated_days: Optional[int] = None
    budget_amount: Optional[float] = None
    currency: str = "USD"
    status: str
    public_token: str
    document_url: Optional[str] = None
    notes: Optional[str] = None
    sent_at: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    public_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("id", "service_request_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = {"from_attributes": True}


class ServiceRequestAdminUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    admin_notes: Optional[str] = None


class ServiceRequestAdminDetailResponse(BaseModel):
    request: ServiceRequestResponse
    assignments: List[TaskAssignmentResponse] = []
    messages: List[ServiceRequestMessageResponse] = []
    proposals: List[ServiceRequestProposalResponse] = []

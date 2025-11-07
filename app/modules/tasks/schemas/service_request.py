# app/modules/tasks/schemas/service_request.py
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import datetime
from decimal import Decimal
import uuid

from app.modules.tasks.models.task_enums import TaskStatusEnum, TaskPriorityEnum


class ServiceRequestBase(BaseModel):
    company_name: str = Field(..., max_length=200)
    client_name: str = Field(..., max_length=100)
    client_email: EmailStr
    client_phone: Optional[str] = Field(None, max_length=20)
    
    service_title: str = Field(..., max_length=200)
    service_description: str
    service_category: str = Field(..., max_length=100)
    required_skills: Optional[str] = None
    
    budget_min: Optional[Decimal] = Field(None, ge=0)
    budget_max: Optional[Decimal] = Field(None, ge=0)
    expected_duration: Optional[str] = Field(None, max_length=100)
    deadline: Optional[datetime] = None
    
    location_preference: Optional[str] = Field(None, max_length=255)
    remote_work_allowed: bool = True
    
    # Use enum defaults
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    priority: TaskPriorityEnum = TaskPriorityEnum.MEDIUM


class ServiceRequestCreate(ServiceRequestBase):
    # Remove status and priority from create - let them default
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    
    @field_validator('budget_max')
    @classmethod
    def validate_budget_max(cls, v, info):
        """Ensure budget_max >= budget_min if both provided"""
        if v is not None and info.data.get('budget_min') is not None:
            if v < info.data['budget_min']:
                raise ValueError('budget_max must be greater than or equal to budget_min')
        return v


class ServiceRequestUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=200)
    client_name: Optional[str] = Field(None, max_length=100)
    client_email: Optional[EmailStr] = None
    client_phone: Optional[str] = Field(None, max_length=20)
    
    service_title: Optional[str] = Field(None, max_length=200)
    service_description: Optional[str] = None
    service_category: Optional[str] = Field(None, max_length=100)
    required_skills: Optional[str] = None
    
    budget_min: Optional[Decimal] = Field(None, ge=0)
    budget_max: Optional[Decimal] = Field(None, ge=0)
    expected_duration: Optional[str] = Field(None, max_length=100)
    deadline: Optional[datetime] = None
    
    location_preference: Optional[str] = Field(None, max_length=255)
    remote_work_allowed: Optional[bool] = None
    
    status: Optional[TaskStatusEnum] = None
    priority: Optional[TaskPriorityEnum] = None
    admin_notes: Optional[str] = None


class ServiceRequestResponse(ServiceRequestBase):
    id: str  # Convert UUID to string for API response
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    model_config = ConfigDict(from_attributes=True)
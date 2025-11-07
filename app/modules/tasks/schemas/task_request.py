# app/modules/tasks/schemas/task_request.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import datetime
from decimal import Decimal
import uuid

from app.modules.tasks.models.task_enums import TaskStatusEnum, TaskPriorityEnum


class BusinessTaskRequestCreate(BaseModel):
    """Schema for business task requests"""
    # Company Information
    company_name: str = Field(..., max_length=200, description="Name of the company requesting the service")
    client_name: str = Field(..., max_length=100, description="Contact person name")
    client_email: EmailStr = Field(..., description="Contact email address")
    client_phone: Optional[str] = Field(None, max_length=20, description="Contact phone number")
    
    # Service Details
    service_title: str = Field(..., max_length=200, description="Title of the service needed")
    service_description: str = Field(..., description="Detailed description of the service")
    service_category: str = Field(..., max_length=100, description="Category of service (e.g., IT, Maintenance, etc.)")
    required_skills: Optional[str] = Field(None, description="Specific skills or qualifications required")
    
    # Budget and Timeline
    estimated_hours: Optional[float] = Field(None, ge=0.5, le=1000, description="Estimated hours to complete the task")
    budget_min: Optional[Decimal] = Field(None, ge=0, description="Minimum budget for the service")
    budget_max: Optional[Decimal] = Field(None, ge=0, description="Maximum budget for the service")
    expected_duration: Optional[str] = Field(None, max_length=100, description="Expected duration (e.g., '2 days', '1 week')")
    deadline: Optional[datetime] = Field(None, description="Deadline for task completion")
    
    # Location and Work Preferences
    location_preference: Optional[str] = Field(None, max_length=255, description="Preferred location for the work")
    remote_work_allowed: bool = Field(True, description="Whether remote work is acceptable")
    
    # Priority
    priority: TaskPriorityEnum = Field(TaskPriorityEnum.MEDIUM, description="Priority level of the task")
    
    # Additional Requirements
    special_requirements: Optional[str] = Field(None, description="Any special requirements or constraints")
    preferred_start_date: Optional[datetime] = Field(None, description="Preferred start date for the work")
    
    @field_validator('budget_max')
    @classmethod
    def validate_budget_max(cls, v, info):
        """Ensure budget_max >= budget_min if both provided"""
        if v is not None and info.data.get('budget_min') is not None:
            if v < info.data['budget_min']:
                raise ValueError('budget_max must be greater than or equal to budget_min')
        return v
    
    @field_validator('deadline')
    @classmethod
    def validate_deadline(cls, v):
        """Ensure deadline is in the future"""
        if v is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if v <= now:
                raise ValueError('deadline must be in the future')
        return v
    
    @field_validator('preferred_start_date')
    @classmethod
    def validate_start_date(cls, v):
        """Ensure start date is in the future"""
        if v is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if v <= now:
                raise ValueError('preferred_start_date must be in the future')
        return v


class TaskAssignmentProposalCreate(BaseModel):
    """Schema for creating task assignment proposals (admin only)"""
    service_request_id: str = Field(..., description="ID of the service request to assign")
    proz_id: str = Field(..., description="ID of the professional to assign the task to")
    assignment_notes: Optional[str] = Field(None, description="Notes for the professional about the assignment")
    estimated_hours: Optional[float] = Field(None, ge=0.5, le=1000, description="Estimated hours for completion")
    proposed_rate: Optional[Decimal] = Field(None, ge=0, description="Proposed hourly rate")
    due_date: Optional[datetime] = Field(None, description="Due date for the task")
    
    @field_validator('due_date')
    @classmethod
    def validate_due_date(cls, v):
        """Ensure due date is in the future"""
        if v is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            if v <= now:
                raise ValueError('due_date must be in the future')
        return v


class TaskAssignmentProposalResponse(BaseModel):
    """Schema for task assignment proposal responses"""
    id: str
    service_request_id: str
    proz_id: str
    assignment_notes: Optional[str] = None
    estimated_hours: Optional[float] = None
    proposed_rate: Optional[Decimal] = None
    status: TaskStatusEnum
    due_date: Optional[datetime] = None
    assigned_at: datetime
    
    # Professional response
    proz_response: Optional[str] = None
    proz_response_at: Optional[datetime] = None
    
    # Service request details
    service_title: str
    service_description: str
    company_name: str
    
    # Professional details
    professional_name: str
    professional_email: str
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    @field_validator('service_request_id', mode='before')
    @classmethod
    def convert_service_request_uuid(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    @field_validator('proz_id', mode='before')
    @classmethod
    def convert_proz_uuid(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    model_config = ConfigDict(from_attributes=True)


class BusinessTaskRequestResponse(BaseModel):
    """Schema for business task request responses"""
    id: str
    company_name: str
    client_name: str
    client_email: str
    client_phone: Optional[str] = None
    
    service_title: str
    service_description: str
    service_category: str
    required_skills: Optional[str] = None
    
    estimated_hours: Optional[float] = None
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    expected_duration: Optional[str] = None
    deadline: Optional[datetime] = None
    
    location_preference: Optional[str] = None
    remote_work_allowed: bool = True
    
    # Return as strings for API response
    priority: str
    status: str
    
    special_requirements: Optional[str] = None
    preferred_start_date: Optional[datetime] = None
    admin_notes: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Assignment information
    assignments_count: int = 0
    accepted_assignments_count: int = 0
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    @field_validator('priority', 'status', mode='before')
    @classmethod
    def enum_to_string(cls, v):
        if hasattr(v, 'value'):
            return v.value
        return str(v) if v is not None else v
    
    model_config = ConfigDict(from_attributes=True)


class TaskAssignmentUpdate(BaseModel):
    """Schema for updating task assignments"""
    assignment_notes: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, ge=0.5, le=1000)
    proposed_rate: Optional[Decimal] = Field(None, ge=0)
    due_date: Optional[datetime] = None
    status: Optional[TaskStatusEnum] = None
    proz_response: Optional[str] = None


class TaskAssignmentResponse(BaseModel):
    """Schema for task assignment responses"""
    id: str
    service_request_id: str
    proz_id: str
    assignment_notes: Optional[str] = None
    estimated_hours: Optional[float] = None
    proposed_rate: Optional[Decimal] = None
    status: TaskStatusEnum
    due_date: Optional[datetime] = None
    assigned_at: datetime
    completed_at: Optional[datetime] = None
    
    # Professional response
    proz_response: Optional[str] = None
    proz_response_at: Optional[datetime] = None
    
    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_string(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    @field_validator('service_request_id', mode='before')
    @classmethod
    def convert_service_request_uuid(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    @field_validator('proz_id', mode='before')
    @classmethod
    def convert_proz_uuid(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    
    model_config = ConfigDict(from_attributes=True)

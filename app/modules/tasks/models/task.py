# app/modules/tasks/models/task.py
from sqlalchemy import Column, String, Text, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

# Import base from the same location as your ProzProfile model
from app.modules.proz.models.proz import Base


class TaskStatus(enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TaskPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ServiceRequest(Base):
    """Service requests from companies/clients"""
    __tablename__ = "service_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Client Information
    company_name = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=False)
    client_email = Column(String(255), nullable=False)
    client_phone = Column(String(20), nullable=True)
    
    # Service Details
    service_title = Column(String(200), nullable=False)
    service_description = Column(Text, nullable=False)
    service_category = Column(String(100), nullable=False)
    
    # Requirements
    required_skills = Column(Text, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    budget_min = Column(Float, nullable=True)
    budget_max = Column(Float, nullable=True)
    expected_duration = Column(String(100), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    location_preference = Column(String(255), nullable=True)
    remote_work_allowed = Column(Boolean, default=True)
    
    # Status and Priority
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    
    # Admin notes
    admin_notes = Column(Text, nullable=True)
    special_requirements = Column(Text, nullable=True)
    preferred_start_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    assignments = relationship("TaskAssignment", back_populates="service_request", cascade="all, delete-orphan")


class TaskAssignment(Base):
    """Assignment of service requests to professionals"""
    __tablename__ = "task_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    service_request_id = Column(UUID(as_uuid=True), ForeignKey("service_requests.id"), nullable=False)
    proz_id = Column(UUID(as_uuid=True), ForeignKey("proz_profiles.id"), nullable=False)
    assigned_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Assignment Details
    assignment_notes = Column(Text, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    proposed_rate = Column(Float, nullable=True)
    
    # Status
    status = Column(Enum(TaskStatus), default=TaskStatus.ASSIGNED, nullable=False)
    
    # Response from Professional
    proz_response = Column(Text, nullable=True)
    proz_response_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    service_request = relationship("ServiceRequest", back_populates="assignments")
    professional = relationship("ProzProfile", back_populates="task_assignments")


class TaskNotification(Base):
    """Notifications for task assignments and updates"""
    __tablename__ = "task_notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Target
    proz_id = Column(UUID(as_uuid=True), ForeignKey("proz_profiles.id"), nullable=False)
    task_assignment_id = Column(UUID(as_uuid=True), ForeignKey("task_assignments.id"), nullable=True)
    
    # Notification Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)
    
    # Status
    is_read = Column(Boolean, default=False)
    is_email_sent = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    professional = relationship("ProzProfile")
    task_assignment = relationship("TaskAssignment")
# app/modules/tasks/models/service_request.py
from sqlalchemy import Column, String, Text, DECIMAL, Boolean, DateTime
from sqlalchemy.sql import func
import uuid

from app.database.base_class import Base
from app.database.types import PortableUUID


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    
    id = Column(PortableUUID, primary_key=True, default=uuid.uuid4, index=True)
    
    # Company and client information
    company_name = Column(String(200), nullable=False)
    client_name = Column(String(100), nullable=False)
    client_email = Column(String(255), nullable=False)
    client_phone = Column(String(20), nullable=True)
    
    # Service details
    service_title = Column(String(200), nullable=False)
    service_description = Column(Text, nullable=False)
    service_category = Column(String(100), nullable=False)
    required_skills = Column(Text, nullable=True)
    
    # Budget and timeline
    budget_min = Column(DECIMAL(10, 2), nullable=True)
    budget_max = Column(DECIMAL(10, 2), nullable=True)
    expected_duration = Column(String(100), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    
    # Location preferences
    location_preference = Column(String(255), nullable=True)
    remote_work_allowed = Column(Boolean, default=True)
    
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(String(20), nullable=False, default="medium")
    
    # Admin notes
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<ServiceRequest(id={self.id}, title={self.service_title}, status={self.status})>"

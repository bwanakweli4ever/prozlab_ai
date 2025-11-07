# app/modules/proz/models/proz.py
import uuid
import enum

from sqlalchemy import Column, String, Text, Integer, Numeric, ForeignKey, Enum, Boolean, Float, DateTime, func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database.base_class import Base


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ProzProfile(Base):
    __tablename__ = "proz_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to User model - ADD THIS
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=True)
    
    # Basic Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_number = Column(String(20), nullable=True)
    
    # Profile Image
    profile_image_url = Column(String(500), nullable=True)
    
    # Professional Information
    bio = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    years_experience = Column(Integer, nullable=True)
    hourly_rate = Column(Float, nullable=True)
    availability = Column(String(50), nullable=True)  # full-time, part-time, contract
    
    # Education & Skills
    education = Column(Text, nullable=True)
    certifications = Column(Text, nullable=True)
    
    # Social & Contact
    website = Column(String(255), nullable=True)
    linkedin = Column(String(255), nullable=True)
    preferred_contact_method = Column(String(50), default="email")
    
    # Status & Verification
    verification_status = Column(String(20), default="pending")  # pending, verified, rejected
    is_featured = Column(Boolean, default=False)
    
    # Ratings & Reviews
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    
    # Account Status
    email_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ProzProfile(id={self.id}, name={self.first_name} {self.last_name}, email={self.email})>"

    # Relationships
    user = relationship("User", backref="proz_profile")  # ADD THIS
    specialties = relationship("ProzSpecialty", back_populates="proz_profile", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="proz_profile", cascade="all, delete-orphan")
    task_assignments = relationship("TaskAssignment", back_populates="professional")
    notifications = relationship("TaskNotification", back_populates="professional")


class Specialty(Base):
    """Specialty Model"""
    __tablename__ = "specialties"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    proz_profiles = relationship("ProzSpecialty", back_populates="specialty")


class ProzSpecialty(Base):
    """Junction Table for Proz Profiles and Specialties"""
    __tablename__ = "proz_specialty"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign Keys
    proz_id = Column(UUID(as_uuid=True), ForeignKey("proz_profiles.id"), nullable=False)
    specialty_id = Column(UUID(as_uuid=True), ForeignKey("specialties.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    proz_profile = relationship("ProzProfile", back_populates="specialties")
    specialty = relationship("Specialty", back_populates="proz_profiles")


class Review(Base):
    """Review Model"""
    __tablename__ = "reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign Key
    proz_id = Column(UUID(as_uuid=True), ForeignKey("proz_profiles.id"), nullable=False)
    
    client_name = Column(String(100), nullable=False)
    client_email = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_text = Column(Text, nullable=True)
    
    # Review status
    is_approved = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    proz_profile = relationship("ProzProfile", back_populates="reviews")
    
    def __repr__(self):
        return f"<Review(id={self.id}, proz_id={self.proz_id}, rating={self.rating})>"
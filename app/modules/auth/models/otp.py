from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database.base_class import Base


class OTPVerification(Base):
    """OTP Verification Model"""
    __tablename__ = "otp_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    phone_number = Column(String(20), nullable=True, index=True)  # Made nullable for email-based OTP
    email = Column(String(255), nullable=True, index=True)  # Added email field
    otp_code = Column(String(10), nullable=False)
    purpose = Column(String(50), nullable=False, default="phone_verification")  # Added purpose field
    attempts = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<OTPVerification(id={self.id}, email={self.email}, phone={self.phone_number}, purpose={self.purpose}, verified={self.is_verified})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the OTP is expired"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        # Handle both timezone-aware and timezone-naive datetimes
        if self.expires_at.tzinfo is None:
            # If expires_at is timezone-naive, assume it's UTC
            expires_at_utc = self.expires_at.replace(tzinfo=timezone.utc)
        else:
            # If expires_at is timezone-aware, convert to UTC
            expires_at_utc = self.expires_at.astimezone(timezone.utc)
        
        return now > expires_at_utc
    
    @property
    def is_valid(self) -> bool:
        """Check if the OTP is valid (not verified and not expired)"""
        return not self.is_verified and not self.is_expired
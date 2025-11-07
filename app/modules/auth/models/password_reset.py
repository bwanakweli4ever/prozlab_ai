# app/modules/auth/models/password_reset.py
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.database.base_class import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship to user
    user = relationship("User", back_populates="password_reset_tokens")
    
    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the token is expired"""
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
        """Check if the token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database.base_class import Base


class OnboardingProgress(Base):
    """Tracks candidate onboarding progress through the 7-step wizard."""

    __tablename__ = "onboarding_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False, index=True)

    current_step = Column(Integer, default=1, nullable=False)
    completed_steps = Column(JSONB, default=list, nullable=False)
    step_data = Column(JSONB, default=dict, nullable=False)

    is_complete = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="onboarding_progress")

    def __repr__(self) -> str:
        return f"<OnboardingProgress(user_id={self.user_id}, step={self.current_step}, complete={self.is_complete})>"

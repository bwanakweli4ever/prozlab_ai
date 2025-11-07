# app/database/session.py
from sqlalchemy.orm import Session

from app.config.database import SessionLocal


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# app/database/base_class.py
from typing import Any
import uuid
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func


@as_declarative()
class Base:
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    __name__: str
    
    # Generate tablename automatically
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
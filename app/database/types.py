"""Portable SQLAlchemy column types for PostgreSQL and MySQL."""

import uuid

from sqlalchemy import JSON, String, TypeDecorator


class PortableUUID(TypeDecorator):
    """Store UUIDs as 36-char strings (works on PostgreSQL and MySQL)."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


PortableJSON = JSON

"""add users.profile_reminder_count

Revision ID: a3c9e7d1f5b2
Revises: f2b6c1d8e9a7
Create Date: 2026-11-22

"""
from alembic import op
import sqlalchemy as sa


revision = "a3c9e7d1f5b2"
down_revision = "f2b6c1d8e9a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_reminder_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "profile_reminder_count")

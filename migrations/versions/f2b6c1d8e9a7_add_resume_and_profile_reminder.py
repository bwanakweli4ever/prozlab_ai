"""add resume fields to proz_profiles and profile_reminder_sent_at to users

Revision ID: f2b6c1d8e9a7
Revises: e8f1a2b3c4d5
Create Date: 2026-11-22

"""
from alembic import op
import sqlalchemy as sa


revision = "f2b6c1d8e9a7"
down_revision = "e8f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("proz_profiles", sa.Column("resume_filename", sa.String(length=255), nullable=True))
    op.add_column("proz_profiles", sa.Column("resume_path", sa.String(length=500), nullable=True))
    op.add_column("proz_profiles", sa.Column("resume_uploaded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("profile_reminder_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_reminder_sent_at")
    op.drop_column("proz_profiles", "resume_uploaded_at")
    op.drop_column("proz_profiles", "resume_path")
    op.drop_column("proz_profiles", "resume_filename")

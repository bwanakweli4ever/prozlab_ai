"""add fraud detection fields to users

Revision ID: d5f9a3b2c104
Revises: c4d8e2f1a903
Create Date: 2026-06-11

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "d5f9a3b2c104"
down_revision = "c4d8e2f1a903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_flagged", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("is_banned", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("fraud_score", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("fraud_signals", JSONB, nullable=True, server_default="[]"))
    op.add_column("users", sa.Column("ban_reason", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("fraud_notes", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("flagged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("banned_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("fraud_scanned_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "fraud_scanned_at")
    op.drop_column("users", "banned_at")
    op.drop_column("users", "flagged_at")
    op.drop_column("users", "fraud_notes")
    op.drop_column("users", "ban_reason")
    op.drop_column("users", "fraud_signals")
    op.drop_column("users", "fraud_score")
    op.drop_column("users", "is_banned")
    op.drop_column("users", "is_flagged")

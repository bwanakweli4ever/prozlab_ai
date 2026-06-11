"""add verification_evidences to proz_profiles

Revision ID: c4d8e2f1a903
Revises: b7e2a1c904f2
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "c4d8e2f1a903"
down_revision = "b7e2a1c904f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proz_profiles",
        sa.Column("verification_evidences", JSONB, nullable=True, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("proz_profiles", "verification_evidences")

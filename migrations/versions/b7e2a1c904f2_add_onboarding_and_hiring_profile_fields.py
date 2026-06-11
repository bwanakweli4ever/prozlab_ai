"""add onboarding and hiring profile fields

Revision ID: b7e2a1c904f2
Revises: 3652d98b88df
Create Date: 2026-06-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b7e2a1c904f2"
down_revision: Union[str, None] = "3652d98b88df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onboarding_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("completed_steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("step_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_onboarding_progress_id"), "onboarding_progress", ["id"], unique=False)
    op.create_index(op.f("ix_onboarding_progress_user_id"), "onboarding_progress", ["user_id"], unique=True)

    op.add_column("proz_profiles", sa.Column("experience_level", sa.String(length=50), nullable=True))
    op.add_column("proz_profiles", sa.Column("work_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("proz_profiles", sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("proz_profiles", sa.Column("portfolio_links", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column(
        "proz_profiles",
        sa.Column("skill_verification_status", sa.String(length=30), nullable=True, server_default="not_started"),
    )
    op.add_column(
        "proz_profiles",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=True, server_default="false"),
    )
    op.add_column("proz_profiles", sa.Column("predicted_success_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("proz_profiles", "predicted_success_score")
    op.drop_column("proz_profiles", "onboarding_completed")
    op.drop_column("proz_profiles", "skill_verification_status")
    op.drop_column("proz_profiles", "portfolio_links")
    op.drop_column("proz_profiles", "skills")
    op.drop_column("proz_profiles", "work_types")
    op.drop_column("proz_profiles", "experience_level")

    op.drop_index(op.f("ix_onboarding_progress_user_id"), table_name="onboarding_progress")
    op.drop_index(op.f("ix_onboarding_progress_id"), table_name="onboarding_progress")
    op.drop_table("onboarding_progress")

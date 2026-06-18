"""Add service request messages and proposals tables

Revision ID: e8f1a2b3c4d5
Revises: d5f9a3b2c104
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa


revision = "e8f1a2b3c4d5"
down_revision = "d5f9a3b2c104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_request_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("service_request_id", sa.UUID(), nullable=False),
        sa.Column("author_type", sa.String(length=20), nullable=False),
        sa.Column("author_name", sa.String(length=120), nullable=False),
        sa.Column("author_email", sa.String(length=255), nullable=True),
        sa.Column("message_type", sa.String(length=30), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("requested_budget_min", sa.Float(), nullable=True),
        sa.Column("requested_budget_max", sa.Float(), nullable=True),
        sa.Column("requested_days", sa.Integer(), nullable=True),
        sa.Column("email_sent", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["service_request_id"], ["service_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_service_request_messages_service_request_id", "service_request_messages", ["service_request_id"])

    op.create_table(
        "service_request_proposals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("service_request_id", sa.UUID(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("proposal_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("introduction", sa.Text(), nullable=True),
        sa.Column("line_items", sa.JSON(), nullable=True),
        sa.Column("subtotal", sa.Float(), nullable=True),
        sa.Column("tax_rate", sa.Float(), nullable=True),
        sa.Column("tax_amount", sa.Float(), nullable=True),
        sa.Column("total", sa.Float(), nullable=True),
        sa.Column("estimated_days", sa.Integer(), nullable=True),
        sa.Column("budget_amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("public_token", sa.String(length=64), nullable=False),
        sa.Column("document_url", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["service_request_id"], ["service_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_token"),
    )
    op.create_index("ix_service_request_proposals_service_request_id", "service_request_proposals", ["service_request_id"])
    op.create_index("ix_service_request_proposals_public_token", "service_request_proposals", ["public_token"])


def downgrade() -> None:
    op.drop_index("ix_service_request_proposals_public_token", table_name="service_request_proposals")
    op.drop_index("ix_service_request_proposals_service_request_id", table_name="service_request_proposals")
    op.drop_table("service_request_proposals")
    op.drop_index("ix_service_request_messages_service_request_id", table_name="service_request_messages")
    op.drop_table("service_request_messages")

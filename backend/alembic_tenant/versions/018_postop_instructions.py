"""Portal hardening: postop_instructions table.

Revision ID: 018_postop_instructions
Revises: gap12_facial_aesthetics
Create Date: 2026-03-12

Creates:
  - postop_instructions — tracks instructions sent to individual patients
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "018_postop_instructions"
down_revision = "gap12_facial_aesthetics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "postop_instructions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("postop_templates.id"), nullable=True),
        sa.Column("procedure_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("instruction_content", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="portal"),
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_postop_instructions_patient", "postop_instructions", ["patient_id"])
    op.create_index("idx_postop_instructions_sent_at", "postop_instructions", ["sent_at"])


def downgrade() -> None:
    op.drop_index("idx_postop_instructions_sent_at", table_name="postop_instructions")
    op.drop_index("idx_postop_instructions_patient", table_name="postop_instructions")
    op.drop_table("postop_instructions")

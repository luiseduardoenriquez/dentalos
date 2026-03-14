"""Add voice_clinical_notes table for AI voice clinical notes (AI-03).

Revision ID: 028
Revises: 027
Create Date: 2026-03-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_clinical_notes",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("voice_sessions.id"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("input_text", sa.Text, nullable=False),
        sa.Column("structured_note", JSONB, nullable=False, server_default="{}"),
        sa.Column("linked_teeth", ARRAY(sa.Integer), nullable=True),
        sa.Column("linked_cie10_codes", JSONB, nullable=False, server_default="[]"),
        sa.Column("linked_cups_codes", JSONB, nullable=False, server_default="[]"),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("evolution_templates.id"), nullable=True),
        sa.Column("template_mapping", JSONB, nullable=True),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clinical_record_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('processing', 'completed', 'failed', 'saved', 'discarded')",
            name="chk_voice_clinical_notes_status",
        ),
    )
    op.create_index("idx_voice_clinical_notes_session", "voice_clinical_notes", ["session_id"])
    op.create_index("idx_voice_clinical_notes_patient", "voice_clinical_notes", ["patient_id"])
    op.create_index("idx_voice_clinical_notes_doctor", "voice_clinical_notes", ["doctor_id"])
    op.create_index("idx_voice_clinical_notes_created", "voice_clinical_notes", ["created_at"])


def downgrade() -> None:
    op.drop_table("voice_clinical_notes")

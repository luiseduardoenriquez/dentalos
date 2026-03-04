"""Add Sprint 29-30 tables: financing, chatbot, NPS surveys, video sessions.

Revision ID: 014_sprint29_financing
Revises: 013_sprint27_ai_marketing
Create Date: 2026-03-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "014_sprint29_financing"
down_revision: Union[str, None] = "013_sprint27_ai_marketing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. financing_applications ─────────────────────────────────────────
    op.create_table(
        "financing_applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("installments", sa.Integer(), nullable=False),
        sa.Column("interest_rate_bps", sa.Integer(), nullable=True),
        sa.Column("provider_reference", sa.String(255), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disbursed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "provider IN ('addi', 'sistecredito', 'mercadopago')",
            name="chk_financing_applications_provider",
        ),
        sa.CheckConstraint(
            "status IN ('requested', 'approved', 'rejected', 'disbursed', 'repaying', 'completed', 'cancelled')",
            name="chk_financing_applications_status",
        ),
        sa.CheckConstraint("amount_cents > 0", name="chk_financing_applications_amount"),
        sa.CheckConstraint("installments > 0", name="chk_financing_applications_installments"),
    )
    op.create_index("idx_financing_applications_patient_id", "financing_applications", ["patient_id"])
    op.create_index("idx_financing_applications_invoice_id", "financing_applications", ["invoice_id"])
    op.create_index("idx_financing_applications_status", "financing_applications", ["status"])

    # ── 2. financing_payments ─────────────────────────────────────────────
    op.create_table(
        "financing_payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("financing_applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("installment_number", sa.Integer(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'paid', 'overdue', 'defaulted')",
            name="chk_financing_payments_status",
        ),
        sa.CheckConstraint("amount_cents > 0", name="chk_financing_payments_amount"),
        sa.CheckConstraint("installment_number > 0", name="chk_financing_payments_number"),
    )
    op.create_index("idx_financing_payments_application_id", "financing_payments", ["application_id"])
    op.create_index("idx_financing_payments_status", "financing_payments", ["status"])

    # ── 3. chatbot_conversations ──────────────────────────────────────────
    op.create_table(
        "chatbot_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "whatsapp_conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("whatsapp_conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("intent_history", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "channel IN ('whatsapp', 'web')",
            name="chk_chatbot_conversations_channel",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'resolved', 'escalated')",
            name="chk_chatbot_conversations_status",
        ),
    )
    op.create_index("idx_chatbot_conversations_patient_id", "chatbot_conversations", ["patient_id"])
    op.create_index("idx_chatbot_conversations_status", "chatbot_conversations", ["status"])

    # ── 4. chatbot_messages ───────────────────────────────────────────────
    op.create_table(
        "chatbot_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chatbot_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(30), nullable=True),
        sa.Column("confidence_score", sa.Numeric(3, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="chk_chatbot_messages_role",
        ),
        sa.CheckConstraint(
            "intent IS NULL OR intent IN ('schedule', 'reschedule', 'cancel', 'faq', 'payment', 'hours', 'location', 'emergency', 'other')",
            name="chk_chatbot_messages_intent",
        ),
    )
    op.create_index("idx_chatbot_messages_conversation_id", "chatbot_messages", ["conversation_id"])

    # ── 5. nps_survey_responses ───────────────────────────────────────────
    op.create_table(
        "nps_survey_responses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("nps_score", sa.SmallInteger(), nullable=False),
        sa.Column("csat_score", sa.SmallInteger(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("channel_sent", sa.String(20), nullable=False, server_default="whatsapp"),
        sa.Column("survey_token", sa.String(64), unique=True, nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("nps_score >= 0 AND nps_score <= 10", name="chk_nps_survey_responses_nps"),
        sa.CheckConstraint("csat_score IS NULL OR (csat_score >= 1 AND csat_score <= 5)", name="chk_nps_survey_responses_csat"),
    )
    op.create_index("idx_nps_survey_responses_patient_id", "nps_survey_responses", ["patient_id"])
    op.create_index("idx_nps_survey_responses_doctor_id", "nps_survey_responses", ["doctor_id"])
    op.create_index("idx_nps_survey_responses_survey_token", "nps_survey_responses", ["survey_token"])

    # ── 6. video_sessions ─────────────────────────────────────────────────
    op.create_table(
        "video_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(20), nullable=False, server_default="daily"),
        sa.Column("provider_session_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="created"),
        sa.Column("join_url_doctor", sa.String(512), nullable=True),
        sa.Column("join_url_patient", sa.String(512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("recording_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "provider IN ('daily', 'twilio')",
            name="chk_video_sessions_provider",
        ),
        sa.CheckConstraint(
            "status IN ('created', 'waiting', 'active', 'ended')",
            name="chk_video_sessions_status",
        ),
    )
    op.create_index("idx_video_sessions_appointment_id", "video_sessions", ["appointment_id"])
    op.create_index("idx_video_sessions_status", "video_sessions", ["status"])

    # ── 7. ALTER clinic_settings: add JSONB config columns ────────────────
    op.add_column(
        "clinic_settings",
        sa.Column(
            "chatbot_config",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "clinic_settings",
        sa.Column(
            "financing_config",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "clinic_settings",
        sa.Column(
            "telemedicine_config",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("clinic_settings", "telemedicine_config")
    op.drop_column("clinic_settings", "financing_config")
    op.drop_column("clinic_settings", "chatbot_config")
    op.drop_table("video_sessions")
    op.drop_table("nps_survey_responses")
    op.drop_table("chatbot_messages")
    op.drop_table("chatbot_conversations")
    op.drop_table("financing_payments")
    op.drop_table("financing_applications")

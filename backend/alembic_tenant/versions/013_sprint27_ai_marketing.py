"""Add Sprint 27-28 tables: WhatsApp chat, AI treatment, email campaigns + patient email unsub.

Revision ID: 013_sprint27_ai_marketing
Revises: 012_sprint25_reputation
Create Date: 2026-03-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "013_sprint27_ai_marketing"
down_revision: Union[str, None] = "012_sprint25_reputation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ALTER patients: add email unsubscribe columns ─────────────────────
    op.add_column(
        "patients",
        sa.Column(
            "email_unsubscribed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "email_unsubscribed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ── whatsapp_conversations ────────────────────────────────────────────
    op.create_table(
        "whatsapp_conversations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=True,
        ),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "unread_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived', 'closed')",
            name="chk_whatsapp_conversations_status",
        ),
    )
    op.create_index(
        "idx_whatsapp_conversations_phone",
        "whatsapp_conversations",
        ["phone_number"],
    )
    op.create_index(
        "idx_whatsapp_conversations_patient",
        "whatsapp_conversations",
        ["patient_id"],
    )
    op.create_index(
        "idx_whatsapp_conversations_status",
        "whatsapp_conversations",
        ["status"],
    )

    # ── whatsapp_messages ─────────────────────────────────────────────────
    op.create_table(
        "whatsapp_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("whatsapp_conversations.id"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("media_url", sa.String(500), nullable=True),
        sa.Column("media_type", sa.String(50), nullable=True),
        sa.Column("whatsapp_message_id", sa.String(100), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "sent_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="chk_whatsapp_messages_direction",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'delivered', 'read', 'failed')",
            name="chk_whatsapp_messages_status",
        ),
    )
    op.create_index(
        "idx_whatsapp_messages_conversation",
        "whatsapp_messages",
        ["conversation_id", "created_at"],
    )

    # ── whatsapp_quick_replies ────────────────────────────────────────────
    op.create_table(
        "whatsapp_quick_replies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── ai_treatment_suggestions ──────────────────────────────────────────
    op.create_table(
        "ai_treatment_suggestions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "odontogram_snapshot",
            postgresql.JSONB(),
            nullable=True,
        ),
        sa.Column(
            "patient_context",
            postgresql.JSONB(),
            nullable=True,
        ),
        sa.Column(
            "suggestions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column(
            "input_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "output_tokens",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending_review'"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "treatment_plan_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending_review', 'reviewed', 'applied', 'rejected')",
            name="chk_ai_treatment_suggestions_status",
        ),
    )
    op.create_index(
        "idx_ai_treatment_suggestions_patient",
        "ai_treatment_suggestions",
        ["patient_id"],
    )
    op.create_index(
        "idx_ai_treatment_suggestions_doctor",
        "ai_treatment_suggestions",
        ["doctor_id"],
    )

    # ── email_campaigns ───────────────────────────────────────────────────
    op.create_table(
        "email_campaigns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("template_id", sa.String(100), nullable=True),
        sa.Column("template_html", sa.Text(), nullable=True),
        sa.Column(
            "segment_filters",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "sent_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "open_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "click_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "bounce_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "unsubscribe_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'scheduled', 'sending', 'sent', 'cancelled')",
            name="chk_email_campaigns_status",
        ),
    )
    op.create_index(
        "idx_email_campaigns_status",
        "email_campaigns",
        ["status"],
    )

    # ── email_campaign_recipients ─────────────────────────────────────────
    op.create_table(
        "email_campaign_recipients",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("email_campaigns.id"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patients.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "campaign_id",
            "patient_id",
            name="uq_email_campaign_recipients_campaign_patient",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'opened', 'clicked', 'bounced', 'unsubscribed')",
            name="chk_email_campaign_recipients_status",
        ),
    )
    op.create_index(
        "idx_email_campaign_recipients_campaign",
        "email_campaign_recipients",
        ["campaign_id"],
    )

    # ── Seed data: WhatsApp quick replies ─────────────────────────────────
    op.execute(
        """
        INSERT INTO whatsapp_quick_replies (id, title, body, category, sort_order, is_active)
        VALUES
          (gen_random_uuid(), 'Confirmar cita', 'Hola, le confirmamos su cita para el día {fecha} a las {hora}. ¡Le esperamos!', 'appointment', 1, true),
          (gen_random_uuid(), 'Indicaciones para llegar', 'Nuestra dirección es {direccion}. Puede ubicarnos en Google Maps en el siguiente enlace: {link_mapa}', 'general', 2, true),
          (gen_random_uuid(), 'Horarios de atención', 'Nuestros horarios de atención son: Lunes a Viernes de {hora_inicio} a {hora_fin}. Sábados de {hora_inicio_sab} a {hora_fin_sab}.', 'general', 3, true),
          (gen_random_uuid(), 'Cuidados post-operatorios', 'Recuerde seguir estas indicaciones después de su procedimiento: {indicaciones}. Si presenta alguna molestia, no dude en contactarnos.', 'clinical', 4, true),
          (gen_random_uuid(), 'Agradecimiento', '¡Gracias por confiar en {nombre_clinica}! Esperamos que su experiencia haya sido excelente. Si necesita algo más, estamos para servirle.', 'general', 5, true)
        """
    )


def downgrade() -> None:
    op.drop_table("email_campaign_recipients")
    op.drop_table("email_campaigns")
    op.drop_table("ai_treatment_suggestions")
    op.drop_table("whatsapp_quick_replies")
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_conversations")
    op.drop_column("patients", "email_unsubscribed_at")
    op.drop_column("patients", "email_unsubscribed")

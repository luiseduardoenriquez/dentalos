"""Add idempotency_key to voice_transcriptions.

Revision ID: 020_voice_idempotency_key
Revises: 019_clinic_settings
Create Date: 2026-03-13

Adds:
  - idempotency_key VARCHAR(64) nullable column to voice_transcriptions
  - Index on (session_id, idempotency_key) for fast duplicate lookup
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "020_voice_idempotency_key"
down_revision = "019_clinic_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_transcriptions",
        sa.Column("idempotency_key", sa.String(64), nullable=True),
    )
    op.create_index(
        "idx_voice_transcriptions_idempotency",
        "voice_transcriptions",
        ["session_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_voice_transcriptions_idempotency",
        table_name="voice_transcriptions",
    )
    op.drop_column("voice_transcriptions", "idempotency_key")

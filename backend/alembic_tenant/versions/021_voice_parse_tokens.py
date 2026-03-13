"""Add input_tokens and output_tokens to voice_parses.

Revision ID: 021_voice_parse_tokens
Revises: 020_voice_idempotency_key
Create Date: 2026-03-13

Adds token tracking columns to voice_parses so AI usage metrics
can aggregate Claude API token consumption from voice-to-odontogram.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "021_voice_parse_tokens"
down_revision = "020_voice_idempotency_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_parses",
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "voice_parses",
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("voice_parses", "output_tokens")
    op.drop_column("voice_parses", "input_tokens")

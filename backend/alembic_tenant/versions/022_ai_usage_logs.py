"""Create ai_usage_logs table for unified AI metrics.

Revision ID: 022_ai_usage_logs
Revises: 021_voice_parse_tokens
Create Date: 2026-03-13

Central log for all AI API calls (Claude, Whisper, Ollama) across features.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers
revision = "022_ai_usage_logs"
down_revision = "021_voice_parse_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("feature", sa.String(30), nullable=False),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_ai_usage_logs_doctor_created", "ai_usage_logs", ["doctor_id", "created_at"])
    op.create_index("idx_ai_usage_logs_feature", "ai_usage_logs", ["feature"])


def downgrade() -> None:
    op.drop_index("idx_ai_usage_logs_feature", table_name="ai_usage_logs")
    op.drop_index("idx_ai_usage_logs_doctor_created", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")

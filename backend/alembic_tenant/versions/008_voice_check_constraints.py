"""Add feedback_received/failed statuses to voice CHECK constraints.

Revision ID: 008_voice_checks
Revises: 007_notification_tables
Create Date: 2026-02-27

Fixes:
  C1+C2: VoiceSession.status now allows 'feedback_received'
  C2+C4: VoiceParse.status now allows 'feedback' and 'failed'
"""

from typing import Sequence, Union

from alembic import op

revision: str = "008_voice_checks"
down_revision: Union[str, None] = "007_notification_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old constraints and recreate with expanded values
    op.drop_constraint("chk_voice_sessions_status", "voice_sessions", type_="check")
    op.create_check_constraint(
        "chk_voice_sessions_status",
        "voice_sessions",
        "status IN ('active', 'applied', 'expired', 'feedback_received')",
    )

    op.drop_constraint("chk_voice_parses_status", "voice_parses", type_="check")
    op.create_check_constraint(
        "chk_voice_parses_status",
        "voice_parses",
        "status IN ('success', 'partial', 'feedback', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_voice_parses_status", "voice_parses", type_="check")
    op.create_check_constraint(
        "chk_voice_parses_status",
        "voice_parses",
        "status IN ('success', 'partial')",
    )

    op.drop_constraint("chk_voice_sessions_status", "voice_sessions", type_="check")
    op.create_check_constraint(
        "chk_voice_sessions_status",
        "voice_sessions",
        "status IN ('active', 'applied', 'expired')",
    )

"""Add must_change_password to portal_credentials.

Revision ID: 009_must_change_pw
Revises: 008_voice_checks
Create Date: 2026-02-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "009_must_change_pw"
down_revision: Union[str, None] = "008_voice_checks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "portal_credentials",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("portal_credentials", "must_change_password")

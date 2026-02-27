"""Create portal_credentials and portal_invitations tables.

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
    op.create_table(
        "portal_credentials",
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", name="uq_portal_credentials_patient"),
    )
    op.create_index("idx_portal_credentials_patient_id", "portal_credentials", ["patient_id"])

    op.create_table(
        "portal_invitations",
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=15), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("channel IN ('email', 'whatsapp')", name="chk_portal_invitations_channel"),
        sa.CheckConstraint("status IN ('pending', 'sent', 'accepted', 'expired')", name="chk_portal_invitations_status"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_portal_invitations_patient_id", "portal_invitations", ["patient_id"])
    op.create_index("idx_portal_invitations_token_hash", "portal_invitations", ["token_hash"])
    op.create_index(
        "idx_portal_invitations_expires",
        "portal_invitations",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_table("portal_invitations")
    op.drop_table("portal_credentials")

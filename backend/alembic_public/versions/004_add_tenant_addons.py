"""Add addons JSONB column to tenants table

Revision ID: 004_add_tenant_addons
Revises: 003_admin_tables
Create Date: 2026-02-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "004_add_tenant_addons"
down_revision: Union[str, None] = "003_admin_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "addons",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="Per-tenant add-on subscriptions, e.g. {'voice_dictation': true}",
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("tenants", "addons", schema="public")

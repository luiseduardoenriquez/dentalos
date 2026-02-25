"""Add service_catalog table to tenant schema

Revision ID: 007_add_service_catalog
Revises: 006_add_evolution_templates
Create Date: 2026-02-25

One table:
  - service_catalog: per-tenant CUPS service price list (COP cents)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "007_add_service_catalog"
down_revision: Union[str, None] = "006_add_evolution_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_catalog",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("cups_code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("default_price", sa.Integer, nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("cups_code", name="uq_service_catalog_cups_code"),
        sa.CheckConstraint(
            "category IN ("
            "'diagnostic','preventive','restorative','endodontic',"
            "'periodontic','surgical','orthodontic','prosthodontic','other'"
            ")",
            name="chk_service_catalog_category",
        ),
    )
    op.create_index("idx_service_catalog_category", "service_catalog", ["category"])
    op.create_index("idx_service_catalog_cups_code", "service_catalog", ["cups_code"])


def downgrade() -> None:
    op.drop_index("idx_service_catalog_cups_code", table_name="service_catalog")
    op.drop_index("idx_service_catalog_category", table_name="service_catalog")
    op.drop_table("service_catalog")

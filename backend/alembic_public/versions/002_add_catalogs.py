"""Add CIE-10 and CUPS catalog tables to public schema

Revision ID: 002_add_catalogs
Revises: 001_initial_public
Create Date: 2026-02-25

Two tables:
  - cie10_catalog: ICD-10 diagnosis codes (Spanish edition)
  - cups_catalog:  Colombian CUPS procedure codes

Both tables include GIN full-text search indexes on the Spanish description
column for efficient type-ahead search from the clinical UI.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "002_add_catalogs"
down_revision: Union[str, None] = "001_initial_public"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── cie10_catalog ────────────────────────────────────────────────────
    op.create_table(
        "cie10_catalog",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_cie10_catalog_code", "cie10_catalog", ["code"], schema="public")
    op.create_index("idx_cie10_catalog_category", "cie10_catalog", ["category"], schema="public")

    # GIN FTS index for Spanish full-text search
    op.execute("""
        CREATE INDEX idx_cie10_catalog_description_fts
        ON public.cie10_catalog
        USING GIN (to_tsvector('spanish', description))
    """)

    # ── cups_catalog ─────────────────────────────────────────────────────
    op.create_table(
        "cups_catalog",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        schema="public",
    )
    op.create_index("idx_cups_catalog_code", "cups_catalog", ["code"], schema="public")
    op.create_index("idx_cups_catalog_category", "cups_catalog", ["category"], schema="public")

    # GIN FTS index for Spanish full-text search
    op.execute("""
        CREATE INDEX idx_cups_catalog_description_fts
        ON public.cups_catalog
        USING GIN (to_tsvector('spanish', description))
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.idx_cups_catalog_description_fts")
    op.drop_index("idx_cups_catalog_category", table_name="cups_catalog", schema="public")
    op.drop_index("idx_cups_catalog_code", table_name="cups_catalog", schema="public")
    op.drop_table("cups_catalog", schema="public")

    op.execute("DROP INDEX IF EXISTS public.idx_cie10_catalog_description_fts")
    op.drop_index("idx_cie10_catalog_category", table_name="cie10_catalog", schema="public")
    op.drop_index("idx_cie10_catalog_code", table_name="cie10_catalog", schema="public")
    op.drop_table("cie10_catalog", schema="public")

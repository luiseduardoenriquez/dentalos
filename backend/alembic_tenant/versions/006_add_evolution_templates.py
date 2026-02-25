"""Add evolution template tables to tenant schema

Revision ID: 006_add_evolution_templates
Revises: 005_add_clinical_records
Create Date: 2026-02-25

Three tables:
  - evolution_templates:          template header (name, procedure type, complexity)
  - evolution_template_steps:     ordered steps with [variable] placeholders
  - evolution_template_variables: variable definitions for placeholder substitution
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "006_add_evolution_templates"
down_revision: Union[str, None] = "005_add_clinical_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── evolution_templates ───────────────────────────────────────────────
    op.create_table(
        "evolution_templates",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("procedure_type", sa.String(50), nullable=False),
        sa.Column("cups_code", sa.String(10), nullable=True),
        sa.Column("complexity", sa.String(20), nullable=False, server_default="simple"),
        sa.Column("is_builtin", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "complexity IN ('simple', 'moderate', 'complex')",
            name="chk_evolution_templates_complexity",
        ),
    )
    op.create_index("idx_evolution_templates_procedure_type", "evolution_templates", ["procedure_type"])
    op.create_index("idx_evolution_templates_is_active", "evolution_templates", ["is_active"])

    # ── evolution_template_steps ──────────────────────────────────────────
    op.create_table(
        "evolution_template_steps",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evolution_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("template_id", "step_order", name="uq_evolution_template_steps_order"),
    )
    op.create_index("idx_evolution_template_steps_template", "evolution_template_steps", ["template_id"])

    # ── evolution_template_variables ──────────────────────────────────────
    op.create_table(
        "evolution_template_variables",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("evolution_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("variable_type", sa.String(20), nullable=False),
        sa.Column("options", JSONB, nullable=True),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("template_id", "name", name="uq_evolution_template_variables_name"),
        sa.CheckConstraint(
            "variable_type IN ('text', 'number', 'select', 'date')",
            name="chk_evolution_template_variables_type",
        ),
    )
    op.create_index("idx_evolution_template_variables_template", "evolution_template_variables", ["template_id"])


def downgrade() -> None:
    op.drop_index("idx_evolution_template_variables_template", table_name="evolution_template_variables")
    op.drop_table("evolution_template_variables")

    op.drop_index("idx_evolution_template_steps_template", table_name="evolution_template_steps")
    op.drop_table("evolution_template_steps")

    op.drop_index("idx_evolution_templates_is_active", table_name="evolution_templates")
    op.drop_index("idx_evolution_templates_procedure_type", table_name="evolution_templates")
    op.drop_table("evolution_templates")

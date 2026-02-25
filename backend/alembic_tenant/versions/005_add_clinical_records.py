"""Add clinical records and anamnesis tables to tenant schema

Revision ID: 005_add_clinical_records
Revises: 004_add_odontogram
Create Date: 2026-02-25

Two tables:
  - clinical_records: examination, evolution note, or procedure entry
  - anamnesis:        one-per-patient medical/dental history form
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "005_add_clinical_records"
down_revision: Union[str, None] = "004_add_odontogram"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── clinical_records ─────────────────────────────────────────────────
    op.create_table(
        "clinical_records",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("tooth_numbers", ARRAY(sa.Integer), nullable=True),
        sa.Column("template_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_editable", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("edit_locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "type IN ('examination', 'evolution_note', 'procedure')",
            name="chk_clinical_records_type",
        ),
    )
    op.create_index("idx_clinical_records_patient", "clinical_records", ["patient_id"])
    op.create_index("idx_clinical_records_doctor", "clinical_records", ["doctor_id"])
    op.create_index("idx_clinical_records_type", "clinical_records", ["type"])
    op.create_index("idx_clinical_records_created_at", "clinical_records", ["created_at"])

    # Now that clinical_records exists, add the FK on odontogram_snapshots
    op.create_foreign_key(
        "fk_odontogram_snapshots_linked_record",
        "odontogram_snapshots",
        "clinical_records",
        ["linked_record_id"],
        ["id"],
    )

    # ── anamnesis ────────────────────────────────────────────────────────
    op.create_table(
        "anamnesis",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, unique=True),
        sa.Column("allergies", JSONB, nullable=True),
        sa.Column("medications", JSONB, nullable=True),
        sa.Column("medical_history", JSONB, nullable=True),
        sa.Column("dental_history", JSONB, nullable=True),
        sa.Column("family_history", JSONB, nullable=True),
        sa.Column("habits", JSONB, nullable=True),
        sa.Column("last_updated_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("patient_id", name="uq_anamnesis_patient"),
    )


def downgrade() -> None:
    op.drop_table("anamnesis")

    op.drop_constraint("fk_odontogram_snapshots_linked_record", "odontogram_snapshots", type_="foreignkey")

    op.drop_index("idx_clinical_records_created_at", table_name="clinical_records")
    op.drop_index("idx_clinical_records_type", table_name="clinical_records")
    op.drop_index("idx_clinical_records_doctor", table_name="clinical_records")
    op.drop_index("idx_clinical_records_patient", table_name="clinical_records")
    op.drop_table("clinical_records")

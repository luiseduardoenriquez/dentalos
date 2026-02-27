"""Add performance indexes for N+1 and FTS optimization.

Adds four indexes that were missing from the baseline schema:
  - idx_patients_fts        GIN full-text search over name + document_number
  - idx_consents_doctor     FK index on consents.doctor_id
  - idx_payment_plans_patient  FK index on payment_plans.patient_id
  - idx_procedures_clinical_record  FK index on procedures.clinical_record_id

Revision ID: 006_perf_indexes
Revises: 005_inventory_tables
Create Date: 2026-02-26 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_perf_indexes"
down_revision: Union[str, None] = "005_inventory_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Patient full-text search GIN index (Spanish dictionary).
    # Covers first_name, last_name, and document_number for fast ILIKE-free search.
    # CREATE INDEX IF NOT EXISTS is safe to re-run across all tenant schemas.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_patients_fts
        ON patients USING gin(
            to_tsvector('spanish',
                coalesce(first_name, '') || ' ' ||
                coalesce(last_name, '') || ' ' ||
                coalesce(document_number, ''))
        )
        """
    )

    # FK index: consents.doctor_id — queries like "all consents for this doctor"
    # were doing sequential scans because only patient_id / status were indexed.
    op.create_index("idx_consents_doctor", "consents", ["doctor_id"])

    # FK index: payment_plans.patient_id — billing summary queries per patient
    # were missing this index despite invoice_id being indexed.
    op.create_index("idx_payment_plans_patient", "payment_plans", ["patient_id"])

    # FK index: procedures.clinical_record_id — clinical record detail page
    # eager-loads its procedures; without this index every fetch was a seqscan.
    op.create_index(
        "idx_procedures_clinical_record", "procedures", ["clinical_record_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_procedures_clinical_record", table_name="procedures")
    op.drop_index("idx_payment_plans_patient", table_name="payment_plans")
    op.drop_index("idx_consents_doctor", table_name="consents")
    op.drop_index("idx_patients_fts", table_name="patients")

"""add compliance tables (RIPS, e-invoicing)

Revision ID: 004_compliance_tables
Revises: 003_add_commission_percentage
Create Date: 2026-02-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004_compliance_tables'
down_revision: Union[str, None] = '003_add_commission_percentage'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # RIPS batches
    op.create_table(
        'rips_batches',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='queued'),
        sa.Column('file_types', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('warning_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('queued', 'generating', 'generated', 'validated', 'failed')", name='chk_rips_batches_status'),
    )
    op.create_index('idx_rips_batches_status', 'rips_batches', ['status'])
    op.create_index('idx_rips_batches_period', 'rips_batches', ['period_start', 'period_end'])

    # RIPS batch files
    op.create_table(
        'rips_batch_files',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('batch_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('rips_batches.id'), nullable=False),
        sa.Column('file_type', sa.String(5), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('record_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_rips_batch_files_batch', 'rips_batch_files', ['batch_id'])

    # RIPS batch errors
    op.create_table(
        'rips_batch_errors',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('batch_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('rips_batches.id'), nullable=False),
        sa.Column('severity', sa.String(10), nullable=False),
        sa.Column('rule_code', sa.String(30), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('record_ref', sa.String(100), nullable=True),
        sa.Column('field_name', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_rips_batch_errors_batch', 'rips_batch_errors', ['batch_id'])

    # E-invoices
    op.create_table(
        'e_invoices',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('invoice_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('invoices.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('cufe', sa.String(128), nullable=True),
        sa.Column('matias_submission_id', sa.String(100), nullable=True),
        sa.Column('dian_environment', sa.String(20), nullable=False, server_default='test'),
        sa.Column('xml_url', sa.String(500), nullable=True),
        sa.Column('pdf_url', sa.String(500), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'submitted', 'accepted', 'rejected', 'error')", name='chk_e_invoices_status'),
    )
    op.create_index('idx_e_invoices_invoice', 'e_invoices', ['invoice_id'])
    op.create_index('idx_e_invoices_status', 'e_invoices', ['status'])

    # Tenant e-invoice config
    op.create_table(
        'tenant_einvoice_configs',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('nit', sa.String(20), nullable=False),
        sa.Column('nit_dv', sa.String(1), nullable=True),
        sa.Column('resolution_number', sa.String(30), nullable=True),
        sa.Column('resolution_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_prefix', sa.String(10), nullable=True),
        sa.Column('range_start', sa.Integer(), nullable=True),
        sa.Column('range_end', sa.Integer(), nullable=True),
        sa.Column('certificate_s3_path', sa.String(500), nullable=True),
        sa.Column('dian_environment', sa.String(20), nullable=False, server_default='test'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('tenant_einvoice_configs')
    op.drop_table('e_invoices')
    op.drop_table('rips_batch_errors')
    op.drop_table('rips_batch_files')
    op.drop_table('rips_batches')

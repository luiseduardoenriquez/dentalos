"""add inventory, sterilization, and implant placement tables

Revision ID: 005_inventory_tables
Revises: 004_compliance_tables
Create Date: 2026-02-26 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '005_inventory_tables'
down_revision: Union[str, None] = '004_compliance_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── inventory_items ──────────────────────────────────────────────────
    op.create_table(
        'inventory_items',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Numeric(), nullable=False, server_default='0'),
        sa.Column('unit', sa.String(10), nullable=False, server_default='units'),
        sa.Column('lot_number', sa.String(100), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column(
            'expiry_status',
            sa.String(10),
            sa.Computed(
                "CASE "
                "WHEN expiry_date IS NULL THEN 'ok' "
                "WHEN expiry_date < CURRENT_DATE THEN 'expired' "
                "WHEN expiry_date < CURRENT_DATE + INTERVAL '30 days' THEN 'critical' "
                "WHEN expiry_date < CURRENT_DATE + INTERVAL '90 days' THEN 'warning' "
                "ELSE 'ok' END",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column('manufacturer', sa.String(200), nullable=True),
        sa.Column('supplier', sa.String(200), nullable=True),
        sa.Column('cost_per_unit', sa.Integer(), nullable=True),
        sa.Column('minimum_stock', sa.Numeric(), nullable=False, server_default='0'),
        sa.Column('location', sa.String(100), nullable=True),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "category IN ('material', 'instrument', 'implant', 'medication')",
            name='chk_inventory_items_category',
        ),
        sa.CheckConstraint(
            "unit IN ('units', 'ml', 'g', 'boxes')",
            name='chk_inventory_items_unit',
        ),
    )
    op.create_index('idx_inventory_items_category', 'inventory_items', ['category'])
    op.create_index('idx_inventory_items_expiry_status', 'inventory_items', ['expiry_status'])
    op.create_index('idx_inventory_items_is_active', 'inventory_items', ['is_active'])

    # ── inventory_quantity_history ────────────────────────────────────────
    op.create_table(
        'inventory_quantity_history',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('item_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('inventory_items.id'), nullable=False),
        sa.Column('quantity_change', sa.Numeric(), nullable=False),
        sa.Column('reason', sa.String(20), nullable=False),
        sa.Column('previous_quantity', sa.Numeric(), nullable=False),
        sa.Column('new_quantity', sa.Numeric(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "reason IN ('received', 'consumed', 'discarded', 'adjustment')",
            name='chk_inventory_quantity_history_reason',
        ),
    )
    op.create_index('idx_inventory_quantity_history_item', 'inventory_quantity_history', ['item_id'])

    # ── sterilization_records ────────────────────────────────────────────
    op.create_table(
        'sterilization_records',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('autoclave_id', sa.String(100), nullable=False),
        sa.Column('load_number', sa.String(50), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('temperature_celsius', sa.Numeric(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('biological_indicator', sa.String(10), nullable=True),
        sa.Column('chemical_indicator', sa.String(10), nullable=True),
        sa.Column('responsible_user_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('signature_data', sa.Text(), nullable=True),
        sa.Column('signature_sha256_hash', sa.String(64), nullable=True),
        sa.Column(
            'is_compliant',
            sa.Boolean(),
            sa.Computed(
                "CASE "
                "WHEN biological_indicator = 'negative' AND chemical_indicator = 'pass' THEN true "
                "ELSE false END",
                persisted=True,
            ),
            nullable=True,
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('autoclave_id', 'load_number', 'date', name='uq_sterilization_autoclave_load_date'),
    )
    op.create_index('idx_sterilization_records_date', 'sterilization_records', ['date'])
    op.create_index('idx_sterilization_records_autoclave', 'sterilization_records', ['autoclave_id'])

    # ── sterilization_record_instruments (junction table) ────────────────
    op.create_table(
        'sterilization_record_instruments',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('sterilization_record_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('sterilization_records.id'), nullable=False),
        sa.Column('inventory_item_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('inventory_items.id'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_sterilization_record_instruments_record', 'sterilization_record_instruments', ['sterilization_record_id'])
    op.create_index('idx_sterilization_record_instruments_item', 'sterilization_record_instruments', ['inventory_item_id'])

    # ── implant_placements ───────────────────────────────────────────────
    op.create_table(
        'implant_placements',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('item_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('inventory_items.id'), nullable=False),
        sa.Column('patient_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.id'), nullable=False),
        sa.Column('procedure_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tooth_number', sa.Integer(), nullable=True),
        sa.Column('placement_date', sa.Date(), nullable=False),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('lot_number', sa.String(100), nullable=True),
        sa.Column('manufacturer', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_implant_placements_item', 'implant_placements', ['item_id'])
    op.create_index('idx_implant_placements_patient', 'implant_placements', ['patient_id'])
    op.create_index('idx_implant_placements_lot_number', 'implant_placements', ['lot_number'])


def downgrade() -> None:
    op.drop_table('implant_placements')
    op.drop_table('sterilization_record_instruments')
    op.drop_table('sterilization_records')
    op.drop_table('inventory_quantity_history')
    op.drop_table('inventory_items')

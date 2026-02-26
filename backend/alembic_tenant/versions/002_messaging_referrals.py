"""messaging and referrals

Revision ID: 002_messaging_referrals
Revises: 001_baseline
Create Date: 2026-02-26 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_messaging_referrals'
down_revision: Union[str, None] = '001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── message_threads ──────────────────────────────────────────────────
    op.create_table(
        'message_threads',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(200), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='open'),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.CheckConstraint("status IN ('open', 'closed', 'archived')", name='chk_message_threads_status'),
    )
    op.create_index('idx_message_threads_patient', 'message_threads', ['patient_id'])
    op.create_index('idx_message_threads_patient_last_msg', 'message_threads', ['patient_id', 'last_message_at'])

    # ── messages ─────────────────────────────────────────────────────────
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_type', sa.String(10), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('attachments', postgresql.JSONB, nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['message_threads.id']),
        sa.CheckConstraint("sender_type IN ('patient', 'staff')", name='chk_messages_sender_type'),
    )
    op.create_index('idx_messages_thread_created', 'messages', ['thread_id', 'created_at'])

    # ── thread_participants ──────────────────────────────────────────────
    op.create_table(
        'thread_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('thread_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['thread_id'], ['message_threads.id']),
        sa.UniqueConstraint('thread_id', 'user_id', name='uq_thread_participants_thread_user'),
    )

    # ── patient_referrals ────────────────────────────────────────────────
    op.create_table(
        'patient_referrals',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('from_doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('to_doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('priority', sa.String(10), nullable=False, server_default='normal'),
        sa.Column('specialty', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.text('true')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id']),
        sa.ForeignKeyConstraint(['from_doctor_id'], ['users.id']),
        sa.ForeignKeyConstraint(['to_doctor_id'], ['users.id']),
        sa.CheckConstraint("priority IN ('urgent', 'normal', 'low')", name='chk_patient_referrals_priority'),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'completed', 'declined')", name='chk_patient_referrals_status'),
        sa.CheckConstraint('from_doctor_id != to_doctor_id', name='chk_patient_referrals_different_doctors'),
    )
    op.create_index('idx_patient_referrals_patient', 'patient_referrals', ['patient_id'])
    op.create_index('idx_patient_referrals_to_doctor_status', 'patient_referrals', ['to_doctor_id', 'status'])


def downgrade() -> None:
    op.drop_table('patient_referrals')
    op.drop_table('thread_participants')
    op.drop_table('messages')
    op.drop_table('message_threads')

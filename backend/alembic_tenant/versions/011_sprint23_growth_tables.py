"""Add Sprint 23-24 growth tables: EPS verification, referrals, postop, cash registers, expenses, tasks.

Revision ID: 011_sprint23_growth
Revises: 010_sprint21_engage
Create Date: 2026-03-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "011_sprint23_growth"
down_revision: Union[str, None] = "010_sprint21_engage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ALTER payments: drop and re-create CHECK to add nequi, daviplata ---
    op.drop_constraint("chk_payments_method", "payments", type_="check")
    op.create_check_constraint(
        "chk_payments_method",
        "payments",
        "payment_method IN ('cash', 'card', 'transfer', 'nequi', 'daviplata', 'other')",
    )

    # --- ALTER users: add RETHUS columns ---
    op.add_column("users", sa.Column("rethus_number", sa.String(length=50), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "rethus_verification_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    op.create_check_constraint(
        "chk_users_rethus_status",
        "users",
        "rethus_verification_status IN ('pending', 'verified', 'failed', 'expired')",
    )
    op.add_column(
        "users",
        sa.Column("rethus_verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- eps_verifications ---
    op.create_table(
        "eps_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verification_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("eps_name", sa.String(length=200), nullable=True),
        sa.Column("eps_code", sa.String(length=20), nullable=True),
        sa.Column("affiliation_status", sa.String(length=20), nullable=True),
        sa.Column("regime", sa.String(length=20), nullable=True),
        sa.Column("copay_category", sa.String(length=10), nullable=True),
        sa.Column("raw_response", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "affiliation_status IN ('activo', 'inactivo', 'suspendido', 'retirado', 'no_afiliado')",
            name="chk_eps_verifications_affiliation_status",
        ),
        sa.CheckConstraint(
            "regime IN ('contributivo', 'subsidiado', 'vinculado', 'excepcion')",
            name="chk_eps_verifications_regime",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_eps_verifications_patient", "eps_verifications", ["patient_id"])

    # --- referral_codes ---
    op.create_table(
        "referral_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("uses_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("idx_referral_codes_patient", "referral_codes", ["patient_id"])
    op.create_index("idx_referral_codes_code", "referral_codes", ["code"])

    # --- referral_rewards ---
    op.create_table(
        "referral_rewards",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("referrer_patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referred_patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referral_code_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reward_type", sa.String(length=20), nullable=False),
        sa.Column("reward_amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("applied_to_invoice_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "reward_type IN ('discount', 'credit')",
            name="chk_referral_rewards_reward_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'applied', 'expired')",
            name="chk_referral_rewards_status",
        ),
        sa.ForeignKeyConstraint(["referrer_patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["referred_patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["referral_code_id"], ["referral_codes.id"]),
        sa.ForeignKeyConstraint(["applied_to_invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_referral_rewards_referrer", "referral_rewards", ["referrer_patient_id"])
    op.create_index("idx_referral_rewards_status", "referral_rewards", ["status"])

    # --- postop_templates ---
    op.create_table(
        "postop_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("procedure_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("instruction_content", sa.Text(), nullable=False),
        sa.Column("channel_preference", sa.String(length=20), nullable=False, server_default=sa.text("'all'")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.CheckConstraint(
            "channel_preference IN ('whatsapp', 'email', 'portal', 'all')",
            name="chk_postop_templates_channel_preference",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_postop_templates_procedure_type", "postop_templates", ["procedure_type"])
    op.create_index("idx_postop_templates_active", "postop_templates", ["is_active"])

    # --- cash_registers ---
    op.create_table(
        "cash_registers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'closed'")),
        sa.Column("opened_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_balance_cents", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("closing_balance_cents", sa.Integer(), nullable=True),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'closed')",
            name="chk_cash_registers_status",
        ),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["closed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cash_registers_status", "cash_registers", ["status"])

    # --- cash_movements ---
    op.create_table(
        "cash_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("register_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("payment_method", sa.String(length=20), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(length=30), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "type IN ('income', 'expense', 'adjustment')",
            name="chk_cash_movements_type",
        ),
        sa.ForeignKeyConstraint(["register_id"], ["cash_registers.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cash_movements_register", "cash_movements", ["register_id"])
    op.create_index("idx_cash_movements_type", "cash_movements", ["type"])

    # --- expense_categories ---
    op.create_table(
        "expense_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_expense_categories_active", "expense_categories", ["is_active"])

    # --- expenses ---
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("receipt_url", sa.String(length=500), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_expenses_category", "expenses", ["category_id"])
    op.create_index("idx_expenses_date", "expenses", ["expense_date"])

    # --- staff_tasks ---
    op.create_table(
        "staff_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default=sa.text("'normal'")),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(length=30), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "task_type IN ('delinquency', 'acceptance', 'manual')",
            name="chk_staff_tasks_task_type",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'in_progress', 'completed', 'dismissed')",
            name="chk_staff_tasks_status",
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="chk_staff_tasks_priority",
        ),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_staff_tasks_status", "staff_tasks", ["status"])
    op.create_index("idx_staff_tasks_type", "staff_tasks", ["task_type"])
    op.create_index("idx_staff_tasks_assigned", "staff_tasks", ["assigned_to"])

    # --- seed: default expense categories ---
    op.execute(
        sa.text(
            """
            INSERT INTO expense_categories (id, name, is_default, is_active, created_at, updated_at)
            VALUES
              (gen_random_uuid(), 'Arriendo', true, true, now(), now()),
              (gen_random_uuid(), 'Insumos', true, true, now(), now()),
              (gen_random_uuid(), 'Laboratorio', true, true, now(), now()),
              (gen_random_uuid(), 'Nómina', true, true, now(), now()),
              (gen_random_uuid(), 'Servicios públicos', true, true, now(), now()),
              (gen_random_uuid(), 'Marketing', true, true, now(), now()),
              (gen_random_uuid(), 'Equipos', true, true, now(), now()),
              (gen_random_uuid(), 'Otro', true, true, now(), now())
            """
        )
    )

    # --- seed: default postop templates ---
    op.execute(
        sa.text(
            """
            INSERT INTO postop_templates (id, procedure_type, title, instruction_content, channel_preference, is_default, is_active, created_at, updated_at)
            VALUES
              (gen_random_uuid(), 'resina', 'Cuidados post-resina', 'Evitar alimentos duros o pegajosos durante 24 horas. No consumir bebidas muy calientes o muy frías el primer día. Si siente sensibilidad, es normal y desaparecerá en pocos días.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'endodoncia', 'Cuidados post-endodoncia', 'No masticar con el diente tratado hasta la cita de control. Tome los medicamentos recetados según indicación. Puede presentar molestia leve los primeros días, es normal.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'exodoncia', 'Cuidados post-exodoncia', 'Muerda suavemente la gasa durante 30 minutos. No escupa, no use pitillo y no fume las primeras 24 horas. Si hay sangrado persistente, llame a la clínica.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'profilaxis', 'Cuidados post-profilaxis', 'Puede presentar sensibilidad leve al frío y al calor durante 24-48 horas. Continúe con su rutina de higiene oral normalmente. Recuerde cepillar y usar hilo dental diariamente.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'cirugia_periodontal', 'Cuidados post-cirugía periodontal', 'Aplique hielo en la zona operada durante las primeras 24 horas (15 min aplicado, 15 min de descanso). No coma alimentos duros ni calientes. Tome los antibióticos y analgésicos según prescripción.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'blanqueamiento', 'Cuidados post-blanqueamiento', 'Evite alimentos y bebidas que manchen (café, vino, té, salsas oscuras) durante 48 horas. Puede sentir sensibilidad temporal, use crema dental para dientes sensibles. No fume durante al menos 48 horas.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'corona', 'Cuidados post-corona provisional', 'Evite alimentos duros o pegajosos que puedan despegar la corona provisional. Si la corona se cae, llame a la clínica inmediatamente. No use hilo dental con fuerza en la zona de la corona.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'implante', 'Cuidados post-implante', 'Aplique hielo las primeras 24 horas para reducir la inflamación. Dieta blanda durante los primeros 7 días. No fume durante al menos 2 semanas. Tome todos los medicamentos recetados.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'ortodoncia_ajuste', 'Cuidados post-ajuste de ortodoncia', 'Es normal sentir molestia o presión los primeros 2-3 días después del ajuste. Tome analgésico de venta libre si es necesario. Evite alimentos duros, pegajosos o muy crujientes.', 'all', true, true, now(), now()),
              (gen_random_uuid(), 'urgencia', 'Cuidados post-urgencia dental', 'Siga estrictamente las indicaciones dadas en la consulta. Si el dolor aumenta o aparece fiebre, acuda a urgencias o llame a la clínica. Tome los medicamentos recetados según indicación.', 'all', true, true, now(), now())
            """
        )
    )


def downgrade() -> None:
    # --- drop tables in reverse dependency order ---
    op.drop_index("idx_staff_tasks_assigned", table_name="staff_tasks")
    op.drop_index("idx_staff_tasks_type", table_name="staff_tasks")
    op.drop_index("idx_staff_tasks_status", table_name="staff_tasks")
    op.drop_table("staff_tasks")

    op.drop_index("idx_expenses_date", table_name="expenses")
    op.drop_index("idx_expenses_category", table_name="expenses")
    op.drop_table("expenses")

    op.drop_index("idx_expense_categories_active", table_name="expense_categories")
    op.drop_table("expense_categories")

    op.drop_index("idx_cash_movements_type", table_name="cash_movements")
    op.drop_index("idx_cash_movements_register", table_name="cash_movements")
    op.drop_table("cash_movements")

    op.drop_index("idx_cash_registers_status", table_name="cash_registers")
    op.drop_table("cash_registers")

    op.drop_index("idx_postop_templates_active", table_name="postop_templates")
    op.drop_index("idx_postop_templates_procedure_type", table_name="postop_templates")
    op.drop_table("postop_templates")

    op.drop_index("idx_referral_rewards_status", table_name="referral_rewards")
    op.drop_index("idx_referral_rewards_referrer", table_name="referral_rewards")
    op.drop_table("referral_rewards")

    op.drop_index("idx_referral_codes_code", table_name="referral_codes")
    op.drop_index("idx_referral_codes_patient", table_name="referral_codes")
    op.drop_table("referral_codes")

    op.drop_index("idx_eps_verifications_patient", table_name="eps_verifications")
    op.drop_table("eps_verifications")

    # --- revert users RETHUS columns ---
    op.drop_constraint("chk_users_rethus_status", "users", type_="check")
    op.drop_column("users", "rethus_verified_at")
    op.drop_column("users", "rethus_verification_status")
    op.drop_column("users", "rethus_number")

    # --- restore original payments CHECK (without nequi, daviplata) ---
    op.drop_constraint("chk_payments_method", "payments", type_="check")
    op.create_check_constraint(
        "chk_payments_method",
        "payments",
        "payment_method IN ('cash', 'card', 'transfer', 'other')",
    )

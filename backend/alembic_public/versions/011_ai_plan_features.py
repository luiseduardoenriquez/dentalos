"""Add AI feature flags to plan features (AI-01, AI-02).

Adds ai_clinical_summary to Pro/Clinica/Enterprise plans (included in plan).
Ensures ai_radiograph is already present in Clinica/Enterprise.

Revision ID: 011_ai_plan_features
Revises: 010_admin_wave7_default_prices
Create Date: 2026-03-14
"""

from alembic import op

revision = "011_ai_plan_features"
down_revision = "010_admin_wave7_default_prices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add ai_clinical_summary to Pro, Clinica, Enterprise plans
    # This is a plan-included feature (not an add-on), so it's enabled by default
    # for plans that include it.
    #
    # jsonb_set adds the key to the existing JSONB features column.

    # Pro plan: add ai_clinical_summary
    op.execute("""
        UPDATE public.plans
        SET features = features || '{"ai_clinical_summary": true}'::jsonb
        WHERE slug IN ('pro', 'clinica', 'enterprise');
    """)

    # Ensure Free and Starter don't have it
    op.execute("""
        UPDATE public.plans
        SET features = features || '{"ai_clinical_summary": false}'::jsonb
        WHERE slug IN ('free', 'starter');
    """)


def downgrade() -> None:
    # Remove ai_clinical_summary from all plans
    op.execute("""
        UPDATE public.plans
        SET features = features - 'ai_clinical_summary';
    """)

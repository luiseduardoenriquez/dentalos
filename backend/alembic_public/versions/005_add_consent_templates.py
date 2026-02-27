"""Add consent_templates table to public schema

Revision ID: 005_add_consent_templates
Revises: 004_add_tenant_addons
Create Date: 2026-02-27 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "005_add_consent_templates"
down_revision: Union[str, None] = "004_add_tenant_addons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSENT_CATEGORIES = (
    "'general','surgery','sedation','orthodontics',"
    "'implants','endodontics','pediatric'"
)


def upgrade() -> None:
    op.create_table(
        "consent_templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("signature_positions", JSONB(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("builtin", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            f"category IN ({_CONSENT_CATEGORIES})",
            name="chk_public_consent_templates_category",
        ),
        schema="public",
    )
    op.create_index(
        "idx_public_consent_templates_category",
        "consent_templates",
        ["category"],
        schema="public",
    )

    # Seed 5 builtin consent templates
    op.execute("""
        INSERT INTO public.consent_templates (name, category, description, content, signature_positions, version, builtin, is_active)
        VALUES
        (
            'Consentimiento Informado General',
            'general',
            'Consentimiento general para procedimientos odontologicos de rutina.',
            '<h2>Consentimiento Informado General</h2><p>Yo, {{patient_name}}, identificado(a) con {{document_type}} No. {{document_number}}, autorizo al Dr(a). {{doctor_name}} a realizar el siguiente procedimiento: {{procedure_description}}.</p><p>He sido informado(a) sobre los riesgos, beneficios y alternativas del tratamiento propuesto.</p><p>Firma del paciente: ___________________</p><p>Fecha: {{date}}</p>',
            '[{"role": "patient", "label": "Firma del paciente", "required": true}, {"role": "doctor", "label": "Firma del profesional", "required": true}]',
            1, true, true
        ),
        (
            'Consentimiento para Cirugia Oral',
            'surgery',
            'Consentimiento para procedimientos quirurgicos orales incluyendo extracciones.',
            '<h2>Consentimiento para Cirugia Oral</h2><p>Yo, {{patient_name}}, autorizo la realizacion del procedimiento quirurgico: {{procedure_description}}.</p><p>He sido informado(a) sobre los riesgos especificos que incluyen: sangrado, infeccion, dano a nervios adyacentes, y complicaciones anestesicas.</p><p>Firma del paciente: ___________________</p><p>Firma del profesional: ___________________</p><p>Fecha: {{date}}</p>',
            '[{"role": "patient", "label": "Firma del paciente", "required": true}, {"role": "doctor", "label": "Firma del cirujano", "required": true}, {"role": "witness", "label": "Firma del testigo", "required": false}]',
            1, true, true
        ),
        (
            'Consentimiento para Ortodoncia',
            'orthodontics',
            'Consentimiento para tratamiento de ortodoncia.',
            '<h2>Consentimiento para Tratamiento de Ortodoncia</h2><p>Yo, {{patient_name}}, autorizo el inicio del tratamiento de ortodoncia propuesto por el Dr(a). {{doctor_name}}.</p><p>Entiendo que el tratamiento tiene una duracion estimada de {{treatment_duration}} y requiere visitas periodicas.</p><p>He sido informado(a) sobre los riesgos que incluyen: reabsorcion radicular, descalcificacion del esmalte, y recidiva post-tratamiento.</p>',
            '[{"role": "patient", "label": "Firma del paciente", "required": true}, {"role": "doctor", "label": "Firma del ortodoncista", "required": true}]',
            1, true, true
        ),
        (
            'Consentimiento para Endodoncia',
            'endodontics',
            'Consentimiento para tratamiento de conductos radiculares.',
            '<h2>Consentimiento para Endodoncia</h2><p>Yo, {{patient_name}}, autorizo la realizacion del tratamiento de conducto en la pieza dental No. {{tooth_number}}.</p><p>He sido informado(a) sobre los riesgos que incluyen: fractura del instrumento, perforacion radicular, y posible necesidad de cirugia apical posterior.</p>',
            '[{"role": "patient", "label": "Firma del paciente", "required": true}, {"role": "doctor", "label": "Firma del endodoncista", "required": true}]',
            1, true, true
        ),
        (
            'Consentimiento para Implantes Dentales',
            'implants',
            'Consentimiento para colocacion de implantes dentales.',
            '<h2>Consentimiento para Implantes Dentales</h2><p>Yo, {{patient_name}}, autorizo la colocacion de implante(s) dental(es) en la(s) posicion(es): {{implant_positions}}.</p><p>He sido informado(a) sobre los riesgos que incluyen: falla de oseointegracion, infeccion peri-implantaria, dano a estructuras anatomicas adyacentes, y posible necesidad de injerto oseo.</p><p>El costo total del tratamiento es de ${{total_cost}} COP.</p>',
            '[{"role": "patient", "label": "Firma del paciente", "required": true}, {"role": "doctor", "label": "Firma del implantologo", "required": true}, {"role": "witness", "label": "Firma del testigo", "required": false}]',
            1, true, true
        );
    """)


def downgrade() -> None:
    op.drop_index("idx_public_consent_templates_category", table_name="consent_templates", schema="public")
    op.drop_table("consent_templates", schema="public")

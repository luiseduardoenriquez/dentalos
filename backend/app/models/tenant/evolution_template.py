"""Evolution template models — live in each tenant schema.

Three tables:
  - EvolutionTemplate:         template header (name, procedure type, complexity)
  - EvolutionTemplateStep:     ordered steps (may contain [variable] placeholders)
  - EvolutionTemplateVariable: variable definitions for placeholder substitution
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TenantBase, TimestampMixin, UUIDPrimaryKeyMixin


class EvolutionTemplate(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """Reusable clinical note template for a specific procedure type.

    Built-in templates (is_builtin=True) ship with the platform and cannot
    be deleted by the tenant — only deactivated (is_active=False).
    Custom templates are created per clinic.
    """

    __tablename__ = "evolution_templates"
    __table_args__ = (
        CheckConstraint(
            "complexity IN ('simple', 'moderate', 'complex')",
            name="chk_evolution_templates_complexity",
        ),
        Index("idx_evolution_templates_procedure_type", "procedure_type"),
        Index("idx_evolution_templates_is_active", "is_active"),
    )

    # Identity
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    procedure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    cups_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Classification
    complexity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="simple",
        server_default="simple",
    )

    # Flags
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    steps: Mapped[list["EvolutionTemplateStep"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="EvolutionTemplateStep.step_order",
    )
    variables: Mapped[list["EvolutionTemplateVariable"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<EvolutionTemplate {self.name!r} "
            f"procedure={self.procedure_type} complexity={self.complexity}>"
        )


class EvolutionTemplateStep(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """One ordered step in an evolution template.

    Content may contain [variable_name] placeholders that map to
    EvolutionTemplateVariable rows for substitution at record creation time.
    Rows are cascade-deleted when the parent template is deleted.
    """

    __tablename__ = "evolution_template_steps"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "step_order",
            name="uq_evolution_template_steps_order",
        ),
        Index("idx_evolution_template_steps_template", "template_id"),
    )

    # Parent
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evolution_templates.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Content
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationship back to parent
    template: Mapped["EvolutionTemplate"] = relationship(back_populates="steps")

    def __repr__(self) -> str:
        return (
            f"<EvolutionTemplateStep template={self.template_id} order={self.step_order}>"
        )


class EvolutionTemplateVariable(UUIDPrimaryKeyMixin, TimestampMixin, TenantBase):
    """A variable definition used in an evolution template's steps.

    At record creation time, the service resolves [variable_name] placeholders
    in step content using the values supplied by the user.
    select-type variables carry their allowed options in the options JSONB column.
    Rows are cascade-deleted when the parent template is deleted.
    """

    __tablename__ = "evolution_template_variables"
    __table_args__ = (
        UniqueConstraint(
            "template_id",
            "name",
            name="uq_evolution_template_variables_name",
        ),
        CheckConstraint(
            "variable_type IN ('text', 'number', 'select', 'date')",
            name="chk_evolution_template_variables_type",
        ),
        Index("idx_evolution_template_variables_template", "template_id"),
    )

    # Parent
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evolution_templates.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Variable definition
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    variable_type: Mapped[str] = mapped_column(String(20), nullable=False)
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationship back to parent
    template: Mapped["EvolutionTemplate"] = relationship(back_populates="variables")

    def __repr__(self) -> str:
        return (
            f"<EvolutionTemplateVariable template={self.template_id} "
            f"name={self.name!r} type={self.variable_type}>"
        )

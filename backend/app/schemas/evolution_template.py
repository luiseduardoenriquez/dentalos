"""Evolution template request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Nested / Embedded Schemas ────────────────────────────────────────────────

_VALID_VARIABLE_TYPES: frozenset[str] = frozenset({"text", "number", "select", "date"})
_VALID_COMPLEXITIES: frozenset[str] = frozenset({"simple", "moderate", "complex"})


class EvolutionTemplateStepSchema(BaseModel):
    """A single ordered step within an evolution template."""

    step_order: int
    content: str

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("El contenido del paso no puede estar en blanco.")
        return stripped


class EvolutionTemplateVariableSchema(BaseModel):
    """A variable placeholder defined within an evolution template."""

    name: str = Field(max_length=100)
    variable_type: str
    options: list[str] | None = None
    is_required: bool = True

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("El nombre de la variable no puede estar en blanco.")
        return stripped

    @field_validator("variable_type")
    @classmethod
    def validate_variable_type(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in _VALID_VARIABLE_TYPES:
            valid = ", ".join(sorted(_VALID_VARIABLE_TYPES))
            raise ValueError(
                f"Tipo de variable inválido '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped

    @field_validator("options")
    @classmethod
    def strip_options(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            return [s.strip() for s in v if s.strip()]
        return v


# ─── Request Schemas ──────────────────────────────────────────────────────────


class EvolutionTemplateCreate(BaseModel):
    """Fields required to create a custom evolution template."""

    name: str = Field(min_length=1, max_length=200)
    procedure_type: str = Field(min_length=1, max_length=50)
    cups_code: str | None = Field(default=None, max_length=10)
    complexity: str = "simple"
    steps: list[EvolutionTemplateStepSchema] = Field(min_length=1)
    variables: list[EvolutionTemplateVariableSchema] | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("El nombre de la plantilla no puede estar en blanco.")
        return stripped

    @field_validator("procedure_type")
    @classmethod
    def strip_procedure_type(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("El tipo de procedimiento no puede estar en blanco.")
        return stripped

    @field_validator("cups_code")
    @classmethod
    def strip_cups_code(cls, v: str | None) -> str | None:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v

    @field_validator("complexity")
    @classmethod
    def validate_complexity(cls, v: str) -> str:
        stripped = v.strip()
        if stripped not in _VALID_COMPLEXITIES:
            valid = ", ".join(sorted(_VALID_COMPLEXITIES))
            raise ValueError(
                f"Complejidad inválida '{stripped}'. Valores permitidos: {valid}."
            )
        return stripped


# ─── Response Schemas ─────────────────────────────────────────────────────────


class EvolutionTemplateResponse(BaseModel):
    """Full evolution template detail — returned from GET and mutation endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    procedure_type: str
    cups_code: str | None = None
    complexity: str
    is_builtin: bool
    is_active: bool
    steps: list[EvolutionTemplateStepSchema]
    variables: list[EvolutionTemplateVariableSchema]
    created_at: datetime


class EvolutionTemplateListItem(BaseModel):
    """Condensed evolution template for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    procedure_type: str
    cups_code: str | None = None
    complexity: str
    is_builtin: bool


class EvolutionTemplateListResponse(BaseModel):
    """Paginated list of evolution templates."""

    items: list[EvolutionTemplateListItem]
    total: int

"""Evolution template service — list, fetch, and create reusable clinical note templates.

Security invariants:
  - Template content does not contain PHI — it is a clinic-level configuration
    artifact. No PHI logging constraints apply beyond the standard practice
    of never logging user-supplied strings verbatim.
  - Built-in templates (is_builtin=True) cannot be hard-deleted.
    Deactivation (is_active=False) is the only allowed "removal" path,
    enforced in the route layer (not here).
  - Steps and variables are always loaded eagerly for get_template, because
    the template is useless without them and the data set is small enough
    that N+1 is not a concern.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.tenant.evolution_template import (
    EvolutionTemplate,
    EvolutionTemplateStep,
    EvolutionTemplateVariable,
)

logger = logging.getLogger("dentalos.templates")


# ─── Serialization helpers ────────────────────────────────────────────────────


def _step_to_dict(step: EvolutionTemplateStep) -> dict[str, Any]:
    return {
        "id": str(step.id),
        "template_id": str(step.template_id),
        "step_order": step.step_order,
        "content": step.content,
        "created_at": step.created_at,
        "updated_at": step.updated_at,
    }


def _variable_to_dict(variable: EvolutionTemplateVariable) -> dict[str, Any]:
    return {
        "id": str(variable.id),
        "template_id": str(variable.template_id),
        "name": variable.name,
        "variable_type": variable.variable_type,
        "options": variable.options,
        "is_required": variable.is_required,
        "created_at": variable.created_at,
        "updated_at": variable.updated_at,
    }


def _template_to_dict(
    template: EvolutionTemplate,
    *,
    include_full: bool = False,
) -> dict[str, Any]:
    """Serialize an EvolutionTemplate ORM instance to a plain dict.

    When include_full=False (list view), steps/variables are omitted but
    their counts are included for display.  When include_full=True (detail
    view), the full steps and variables lists are included.

    EvolutionTemplate.steps and .variables are available only when the
    relationships have been loaded (via selectinload or lazy access within
    the same session scope).
    """
    data: dict[str, Any] = {
        "id": str(template.id),
        "name": template.name,
        "procedure_type": template.procedure_type,
        "cups_code": template.cups_code,
        "complexity": template.complexity,
        "is_builtin": template.is_builtin,
        "is_active": template.is_active,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }

    if include_full:
        data["steps"] = [_step_to_dict(s) for s in template.steps]
        data["variables"] = [_variable_to_dict(v) for v in template.variables]
        data["step_count"] = len(template.steps)
        data["variable_count"] = len(template.variables)
    else:
        # Counts are safe to access after a selectinload or within session scope
        data["step_count"] = len(template.steps)
        data["variable_count"] = len(template.variables)

    return data


# ─── Evolution Template Service ───────────────────────────────────────────────


class EvolutionTemplateService:
    """Stateless evolution template service.

    All methods accept primitive arguments and an AsyncSession so they can
    be called from API routes, workers, CLI scripts, and tests without
    coupling to HTTP concerns.

    The search_path for each method is already set by get_tenant_db().
    Methods do NOT call SET search_path themselves — the session is already
    scoped to the correct tenant schema by the time it arrives here.
    """

    async def list_templates(
        self,
        *,
        db: AsyncSession,
        procedure_type: str | None = None,
    ) -> dict[str, Any]:
        """Return all active templates, builtin first then alphabetical.

        Steps and variables are selectinload-ed so _template_to_dict can
        access their counts without triggering lazy-load queries.

        Args:
            procedure_type: When provided, restrict to templates for that
                            procedure type (e.g. "extraction", "restoration").

        Returns:
            dict with keys: items (list of template dicts), total (int).
        """
        stmt = (
            select(EvolutionTemplate)
            .where(EvolutionTemplate.is_active.is_(True))
            .options(
                selectinload(EvolutionTemplate.steps),
                selectinload(EvolutionTemplate.variables),
            )
            # Built-in templates first, then alphabetical by name
            .order_by(
                EvolutionTemplate.is_builtin.desc(),
                EvolutionTemplate.name.asc(),
            )
        )

        if procedure_type is not None:
            stmt = stmt.where(EvolutionTemplate.procedure_type == procedure_type)

        # Count via a separate scalar query (avoids subquery overhead on small sets)
        count_stmt = select(func.count(EvolutionTemplate.id)).where(
            EvolutionTemplate.is_active.is_(True)
        )
        if procedure_type is not None:
            count_stmt = count_stmt.where(
                EvolutionTemplate.procedure_type == procedure_type
            )

        count_result = await db.execute(count_stmt)
        total: int = count_result.scalar_one()

        templates_result = await db.execute(stmt)
        templates = templates_result.scalars().all()

        return {
            "items": [_template_to_dict(t, include_full=False) for t in templates],
            "total": total,
        }

    async def get_template(
        self,
        *,
        db: AsyncSession,
        template_id: str,
    ) -> dict[str, Any] | None:
        """Fetch a single active template with its full steps and variables.

        Steps are ordered by step_order (enforced by the ORM relationship
        order_by on EvolutionTemplate.steps).

        Returns None when the template does not exist or is inactive.
        """
        stmt = (
            select(EvolutionTemplate)
            .where(
                EvolutionTemplate.id == uuid.UUID(template_id),
                EvolutionTemplate.is_active.is_(True),
            )
            .options(
                selectinload(EvolutionTemplate.steps),
                selectinload(EvolutionTemplate.variables),
            )
        )

        result = await db.execute(stmt)
        template = result.scalar_one_or_none()

        if template is None:
            return None

        return _template_to_dict(template, include_full=True)

    async def create_template(
        self,
        *,
        db: AsyncSession,
        name: str,
        procedure_type: str,
        cups_code: str | None = None,
        complexity: str = "simple",
        steps: list[dict[str, Any]] | None = None,
        variables: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a custom evolution template with optional steps and variables.

        steps items are expected to have at least a "content" key. The
        step_order is assigned from the list position (0-indexed) so
        callers do not need to supply it.

        variables items are expected to have "name", "variable_type",
        and optionally "options" and "is_required" keys.

        Custom templates are created with is_builtin=False. Built-in
        templates are seeded via migration scripts, not this method.

        Args:
            name: Human-readable template name (e.g. "Extracción simple").
            procedure_type: Procedure category key (e.g. "extraction").
            cups_code: Optional CUPS code to link this template to a catalog entry.
            complexity: One of "simple", "moderate", "complex".
            steps: Ordered list of step dicts (may be empty).
            variables: List of variable definition dicts (may be empty).

        Returns:
            dict matching EvolutionTemplateResponse shape (full, with steps
            and variables).
        """
        template = EvolutionTemplate(
            name=name,
            procedure_type=procedure_type,
            cups_code=cups_code,
            complexity=complexity,
            is_builtin=False,
            is_active=True,
        )
        db.add(template)
        await db.flush()  # Assign template.id before creating children

        # Create steps in positional order
        step_orm_list: list[EvolutionTemplateStep] = []
        for idx, step_data in enumerate(steps or []):
            step = EvolutionTemplateStep(
                template_id=template.id,
                step_order=idx,
                content=step_data.get("content", ""),
            )
            db.add(step)
            step_orm_list.append(step)

        # Create variable definitions
        variable_orm_list: list[EvolutionTemplateVariable] = []
        for var_data in variables or []:
            variable = EvolutionTemplateVariable(
                template_id=template.id,
                name=var_data["name"],
                variable_type=var_data["variable_type"],
                options=var_data.get("options"),
                is_required=var_data.get("is_required", True),
            )
            db.add(variable)
            variable_orm_list.append(variable)

        await db.flush()

        logger.info(
            "EvolutionTemplate created: id=%s name=%r steps=%d variables=%d",
            str(template.id)[:8],
            template.name,
            len(step_orm_list),
            len(variable_orm_list),
        )

        # Attach in-memory lists so _template_to_dict can serialize them
        # without an extra round-trip (steps/variables are already in session).
        template.steps = step_orm_list
        template.variables = variable_orm_list

        return _template_to_dict(template, include_full=True)


# Module-level singleton for dependency injection
evolution_template_service = EvolutionTemplateService()

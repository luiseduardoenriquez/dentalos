"""Post-operative instruction service — template CRUD + event dispatch.

Security invariants:
  - PHI is NEVER logged (no patient names, phone numbers, or clinical notes).
  - Template content is not logged in full — only IDs and procedure types.
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import PostopErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.core.queue import publish_message
from app.models.tenant.postop_template import PostopTemplate
from app.schemas.queue import QueueMessage

logger = logging.getLogger("dentalos.postop")


class PostopService:
    """Stateless post-operative instruction service."""

    # ── Template CRUD ─────────────────────────────────────────────────────────

    async def create_template(
        self,
        *,
        db: AsyncSession,
        procedure_type: str,
        title: str,
        instruction_content: str,
        channel_preference: str = "all",
        is_default: bool = False,
    ) -> dict[str, Any]:
        """Create a new post-op instruction template.

        If is_default=True, all other templates for the same procedure_type
        are unset as default before the new one is persisted.
        """
        if is_default:
            await self._unset_defaults(db=db, procedure_type=procedure_type)

        template = PostopTemplate(
            procedure_type=procedure_type,
            title=title,
            instruction_content=instruction_content,
            channel_preference=channel_preference,
            is_default=is_default,
            is_active=True,
        )
        db.add(template)
        await db.flush()
        await db.refresh(template)
        logger.info(
            "Postop template created: id=%s procedure_type=%s",
            str(template.id)[:8],
            procedure_type,
        )
        return self._template_to_dict(template)

    async def update_template(
        self,
        *,
        db: AsyncSession,
        template_id: uuid.UUID,
        **fields: Any,
    ) -> dict[str, Any]:
        """Update mutable fields on an existing post-op template.

        If is_default is being set to True, existing defaults for the same
        procedure_type are cleared first.
        """
        template = await self._get_template(db, template_id)

        # If promoting this template to default, clear others first
        if fields.get("is_default") is True:
            await self._unset_defaults(db=db, procedure_type=template.procedure_type)

        for key, value in fields.items():
            if value is not None and hasattr(template, key):
                setattr(template, key, value)

        await db.flush()
        await db.refresh(template)
        logger.info("Postop template updated: id=%s", str(template_id)[:8])
        return self._template_to_dict(template)

    async def list_templates(
        self,
        *,
        db: AsyncSession,
        procedure_type: str | None = None,
    ) -> dict[str, Any]:
        """List active post-op instruction templates.

        Optionally filtered by procedure_type. Ordered by is_default desc,
        then created_at desc so defaults surface first.
        """
        conditions = [PostopTemplate.is_active.is_(True)]
        if procedure_type:
            conditions.append(PostopTemplate.procedure_type == procedure_type)

        result = await db.execute(
            select(PostopTemplate)
            .where(*conditions)
            .order_by(
                PostopTemplate.is_default.desc(),
                PostopTemplate.created_at.desc(),
            )
        )
        templates = result.scalars().all()

        items = [self._template_to_dict(t) for t in templates]
        return {"items": items, "total": len(items)}

    async def get_template(
        self,
        *,
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Return a single post-op template by id."""
        template = await self._get_template(db, template_id)
        return self._template_to_dict(template)

    # ── Dispatch ──────────────────────────────────────────────────────────────

    async def send_instructions(
        self,
        *,
        db: AsyncSession,
        patient_id: uuid.UUID,
        procedure_type: str,
        template_id: uuid.UUID | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Send post-op instructions to a patient.

        Resolves the template by explicit template_id, falling back to the
        default template for the given procedure_type. Publishes a
        'postop.send' job to the notifications queue.
        """
        if template_id is not None:
            template = await self._get_template(db, template_id)
        else:
            template = await self._get_default_template(db, procedure_type)
            if template is None:
                raise DentalOSError(
                    error=PostopErrors.TEMPLATE_NOT_FOUND,
                    message=(
                        f"No default post-op template found for procedure_type "
                        f"'{procedure_type}'."
                    ),
                    status_code=404,
                )

        try:
            await publish_message(
                "notifications",
                QueueMessage(
                    tenant_id=tenant_id or "",
                    job_type="postop.send",
                    payload={
                        "patient_id": str(patient_id),
                        "template_id": str(template.id),
                        "channel": template.channel_preference,
                        "content": template.instruction_content,
                        "title": template.title,
                    },
                ),
            )
        except Exception as exc:
            logger.error(
                "Postop send failed: template_id=%s error=%s",
                str(template.id)[:8],
                type(exc).__name__,
            )
            raise DentalOSError(
                error=PostopErrors.SEND_FAILED,
                message="No se pudo enviar las instrucciones postoperatorias.",
                status_code=502,
            ) from exc

        logger.info(
            "Postop instructions queued: template_id=%s channel=%s",
            str(template.id)[:8],
            template.channel_preference,
        )
        return {
            "sent": True,
            "channel": template.channel_preference,
            "patient_id": str(patient_id),
            "template_id": str(template.id),
        }

    async def auto_dispatch(
        self,
        *,
        db: AsyncSession,
        patient_id: uuid.UUID,
        procedure_type: str,
        record_id: uuid.UUID,
        tenant_id: str,
    ) -> None:
        """Auto-dispatch post-op instructions from a worker after a clinical record.

        Silently skips if no default template exists for the procedure_type.
        Called from the clinical worker after a record is finalised.
        """
        template = await self._get_default_template(db, procedure_type)
        if template is None:
            logger.debug(
                "Auto-dispatch skipped — no default template for procedure_type=%s",
                procedure_type,
            )
            return

        try:
            await publish_message(
                "notifications",
                QueueMessage(
                    tenant_id=tenant_id,
                    job_type="postop.send",
                    payload={
                        "patient_id": str(patient_id),
                        "template_id": str(template.id),
                        "channel": template.channel_preference,
                        "content": template.instruction_content,
                        "title": template.title,
                        "record_id": str(record_id),
                    },
                ),
            )
            logger.info(
                "Postop auto-dispatch queued: template_id=%s record_id=%s",
                str(template.id)[:8],
                str(record_id)[:8],
            )
        except Exception as exc:
            # Auto-dispatch failures are non-fatal — log and continue.
            logger.error(
                "Postop auto-dispatch failed: template_id=%s error=%s",
                str(template.id)[:8],
                type(exc).__name__,
            )

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _get_template(
        self, db: AsyncSession, template_id: uuid.UUID
    ) -> PostopTemplate:
        """Load a PostopTemplate by id or raise ResourceNotFoundError."""
        result = await db.execute(
            select(PostopTemplate).where(
                PostopTemplate.id == template_id,
                PostopTemplate.is_active.is_(True),
            )
        )
        template = result.scalar_one_or_none()
        if template is None:
            raise ResourceNotFoundError(
                error=PostopErrors.TEMPLATE_NOT_FOUND,
                resource_name="PostopTemplate",
            )
        return template

    async def _get_default_template(
        self, db: AsyncSession, procedure_type: str
    ) -> PostopTemplate | None:
        """Return the default active template for a procedure_type, or None."""
        result = await db.execute(
            select(PostopTemplate).where(
                PostopTemplate.procedure_type == procedure_type,
                PostopTemplate.is_default.is_(True),
                PostopTemplate.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def _unset_defaults(
        self, *, db: AsyncSession, procedure_type: str
    ) -> None:
        """Clear is_default on all active templates for a given procedure_type."""
        await db.execute(
            update(PostopTemplate)
            .where(
                PostopTemplate.procedure_type == procedure_type,
                PostopTemplate.is_default.is_(True),
                PostopTemplate.is_active.is_(True),
            )
            .values(is_default=False)
        )

    @staticmethod
    def _template_to_dict(template: PostopTemplate) -> dict[str, Any]:
        """Serialize a PostopTemplate ORM instance to a plain dict."""
        return {
            "id": str(template.id),
            "procedure_type": template.procedure_type,
            "title": template.title,
            "instruction_content": template.instruction_content,
            "channel_preference": template.channel_preference,
            "is_default": template.is_default,
            "is_active": template.is_active,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }


postop_service = PostopService()

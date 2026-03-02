"""Unit tests for the PostopService class.

Tests cover:
  - list_templates: returns all active templates
  - create_template: creates new template, promotes to default correctly
  - update_template: modifies template fields, re-promotes default
  - send_instructions: publishes to notifications queue
  - auto_dispatch: finds matching default template and dispatches; skips if none
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.error_codes import PostopErrors
from app.core.exceptions import DentalOSError, ResourceNotFoundError
from app.services.postop_service import PostopService


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_template(**overrides) -> MagicMock:
    template = MagicMock()
    template.id = overrides.get("id", uuid.uuid4())
    template.procedure_type = overrides.get("procedure_type", "extraction")
    template.title = overrides.get("title", "Instrucciones post-extracción")
    template.instruction_content = overrides.get(
        "instruction_content",
        "No coma durante 2 horas. Aplique hielo cada 20 minutos.",
    )
    template.channel_preference = overrides.get("channel_preference", "all")
    template.is_default = overrides.get("is_default", False)
    template.is_active = overrides.get("is_active", True)
    template.created_at = datetime.now(UTC)
    template.updated_at = datetime.now(UTC)
    return template


# ── list_templates ────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestListTemplates:
    async def test_list_templates_returns_paginated_dict(self):
        """list_templates must return a dict with items and total."""
        service = PostopService()
        db = AsyncMock()

        t1 = _make_template(is_default=True)
        t2 = _make_template()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [t1, t2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.list_templates(db=db)

        assert "items" in result
        assert "total" in result
        assert result["total"] == 2

    async def test_list_templates_empty(self):
        """list_templates must return total=0 when no active templates exist."""
        service = PostopService()
        db = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.list_templates(db=db)

        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_templates_filtered_by_procedure_type(self):
        """list_templates with procedure_type filter must execute without error."""
        service = PostopService()
        db = AsyncMock()

        t = _make_template(procedure_type="cleaning")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [t]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=result_mock)

        result = await service.list_templates(db=db, procedure_type="cleaning")

        assert result["total"] == 1


# ── create_template ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCreateTemplate:
    async def test_create_template_calls_add_and_flush(self):
        """create_template must call db.add and db.flush to persist the template."""
        service = PostopService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        template = _make_template()

        async def fake_refresh(obj):
            obj.id = template.id
            obj.procedure_type = template.procedure_type
            obj.title = template.title
            obj.instruction_content = template.instruction_content
            obj.channel_preference = template.channel_preference
            obj.is_default = template.is_default
            obj.is_active = True
            obj.created_at = template.created_at
            obj.updated_at = template.updated_at

        db.refresh = fake_refresh

        with patch(
            "app.services.postop_service.PostopTemplate"
        ) as MockTemplate:
            MockTemplate.return_value = template

            result = await service.create_template(
                db=db,
                procedure_type="extraction",
                title="Instrucciones post-extracción",
                instruction_content="No coma durante 2 horas.",
            )

        db.add.assert_called_once()
        db.flush.assert_called_once()

    async def test_create_template_returns_dict_with_procedure_type(self):
        """create_template must return a dict containing procedure_type."""
        service = PostopService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        template = _make_template(procedure_type="implant")

        async def fake_refresh(obj):
            obj.id = template.id
            obj.procedure_type = "implant"
            obj.title = template.title
            obj.instruction_content = template.instruction_content
            obj.channel_preference = template.channel_preference
            obj.is_default = False
            obj.is_active = True
            obj.created_at = template.created_at
            obj.updated_at = template.updated_at

        db.refresh = fake_refresh

        with patch("app.services.postop_service.PostopTemplate") as MockTemplate:
            MockTemplate.return_value = template

            result = await service.create_template(
                db=db,
                procedure_type="implant",
                title="Post-implante",
                instruction_content="Evite fumar por 72 horas.",
            )

        assert result["procedure_type"] == "implant"

    async def test_create_template_as_default_unsets_previous_defaults(self):
        """create_template with is_default=True must call _unset_defaults."""
        service = PostopService()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        template = _make_template(is_default=True, procedure_type="extraction")

        async def fake_refresh(obj):
            obj.id = template.id
            obj.procedure_type = template.procedure_type
            obj.title = template.title
            obj.instruction_content = template.instruction_content
            obj.channel_preference = template.channel_preference
            obj.is_default = True
            obj.is_active = True
            obj.created_at = template.created_at
            obj.updated_at = template.updated_at

        db.refresh = fake_refresh

        # _unset_defaults issues an UPDATE, which is the execute call.
        unset_result = MagicMock()
        db.execute = AsyncMock(return_value=unset_result)

        with patch("app.services.postop_service.PostopTemplate") as MockTemplate:
            MockTemplate.return_value = template

            result = await service.create_template(
                db=db,
                procedure_type="extraction",
                title="Default extracción",
                instruction_content="Instrucciones por defecto.",
                is_default=True,
            )

        # _unset_defaults must have triggered an execute (the UPDATE)
        db.execute.assert_called_once()


# ── update_template ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestUpdateTemplate:
    async def test_update_template_modifies_fields(self):
        """update_template must apply provided field values to the template."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template(title="Titulo Viejo")
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=template_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        result = await service.update_template(
            db=db,
            template_id=template.id,
            title="Titulo Nuevo",
        )

        assert template.title == "Titulo Nuevo"

    async def test_update_template_not_found_raises_404(self):
        """update_template must raise ResourceNotFoundError for an unknown template_id."""
        service = PostopService()
        db = AsyncMock()

        not_found_result = MagicMock()
        not_found_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=not_found_result)

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.update_template(
                db=db,
                template_id=uuid.uuid4(),
                title="No existe",
            )

        assert exc_info.value.error == PostopErrors.TEMPLATE_NOT_FOUND

    async def test_update_template_flushes(self):
        """update_template must call db.flush() after updating."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template()
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=template_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        await service.update_template(
            db=db,
            template_id=template.id,
            channel_preference="whatsapp",
        )

        db.flush.assert_called_once()


# ── send_instructions ─────────────────────────────────────────────────────────


@pytest.mark.unit
class TestSendInstructions:
    async def test_send_instructions_publishes_to_queue(self):
        """send_instructions must call publish_message on the notifications queue."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template(is_default=True)
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=template_result)

        with patch(
            "app.services.postop_service.publish_message"
        ) as mock_publish:
            mock_publish.return_value = None

            result = await service.send_instructions(
                db=db,
                patient_id=uuid.uuid4(),
                procedure_type="extraction",
                template_id=template.id,
            )

        mock_publish.assert_called_once()
        assert result["sent"] is True

    async def test_send_instructions_returns_channel(self):
        """send_instructions result must include the channel used."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template(channel_preference="whatsapp")
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=template_result)

        with patch("app.services.postop_service.publish_message") as mock_publish:
            mock_publish.return_value = None

            result = await service.send_instructions(
                db=db,
                patient_id=uuid.uuid4(),
                procedure_type="extraction",
                template_id=template.id,
            )

        assert result["channel"] == "whatsapp"

    async def test_send_instructions_no_default_raises_404(self):
        """send_instructions without explicit template_id must raise 404 when no default exists."""
        service = PostopService()
        db = AsyncMock()

        # No default template found
        no_default_result = MagicMock()
        no_default_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_default_result)

        with pytest.raises(DentalOSError) as exc_info:
            await service.send_instructions(
                db=db,
                patient_id=uuid.uuid4(),
                procedure_type="unknown_procedure",
                # template_id is None — triggers default lookup
            )

        assert exc_info.value.error == PostopErrors.TEMPLATE_NOT_FOUND
        assert exc_info.value.status_code == 404

    async def test_send_instructions_publish_failure_raises_502(self):
        """send_instructions must raise 502 DentalOSError when publish_message fails."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template()
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=template_result)

        with patch(
            "app.services.postop_service.publish_message",
            side_effect=RuntimeError("Queue unavailable"),
        ):
            with pytest.raises(DentalOSError) as exc_info:
                await service.send_instructions(
                    db=db,
                    patient_id=uuid.uuid4(),
                    procedure_type="extraction",
                    template_id=template.id,
                )

        assert exc_info.value.status_code == 502
        assert exc_info.value.error == PostopErrors.SEND_FAILED


# ── auto_dispatch ─────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAutoDispatch:
    async def test_auto_dispatch_publishes_when_default_exists(self):
        """auto_dispatch must publish a message when a default template is found."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template(is_default=True, procedure_type="cleaning")
        default_result = MagicMock()
        default_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=default_result)

        with patch(
            "app.services.postop_service.publish_message"
        ) as mock_publish:
            mock_publish.return_value = None

            await service.auto_dispatch(
                db=db,
                patient_id=uuid.uuid4(),
                procedure_type="cleaning",
                record_id=uuid.uuid4(),
                tenant_id="tn_test123",
            )

        mock_publish.assert_called_once()

    async def test_auto_dispatch_skips_when_no_default(self):
        """auto_dispatch must silently skip when no default template is found."""
        service = PostopService()
        db = AsyncMock()

        no_default_result = MagicMock()
        no_default_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=no_default_result)

        with patch(
            "app.services.postop_service.publish_message"
        ) as mock_publish:
            await service.auto_dispatch(
                db=db,
                patient_id=uuid.uuid4(),
                procedure_type="rare_procedure",
                record_id=uuid.uuid4(),
                tenant_id="tn_test123",
            )

        mock_publish.assert_not_called()

    async def test_auto_dispatch_swallows_publish_errors(self):
        """auto_dispatch must not propagate publish errors (non-fatal)."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template(is_default=True)
        default_result = MagicMock()
        default_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=default_result)

        with patch(
            "app.services.postop_service.publish_message",
            side_effect=RuntimeError("Queue down"),
        ):
            # Should not raise — errors are logged and swallowed.
            await service.auto_dispatch(
                db=db,
                patient_id=uuid.uuid4(),
                procedure_type="extraction",
                record_id=uuid.uuid4(),
                tenant_id="tn_test123",
            )

    async def test_auto_dispatch_includes_record_id_in_payload(self):
        """auto_dispatch must include record_id in the published payload."""
        service = PostopService()
        db = AsyncMock()

        template = _make_template(is_default=True)
        default_result = MagicMock()
        default_result.scalar_one_or_none.return_value = template
        db.execute = AsyncMock(return_value=default_result)

        record_id = uuid.uuid4()
        captured_messages: list = []

        async def capture_publish(queue, message):
            captured_messages.append(message)

        with patch(
            "app.services.postop_service.publish_message",
            side_effect=capture_publish,
        ):
            await service.auto_dispatch(
                db=db,
                patient_id=uuid.uuid4(),
                procedure_type="extraction",
                record_id=record_id,
                tenant_id="tn_test123",
            )

        assert len(captured_messages) == 1
        assert captured_messages[0].payload["record_id"] == str(record_id)

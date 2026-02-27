"""Unit tests for the voice NLP service (app/services/voice_nlp.py).

Tests cover:
  - _extract_json_array: all supported input formats plus edge/failure cases
  - parse_dental_text: Ollama and Anthropic dispatch paths
  - _parse_with_ollama: retry logic and connection error handling
  - get_model_identifier: returns correct string per provider
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.voice_nlp as nlp_module
from app.services.voice_nlp import (
    _extract_json_array,
    _parse_with_ollama,
    get_model_identifier,
    parse_dental_text,
)

# ── sample dental findings fixture ───────────────────────────────────────────

SAMPLE_FINDINGS = [
    {"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.95},
    {"tooth_number": 21, "zone": "vestibular", "condition_code": "fractura", "confidence": 0.88},
]


def _ollama_response(content: str) -> dict:
    """Build an Ollama-style chat completion response dict."""
    return {
        "choices": [
            {"message": {"content": content}}
        ]
    }


def _anthropic_response(content: str) -> dict:
    """Build an Anthropic Messages API response dict."""
    return {
        "content": [{"type": "text", "text": content}]
    }


# ── _extract_json_array ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestExtractJsonArrayClean:
    def test_clean_json_array(self):
        """A raw JSON array string is parsed directly."""
        raw = json.dumps(SAMPLE_FINDINGS)
        result = _extract_json_array(raw)
        assert result == SAMPLE_FINDINGS

    def test_clean_array_with_whitespace_padding(self):
        """Leading/trailing whitespace around a clean array is handled."""
        raw = "  \n" + json.dumps(SAMPLE_FINDINGS) + "\n  "
        result = _extract_json_array(raw)
        assert result == SAMPLE_FINDINGS


@pytest.mark.unit
class TestExtractJsonArrayMarkdownFences:
    def test_json_fenced_block(self):
        """JSON wrapped in ```json ... ``` code fences is extracted."""
        content = "```json\n" + json.dumps(SAMPLE_FINDINGS) + "\n```"
        result = _extract_json_array(content)
        assert result == SAMPLE_FINDINGS

    def test_plain_fenced_block(self):
        """JSON wrapped in ``` ... ``` (no language tag) is extracted."""
        content = "```\n" + json.dumps(SAMPLE_FINDINGS) + "\n```"
        result = _extract_json_array(content)
        assert result == SAMPLE_FINDINGS

    def test_fenced_with_surrounding_text(self):
        """Code fence extraction works even with text before/after the fence."""
        content = (
            "Aquí están los hallazgos:\n"
            "```json\n"
            + json.dumps(SAMPLE_FINDINGS)
            + "\n```\n"
            "Fin del análisis."
        )
        result = _extract_json_array(content)
        assert result == SAMPLE_FINDINGS


@pytest.mark.unit
class TestExtractJsonArrayWrapperObject:
    def test_findings_key_wrapper(self):
        """{"findings": [...]} wrapper is unwrapped automatically."""
        payload = {"findings": SAMPLE_FINDINGS}
        result = _extract_json_array(json.dumps(payload))
        assert result == SAMPLE_FINDINGS

    def test_results_key_wrapper(self):
        """{"results": [...]} wrapper is unwrapped automatically."""
        payload = {"results": SAMPLE_FINDINGS}
        result = _extract_json_array(json.dumps(payload))
        assert result == SAMPLE_FINDINGS

    def test_data_key_wrapper(self):
        """{"data": [...]} wrapper is unwrapped automatically."""
        payload = {"data": SAMPLE_FINDINGS}
        result = _extract_json_array(json.dumps(payload))
        assert result == SAMPLE_FINDINGS

    def test_unknown_key_returns_empty(self):
        """A wrapper object whose keys aren't recognised returns []."""
        payload = {"unknown_key": SAMPLE_FINDINGS}
        result = _extract_json_array(json.dumps(payload))
        assert result == []


@pytest.mark.unit
class TestExtractJsonArrayPreamble:
    def test_text_before_array(self):
        """Free-form text before the JSON array is skipped via regex fallback."""
        preamble = "Analicé el texto y encontré los siguientes hallazgos:\n"
        raw = preamble + json.dumps(SAMPLE_FINDINGS)
        result = _extract_json_array(raw)
        assert result == SAMPLE_FINDINGS

    def test_text_before_and_after_array(self):
        """Bracket-regex fallback extracts the array even with trailing text."""
        content = (
            "Respuesta:\n"
            + json.dumps(SAMPLE_FINDINGS)
            + "\nEspero que sea de ayuda."
        )
        result = _extract_json_array(content)
        assert result == SAMPLE_FINDINGS


@pytest.mark.unit
class TestExtractJsonArrayInvalid:
    def test_garbage_input_returns_empty_list(self):
        """Non-JSON garbage returns [] without raising."""
        result = _extract_json_array("this is not json at all!!!")
        assert result == []

    def test_partial_json_returns_empty_list(self):
        """Truncated JSON that cannot be parsed returns []."""
        result = _extract_json_array('[{"tooth_number": 36, "zone"')
        assert result == []

    def test_json_object_no_known_key_returns_empty(self):
        """A plain dict with no recognised list key returns []."""
        result = _extract_json_array('{"message": "sin hallazgos"}')
        assert result == []


@pytest.mark.unit
class TestExtractJsonArrayEmpty:
    def test_empty_array_string_returns_empty_list(self):
        """The string '[]' represents no findings and returns []."""
        result = _extract_json_array("[]")
        assert result == []

    def test_empty_string_returns_empty_list(self):
        """A blank / whitespace-only input returns []."""
        result = _extract_json_array("   ")
        assert result == []


# ── parse_dental_text — local (Ollama) provider ──────────────────────────────


@pytest.mark.unit
class TestParseDentalTextLocalProvider:
    async def test_calls_ollama_endpoint(self, monkeypatch):
        """With provider='local', parse_dental_text must POST to Ollama's
        /v1/chat/completions endpoint and return parsed findings."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "local")
        monkeypatch.setattr(nlp_module.settings, "ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")
        monkeypatch.setattr(nlp_module.settings, "ollama_timeout_seconds", 120)

        response_body = _ollama_response(json.dumps(SAMPLE_FINDINGS))

        mock_response = MagicMock()
        mock_response.json.return_value = response_body
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            result = await parse_dental_text("texto de prueba", "system prompt")

        assert result == SAMPLE_FINDINGS
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        url = call_args.args[0] if call_args.args else call_args.kwargs.get("url", call_args.args[0])
        assert "/v1/chat/completions" in url

    async def test_request_payload_contains_model_and_messages(self, monkeypatch):
        """The Ollama request body must include the configured model and the
        system+user messages."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "local")
        monkeypatch.setattr(nlp_module.settings, "ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")
        monkeypatch.setattr(nlp_module.settings, "ollama_timeout_seconds", 120)

        captured_payload: dict = {}

        async def capture_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            mock_resp = MagicMock()
            mock_resp.json.return_value = _ollama_response(
                '[{"tooth_number": 11, "zone": "incisal", "condition_code": "fractura", "confidence": 0.9}]'
            )
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = capture_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            await parse_dental_text("dictado del doctor", "eres un asistente dental")

        assert captured_payload["model"] == "qwen2.5:32b"
        messages = captured_payload["messages"]
        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert "user" in roles
        system_msg = next(m for m in messages if m["role"] == "system")
        assert system_msg["content"] == "eres un asistente dental"
        user_msg = next(m for m in messages if m["role"] == "user")
        assert user_msg["content"] == "dictado del doctor"


# ── parse_dental_text — anthropic provider ───────────────────────────────────


@pytest.mark.unit
class TestParseDentalTextAnthropicProvider:
    async def test_calls_anthropic_api(self, monkeypatch):
        """With provider='anthropic', parse_dental_text must POST to the
        Anthropic messages endpoint and return parsed findings."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_api_key", "sk-ant-test-key")

        response_body = _anthropic_response(json.dumps(SAMPLE_FINDINGS))

        mock_response = MagicMock()
        mock_response.json.return_value = response_body
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            result = await parse_dental_text("descripción clínica", "prompt del sistema")

        assert result == SAMPLE_FINDINGS
        mock_post.assert_called_once()
        url_called = mock_post.call_args.args[0] if mock_post.call_args.args else mock_post.call_args.kwargs.get("url")
        assert "anthropic.com" in url_called

    async def test_anthropic_request_includes_api_key_header(self, monkeypatch):
        """The Anthropic request must include x-api-key and anthropic-version
        headers."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_api_key", "sk-ant-my-key")

        captured_headers: dict = {}

        async def capture_post(url, json=None, headers=None, **kwargs):
            captured_headers.update(headers or {})
            mock_resp = MagicMock()
            mock_resp.json.return_value = _anthropic_response("[]")
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = capture_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            await parse_dental_text("texto", "prompt")

        assert captured_headers.get("x-api-key") == "sk-ant-my-key"
        assert "anthropic-version" in captured_headers

    async def test_anthropic_missing_api_key_returns_empty(self, monkeypatch):
        """If anthropic_api_key is empty, the function returns [] immediately
        without making any HTTP request."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_api_key", "")

        mock_post = AsyncMock()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            result = await parse_dental_text("texto", "prompt")

        assert result == []
        mock_post.assert_not_called()


# ── Ollama retry logic ────────────────────────────────────────────────────────


@pytest.mark.unit
class TestParseDentalTextOllamaRetry:
    async def test_retries_on_empty_first_response(self, monkeypatch):
        """If Ollama returns empty findings on the first attempt, the function
        must retry with a stricter prompt and return the second response."""
        monkeypatch.setattr(nlp_module.settings, "ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")
        monkeypatch.setattr(nlp_module.settings, "ollama_timeout_seconds", 120)

        call_count = 0

        async def mock_post(url, json=None, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt: model returns empty array
                content = "[]"
            else:
                # Second attempt: model returns actual findings
                content = json_module_dumps(SAMPLE_FINDINGS)
            mock_resp = MagicMock()
            mock_resp.json.return_value = _ollama_response(content)
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            result = await _parse_with_ollama("texto", "prompt")

        assert result == SAMPLE_FINDINGS
        assert call_count == 2, "Expected exactly two HTTP calls (initial + retry)"

    async def test_retry_adds_strict_instruction_to_messages(self, monkeypatch):
        """On the second attempt, the messages list must contain a third
        message that instructs the model to return only JSON."""
        monkeypatch.setattr(nlp_module.settings, "ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")
        monkeypatch.setattr(nlp_module.settings, "ollama_timeout_seconds", 120)

        payloads: list[dict] = []

        async def capture_post(url, json=None, **kwargs):
            payloads.append(json or {})
            # Always return empty on first, findings on second
            content = "[]" if len(payloads) == 1 else json_module_dumps(SAMPLE_FINDINGS)
            mock_resp = MagicMock()
            mock_resp.json.return_value = _ollama_response(content)
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = capture_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            await _parse_with_ollama("texto", "prompt")

        # First request: 2 messages (system + user)
        assert len(payloads[0]["messages"]) == 2
        # Retry request: 3 messages (system + user + strict instruction)
        assert len(payloads[1]["messages"]) == 3
        strict_msg = payloads[1]["messages"][2]
        assert strict_msg["role"] == "user"
        assert "JSON" in strict_msg["content"]

    async def test_does_not_retry_more_than_once(self, monkeypatch):
        """The retry must happen at most once (max 2 total attempts), even if
        the second attempt also returns empty findings."""
        monkeypatch.setattr(nlp_module.settings, "ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")
        monkeypatch.setattr(nlp_module.settings, "ollama_timeout_seconds", 120)

        call_count = 0

        async def always_empty_post(url, json=None, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            mock_resp.json.return_value = _ollama_response("[]")
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = always_empty_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            result = await _parse_with_ollama("texto", "prompt")

        assert result == []
        assert call_count == 2, "Should stop retrying after one retry (2 total calls)"


# ── Ollama connection error ───────────────────────────────────────────────────


@pytest.mark.unit
class TestParseDentalTextOllamaConnectionError:
    async def test_connect_error_returns_empty_list(self, monkeypatch):
        """A ConnectError (Ollama not running) must be caught and return []
        instead of propagating."""
        import httpx

        monkeypatch.setattr(nlp_module.settings, "ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")
        monkeypatch.setattr(nlp_module.settings, "ollama_timeout_seconds", 120)

        async def raise_connect_error(url, **kwargs):
            raise httpx.ConnectError("Connection refused")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = raise_connect_error

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            result = await _parse_with_ollama("texto", "prompt")

        assert result == []

    async def test_http_status_error_returns_empty_list(self, monkeypatch):
        """An HTTP 500 from Ollama must be caught and return []."""
        import httpx

        monkeypatch.setattr(nlp_module.settings, "ollama_base_url", "http://localhost:11434")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")
        monkeypatch.setattr(nlp_module.settings, "ollama_timeout_seconds", 120)

        async def raise_http_error(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            raise httpx.HTTPStatusError(
                "500 Server Error", request=MagicMock(), response=mock_resp
            )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = raise_http_error

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            result = await _parse_with_ollama("texto", "prompt")

        assert result == []


# ── get_model_identifier ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestGetModelIdentifierLocal:
    def test_local_provider_returns_ollama_prefix(self, monkeypatch):
        """get_model_identifier with provider='local' returns 'ollama/{model}'."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "local")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "qwen2.5:32b")

        result = get_model_identifier()

        assert result == "ollama/qwen2.5:32b"

    def test_local_provider_reflects_configured_model(self, monkeypatch):
        """The model name in the identifier matches whatever ollama_model is
        configured."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "local")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "llama3.1:8b")

        result = get_model_identifier()

        assert result == "ollama/llama3.1:8b"


@pytest.mark.unit
class TestGetModelIdentifierAnthropic:
    def test_anthropic_provider_returns_claude_haiku(self, monkeypatch):
        """get_model_identifier with provider='anthropic' returns the exact
        Claude Haiku model ID used in the API call."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")

        result = get_model_identifier()

        assert result == "claude-haiku-4-5-20251001"

    def test_unknown_provider_returns_unknown_prefix(self, monkeypatch):
        """An unrecognised provider returns 'unknown/{provider}' so the caller
        can always inspect what was used."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "azure")

        result = get_model_identifier()

        assert result == "unknown/azure"


# ── parse_dental_text — invalid provider ─────────────────────────────────────


@pytest.mark.unit
class TestParseDentalTextInvalidProvider:
    async def test_unknown_provider_raises_value_error(self, monkeypatch):
        """An unknown provider in parse_dental_text must raise ValueError."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "gpt4")

        with pytest.raises(ValueError, match="Unknown NLP provider"):
            await parse_dental_text("texto", "prompt")

    async def test_error_message_includes_provider_name(self, monkeypatch):
        """The ValueError must include the actual bad provider name."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "bad_nlp")

        with pytest.raises(ValueError, match="bad_nlp"):
            await parse_dental_text("texto", "prompt")


# ── test_anthropic_empty_content ──────────────────────────────────────────────


@pytest.mark.unit
class TestAnthropicEmptyContent:
    """M4 fix: various degenerate Anthropic response shapes must return []
    without raising IndexError or KeyError."""

    async def _call_with_body(self, monkeypatch, response_body: dict) -> list:
        """Helper: configure Anthropic provider and mock POST to return body."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_api_key", "sk-ant-test")

        mock_response = MagicMock()
        mock_response.json.return_value = response_body
        mock_response.raise_for_status = MagicMock()

        mock_post = AsyncMock(return_value=mock_response)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = mock_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            return await parse_dental_text("texto", "prompt")

    async def test_empty_content_list_returns_empty(self, monkeypatch):
        """An Anthropic response with content=[] must return [] without
        raising IndexError."""
        response_body = {"content": []}
        result = await self._call_with_body(monkeypatch, response_body)
        assert result == []

    async def test_missing_content_key_returns_empty(self, monkeypatch):
        """An Anthropic response with no 'content' key must return [] without
        raising KeyError."""
        response_body = {"id": "msg_abc", "type": "message"}
        result = await self._call_with_body(monkeypatch, response_body)
        assert result == []

    async def test_empty_text_in_content_item_returns_empty(self, monkeypatch):
        """An Anthropic response where content[0].text == '' must return []
        without crashing."""
        response_body = {"content": [{"type": "text", "text": ""}]}
        result = await self._call_with_body(monkeypatch, response_body)
        assert result == []

    async def test_none_text_in_content_item_returns_empty(self, monkeypatch):
        """An Anthropic response where content[0].text is None must return []
        without raising AttributeError."""
        response_body = {"content": [{"type": "text", "text": None}]}
        result = await self._call_with_body(monkeypatch, response_body)
        assert result == []


# ── test_anthropic_uses_config_model ──────────────────────────────────────────


@pytest.mark.unit
class TestAnthropicUsesConfigModel:
    """M6 fix: the model field in the Anthropic POST payload must come from
    settings.anthropic_model, not a hardcoded string."""

    async def test_payload_model_matches_settings(self, monkeypatch):
        """When settings.anthropic_model is set to a custom value, the POST
        body's 'model' field must reflect that value exactly."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_api_key", "sk-ant-test")
        monkeypatch.setattr(nlp_module.settings, "anthropic_model", "test-model-123")

        captured_payload: dict = {}

        async def capture_post(url, json=None, headers=None, **kwargs):
            captured_payload.update(json or {})
            mock_resp = MagicMock()
            mock_resp.json.return_value = _anthropic_response(
                '[{"tooth_number": 11, "zone": "incisal", "condition_code": "fractura", "confidence": 0.9}]'
            )
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = capture_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            await parse_dental_text("texto", "prompt")

        assert captured_payload.get("model") == "test-model-123"

    async def test_different_model_values_propagate(self, monkeypatch):
        """Changing settings.anthropic_model to a different string produces a
        different 'model' field in the request — not a stale cached value."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_api_key", "sk-ant-test")
        monkeypatch.setattr(nlp_module.settings, "anthropic_model", "claude-opus-4-0")

        captured_payload: dict = {}

        async def capture_post(url, json=None, headers=None, **kwargs):
            captured_payload.update(json or {})
            mock_resp = MagicMock()
            mock_resp.json.return_value = _anthropic_response("[]")
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = capture_post

        with patch("app.services.voice_nlp.httpx.AsyncClient", return_value=mock_client):
            await parse_dental_text("texto", "prompt")

        assert captured_payload.get("model") == "claude-opus-4-0"


# ── test_get_model_identifier_uses_config ─────────────────────────────────────


@pytest.mark.unit
class TestGetModelIdentifierUsesConfig:
    """get_model_identifier() for the 'anthropic' provider must read
    settings.anthropic_model at call-time instead of returning a hardcoded
    model ID."""

    def test_returns_settings_anthropic_model_value(self, monkeypatch):
        """get_model_identifier() returns exactly the value of
        settings.anthropic_model when provider is 'anthropic'."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_model", "test-model-123")

        result = get_model_identifier()

        assert result == "test-model-123"

    def test_reflects_changed_model_without_restart(self, monkeypatch):
        """Changing settings.anthropic_model within the same process causes
        get_model_identifier() to return the new value (no caching)."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "anthropic")
        monkeypatch.setattr(nlp_module.settings, "anthropic_model", "model-v1")

        result_v1 = get_model_identifier()

        monkeypatch.setattr(nlp_module.settings, "anthropic_model", "model-v2")
        result_v2 = get_model_identifier()

        assert result_v1 == "model-v1"
        assert result_v2 == "model-v2"

    def test_local_provider_not_affected_by_anthropic_model(self, monkeypatch):
        """When provider is 'local', get_model_identifier() returns the Ollama
        prefix regardless of what settings.anthropic_model is set to."""
        monkeypatch.setattr(nlp_module.settings, "voice_nlp_provider", "local")
        monkeypatch.setattr(nlp_module.settings, "ollama_model", "llama3:8b")
        monkeypatch.setattr(nlp_module.settings, "anthropic_model", "should-not-appear")

        result = get_model_identifier()

        assert result == "ollama/llama3:8b"
        assert "should-not-appear" not in result


# ── test_extract_json_array_edge_cases ────────────────────────────────────────


@pytest.mark.unit
class TestExtractJsonArrayEdgeCases:
    def test_single_element_array(self):
        """A JSON array with exactly one element is parsed correctly."""
        single = [{"tooth_number": 11, "zone": "incisal", "condition_code": "fractura", "confidence": 0.9}]
        result = _extract_json_array(json.dumps(single))
        assert result == single
        assert len(result) == 1

    def test_single_element_with_whitespace_padding(self):
        """A single-element array with surrounding whitespace is trimmed and
        parsed without error."""
        single = [{"tooth_number": 48, "zone": "distal", "condition_code": "impactacion", "confidence": 0.75}]
        raw = "\n\n  " + json.dumps(single) + "  \n"
        result = _extract_json_array(raw)
        assert result == single

    def test_single_element_in_fenced_block(self):
        """A single-element array inside a ```json fence is extracted."""
        single = [{"tooth_number": 21, "zone": "vestibular", "condition_code": "fractura", "confidence": 0.88}]
        content = "```json\n" + json.dumps(single) + "\n```"
        result = _extract_json_array(content)
        assert result == single

    def test_nested_array_in_findings_value(self):
        """An object where the 'findings' key maps to a nested list of lists
        returns the outer list (not recursively unwrapped)."""
        # The wrapper unwrap logic returns whatever is under 'findings'
        inner_list = [{"tooth_number": 36, "zone": "oclusal", "condition_code": "caries", "confidence": 0.95}]
        payload = {"findings": inner_list}
        result = _extract_json_array(json.dumps(payload))
        assert result == inner_list

    def test_nested_object_within_array_element(self):
        """Array elements that themselves contain nested dicts are returned
        intact (no flattening)."""
        complex_finding = [
            {
                "tooth_number": 36,
                "zone": "oclusal",
                "condition_code": "caries",
                "confidence": 0.95,
                "metadata": {"severity": "moderate", "notes": ["note1", "note2"]},
            }
        ]
        result = _extract_json_array(json.dumps(complex_finding))
        assert result == complex_finding
        assert result[0]["metadata"]["notes"] == ["note1", "note2"]

    def test_array_of_two_elements_with_wrapper_key(self):
        """A 'results' wrapper containing exactly two items unwraps to a
        two-element list."""
        two_findings = [
            {"tooth_number": 11, "zone": "incisal", "condition_code": "fractura", "confidence": 0.9},
            {"tooth_number": 21, "zone": "vestibular", "condition_code": "abrasion", "confidence": 0.7},
        ]
        payload = {"results": two_findings}
        result = _extract_json_array(json.dumps(payload))
        assert result == two_findings
        assert len(result) == 2


# ── module-level import of json (needed in test closures above) ───────────────
# The retry test closures reference json.dumps through a local alias to avoid
# shadowing the module-level `json` import.

import json as json_module_dumps  # noqa: E402 — intentional late alias

json_module_dumps = json.dumps  # type: ignore[assignment]

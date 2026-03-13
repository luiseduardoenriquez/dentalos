"""Dental NLP provider for the voice pipeline.

Dispatches to either a local Ollama model (Qwen2.5) or the Anthropic Claude API
based on ``settings.voice_nlp_provider``.

Local mode:
  - Uses Ollama's OpenAI-compatible ``/v1/chat/completions`` endpoint.
  - Retries once with a stricter "return only JSON" instruction on parse failure.

Anthropic mode:
  - Calls the Claude Messages API directly via httpx (no SDK needed).

Both paths use ``_extract_json_array()`` to robustly parse the LLM output,
handling markdown fences, wrapper objects, preamble text, etc.
"""

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("dentalos.voice.nlp")


# ── JSON extraction helper ────────────────────────────────────────────────


def _extract_json_array(content: str) -> list[dict[str, Any]]:
    r"""Robustly extract a JSON array of findings from LLM output.

    Handles common patterns:
      1. Clean JSON array: ``[{...}, ...]``
      2. Markdown fenced block: ``\`\`\`json\n[...]\n\`\`\```
      3. Wrapper object: ``{"findings": [...]}``
      4. Preamble text followed by array: ``Here are the findings:\n[...]``
    """
    text = content.strip()

    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        # Wrapper object with a findings key
        if isinstance(parsed, dict):
            for key in ("findings", "results", "data"):
                if key in parsed and isinstance(parsed[key], list):
                    return parsed[key]
            return []
    except json.JSONDecodeError:
        pass

    # Find the first JSON array in the text
    bracket_match = re.search(r"\[.*\]", text, re.DOTALL)
    if bracket_match:
        try:
            parsed = json.loads(bracket_match.group())
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    logger.warning("Could not extract JSON array from LLM output (len=%d)", len(content))
    return []


# ── Public API ────────────────────────────────────────────────────────────


class ParseResult:
    """Result of an NLP parse including findings and token usage metadata."""

    __slots__ = ("findings", "input_tokens", "output_tokens")

    def __init__(
        self,
        findings: list[dict[str, Any]],
        input_tokens: int = 0,
        output_tokens: int = 0,
    ):
        self.findings = findings
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


async def parse_dental_text(
    text: str,
    prompt: str,
) -> ParseResult:
    """Parse dental dictation text into structured findings.

    Dispatches based on ``settings.voice_nlp_provider``:
      - ``"local"``: Ollama (Qwen2.5 via OpenAI-compatible API)
      - ``"anthropic"``: Claude Haiku API

    Returns a ParseResult with findings list and token usage metadata.
    """
    provider = settings.voice_nlp_provider

    if provider == "local":
        findings = await _parse_with_ollama(text, prompt)
        return ParseResult(findings)

    if provider == "anthropic":
        return await _parse_with_anthropic(text, prompt)

    raise ValueError(
        f"Unknown NLP provider: {provider!r}. Use 'local' or 'anthropic'."
    )


# ── Ollama (local) ────────────────────────────────────────────────────────


async def _parse_with_ollama(
    text: str,
    prompt: str,
    *,
    _attempt: int = 1,
) -> list[dict[str, Any]]:
    """Call Ollama's OpenAI-compatible chat completions endpoint."""
    url = f"{settings.ollama_base_url}/v1/chat/completions"
    timeout = settings.ollama_timeout_seconds

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]

    # On retry, add a stricter instruction
    if _attempt > 1:
        messages.append({
            "role": "user",
            "content": (
                "IMPORTANT: Return ONLY a valid JSON array, no extra text. "
                "Example: [{\"tooth_number\": 36, \"zone\": \"oclusal\", "
                "\"condition_code\": \"caries\", \"confidence\": 0.95}]"
            ),
        })

    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "temperature": 0.1,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        findings = _extract_json_array(content)

        if not findings and _attempt < 2:
            logger.info("Ollama returned no findings, retrying with stricter prompt")
            return await _parse_with_ollama(text, prompt, _attempt=_attempt + 1)

        logger.info(
            "Ollama NLP completed: model=%s findings=%d attempt=%d",
            settings.ollama_model,
            len(findings),
            _attempt,
        )
        return findings

    except httpx.HTTPStatusError as e:
        logger.error(
            "Ollama HTTP error: status=%d body=%s",
            e.response.status_code,
            e.response.text[:200],
        )
        return []
    except httpx.ConnectError:
        logger.error(
            "Cannot connect to Ollama at %s — is it running?",
            settings.ollama_base_url,
        )
        return []
    except Exception:
        logger.exception("Unexpected error calling Ollama")
        return []


# ── Anthropic (cloud) ─────────────────────────────────────────────────────


async def _parse_with_anthropic(
    text: str,
    prompt: str,
) -> "ParseResult":
    """Call the Anthropic Messages API directly via httpx."""
    url = "https://api.anthropic.com/v1/messages"

    if not settings.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set — cannot use anthropic NLP provider")
        return ParseResult([])

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # M6: Use configurable model from settings
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 2048,
        "system": prompt,
        "messages": [{"role": "user", "content": text}],
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        usage = data.get("usage", {})
        inp_tokens = usage.get("input_tokens", 0)
        out_tokens = usage.get("output_tokens", 0)

        # M4: Guard against empty content list
        content_blocks = data.get("content", [])
        if not content_blocks:
            logger.warning("Anthropic returned empty content list")
            return ParseResult([], inp_tokens, out_tokens)

        content = content_blocks[0].get("text", "")
        if not content:
            logger.warning("Anthropic returned empty text in first content block")
            return ParseResult([], inp_tokens, out_tokens)

        findings = _extract_json_array(content)

        logger.info(
            "Anthropic NLP completed: findings=%d input_tokens=%d output_tokens=%d",
            len(findings), inp_tokens, out_tokens,
        )
        return ParseResult(findings, inp_tokens, out_tokens)

    except httpx.HTTPStatusError as e:
        logger.error(
            "Anthropic HTTP error: status=%d body=%s",
            e.response.status_code,
            e.response.text[:200],
        )
        return ParseResult([])
    except Exception:
        logger.exception("Unexpected error calling Anthropic API")
        return ParseResult([])


def get_model_identifier() -> str:
    """Return the model name string for VoiceParse.llm_model field."""
    provider = settings.voice_nlp_provider
    if provider == "local":
        return f"ollama/{settings.ollama_model}"
    if provider == "anthropic":
        return settings.anthropic_model
    return f"unknown/{provider}"

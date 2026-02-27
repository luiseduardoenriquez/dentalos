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


async def parse_dental_text(
    text: str,
    prompt: str,
) -> list[dict[str, Any]]:
    """Parse dental dictation text into structured findings.

    Dispatches based on ``settings.voice_nlp_provider``:
      - ``"local"``: Ollama (Qwen2.5 via OpenAI-compatible API)
      - ``"anthropic"``: Claude Haiku API

    Returns a list of finding dicts, or empty list on failure.
    """
    provider = settings.voice_nlp_provider

    if provider == "local":
        return await _parse_with_ollama(text, prompt)

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
) -> list[dict[str, Any]]:
    """Call the Anthropic Messages API directly via httpx."""
    url = "https://api.anthropic.com/v1/messages"

    if not settings.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set — cannot use anthropic NLP provider")
        return []

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2048,
        "system": prompt,
        "messages": [{"role": "user", "content": text}],
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

        data = response.json()
        content = data["content"][0]["text"]
        findings = _extract_json_array(content)

        logger.info("Anthropic NLP completed: findings=%d", len(findings))
        return findings

    except httpx.HTTPStatusError as e:
        logger.error(
            "Anthropic HTTP error: status=%d body=%s",
            e.response.status_code,
            e.response.text[:200],
        )
        return []
    except Exception:
        logger.exception("Unexpected error calling Anthropic API")
        return []


def get_model_identifier() -> str:
    """Return the model name string for VoiceParse.llm_model field."""
    provider = settings.voice_nlp_provider
    if provider == "local":
        return f"ollama/{settings.ollama_model}"
    if provider == "anthropic":
        return "claude-haiku-4-5-20251001"
    return f"unknown/{provider}"

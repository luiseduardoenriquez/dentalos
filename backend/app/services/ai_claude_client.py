"""Shared Claude API client for AI features (VP-13, GAP-14).

Extracted from voice_nlp.py pattern. Calls the Anthropic Messages API
directly via httpx — no SDK dependency.

Used by:
  - ai_treatment_service.py (VP-13: AI Treatment Advisor)
  - ai_report_service.py (GAP-14: Natural Language Reports)
"""

import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("dentalos.ai.claude")

_API_URL = "https://api.anthropic.com/v1/messages"


async def call_claude(
    *,
    system_prompt: str,
    user_content: str,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    model_override: str | None = None,
) -> dict[str, Any]:
    """Call Claude Messages API and return parsed response.

    Args:
        system_prompt: System instructions for Claude.
        user_content: The user message content.
        max_tokens: Maximum tokens for the response.
        temperature: Sampling temperature (0.0-1.0).
        model_override: Override the default model from settings.

    Returns:
        dict with keys: content (str), input_tokens (int), output_tokens (int)

    Raises:
        RuntimeError: If API key is not configured or API call fails.
    """
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    model = model_override or settings.anthropic_model
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user_content}],
    }

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(_API_URL, json=payload, headers=headers)
        response.raise_for_status()

    data = response.json()
    content_blocks = data.get("content", [])
    content = content_blocks[0].get("text", "") if content_blocks else ""
    usage = data.get("usage", {})

    logger.info(
        "Claude call completed: model=%s input_tokens=%d output_tokens=%d",
        model,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )

    return {
        "content": content,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
    }


def extract_json_object(content: str) -> dict[str, Any]:
    """Robustly extract a JSON object from LLM output.

    Handles markdown fences, preamble text, etc.
    """
    text = content.strip()

    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Find the first JSON object in the text
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            parsed = json.loads(brace_match.group())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    logger.warning("Could not extract JSON object from LLM output (len=%d)", len(content))
    return {}


def extract_json_array(content: str) -> list[dict[str, Any]]:
    """Robustly extract a JSON array from LLM output.

    Handles markdown fences, wrapper objects, preamble text.
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
        if isinstance(parsed, dict):
            for key in ("suggestions", "findings", "results", "data", "items"):
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

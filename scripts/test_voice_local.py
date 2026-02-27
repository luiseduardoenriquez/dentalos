#!/usr/bin/env python3
"""Smoke test for the local Voice AI pipeline (NLP only).

Sends sample Spanish dental dictation to the Ollama NLP provider
and prints the extracted findings.

Usage:
    cd backend
    python ../scripts/test_voice_local.py

Prerequisites:
    - Ollama running: curl http://localhost:11434/api/tags
    - Model pulled: ollama pull qwen2.5:32b
"""

import asyncio
import json
import sys

# Add backend to path so we can import app modules
sys.path.insert(0, ".")

SAMPLE_TEXT = (
    "El paciente presenta caries en el diente 36 cara oclusal "
    "y fractura en el diente 11 borde incisal. "
    "Se observa corona en el 46 y resina en el 24 cara mesial."
)

EXPECTED_CONDITIONS = {"caries", "fractura", "corona", "resina"}
EXPECTED_TEETH = {36, 11, 46, 24}


async def main() -> None:
    # Import after path setup
    from app.core.config import settings
    from app.services.voice_nlp import parse_dental_text
    from app.services.voice_service import DENTAL_NLP_PROMPT

    print(f"NLP provider: {settings.voice_nlp_provider}")
    print(f"Ollama URL:   {settings.ollama_base_url}")
    print(f"Ollama model: {settings.ollama_model}")
    print(f"\nInput text:\n  {SAMPLE_TEXT}\n")
    print("Calling NLP provider...")

    findings = await parse_dental_text(SAMPLE_TEXT, DENTAL_NLP_PROMPT)

    print(f"\nFindings ({len(findings)}):")
    print(json.dumps(findings, indent=2, ensure_ascii=False))

    # Validate structure
    ok = True
    found_conditions = set()
    found_teeth = set()

    for f in findings:
        for key in ("tooth_number", "zone", "condition_code", "confidence"):
            if key not in f:
                print(f"\n  FAIL: finding missing key '{key}': {f}")
                ok = False
        if "condition_code" in f:
            found_conditions.add(f["condition_code"])
        if "tooth_number" in f:
            found_teeth.add(int(f["tooth_number"]))

    missing_conditions = EXPECTED_CONDITIONS - found_conditions
    missing_teeth = EXPECTED_TEETH - found_teeth

    if missing_conditions:
        print(f"\n  WARN: missing conditions: {missing_conditions}")
    if missing_teeth:
        print(f"\n  WARN: missing teeth: {missing_teeth}")

    if ok and not missing_conditions and not missing_teeth:
        print("\n  ALL CHECKS PASSED")
    elif ok:
        print("\n  STRUCTURE OK (some expected values missing — check model output)")
    else:
        print("\n  STRUCTURE ERRORS FOUND")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

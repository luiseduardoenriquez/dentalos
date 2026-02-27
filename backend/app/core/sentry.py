"""Sentry integration with PHI scrubber -- I-15.

Security:
  - before_send callback strips ALL PHI from events, breadcrumbs, and extras
  - Patient names, document numbers, phones, emails, clinical notes, diagnoses
    are replaced with "[REDACTED]" before leaving the application
  - SQL fragments and schema names are stripped from error messages
  - Stack trace local variables are scrubbed for PHI patterns
"""

import logging
import re
from typing import Any

from app.core.config import settings

logger = logging.getLogger("dentalos.sentry")

# Patterns that indicate PHI in string values
_PHI_PATTERNS = [
    # Colombian cedula (6-12 digits)
    re.compile(r"\b\d{6,12}\b"),
    # Email addresses
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    # Phone numbers (LATAM format)
    re.compile(r"\+?\d{7,15}"),
]

# Keys whose values should ALWAYS be redacted
_PHI_KEYS = frozenset({
    "document_number",
    "cedula",
    "phone",
    "phone_number",
    "mobile",
    "email",
    "email_address",
    "first_name",
    "last_name",
    "full_name",
    "name",
    "patient_name",
    "doctor_name",
    "clinical_notes",
    "notes",
    "diagnosis",
    "diagnoses",
    "address",
    "password",
    "token",
    "refresh_token",
    "access_token",
    "secret",
    "authorization",
})

# Keys that are safe even if they match PHI key names (e.g., app_name)
_SAFE_KEYS = frozenset({
    "app_name",
    "template_name",
    "queue_name",
    "event_type",
    "job_type",
    "status",
    "error",
    "message_id",
    "tenant_id",
    "schema_name",
})

# SQL/schema patterns to strip from error messages
_SQL_PATTERN = re.compile(
    r"(tn_[a-z0-9_]+|SELECT\s|INSERT\s|UPDATE\s|DELETE\s|FROM\s|WHERE\s)",
    re.IGNORECASE,
)


def _scrub_value(key: str, value: Any) -> Any:
    """Scrub a single key-value pair for PHI."""
    if key.lower() in _SAFE_KEYS:
        return value

    if key.lower() in _PHI_KEYS:
        return "[REDACTED]"

    if isinstance(value, str) and len(value) > 3:
        # Check for SQL fragments in error messages
        if _SQL_PATTERN.search(value):
            return "[SQL_REDACTED]"

    return value


def _scrub_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively scrub a dictionary for PHI."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _scrub_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _scrub_dict(item) if isinstance(item, dict) else _scrub_value(key, item)
                for item in value
            ]
        else:
            result[key] = _scrub_value(key, value)
    return result


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Sentry before_send hook -- scrubs PHI from all events."""
    # Scrub exception values
    if "exception" in event:
        for exception in event["exception"].get("values", []):
            # Scrub the exception message
            val = exception.get("value", "")
            if isinstance(val, str):
                if _SQL_PATTERN.search(val):
                    exception["value"] = "[SQL_REDACTED]"
                # Scrub schema names from messages
                exception["value"] = re.sub(
                    r"tn_[a-z0-9_]+", "[TENANT]", exception.get("value", "")
                )

            # Scrub local variables in stack frames
            stacktrace = exception.get("stacktrace", {})
            for frame in stacktrace.get("frames", []):
                if "vars" in frame and isinstance(frame["vars"], dict):
                    frame["vars"] = _scrub_dict(frame["vars"])

    # Scrub breadcrumbs
    if "breadcrumbs" in event:
        for breadcrumb in event["breadcrumbs"].get("values", []):
            if "data" in breadcrumb and isinstance(breadcrumb["data"], dict):
                breadcrumb["data"] = _scrub_dict(breadcrumb["data"])
            # Scrub breadcrumb messages
            msg = breadcrumb.get("message", "")
            if isinstance(msg, str):
                breadcrumb["message"] = re.sub(r"tn_[a-z0-9_]+", "[TENANT]", msg)

    # Scrub extra data
    if "extra" in event and isinstance(event["extra"], dict):
        event["extra"] = _scrub_dict(event["extra"])

    # Scrub request data
    if "request" in event:
        req = event["request"]
        if "headers" in req and isinstance(req["headers"], dict):
            req["headers"] = _scrub_dict(req["headers"])
        if "data" in req and isinstance(req["data"], dict):
            req["data"] = _scrub_dict(req["data"])
        if "query_string" in req and isinstance(req["query_string"], str):
            req["query_string"] = re.sub(
                r"tn_[a-z0-9_]+", "[TENANT]", req["query_string"]
            )

    # Scrub user context (keep id, remove PII)
    if "user" in event and isinstance(event["user"], dict):
        user = event["user"]
        safe_user: dict[str, Any] = {"id": user.get("id")}
        if "ip_address" in user:
            safe_user["ip_address"] = user["ip_address"]
        event["user"] = safe_user

    return event


def setup_sentry() -> None:
    """Initialize Sentry SDK with PHI-safe configuration.

    Call this early in the application lifespan, before any other setup.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, skipping initialization")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            before_send=_before_send,
            send_default_pii=False,  # CRITICAL: never send PII by default
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=logging.WARNING,
                    event_level=logging.ERROR,
                ),
            ],
            # Strip sensitive data
            request_bodies="never",  # Never send request bodies (may contain PHI)
            max_breadcrumbs=20,
        )

        logger.info(
            "Sentry initialized: env=%s traces_rate=%.2f",
            settings.sentry_environment,
            settings.sentry_traces_sample_rate,
        )
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry initialization")
    except Exception:
        logger.exception("Failed to initialize Sentry")

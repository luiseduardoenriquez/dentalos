"""Medical history timeline service — unified event feed across clinical domains.

Aggregates events from diagnoses, procedures, clinical_records,
prescriptions, and consents into a single chronological timeline.
Uses cursor-based pagination for efficiency.
"""

import base64
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("dentalos.medical_history")


def _encode_cursor(event_date: datetime, event_id: uuid.UUID) -> str:
    raw = f"{event_date.isoformat()}|{event_id}"
    return base64.b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.b64decode(cursor.encode()).decode()
    parts = raw.split("|", 1)
    if len(parts) != 2:
        raise ValueError("Malformed cursor")
    return datetime.fromisoformat(parts[0]), uuid.UUID(parts[1])


class MedicalHistoryService:
    """Stateless medical history service."""

    async def get_timeline(
        self,
        *,
        db: AsyncSession,
        patient_id: str,
        cursor: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Return a unified medical history timeline for a patient.

        UNION ALL across: diagnoses, procedures, clinical_records,
        prescriptions, consents (signed only).
        Cursor-paginated by event_date DESC.
        """
        pid = uuid.UUID(patient_id)
        params: dict[str, Any] = {"patient_id": pid, "limit": limit + 1}

        cursor_clause = ""
        if cursor is not None:
            try:
                cursor_date, cursor_id = _decode_cursor(cursor)
                params["cursor_date"] = cursor_date
                params["cursor_id"] = cursor_id
                cursor_clause = "WHERE event_date < :cursor_date OR (event_date = :cursor_date AND event_id < :cursor_id)"
            except (ValueError, Exception):
                pass

        # UNION ALL query across clinical domains
        sql = text(f"""
            SELECT * FROM (
                SELECT id AS event_id, 'diagnosis' AS event_type,
                       cie10_code AS event_code, cie10_description AS event_description,
                       created_at AS event_date
                FROM diagnoses
                WHERE patient_id = :patient_id AND is_active = true

                UNION ALL

                SELECT id AS event_id, 'procedure' AS event_type,
                       cups_code AS event_code, cups_description AS event_description,
                       created_at AS event_date
                FROM procedures
                WHERE patient_id = :patient_id AND is_active = true

                UNION ALL

                SELECT id AS event_id, type AS event_type,
                       NULL AS event_code, NULL AS event_description,
                       created_at AS event_date
                FROM clinical_records
                WHERE patient_id = :patient_id AND is_active = true

                UNION ALL

                SELECT id AS event_id, 'prescription' AS event_type,
                       NULL AS event_code, NULL AS event_description,
                       created_at AS event_date
                FROM prescriptions
                WHERE patient_id = :patient_id AND is_active = true

                UNION ALL

                SELECT id AS event_id, 'consent' AS event_type,
                       NULL AS event_code, title AS event_description,
                       signed_at AS event_date
                FROM consents
                WHERE patient_id = :patient_id AND is_active = true AND status = 'signed'
            ) AS timeline
            {cursor_clause}
            ORDER BY event_date DESC, event_id DESC
            LIMIT :limit
        """)

        result = await db.execute(sql, params)
        rows = result.mappings().all()

        has_more = len(rows) > limit
        rows = rows[:limit]

        items = []
        for row in rows:
            items.append({
                "event_id": str(row["event_id"]),
                "event_type": row["event_type"],
                "event_code": row["event_code"],
                "event_description": row["event_description"],
                "event_date": row["event_date"],
            })

        next_cursor: str | None = None
        if has_more and items:
            last = rows[-1]
            next_cursor = _encode_cursor(last["event_date"], last["event_id"])

        return {
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }


# Module-level singleton
medical_history_service = MedicalHistoryService()

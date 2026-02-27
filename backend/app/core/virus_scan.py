"""Virus scanning interface — pluggable ClamAV integration."""
import io
import logging

from app.core.config import settings

logger = logging.getLogger("dentalos.virus_scan")


async def scan_file(data: bytes) -> dict:
    """Scan file data for viruses.

    Uses ClamAV via a Unix socket when configured. Fails open — if the scanner
    is unavailable the upload is allowed through and a warning is logged, so that
    a ClamAV outage does not block clinical workflows.

    Args:
        data: Raw file bytes to scan.

    Returns:
        {"clean": bool, "threat": str | None}
    """
    if not settings.clamav_socket:
        logger.warning("Virus scanning disabled — no clamav_socket configured")
        return {"clean": True, "threat": None}

    try:
        import clamd  # type: ignore[import]

        cd = clamd.ClamdUnixSocket(settings.clamav_socket)
        result = cd.instream(io.BytesIO(data))
        status = result.get("stream", ("OK", None))
        if status[0] == "FOUND":
            logger.warning("Virus detected in upload: threat=%s", status[1])
            return {"clean": False, "threat": status[1]}
        return {"clean": True, "threat": None}
    except Exception as exc:
        # Fail-open: log warning but allow upload so that a ClamAV outage
        # does not block clinical workflows.
        logger.warning("Virus scan failed (fail-open): %s", type(exc).__name__)
        return {"clean": True, "threat": None}

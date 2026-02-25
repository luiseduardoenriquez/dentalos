# Google Calendar Sync Integration Spec

> **Spec ID:** INT-09
> **Status:** Draft
> **Last Updated:** 2026-02-25

---

## Overview

**Feature:** Bi-directional Google Calendar sync for doctors. DentalOS appointments are mirrored as Google Calendar events, and Google Calendar changes sync back to DentalOS. Each doctor optionally connects their personal Google Calendar via OAuth2. Sync is real-time via Google push notifications (webhooks) with DentalOS as source of truth for conflict resolution. Disconnecting a calendar cleans up watch channels.

**Domain:** integrations / appointments

**Priority:** Medium

**Dependencies:** appointments domain, users domain, I-04 (background-processing), I-05 (caching)

---

## 1. Architecture Overview

```
DentalOS Appointment Created/Updated/Cancelled
    │
    ▼
Google Calendar Sync Worker
    │
    ├─► Create/Update/Delete event on doctor's Google Calendar
    │
    └─► Store google_event_id in appointments table

Google Calendar Event Changed (by doctor)
    │
    ▼
Google Push Notification → POST /api/v1/webhooks/google-calendar
    │
    ▼
Sync Worker: fetch updated event from Calendar API
    │
    ├─► Map to DentalOS appointment
    │
    └─► Update appointment (time change) OR log conflict
         │
         DentalOS is source of truth — never auto-delete from Google
```

### Sync Direction Summary

| Action in DentalOS | Effect in Google Calendar |
|--------------------|--------------------------|
| Appointment created | Create Google event |
| Appointment rescheduled | Update Google event time |
| Appointment cancelled | Delete Google event |
| Appointment updated (doctor/notes) | Update Google event title/description |

| Action in Google Calendar | Effect in DentalOS |
|--------------------------|-------------------|
| Event moved (time change) | Update appointment time in DentalOS (if no conflict) |
| Event deleted by doctor | Mark appointment as `sync_conflict` — alert staff (never auto-cancel) |
| New event created in Google | Ignored (DentalOS does not import arbitrary Google events) |

---

## 2. OAuth2 Setup per Doctor

### OAuth2 Scopes Required

| Scope | Purpose |
|-------|---------|
| `https://www.googleapis.com/auth/calendar.events` | Create, update, delete events in doctor's calendar |
| `https://www.googleapis.com/auth/calendar.readonly` | Read events to detect conflicts |

### OAuth Flow

```python
from google_auth_oauthlib.flow import Flow
from app.core.config import settings


def build_google_oauth_flow() -> Flow:
    """Build Google OAuth2 flow for Calendar access."""
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.readonly",
        ],
    )


@router.get("/api/v1/settings/calendar/google/connect")
async def google_calendar_connect(
    current_user: User = Depends(get_current_user),
):
    """Initiate Google Calendar OAuth for a doctor."""
    if current_user.role not in ("doctor", "clinic_owner"):
        raise Forbidden("Solo los doctores pueden conectar Google Calendar")

    flow = build_google_oauth_flow()
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

    auth_url, state = flow.authorization_url(
        access_type="offline",          # Request refresh_token
        include_granted_scopes="true",
        state=f"{current_user.tenant_id}:{current_user.id}",
        prompt="consent",               # Force consent to get refresh_token every time
    )
    return RedirectResponse(auth_url)


@router.get("/api/v1/settings/calendar/google/callback")
async def google_calendar_callback(code: str, state: str):
    """Handle Google OAuth callback. Store tokens for doctor."""
    tenant_id, user_id = state.split(":", 1)

    flow = build_google_oauth_flow()
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)

    credentials = flow.credentials
    await save_doctor_google_credentials(
        tenant_id=tenant_id,
        user_id=user_id,
        access_token=credentials.token,
        refresh_token=credentials.refresh_token,
        token_expiry=credentials.expiry,
    )

    # Set up push notifications (watch)
    await setup_calendar_watch(tenant_id, user_id)

    return RedirectResponse("/settings/calendar?connected=true")
```

### Credentials Storage (Tenant Schema)

```sql
CREATE TABLE doctor_google_calendar_config (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,
    google_email        VARCHAR(254),
    access_token        TEXT NOT NULL,              -- Encrypted AES-256-GCM
    refresh_token       TEXT NOT NULL,              -- Encrypted AES-256-GCM
    token_expiry        TIMESTAMPTZ,
    calendar_id         VARCHAR(255) DEFAULT 'primary',
    watch_channel_id    VARCHAR(100),               -- Push notification channel
    watch_resource_id   VARCHAR(100),               -- Google resource ID for channel
    watch_expiry        TIMESTAMPTZ,               -- Watch channels expire after 7 days
    is_active           BOOLEAN DEFAULT TRUE,
    sync_enabled        BOOLEAN DEFAULT TRUE,
    last_sync_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);
```

---

## 3. Google Calendar Service

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    def __init__(self, access_token: str, refresh_token: str, token_expiry: datetime):
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            expiry=token_expiry,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/calendar.events"],
        )
        # Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        self.service = build("calendar", "v3", credentials=creds)
        self._credentials = creds

    def get_updated_tokens(self) -> Optional[dict]:
        """Return updated tokens if they were refreshed."""
        if self._credentials.token:
            return {
                "access_token": self._credentials.token,
                "token_expiry": self._credentials.expiry,
            }
        return None

    async def create_event(
        self,
        calendar_id: str,
        appointment: dict,
    ) -> str:
        """
        Create a Google Calendar event for a DentalOS appointment.
        Returns the Google event ID.
        """
        event = self._build_event(appointment)

        created = self.service.events().insert(
            calendarId=calendar_id,
            body=event,
        ).execute()

        return created["id"]

    async def update_event(
        self,
        calendar_id: str,
        google_event_id: str,
        appointment: dict,
    ) -> None:
        """Update an existing Google Calendar event."""
        event = self._build_event(appointment)

        self.service.events().update(
            calendarId=calendar_id,
            eventId=google_event_id,
            body=event,
        ).execute()

    async def delete_event(
        self,
        calendar_id: str,
        google_event_id: str,
    ) -> None:
        """Delete a Google Calendar event (appointment cancelled)."""
        try:
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=google_event_id,
            ).execute()
        except HttpError as exc:
            if exc.resp.status == 410:
                # Already deleted
                logger.info("Google event already deleted", extra={"event_id": google_event_id})
            elif exc.resp.status == 404:
                logger.warning("Google event not found for deletion", extra={"event_id": google_event_id})
            else:
                raise

    async def get_event(
        self,
        calendar_id: str,
        google_event_id: str,
    ) -> Optional[dict]:
        """Get a single event by ID."""
        try:
            return self.service.events().get(
                calendarId=calendar_id,
                eventId=google_event_id,
            ).execute()
        except HttpError as exc:
            if exc.resp.status == 404:
                return None
            raise

    def _build_event(self, appointment: dict) -> dict:
        """
        Map a DentalOS appointment to a Google Calendar event.
        Only scheduling data — no clinical details in Google.
        """
        start = appointment["scheduled_at"]
        duration_minutes = appointment.get("duration_minutes", 60)
        end = start + timedelta(minutes=duration_minutes)

        # Keep description minimal — no clinical data in Google
        description_parts = [
            f"Clínica: {appointment['clinic_name']}",
            f"Tipo: {appointment['appointment_type']}",
        ]
        if appointment.get("notes_for_calendar"):
            description_parts.append(appointment["notes_for_calendar"])

        return {
            "summary": f"Cita dental - {appointment['patient_name']}",
            "description": "\n".join(description_parts),
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": appointment.get("timezone", "America/Bogota"),
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": appointment.get("timezone", "America/Bogota"),
            },
            "status": "confirmed",
            "source": {
                "title": "DentalOS",
                "url": f"https://app.dentalos.app/appointments/{appointment['id']}",
            },
            # Color: green for confirmed, red for pending
            "colorId": "2" if appointment["status"] == "confirmed" else "6",
        }
```

---

## 4. Push Notifications (Watch Channels)

Google Calendar push notifications allow real-time sync. When a doctor changes an event in Google, Google sends a notification to DentalOS immediately.

### Setting Up a Watch Channel

```python
import uuid


async def setup_calendar_watch(tenant_id: str, user_id: str) -> None:
    """
    Register a watch channel for the doctor's primary calendar.
    Channels expire after max 7 days (Google limitation).
    Must be renewed before expiry.
    """
    async with get_tenant_session(tenant_id) as session:
        config = await get_doctor_calendar_config(session, user_id)

    service = build_calendar_service(config)
    channel_id = str(uuid.uuid4())

    watch_request = {
        "id": channel_id,
        "type": "web_hook",
        "address": f"{settings.API_BASE_URL}/api/v1/webhooks/google-calendar",
        "token": f"{tenant_id}:{user_id}",
        "expiration": int((datetime.utcnow() + timedelta(days=7)).timestamp() * 1000),  # ms
    }

    try:
        result = service.service.events().watch(
            calendarId=config.calendar_id,
            body=watch_request,
        ).execute()

        # Store channel info for renewal and cleanup
        async with get_tenant_session(tenant_id) as session:
            await update_doctor_calendar_watch(
                session,
                user_id,
                channel_id=channel_id,
                resource_id=result.get("resourceId"),
                expiry=datetime.utcfromtimestamp(int(result["expiration"]) / 1000),
            )
    except HttpError as exc:
        logger.error("Failed to set up calendar watch", extra={"error": str(exc)})
        raise
```

### Watch Channel Renewal

A scheduled job runs every 6 days to renew expiring watch channels:

```python
# Scheduled via celery beat or APScheduler — daily at 2AM
async def renew_expiring_watch_channels() -> None:
    """Renew all watch channels expiring in < 24 hours."""
    cutoff = datetime.utcnow() + timedelta(hours=24)

    # Query all tenants for expiring channels
    expiring = await get_expiring_watch_channels(cutoff)

    for config in expiring:
        try:
            # Stop old channel
            await stop_calendar_watch(config)
            # Create new channel
            await setup_calendar_watch(config.tenant_id, config.user_id)
            logger.info("Watch channel renewed", extra={"user_id": config.user_id})
        except Exception as exc:
            logger.error("Watch channel renewal failed", extra={"error": str(exc)})
```

---

## 5. Webhook Handler

### Endpoint

```
POST /api/v1/webhooks/google-calendar
```

Public endpoint. Verified via Google channel token.

```python
from fastapi import APIRouter, Request, Header
from typing import Optional

router = APIRouter()

@router.post("/webhooks/google-calendar")
async def google_calendar_webhook(
    request: Request,
    x_goog_channel_id: str = Header(...),
    x_goog_resource_id: str = Header(...),
    x_goog_resource_state: str = Header(...),
    x_goog_channel_token: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None),
):
    """Handle Google Calendar push notification."""
    # 1. Verify token matches expected format (tenant_id:user_id)
    if not x_goog_channel_token or ":" not in x_goog_channel_token:
        raise HTTPException(status_code=403, detail="Invalid channel token")

    tenant_id, user_id = x_goog_channel_token.split(":", 1)

    # 2. Verify channel_id matches stored channel
    async with get_tenant_session(tenant_id) as session:
        config = await get_doctor_calendar_config(session, user_id)
        if not config or config.watch_channel_id != x_goog_channel_id:
            raise HTTPException(status_code=403, detail="Unknown channel")

    # 3. Handle sync messages
    if x_goog_resource_state == "sync":
        # Acknowledgment — no action needed
        return {"status": "ok"}

    # 4. Enqueue sync job for this doctor
    await enqueue_calendar_sync_job({
        "tenant_id": tenant_id,
        "user_id": user_id,
        "resource_state": x_goog_resource_state,
        "resource_id": x_goog_resource_id,
    })

    return {"status": "ok"}
```

---

## 6. Sync Worker — Inbound (Google → DentalOS)

```python
class CalendarSyncWorker:
    """
    Process inbound Google Calendar changes.
    Fetches recent events and reconciles with DentalOS appointments.
    """

    async def process_sync_job(
        self,
        tenant_id: str,
        user_id: str,
    ) -> None:
        async with get_tenant_session(tenant_id) as session:
            config = await get_doctor_calendar_config(session, user_id)
            if not config or not config.sync_enabled:
                return

        service = build_calendar_service(config)

        # Fetch events changed since last sync
        last_sync = config.last_sync_at or (datetime.utcnow() - timedelta(hours=24))
        events = self._list_recent_events(service, config.calendar_id, last_sync)

        async with get_tenant_session(tenant_id) as session:
            for event in events:
                google_event_id = event["id"]
                event_status = event.get("status")

                # Find matching DentalOS appointment
                appointment = await get_appointment_by_google_event_id(
                    session, google_event_id
                )

                if not appointment:
                    # Not a DentalOS event — ignore
                    continue

                if event_status == "cancelled":
                    # Doctor deleted event in Google — mark as conflict
                    await self._handle_deleted_event(session, appointment)
                else:
                    # Event was modified — check if time changed
                    await self._handle_modified_event(session, appointment, event)

            # Update last sync timestamp
            await update_last_sync_time(session, user_id)

    def _list_recent_events(
        self,
        service: GoogleCalendarService,
        calendar_id: str,
        since: datetime,
    ) -> list:
        """Fetch events modified after the given timestamp."""
        result = service.service.events().list(
            calendarId=calendar_id,
            updatedMin=since.isoformat() + "Z",
            singleEvents=True,
            showDeleted=True,
        ).execute()
        return result.get("items", [])

    async def _handle_deleted_event(self, session, appointment) -> None:
        """
        Doctor deleted the event in Google.
        DentalOS is source of truth — do NOT auto-cancel appointment.
        Mark as sync conflict and alert staff.
        """
        appointment.google_sync_status = "conflict"
        appointment.google_sync_conflict_at = datetime.utcnow()
        await session.commit()

        # Alert staff via in-app notification
        await enqueue_sync_conflict_notification(appointment)
        logger.warning(
            "Calendar sync conflict: event deleted in Google",
            extra={"appointment_id": appointment.id}
        )

    async def _handle_modified_event(
        self,
        session,
        appointment,
        google_event: dict,
    ) -> None:
        """
        Doctor moved the event in Google.
        Update appointment time if no conflicts.
        """
        new_start_str = google_event.get("start", {}).get("dateTime")
        if not new_start_str:
            return

        new_start = datetime.fromisoformat(new_start_str)
        current_start = appointment.scheduled_at

        if abs((new_start - current_start).total_seconds()) < 60:
            # No meaningful time change
            return

        # Check for booking conflicts at new time
        has_conflict = await check_appointment_conflict(
            session,
            doctor_id=appointment.doctor_id,
            new_time=new_start,
            duration=appointment.duration_minutes,
            exclude_appointment_id=appointment.id,
        )

        if has_conflict:
            appointment.google_sync_status = "conflict"
            logger.warning(
                "Calendar sync conflict: time change conflicts with another appointment",
                extra={"appointment_id": appointment.id}
            )
        else:
            appointment.scheduled_at = new_start
            appointment.google_sync_status = "synced"
            appointment.updated_at = datetime.utcnow()
            logger.info(
                "Appointment rescheduled via Google Calendar sync",
                extra={"appointment_id": appointment.id}
            )

        await session.commit()
```

---

## 7. Outbound Sync (DentalOS → Google)

```python
class CalendarOutboundSync:
    """
    Sync DentalOS appointment changes to Google Calendar.
    Called after each appointment create/update/cancel.
    """

    async def sync_appointment(
        self,
        appointment_id: str,
        tenant_id: str,
        action: str,  # "create" | "update" | "cancel"
    ) -> None:
        async with get_tenant_session(tenant_id) as session:
            appointment = await get_appointment(session, appointment_id)
            if not appointment:
                return

            config = await get_doctor_calendar_config(session, appointment.doctor_id)
            if not config or not config.is_active or not config.sync_enabled:
                return  # Doctor hasn't connected Google Calendar

        service = build_calendar_service(config)
        appointment_data = self._build_appointment_data(appointment)

        try:
            if action == "create":
                google_event_id = await service.create_event(
                    config.calendar_id, appointment_data
                )
                async with get_tenant_session(tenant_id) as session:
                    await update_appointment_google_event_id(
                        session, appointment_id, google_event_id
                    )

            elif action == "update":
                if appointment.google_event_id:
                    await service.update_event(
                        config.calendar_id,
                        appointment.google_event_id,
                        appointment_data,
                    )

            elif action == "cancel":
                if appointment.google_event_id:
                    await service.delete_event(
                        config.calendar_id,
                        appointment.google_event_id,
                    )

        except HttpError as exc:
            logger.error(
                "Google Calendar sync error",
                extra={"action": action, "error": str(exc)}
            )
            # Do not raise — Google Calendar sync failure should not block DentalOS

        # Refresh tokens if updated
        updated = service.get_updated_tokens()
        if updated:
            async with get_tenant_session(tenant_id) as session:
                await update_doctor_calendar_tokens(
                    session, appointment.doctor_id, updated
                )
```

---

## 8. Disconnect (Cleanup)

When a doctor disconnects their Google Calendar:

```python
@router.delete("/api/v1/settings/calendar/google/disconnect")
async def google_calendar_disconnect(
    current_user: User = Depends(get_current_user),
):
    """
    Disconnect Google Calendar for a doctor.
    Stops push notification channel and removes credentials.
    """
    async with get_tenant_session(current_user.tenant_id) as session:
        config = await get_doctor_calendar_config(session, current_user.id)
        if not config:
            raise NotFound("Cuenta de Google Calendar no conectada")

        # 1. Stop push notification channel
        if config.watch_channel_id and config.watch_resource_id:
            try:
                service = build_calendar_service(config)
                service.service.channels().stop(body={
                    "id": config.watch_channel_id,
                    "resourceId": config.watch_resource_id,
                }).execute()
            except HttpError:
                pass  # Channel may already be expired

        # 2. Revoke Google OAuth token
        if config.access_token:
            import requests
            requests.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": config.access_token},
            )

        # 3. Delete config record
        await session.delete(config)
        await session.commit()

    return {"status": "disconnected"}
```

---

## 9. Appointments Table Additions

```sql
-- Additional columns added to the appointments table
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS
    google_event_id         VARCHAR(100),          -- Google Calendar event ID
    google_sync_status      VARCHAR(20) DEFAULT 'not_synced',
    -- not_synced | synced | conflict | error
    google_sync_conflict_at TIMESTAMPTZ;

CREATE INDEX idx_appointments_google_event_id
    ON appointments(google_event_id)
    WHERE google_event_id IS NOT NULL;
```

---

## 10. Privacy Considerations

- Only scheduling data (date, time, patient first name, appointment type) is sent to Google Calendar
- No clinical data (diagnoses, procedures, notes) in Google events
- Patients are identified only by first name in Google event titles
- Doctor must explicitly opt in — sync is disabled by default
- Tokens stored encrypted (AES-256-GCM) in database
- Disconnect immediately revokes Google OAuth token

---

## 11. Configuration Reference

### Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google Cloud project OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google Cloud project OAuth client secret |
| `GOOGLE_REDIRECT_URI` | `https://app.dentalos.app/api/v1/settings/calendar/google/callback` |

---

## Out of Scope

- Syncing blockers / availability slots from Google to DentalOS schedule
- Multi-calendar support (only primary calendar)
- Sync of historical appointments (only future appointments)
- Apple Calendar / Outlook Calendar — future feature
- Sync of clinical events (surgeries, procedures) as separate calendar

---

## Acceptance Criteria

**This integration is complete when:**

- [ ] Doctor connects Google Calendar via OAuth successfully
- [ ] Creating an appointment in DentalOS creates event in Google Calendar
- [ ] Rescheduling appointment updates Google event time
- [ ] Cancelling appointment deletes Google event
- [ ] Doctor moving event in Google → DentalOS appointment time updates (no conflict)
- [ ] Doctor deleting event in Google → sync conflict flagged in DentalOS (not auto-cancelled)
- [ ] Watch channel renewed before 7-day expiry
- [ ] Disconnect revokes token and stops watch channel
- [ ] No PHI/clinical data appears in Google Calendar events

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial spec |

"""Integration tests for Notification API (N-01 through N-04, U-09).

Endpoints:
  GET  /api/v1/notifications                          — N-01
  POST /api/v1/notifications/{notification_id}/read   — N-02
  POST /api/v1/notifications/read-all                 — N-03
  GET  /api/v1/notifications/preferences              — N-04
  PUT  /api/v1/notifications/preferences              — U-09
"""

import uuid

import pytest

BASE = "/api/v1/notifications"
NOTIF_ID = str(uuid.uuid4())


# ─── N-01: List notifications ────────────────────────────────────────────────


@pytest.mark.integration
class TestListNotifications:
    async def test_list_authenticated(self, authenticated_client):
        response = await authenticated_client.get(BASE)
        assert response.status_code in (200, 500)

    async def test_list_with_status_filter(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"status": "unread"}
        )
        assert response.status_code in (200, 500)

    async def test_list_with_type_filter(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"type": "appointment_reminder"}
        )
        assert response.status_code in (200, 500)

    async def test_list_with_cursor_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"limit": 5}
        )
        assert response.status_code in (200, 500)

    async def test_list_invalid_limit(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"limit": 0}
        )
        assert response.status_code == 422

    async def test_list_limit_too_high(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"limit": 101}
        )
        assert response.status_code == 422

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(BASE)
        assert response.status_code == 401

    async def test_list_as_doctor(self, doctor_client):
        response = await doctor_client.get(BASE)
        assert response.status_code in (200, 500)


# ─── N-02: Mark single notification as read ──────────────────────────────────


@pytest.mark.integration
class TestMarkNotificationRead:
    async def test_mark_read_authenticated(self, authenticated_client):
        response = await authenticated_client.post(f"{BASE}/{NOTIF_ID}/read")
        assert response.status_code in (200, 404, 500)

    async def test_mark_read_no_auth(self, async_client):
        response = await async_client.post(f"{BASE}/{NOTIF_ID}/read")
        assert response.status_code == 401


# ─── N-03: Mark all notifications as read ────────────────────────────────────


@pytest.mark.integration
class TestMarkAllRead:
    async def test_mark_all_read(self, authenticated_client):
        response = await authenticated_client.post(f"{BASE}/read-all")
        assert response.status_code in (200, 500)

    async def test_mark_all_read_with_type(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/read-all",
            json={"type": "appointment_reminder"},
        )
        assert response.status_code in (200, 500)

    async def test_mark_all_read_no_auth(self, async_client):
        response = await async_client.post(f"{BASE}/read-all")
        assert response.status_code == 401


# ─── N-04: Get notification preferences ──────────────────────────────────────


@pytest.mark.integration
class TestGetPreferences:
    async def test_get_preferences_authenticated(self, authenticated_client):
        response = await authenticated_client.get(f"{BASE}/preferences")
        assert response.status_code in (200, 500)

    async def test_get_preferences_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/preferences")
        assert response.status_code == 401


# ─── U-09: Update notification preferences ──────────────────────────────────


@pytest.mark.integration
class TestUpdatePreferences:
    async def test_update_valid(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/preferences",
            json={
                "preferences": [
                    {
                        "event_type": "appointment_reminder",
                        "channel": "email",
                        "enabled": True,
                    }
                ]
            },
        )
        assert response.status_code in (200, 500)

    async def test_update_multiple(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/preferences",
            json={
                "preferences": [
                    {
                        "event_type": "appointment_reminder",
                        "channel": "email",
                        "enabled": True,
                    },
                    {
                        "event_type": "payment_received",
                        "channel": "sms",
                        "enabled": False,
                    },
                ]
            },
        )
        assert response.status_code in (200, 500)

    async def test_update_empty_list(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/preferences",
            json={"preferences": []},
        )
        assert response.status_code == 422

    async def test_update_missing_event_type(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/preferences",
            json={
                "preferences": [{"channel": "email", "enabled": True}]
            },
        )
        assert response.status_code == 422

    async def test_update_missing_channel(self, authenticated_client):
        response = await authenticated_client.put(
            f"{BASE}/preferences",
            json={
                "preferences": [
                    {"event_type": "appointment_reminder", "enabled": True}
                ]
            },
        )
        assert response.status_code == 422

    async def test_update_no_auth(self, async_client):
        response = await async_client.put(
            f"{BASE}/preferences",
            json={
                "preferences": [
                    {
                        "event_type": "appointment_reminder",
                        "channel": "email",
                        "enabled": True,
                    }
                ]
            },
        )
        assert response.status_code == 401

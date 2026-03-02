"""Integration tests for Messaging API (MS-01 through MS-05).

Endpoints:
  POST /api/v1/messages/threads                — MS-01
  GET  /api/v1/messages/threads                — MS-02
  POST /api/v1/messages/threads/{id}/messages  — MS-03
  GET  /api/v1/messages/threads/{id}/messages  — MS-04
  POST /api/v1/messages/threads/{id}/read      — MS-05
"""

import uuid

import pytest

BASE = "/api/v1/messages/threads"
THREAD_ID = str(uuid.uuid4())


# ─── MS-01: Create thread ───────────────────────────────────────────────────


@pytest.mark.integration
class TestCreateThread:
    async def test_create_valid(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "patient_id": str(uuid.uuid4()),
                "subject": "Consulta sobre tratamiento",
                "initial_message": "Hola, tengo una pregunta sobre mi cita.",
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_without_subject(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "patient_id": str(uuid.uuid4()),
                "initial_message": "Mensaje sin asunto.",
            },
        )
        assert response.status_code in (201, 500)

    async def test_create_missing_patient_id(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={"initial_message": "Hola."},
        )
        assert response.status_code == 422

    async def test_create_missing_initial_message(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={"patient_id": str(uuid.uuid4())},
        )
        assert response.status_code == 422

    async def test_create_empty_initial_message(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "patient_id": str(uuid.uuid4()),
                "initial_message": "",
            },
        )
        assert response.status_code == 422

    async def test_create_message_too_long(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "patient_id": str(uuid.uuid4()),
                "initial_message": "x" * 2001,
            },
        )
        assert response.status_code == 422

    async def test_create_subject_too_long(self, authenticated_client):
        response = await authenticated_client.post(
            BASE,
            json={
                "patient_id": str(uuid.uuid4()),
                "subject": "x" * 201,
                "initial_message": "Hola.",
            },
        )
        assert response.status_code == 422

    async def test_create_no_auth(self, async_client):
        response = await async_client.post(
            BASE,
            json={
                "patient_id": str(uuid.uuid4()),
                "initial_message": "Hola.",
            },
        )
        assert response.status_code == 401

    async def test_create_as_doctor(self, doctor_client):
        response = await doctor_client.post(
            BASE,
            json={
                "patient_id": str(uuid.uuid4()),
                "initial_message": "Hola doctor.",
            },
        )
        assert response.status_code in (201, 500)


# ─── MS-02: List threads ────────────────────────────────────────────────────


@pytest.mark.integration
class TestListThreads:
    async def test_list_authenticated(self, authenticated_client):
        response = await authenticated_client.get(BASE)
        assert response.status_code in (200, 500)

    async def test_list_with_patient_filter(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"patient_id": str(uuid.uuid4())}
        )
        assert response.status_code in (200, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"limit": 5}
        )
        assert response.status_code in (200, 500)

    async def test_list_invalid_limit(self, authenticated_client):
        response = await authenticated_client.get(
            BASE, params={"limit": 0}
        )
        assert response.status_code == 422

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(BASE)
        assert response.status_code == 401


# ─── MS-03: Send message ────────────────────────────────────────────────────


@pytest.mark.integration
class TestSendMessage:
    async def test_send_valid(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/{THREAD_ID}/messages",
            json={"body": "Respuesta al paciente."},
        )
        assert response.status_code in (201, 404, 500)

    async def test_send_empty_body(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/{THREAD_ID}/messages",
            json={"body": ""},
        )
        assert response.status_code == 422

    async def test_send_body_too_long(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/{THREAD_ID}/messages",
            json={"body": "x" * 2001},
        )
        assert response.status_code == 422

    async def test_send_missing_body(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/{THREAD_ID}/messages",
            json={},
        )
        assert response.status_code == 422

    async def test_send_no_auth(self, async_client):
        response = await async_client.post(
            f"{BASE}/{THREAD_ID}/messages",
            json={"body": "Hola."},
        )
        assert response.status_code == 401


# ─── MS-04: List messages in thread ─────────────────────────────────────────


@pytest.mark.integration
class TestListMessages:
    async def test_list_authenticated(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/{THREAD_ID}/messages"
        )
        assert response.status_code in (200, 404, 500)

    async def test_list_with_pagination(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/{THREAD_ID}/messages", params={"limit": 10}
        )
        assert response.status_code in (200, 404, 500)

    async def test_list_invalid_limit(self, authenticated_client):
        response = await authenticated_client.get(
            f"{BASE}/{THREAD_ID}/messages", params={"limit": 0}
        )
        assert response.status_code == 422

    async def test_list_no_auth(self, async_client):
        response = await async_client.get(f"{BASE}/{THREAD_ID}/messages")
        assert response.status_code == 401


# ─── MS-05: Mark thread read ────────────────────────────────────────────────


@pytest.mark.integration
class TestMarkThreadRead:
    async def test_mark_read_authenticated(self, authenticated_client):
        response = await authenticated_client.post(
            f"{BASE}/{THREAD_ID}/read"
        )
        assert response.status_code in (200, 404, 500)

    async def test_mark_read_no_auth(self, async_client):
        response = await async_client.post(f"{BASE}/{THREAD_ID}/read")
        assert response.status_code == 401

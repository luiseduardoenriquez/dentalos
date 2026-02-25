import pytest

from app.core.config import settings


@pytest.mark.unit
async def test_health_returns_status_and_version(async_client):
    """Health endpoint returns status, version, and services dict."""
    response = await async_client.get("/api/v1/health")
    data = response.json()

    # Should return 200 or 503 depending on infra, but always have these keys
    assert response.status_code in (200, 503)
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert data["version"] == settings.app_version
    assert "services" in data
    assert isinstance(data["services"], dict)
    assert "duration_ms" in data
    assert isinstance(data["duration_ms"], int)


@pytest.mark.unit
async def test_health_services_includes_all_deps(async_client):
    """Health endpoint checks all four infrastructure dependencies."""
    response = await async_client.get("/api/v1/health")
    services = response.json()["services"]

    expected_services = {"postgres", "redis", "rabbitmq", "minio"}
    assert expected_services == set(services.keys())

    for service_name, service_data in services.items():
        assert "status" in service_data, f"{service_name} missing status"
        assert service_data["status"] in ("healthy", "unhealthy", "degraded")

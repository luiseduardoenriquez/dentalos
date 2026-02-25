from collections.abc import AsyncGenerator

import httpx
import pytest

from app.main import app


@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """httpx AsyncClient configured for FastAPI test server."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

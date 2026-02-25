"""Unit tests for SecurityHeadersMiddleware.

Uses the httpx async client with the FastAPI test transport (from conftest.py)
to verify that all required security headers are present on every response.
The /api/v1/health endpoint is used as a lightweight target — it does not
require authentication and is always present.
"""
import pytest


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    async def test_x_content_type_options_nosniff(self, async_client):
        response = await async_client.get("/api/v1/health")
        assert response.headers.get("x-content-type-options") == "nosniff"

    async def test_x_frame_options_deny(self, async_client):
        response = await async_client.get("/api/v1/health")
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_x_xss_protection_disabled(self, async_client):
        """Modern browsers rely on CSP, not X-XSS-Protection. Value must be 0."""
        response = await async_client.get("/api/v1/health")
        assert response.headers.get("x-xss-protection") == "0"

    async def test_referrer_policy(self, async_client):
        response = await async_client.get("/api/v1/health")
        assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    async def test_permissions_policy_restrictive(self, async_client):
        response = await async_client.get("/api/v1/health")
        policy = response.headers.get("permissions-policy", "")
        # Camera, microphone, geolocation, and payment must all be blocked
        assert "camera=()" in policy
        assert "microphone=()" in policy
        assert "geolocation=()" in policy
        assert "payment=()" in policy

    async def test_csp_default_src_self(self, async_client):
        response = await async_client.get("/api/v1/health")
        csp = response.headers.get("content-security-policy", "")
        assert "default-src 'self'" in csp

    async def test_csp_frame_ancestors_none(self, async_client):
        """Clickjacking protection: frame-ancestors 'none' prevents embedding."""
        response = await async_client.get("/api/v1/health")
        csp = response.headers.get("content-security-policy", "")
        assert "frame-ancestors 'none'" in csp

    async def test_csp_script_src_self_only(self, async_client):
        """Inline scripts must not be permitted."""
        response = await async_client.get("/api/v1/health")
        csp = response.headers.get("content-security-policy", "")
        assert "script-src 'self'" in csp
        assert "'unsafe-eval'" not in csp

    async def test_server_header_removed(self, async_client):
        """The server header must be stripped to avoid version fingerprinting."""
        response = await async_client.get("/api/v1/health")
        assert "server" not in response.headers

    async def test_security_headers_present_on_404(self, async_client):
        """Security headers must appear on error responses too, not just 200s."""
        response = await async_client.get("/api/v1/this-route-does-not-exist")
        # Header must be set regardless of status code
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"

    async def test_all_required_headers_present(self, async_client):
        """Single-pass smoke test — all six headers exist in one response."""
        response = await async_client.get("/api/v1/health")
        required_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
            "referrer-policy",
            "permissions-policy",
            "content-security-policy",
        ]
        missing = [h for h in required_headers if h not in response.headers]
        assert not missing, f"Missing security headers: {missing}"

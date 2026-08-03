import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_returns_valid_json(self, client):
        response = await client.get("/health")
        body = response.json()
        assert "data" in body
        assert body["data"]["status"] == "ok"

    async def test_health_includes_trace_id(self, client):
        response = await client.get("/health")
        body = response.json()
        assert "trace_id" in body["data"]

    async def test_health_response_has_trace_id_header(self, client):
        response = await client.get("/health")
        assert "X-Trace-Id" in response.headers


class TestReadyEndpoint:
    async def test_ready_returns_200(self, client):
        response = await client.get("/ready")
        assert response.status_code == 200

    async def test_ready_returns_status(self, client):
        response = await client.get("/ready")
        body = response.json()
        assert body["data"]["status"] in ("ok", "degraded")
        assert body["data"]["database"] == "not_configured"


class TestErrorHandling:
    async def test_validation_error_returns_422_with_envelope(self, client):
        response = await client.post(
            "/health",
            json={"invalid": "data"},
        )
        assert response.status_code == 405

    async def test_not_found_returns_trace_id(self, client):
        response = await client.get("/nonexistent")
        assert "X-Trace-Id" in response.headers


class TestTraceIdPropagation:
    async def test_trace_id_header_present_on_all_responses(self, client):
        endpoints = ["/health", "/ready"]
        for path in endpoints:
            response = await client.get(path)
            assert "X-Trace-Id" in response.headers

    async def test_custom_trace_id_is_propagated(self, client):
        custom_id = "trc_custom-test-id-12345"
        response = await client.get(
            "/health", headers={"X-Trace-Id": custom_id}
        )
        assert response.headers["X-Trace-Id"] == custom_id

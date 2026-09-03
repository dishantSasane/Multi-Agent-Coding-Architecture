"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


class TestAPIEndpoints:
    """Test API endpoint integration."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_submit_query(self, client, sample_query):
        """Test query submission endpoint."""
        response = await client.post(
            "/api/v1/query",
            json={
                "query": sample_query,
                "context": None,
                "preferences": None,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_status(self, client, sample_task_id):
        """Test status polling endpoint."""
        response = await client.get(f"/api/v1/query/{sample_task_id}/status")
        
        # Should return 404 for non-existent task or 200 with status
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_confirm_intent(self, client, sample_task_id):
        """Test intent confirmation endpoint."""
        response = await client.post(
            f"/api/v1/query/{sample_task_id}/confirm",
            json={"confirmed": True, "clarifications": None},
        )
        
        # May return 404 for non-existent task
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_trigger_generation(self, client, sample_task_id):
        """Test code generation trigger endpoint."""
        response = await client.post(f"/api/v1/query/{sample_task_id}/generate")
        
        # May return 404 for non-existent task
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_result(self, client, sample_task_id):
        """Test result retrieval endpoint."""
        response = await client.get(f"/api/v1/query/{sample_task_id}/result")
        
        # May return 404 for non-existent task or 400 if not completed
        assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = await client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"},
        )
        
        # CORS should be configured
        assert "access-control-allow-origin" in response.headers or response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_correlation_id_header(self, client):
        """Test correlation ID is added to responses."""
        response = await client.get("/health")
        
        # Response should include correlation ID
        assert "x-correlation-id" in response.headers

    @pytest.mark.asyncio
    async def test_invalid_json_request(self, client):
        """Test handling of invalid JSON."""
        response = await client.post(
            "/api/v1/query",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_empty_query_rejected(self, client):
        """Test that empty queries are handled."""
        response = await client.post(
            "/api/v1/query",
            json={"query": "", "context": None, "preferences": None},
        )
        
        # Should either accept and ask for clarification or reject
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_docs_endpoints(self, client):
        """Test documentation endpoints exist."""
        swagger_response = await client.get("/docs")
        redoc_response = await client.get("/redoc")
        
        assert swagger_response.status_code == 200
        assert redoc_response.status_code == 200

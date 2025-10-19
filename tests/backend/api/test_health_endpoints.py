"""Unit tests for Health and Status endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test suite for health check and status endpoints."""

    def test_root_endpoint(self):
        """Test GET /."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "service" in data

    def test_health_check(self):
        """Test GET /health."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_liveness_probe(self):
        """Test GET /live."""
        response = client.get("/live")
        assert response.status_code == 200

    def test_detailed_health_check(self):
        """Test GET /health/detailed."""
        response = client.get("/health/detailed")
        assert response.status_code == 200
        data = response.json()
        print(f"Response data: {data}")
        assert "status" in data
        # Should have component health checks
        assert any(key in data for key in ["cache", "database", "websocket", "components", "services"])

    def test_websocket_status(self):
        """Test GET /ws/status."""
        response = client.get("/ws/status")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data or "status" in data

    def test_websocket_audio_status(self):
        """Test GET /ws/status/audio."""
        response = client.get("/ws/status/audio")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or isinstance(data, dict)

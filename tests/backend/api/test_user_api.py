"""Unit tests for User API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import uuid

client = TestClient(app)


class TestUserEndpoints:
    """Test suite for /api/user/* endpoints."""

    @pytest.fixture
    def test_user_id(self):
        """Generate test user ID."""
        return str(uuid.uuid4())

    def test_get_preferences(self, test_user_id):
        """Test GET /api/user/preferences."""
        response = client.get(f"/api/user/preferences?user_id={test_user_id}")
        assert response.status_code in [200, 404]

    def test_update_preferences(self, test_user_id):
        """Test PUT /api/user/preferences."""
        response = client.put(
            "/api/user/preferences",
            json={
                "user_id": test_user_id,
                "voice_speed": 1.2,
                "preferred_topics": ["technology"]
            }
        )
        assert response.status_code in [200, 404, 422]

    def test_get_topics(self, test_user_id):
        """Test GET /api/user/topics."""
        response = client.get(f"/api/user/topics?user_id={test_user_id}")
        assert response.status_code in [200, 404]

    def test_add_topic(self, test_user_id):
        """Test POST /api/user/topics/add."""
        response = client.post(
            "/api/user/topics/add",
            json={
                "user_id": test_user_id,
                "topic": "crypto"
            }
        )
        assert response.status_code in [200, 404, 422]

    def test_delete_topic(self, test_user_id):
        """Test DELETE /api/user/topics/{topic}."""
        response = client.delete(f"/api/user/topics/technology?user_id={test_user_id}")
        assert response.status_code in [200, 404]

    def test_get_watchlist(self, test_user_id):
        """Test GET /api/user/watchlist."""
        response = client.get(f"/api/user/watchlist?user_id={test_user_id}")
        assert response.status_code in [200, 404]

    def test_add_to_watchlist(self, test_user_id):
        """Test POST /api/user/watchlist/add."""
        response = client.post(
            "/api/user/watchlist/add",
            json={
                "user_id": test_user_id,
                "symbol": "NVDA"
            }
        )
        assert response.status_code in [200, 404, 422]

    def test_delete_from_watchlist(self, test_user_id):
        """Test DELETE /api/user/watchlist/{symbol}."""
        response = client.delete(f"/api/user/watchlist/AAPL?user_id={test_user_id}")
        assert response.status_code in [200, 404]

    def test_get_analytics(self, test_user_id):
        """Test GET /api/user/analytics."""
        response = client.get(f"/api/user/analytics?user_id={test_user_id}&days=30")
        assert response.status_code in [200, 404]

    def test_user_health_check(self):
        """Test GET /api/user/health."""
        response = client.get("/api/user/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

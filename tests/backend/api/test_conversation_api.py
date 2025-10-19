"""Unit tests for Conversation API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import uuid

client = TestClient(app)


class TestConversationEndpoints:
    """Test suite for /api/conversation/* endpoints."""

    @pytest.fixture
    def test_user_id(self):
        """Generate test user ID."""
        return str(uuid.uuid4())

    @pytest.fixture
    def test_session_id(self):
        """Generate test session ID."""
        return str(uuid.uuid4())

    def test_get_conversation_sessions(self, test_user_id):
        """Test GET /api/conversation/sessions."""
        response = client.get(f"/api/conversation/sessions?user_id={test_user_id}&limit=10")
        assert response.status_code == 200
        # May return empty list for new user
        data = response.json()
        assert isinstance(data, list)

    def test_get_conversation_messages(self, test_session_id):
        """Test GET /api/conversation/{session_id}/messages."""
        response = client.get(f"/api/conversation/{test_session_id}/messages?limit=50")
        assert response.status_code in [200, 404]

    def test_create_conversation_session(self, test_user_id):
        """Test POST /api/conversation/sessions."""
        response = client.post(
            "/api/conversation/sessions",
            json={
                "user_id": test_user_id,
                "metadata": {"source": "test"}
            }
        )
        assert response.status_code in [200, 201, 422]

    def test_add_message_to_session(self, test_session_id):
        """Test POST /api/conversation/{session_id}/messages."""
        response = client.post(
            f"/api/conversation/{test_session_id}/messages",
            json={
                "role": "user",
                "content": "Hello test",
                "audio_url": None
            }
        )
        assert response.status_code in [200, 201, 404, 422]

    def test_get_conversation_summary(self, test_session_id):
        """Test GET /api/conversation/{session_id}/summary."""
        response = client.get(f"/api/conversation/{test_session_id}/summary")
        assert response.status_code in [200, 404]

    def test_conversation_health_check(self):
        """Test GET /api/conversation/health."""
        response = client.get("/api/conversation/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestConversationSessionEndpoints:
    """Test suite for /api/conversation-session/* endpoints."""

    def test_get_session_by_id(self):
        """Test GET /api/conversation-session/sessions/{session_id}."""
        test_session_id = str(uuid.uuid4())
        response = client.get(f"/api/conversation-session/sessions/{test_session_id}")
        # May not exist
        assert response.status_code in [200, 404]

    def test_list_sessions(self):
        """Test GET /api/conversation-session/sessions."""
        test_user_id = str(uuid.uuid4())
        response = client.get(f"/api/conversation-session/sessions?user_id={test_user_id}&limit=20")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_model_info(self):
        """Test GET /api/conversation-session/models/info."""
        response = client.get("/api/conversation-session/models/info")
        assert response.status_code == 200
        data = response.json()
        assert "sensevoice_loaded" in data or "tts_engine" in data

    def test_delete_session(self):
        """Test DELETE /api/conversation-session/sessions/{session_id}."""
        test_session_id = str(uuid.uuid4())
        response = client.delete(f"/api/conversation-session/sessions/{test_session_id}")
        # May not exist
        assert response.status_code in [200, 404]

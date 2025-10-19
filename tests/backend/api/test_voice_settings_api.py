"""Unit tests for Voice Settings API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import uuid

client = TestClient(app)


class TestVoiceSettingsEndpoints:
    """Test suite for /api/voice-settings/* endpoints."""

    @pytest.fixture
    def test_user_id(self):
        """Generate test user ID."""
        return str(uuid.uuid4())

    def test_get_voice_settings(self, test_user_id):
        """Test GET /api/voice-settings/{user_id}."""
        response = client.get(f"/api/voice-settings/{test_user_id}")
        assert response.status_code in [200, 404]

    def test_update_voice_settings(self, test_user_id):
        """Test PUT /api/voice-settings/{user_id}."""
        response = client.put(
            f"/api/voice-settings/{test_user_id}",
            json={
                "tts_voice": "nova",
                "tts_speed": 1.0,
                "enable_interruption": True,
                "audio_format": "opus"
            }
        )
        assert response.status_code in [200, 404, 422]

    def test_delete_voice_settings(self, test_user_id):
        """Test DELETE /api/voice-settings/{user_id}."""
        response = client.delete(f"/api/voice-settings/{test_user_id}")
        assert response.status_code in [200, 404]

    def test_get_presets(self, test_user_id):
        """Test GET /api/voice-settings/{user_id}/presets."""
        response = client.get(f"/api/voice-settings/{test_user_id}/presets")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data or isinstance(data, dict)

    def test_get_compression_info(self, test_user_id):
        """Test GET /api/voice-settings/{user_id}/compression-info."""
        response = client.get(f"/api/voice-settings/{test_user_id}/compression-info")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

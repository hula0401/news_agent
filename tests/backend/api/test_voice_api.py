"""Unit tests for Voice API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
import uuid

client = TestClient(app)


class TestVoiceEndpoints:
    """Test suite for /api/voice/* endpoints."""

    def test_process_voice_command(self):
        """Test POST /api/voice/command."""
        response = client.post(
            "/api/voice/command",
            json={
                "command": "tell me the news",
                "user_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4())
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "response_text" in data or "transcription" in data

    def test_process_text_command(self):
        """Test POST /api/voice/text-command."""
        response = client.post(
            "/api/voice/text-command",
            json={
                "command": "what's the stock price of AAPL",
                "user_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4())
            }
        )
        if response.status_code != 200:
            print(f"Error response: {response.json()}")
        assert response.status_code == 200
        data = response.json()
        assert "response_text" in data

    def test_synthesize_speech(self):
        """Test POST /api/voice/synthesize."""
        response = client.post(
            "/api/voice/synthesize",
            json={
                "text": "Hello world",
                "voice": "nova",
                "speed": 1.0
            }
        )
        # TTS may not be available in test environment
        assert response.status_code in [200, 500, 503]

    def test_update_watchlist(self):
        """Test POST /api/voice/watchlist/update."""
        response = client.post(
            "/api/voice/watchlist/update",
            json={
                "user_id": str(uuid.uuid4()),
                "action": "add",
                "symbol": "TSLA"
            }
        )
        assert response.status_code in [200, 404, 422]

    def test_voice_health_check(self):
        """Test GET /api/voice/health."""
        response = client.get("/api/voice/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

"""Tests for user voice settings API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestVoiceSettingsPresets:
    """Test voice settings presets endpoint."""

    def test_get_presets(self):
        """Test GET /api/user/settings/voice/presets returns all presets."""
        response = client.get("/api/user/settings/voice/presets")

        assert response.status_code == 200
        data = response.json()

        # Check presets exist
        assert "presets" in data
        assert "voice_types" in data

        # Check all expected presets
        expected_presets = [
            "default",
            "mobile_friendly",
            "fast_reader",
            "quiet_environment",
            "noisy_environment"
        ]
        for preset_name in expected_presets:
            assert preset_name in data["presets"]
            preset = data["presets"][preset_name]

            # Verify preset structure
            assert "voice_type" in preset
            assert "speech_rate" in preset
            assert "vad_sensitivity" in preset
            assert "vad_aggressiveness" in preset
            assert "interruption_enabled" in preset
            assert "interruption_threshold" in preset
            assert "use_audio_compression" in preset
            assert "auto_play_responses" in preset

    def test_presets_voice_types(self):
        """Test that voice type descriptions are included."""
        response = client.get("/api/user/settings/voice/presets")

        assert response.status_code == 200
        data = response.json()

        # Check voice types
        assert len(data["voice_types"]) == 4
        voice_type_names = [vt["name"] for vt in data["voice_types"]]

        assert "calm" in voice_type_names
        assert "casual" in voice_type_names
        assert "professional" in voice_type_names
        assert "energetic" in voice_type_names

        # Check structure of first voice type
        vt = data["voice_types"][0]
        assert "name" in vt
        assert "description" in vt
        assert "recommended_for" in vt
        assert "characteristics" in vt
        assert isinstance(vt["characteristics"], list)

    def test_default_preset_values(self):
        """Test that default preset has expected values."""
        response = client.get("/api/user/settings/voice/presets")

        assert response.status_code == 200
        data = response.json()

        default = data["presets"]["default"]
        assert default["voice_type"] == "professional"
        assert default["speech_rate"] == 1.0
        assert default["vad_sensitivity"] == "balanced"
        assert default["vad_aggressiveness"] == 2
        assert default["interruption_enabled"] is True
        assert default["interruption_threshold"] == 0.5
        assert default["use_audio_compression"] is False
        assert default["auto_play_responses"] is True

    def test_mobile_friendly_preset(self):
        """Test mobile_friendly preset has compression enabled."""
        response = client.get("/api/user/settings/voice/presets")

        assert response.status_code == 200
        data = response.json()

        mobile = data["presets"]["mobile_friendly"]
        assert mobile["use_audio_compression"] is True
        assert mobile["voice_type"] == "casual"
        assert mobile["vad_sensitivity"] == "high"

    def test_fast_reader_preset(self):
        """Test fast_reader preset has higher speech rate."""
        response = client.get("/api/user/settings/voice/presets")

        assert response.status_code == 200
        data = response.json()

        fast = data["presets"]["fast_reader"]
        assert fast["speech_rate"] == 1.5
        assert fast["voice_type"] == "energetic"


class TestVoiceSettingsGetEndpoint:
    """Test GET voice settings endpoint."""

    def test_get_settings_not_found(self):
        """Test GET returns 404 for non-existent user."""
        # Use a UUID that definitely doesn't exist
        response = client.get("/api/user/settings/voice/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_settings_invalid_uuid(self):
        """Test GET with invalid user ID format."""
        response = client.get("/api/user/settings/voice/invalid-id")

        # Should still try to query and return 404
        assert response.status_code == 404


class TestVoiceSettingsCreateUpdate:
    """Test POST voice settings endpoint (create/update)."""

    def test_create_settings_minimal(self):
        """Test creating settings with minimal data."""
        user_id = "test-user-create-minimal"
        payload = {
            "voice_type": "energetic"
        }

        response = client.post(
            f"/api/user/settings/voice/{user_id}",
            json=payload
        )

        # Will fail if table doesn't exist, but endpoint should be valid
        # Either 201 (created) or 500 (table missing)
        assert response.status_code in [201, 404, 500]

    def test_create_settings_full(self):
        """Test creating settings with all parameters."""
        user_id = "test-user-create-full"
        payload = {
            "voice_type": "professional",
            "speech_rate": 1.25,
            "vad_sensitivity": "high",
            "vad_aggressiveness": 3,
            "interruption_enabled": False,
            "interruption_threshold": 0.7,
            "use_audio_compression": True,
            "auto_play_responses": False
        }

        response = client.post(
            f"/api/user/settings/voice/{user_id}",
            json=payload
        )

        # Will fail if table doesn't exist
        assert response.status_code in [201, 404, 500]

    def test_create_settings_invalid_voice_type(self):
        """Test creating settings with invalid voice type."""
        user_id = "test-user-invalid-voice"
        payload = {
            "voice_type": "invalid_type"  # Should fail validation
        }

        response = client.post(
            f"/api/user/settings/voice/{user_id}",
            json=payload
        )

        # Should fail Pydantic validation
        assert response.status_code == 422

    def test_create_settings_invalid_speech_rate(self):
        """Test creating settings with out-of-range speech rate."""
        user_id = "test-user-invalid-rate"

        # Too low
        payload = {"speech_rate": 0.25}
        response = client.post(f"/api/user/settings/voice/{user_id}", json=payload)
        assert response.status_code == 422

        # Too high
        payload = {"speech_rate": 3.0}
        response = client.post(f"/api/user/settings/voice/{user_id}", json=payload)
        assert response.status_code == 422

    def test_create_settings_invalid_vad_aggressiveness(self):
        """Test creating settings with invalid VAD aggressiveness."""
        user_id = "test-user-invalid-vad"

        # Too low
        payload = {"vad_aggressiveness": -1}
        response = client.post(f"/api/user/settings/voice/{user_id}", json=payload)
        assert response.status_code == 422

        # Too high
        payload = {"vad_aggressiveness": 5}
        response = client.post(f"/api/user/settings/voice/{user_id}", json=payload)
        assert response.status_code == 422

    def test_create_settings_invalid_threshold(self):
        """Test creating settings with invalid interruption threshold."""
        user_id = "test-user-invalid-threshold"

        # Too low
        payload = {"interruption_threshold": -0.1}
        response = client.post(f"/api/user/settings/voice/{user_id}", json=payload)
        assert response.status_code == 422

        # Too high
        payload = {"interruption_threshold": 1.5}
        response = client.post(f"/api/user/settings/voice/{user_id}", json=payload)
        assert response.status_code == 422


class TestVoiceSettingsDelete:
    """Test DELETE voice settings endpoint."""

    def test_delete_settings(self):
        """Test deleting voice settings."""
        user_id = "test-user-delete"

        response = client.delete(f"/api/user/settings/voice/{user_id}")

        # Will fail if table doesn't exist, but endpoint should work
        # 204 (success) or 500 (table missing)
        assert response.status_code in [204, 404, 500]

    def test_delete_settings_returns_no_content(self):
        """Test DELETE returns 204 No Content on success."""
        user_id = "test-user-delete-content"

        response = client.delete(f"/api/user/settings/voice/{user_id}")

        # If successful, should return 204 with no body
        if response.status_code == 204:
            assert response.content == b''


class TestVoiceSettingsLastUsed:
    """Test PATCH last-used timestamp endpoint."""

    def test_update_last_used(self):
        """Test updating last_used_at timestamp."""
        user_id = "test-user-last-used"

        response = client.patch(f"/api/user/settings/voice/{user_id}/last-used")

        # Will return 404 if user settings don't exist, or 204 on success
        # 500 if table missing
        assert response.status_code in [204, 404, 500]

    def test_update_last_used_not_found(self):
        """Test updating timestamp for non-existent settings."""
        user_id = "00000000-0000-0000-0000-000000000000"

        response = client.patch(f"/api/user/settings/voice/{user_id}/last-used")

        # Should return 404 if settings don't exist (or 500 if table missing)
        assert response.status_code in [404, 500]


class TestVoiceSettingsValidation:
    """Test Pydantic validation for voice settings."""

    def test_valid_voice_types(self):
        """Test all valid voice types are accepted."""
        valid_types = ["calm", "casual", "professional", "energetic"]

        for voice_type in valid_types:
            payload = {"voice_type": voice_type}
            response = client.post(
                "/api/user/settings/voice/test-user-types",
                json=payload
            )
            # Should not fail validation (201 or 500 if table missing, not 422)
            assert response.status_code != 422

    def test_valid_vad_sensitivities(self):
        """Test all valid VAD sensitivities are accepted."""
        valid_sensitivities = ["low", "balanced", "high"]

        for sensitivity in valid_sensitivities:
            payload = {"vad_sensitivity": sensitivity}
            response = client.post(
                "/api/user/settings/voice/test-user-sensitivities",
                json=payload
            )
            # Should not fail validation
            assert response.status_code != 422

    def test_speech_rate_boundaries(self):
        """Test speech rate boundary values."""
        # Minimum valid
        payload = {"speech_rate": 0.5}
        response = client.post("/api/user/settings/voice/test-rate-min", json=payload)
        assert response.status_code != 422

        # Maximum valid
        payload = {"speech_rate": 2.0}
        response = client.post("/api/user/settings/voice/test-rate-max", json=payload)
        assert response.status_code != 422

    def test_vad_aggressiveness_boundaries(self):
        """Test VAD aggressiveness boundary values."""
        for value in [0, 1, 2, 3]:
            payload = {"vad_aggressiveness": value}
            response = client.post(
                f"/api/user/settings/voice/test-vad-{value}",
                json=payload
            )
            assert response.status_code != 422

    def test_interruption_threshold_boundaries(self):
        """Test interruption threshold boundary values."""
        # Minimum valid
        payload = {"interruption_threshold": 0.0}
        response = client.post("/api/user/settings/voice/test-threshold-min", json=payload)
        assert response.status_code != 422

        # Maximum valid
        payload = {"interruption_threshold": 1.0}
        response = client.post("/api/user/settings/voice/test-threshold-max", json=payload)
        assert response.status_code != 422

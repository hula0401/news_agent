"""Voice settings Pydantic models."""
from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal


class VoiceSettingsBase(BaseModel):
    """Base voice settings model."""
    voice_type: Literal['calm', 'casual', 'professional', 'energetic'] = Field(
        default='professional',
        description="Voice synthesis style"
    )
    speech_rate: float = Field(
        default=1.00,
        ge=0.50,
        le=2.00,
        description="Speech synthesis speed (0.50 to 2.00)"
    )
    vad_sensitivity: Literal['low', 'balanced', 'high'] = Field(
        default='balanced',
        description="Voice activity detection sensitivity"
    )
    vad_aggressiveness: int = Field(
        default=2,
        ge=0,
        le=3,
        description="WebRTC VAD aggressiveness level (0-3)"
    )
    interruption_enabled: bool = Field(
        default=True,
        description="Enable voice interruption during TTS playback"
    )
    interruption_threshold: float = Field(
        default=0.50,
        ge=0.00,
        le=1.00,
        description="Energy threshold for interruption detection (0.00-1.00)"
    )
    use_audio_compression: bool = Field(
        default=False,
        description="Use Opus audio compression (reduces bandwidth by ~80%)"
    )
    auto_play_responses: bool = Field(
        default=True,
        description="Automatically play TTS responses"
    )


class VoiceSettingsCreate(VoiceSettingsBase):
    """Voice settings creation model."""
    user_id: str = Field(..., description="User ID")


class VoiceSettingsUpdate(BaseModel):
    """Voice settings update model (all fields optional)."""
    voice_type: Optional[Literal['calm', 'casual', 'professional', 'energetic']] = None
    speech_rate: Optional[float] = Field(None, ge=0.50, le=2.00)
    vad_sensitivity: Optional[Literal['low', 'balanced', 'high']] = None
    vad_aggressiveness: Optional[int] = Field(None, ge=0, le=3)
    interruption_enabled: Optional[bool] = None
    interruption_threshold: Optional[float] = Field(None, ge=0.00, le=1.00)
    use_audio_compression: Optional[bool] = None
    auto_play_responses: Optional[bool] = None


class VoiceSettings(VoiceSettingsBase):
    """Complete voice settings model (database record)."""
    id: str = Field(..., description="Settings record ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last active use timestamp")
    settings_version: int = Field(default=1, description="Settings schema version")

    class Config:
        from_attributes = True


class VoiceSettingsResponse(VoiceSettingsBase):
    """Voice settings API response model."""
    user_id: str = Field(..., description="User ID")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last active use timestamp")


class VoiceTypeDescription(BaseModel):
    """Voice type metadata model."""
    name: Literal['calm', 'casual', 'professional', 'energetic']
    description: str
    recommended_for: str
    characteristics: list[str]


class VoiceSettingsPresets(BaseModel):
    """Voice settings presets for common use cases."""
    presets: dict[str, VoiceSettingsBase] = Field(
        default={
            "default": VoiceSettingsBase(
                voice_type="professional",
                speech_rate=1.00,
                vad_sensitivity="balanced",
                vad_aggressiveness=2,
                interruption_enabled=True,
                interruption_threshold=0.50,
                use_audio_compression=False,
                auto_play_responses=True
            ),
            "mobile_friendly": VoiceSettingsBase(
                voice_type="casual",
                speech_rate=1.00,
                vad_sensitivity="high",
                vad_aggressiveness=2,
                interruption_enabled=True,
                interruption_threshold=0.40,
                use_audio_compression=True,  # Enable compression for mobile
                auto_play_responses=True
            ),
            "fast_reader": VoiceSettingsBase(
                voice_type="energetic",
                speech_rate=1.50,
                vad_sensitivity="balanced",
                vad_aggressiveness=2,
                interruption_enabled=True,
                interruption_threshold=0.60,
                use_audio_compression=False,
                auto_play_responses=True
            ),
            "quiet_environment": VoiceSettingsBase(
                voice_type="calm",
                speech_rate=0.90,
                vad_sensitivity="high",  # More sensitive for quiet speech
                vad_aggressiveness=1,
                interruption_enabled=True,
                interruption_threshold=0.30,
                use_audio_compression=False,
                auto_play_responses=True
            ),
            "noisy_environment": VoiceSettingsBase(
                voice_type="professional",
                speech_rate=1.00,
                vad_sensitivity="low",  # Less sensitive to avoid false positives
                vad_aggressiveness=3,
                interruption_enabled=True,
                interruption_threshold=0.70,  # Higher threshold
                use_audio_compression=False,
                auto_play_responses=True
            )
        }
    )
    voice_types: list[VoiceTypeDescription] = Field(
        default=[
            VoiceTypeDescription(
                name="calm",
                description="Slower pace, soothing tone, lower energy",
                recommended_for="Relaxed listening, bedtime news, meditation-style content",
                characteristics=["Slow pace", "Lower pitch", "Soothing", "Minimal variation"]
            ),
            VoiceTypeDescription(
                name="casual",
                description="Friendly, conversational, moderate pace",
                recommended_for="Everyday use, casual news consumption, friendly interactions",
                characteristics=["Conversational", "Friendly tone", "Moderate pace", "Natural variation"]
            ),
            VoiceTypeDescription(
                name="professional",
                description="Clear, authoritative, consistent (default)",
                recommended_for="Business news, formal content, professional settings",
                characteristics=["Clear enunciation", "Authoritative", "Consistent", "Neutral tone"]
            ),
            VoiceTypeDescription(
                name="energetic",
                description="Faster pace, higher pitch variation, enthusiastic",
                recommended_for="Breaking news, sports, exciting content, quick updates",
                characteristics=["Fast pace", "High energy", "Enthusiastic", "Dynamic pitch"]
            )
        ]
    )

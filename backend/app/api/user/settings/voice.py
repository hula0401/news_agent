"""Voice settings API endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import asyncio
from ....models.voice_settings import (
    VoiceSettings,
    VoiceSettingsCreate,
    VoiceSettingsUpdate,
    VoiceSettingsResponse,
    VoiceSettingsPresets
)
from ....database import get_database

router = APIRouter(prefix="/api/user/settings/voice", tags=["user-settings", "voice"])


@router.get("/presets", response_model=VoiceSettingsPresets)
async def get_voice_settings_presets():
    """
    Get voice settings presets and voice type descriptions.

    Returns predefined settings configurations for common use cases:
    - default: Standard professional settings
    - mobile_friendly: Optimized for mobile with compression
    - fast_reader: Higher speech rate for experienced users
    - quiet_environment: High sensitivity for quiet speech
    - noisy_environment: Low sensitivity to avoid false positives
    """
    return VoiceSettingsPresets()


@router.get("/{user_id}", response_model=VoiceSettingsResponse)
async def get_voice_settings(
    user_id: str,
    db=Depends(get_database)
):
    """
    Get voice settings for a specific user.

    Returns 404 if user has no voice settings configured.
    Returns default settings if user exists but hasn't customized voice settings.
    """
    try:
        # Query database for voice settings (wrap sync client in async)
        def _fetch():
            return db.client.table("user_voice_settings")\
                .select("*")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()

        result = await asyncio.to_thread(_fetch)

        if not result.data:
            raise HTTPException(
                status_code=404,
                detail=f"Voice settings not found for user {user_id}"
            )

        settings = result.data

        # Convert to response model
        return VoiceSettingsResponse(
            user_id=settings["user_id"],
            voice_type=settings["voice_type"],
            speech_rate=float(settings["speech_rate"]),
            vad_sensitivity=settings["vad_sensitivity"],
            vad_aggressiveness=settings["vad_aggressiveness"],
            interruption_enabled=settings["interruption_enabled"],
            interruption_threshold=float(settings["interruption_threshold"]),
            use_audio_compression=settings["use_audio_compression"],
            auto_play_responses=settings["auto_play_responses"],
            updated_at=settings["updated_at"],
            last_used_at=settings.get("last_used_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving voice settings: {str(e)}"
        )


@router.post("/{user_id}", response_model=VoiceSettingsResponse, status_code=201)
async def create_or_update_voice_settings(
    user_id: str,
    settings: VoiceSettingsUpdate,
    db=Depends(get_database)
):
    """
    Create or update voice settings for a user (UPSERT operation).

    If user already has settings, updates only the provided fields.
    If user has no settings, creates new record with provided values + defaults.
    """
    try:
        # Prepare settings data
        settings_data = {
            "user_id": user_id,
            **settings.model_dump(exclude_unset=True, exclude_none=True)
        }

        # Upsert to database (insert or update if user_id exists)
        def _upsert():
            return db.client.table("user_voice_settings")\
                .upsert(settings_data, on_conflict="user_id")\
                .select("*")\
                .execute()

        result = await asyncio.to_thread(_upsert)

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=500,
                detail="Failed to create/update voice settings"
            )

        created_settings = result.data[0]

        # Return response
        return VoiceSettingsResponse(
            user_id=created_settings["user_id"],
            voice_type=created_settings["voice_type"],
            speech_rate=float(created_settings["speech_rate"]),
            vad_sensitivity=created_settings["vad_sensitivity"],
            vad_aggressiveness=created_settings["vad_aggressiveness"],
            interruption_enabled=created_settings["interruption_enabled"],
            interruption_threshold=float(created_settings["interruption_threshold"]),
            use_audio_compression=created_settings["use_audio_compression"],
            auto_play_responses=created_settings["auto_play_responses"],
            updated_at=created_settings["updated_at"],
            last_used_at=created_settings.get("last_used_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating/updating voice settings: {str(e)}"
        )


@router.delete("/{user_id}", status_code=204)
async def delete_voice_settings(
    user_id: str,
    db=Depends(get_database)
):
    """
    Delete voice settings for a user (reset to defaults).

    User will get default settings on next access.
    Returns 204 No Content on success.
    """
    try:
        def _delete():
            return db.client.table("user_voice_settings")\
                .delete()\
                .eq("user_id", user_id)\
                .execute()

        result = await asyncio.to_thread(_delete)

        # Supabase delete doesn't error if no rows match, so we're good
        return None

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting voice settings: {str(e)}"
        )


@router.patch("/{user_id}/last-used", status_code=204)
async def update_last_used(
    user_id: str,
    db=Depends(get_database)
):
    """
    Update last_used_at timestamp for voice settings.

    Called when user starts a voice session to track active usage.
    Returns 204 No Content on success.
    """
    try:
        from datetime import datetime

        def _update():
            return db.client.table("user_voice_settings")\
                .update({"last_used_at": datetime.utcnow().isoformat()})\
                .eq("user_id", user_id)\
                .execute()

        result = await asyncio.to_thread(_update)

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Voice settings not found for user {user_id}"
            )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating last used timestamp: {str(e)}"
        )

-- User Voice Settings Table
-- Stores personalized voice interaction settings for each user
-- Created: 2025-10-19

CREATE TABLE IF NOT EXISTS user_voice_settings (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- User Reference
    user_id UUID NOT NULL UNIQUE,
    -- CONSTRAINT: Each user can have only one voice settings record
    -- Use UPSERT pattern for updates

    -- Voice Type Settings
    voice_type TEXT NOT NULL DEFAULT 'professional',
    -- OPTIONS: 'calm', 'casual', 'professional', 'energetic'
    -- DESCRIPTION: Tone and style of voice synthesis
    --   - calm: Slower pace, soothing tone, lower energy
    --   - casual: Friendly, conversational, moderate pace
    --   - professional: Clear, authoritative, consistent (default)
    --   - energetic: Faster pace, higher pitch variation, enthusiastic
    CONSTRAINT check_voice_type CHECK (voice_type IN ('calm', 'casual', 'professional', 'energetic')),

    -- Speech Rate
    speech_rate DECIMAL(3, 2) NOT NULL DEFAULT 1.00,
    -- RANGE: 0.50 to 2.00
    -- DESCRIPTION: Speed of speech synthesis
    --   - 0.50: Very slow (for detailed comprehension)
    --   - 0.75: Slow (for language learners)
    --   - 1.00: Normal speed (default, most natural)
    --   - 1.25: Slightly faster (for experienced users)
    --   - 1.50: Fast (for quick information consumption)
    --   - 2.00: Very fast (maximum speed)
    CONSTRAINT check_speech_rate CHECK (speech_rate BETWEEN 0.50 AND 2.00),

    -- VAD (Voice Activity Detection) Sensitivity
    vad_sensitivity TEXT NOT NULL DEFAULT 'balanced',
    -- OPTIONS: 'low', 'balanced', 'high'
    -- DESCRIPTION: Sensitivity of voice activity detection for interruptions
    --   - low: Higher threshold, requires clearer speech (fewer false positives, may miss soft speech)
    --   - balanced: Moderate threshold, good for most environments (default)
    --   - high: Lower threshold, more responsive (better for quiet speech, more false positives)
    CONSTRAINT check_vad_sensitivity CHECK (vad_sensitivity IN ('low', 'balanced', 'high')),

    -- VAD Aggressiveness (WebRTC VAD parameter)
    vad_aggressiveness INTEGER NOT NULL DEFAULT 2,
    -- RANGE: 0 to 3
    -- DESCRIPTION: WebRTC VAD aggressiveness level
    --   - 0: Least aggressive, more permissive (detects more as speech)
    --   - 1: Low aggressiveness
    --   - 2: Moderate aggressiveness (default)
    --   - 3: Most aggressive (stricter filtering, reduces false positives)
    CONSTRAINT check_vad_aggressiveness CHECK (vad_aggressiveness BETWEEN 0 AND 3),

    -- Interruption Settings
    interruption_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    -- DESCRIPTION: Enable/disable voice interruption during TTS playback

    interruption_threshold DECIMAL(3, 2) NOT NULL DEFAULT 0.50,
    -- RANGE: 0.00 to 1.00
    -- DESCRIPTION: Energy threshold for interruption detection
    --   - 0.00 to 0.30: Very sensitive (any sound can interrupt)
    --   - 0.31 to 0.50: Balanced (default, normal speech)
    --   - 0.51 to 0.70: Less sensitive (requires clear speech)
    --   - 0.71 to 1.00: Very strict (requires loud, clear speech)
    CONSTRAINT check_interruption_threshold CHECK (interruption_threshold BETWEEN 0.00 AND 1.00),

    -- Audio Compression
    use_audio_compression BOOLEAN NOT NULL DEFAULT FALSE,
    -- DESCRIPTION: Enable Opus audio compression (reduces bandwidth by ~80%)
    --   - true: Use Opus compression (18KB per 3s, recommended for mobile)
    --   - false: Use WAV format (94KB per 3s, better quality for desktop)

    -- Auto-play Settings
    auto_play_responses BOOLEAN NOT NULL DEFAULT TRUE,
    -- DESCRIPTION: Automatically play TTS responses without user confirmation

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Metadata
    last_used_at TIMESTAMPTZ,
    -- DESCRIPTION: Last time these settings were actively used in a voice session

    settings_version INTEGER NOT NULL DEFAULT 1
    -- DESCRIPTION: Version number for settings schema evolution
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_voice_settings_user_id ON user_voice_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_voice_settings_updated_at ON user_voice_settings(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_voice_settings_last_used ON user_voice_settings(last_used_at DESC) WHERE last_used_at IS NOT NULL;

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_user_voice_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_voice_settings_updated_at
    BEFORE UPDATE ON user_voice_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_user_voice_settings_updated_at();

-- Comments for documentation
COMMENT ON TABLE user_voice_settings IS 'Stores personalized voice interaction settings for each user including voice type, speech rate, VAD sensitivity, and interruption preferences';
COMMENT ON COLUMN user_voice_settings.user_id IS 'Unique user identifier - one settings record per user';
COMMENT ON COLUMN user_voice_settings.voice_type IS 'Voice synthesis style: calm, casual, professional (default), or energetic';
COMMENT ON COLUMN user_voice_settings.speech_rate IS 'Speech synthesis speed (0.50 to 2.00, default 1.00)';
COMMENT ON COLUMN user_voice_settings.vad_sensitivity IS 'Voice activity detection sensitivity: low, balanced (default), or high';
COMMENT ON COLUMN user_voice_settings.vad_aggressiveness IS 'WebRTC VAD aggressiveness level (0-3, default 2)';
COMMENT ON COLUMN user_voice_settings.interruption_enabled IS 'Allow voice interruption during TTS playback';
COMMENT ON COLUMN user_voice_settings.interruption_threshold IS 'Energy threshold for detecting interruptions (0.00-1.00, default 0.50)';
COMMENT ON COLUMN user_voice_settings.use_audio_compression IS 'Use Opus compression to reduce bandwidth (recommended for mobile)';
COMMENT ON COLUMN user_voice_settings.auto_play_responses IS 'Automatically play TTS responses without confirmation';
COMMENT ON COLUMN user_voice_settings.last_used_at IS 'Timestamp of last active use in a voice session';
COMMENT ON COLUMN user_voice_settings.settings_version IS 'Schema version for future migrations';

-- Sample data (for testing)
-- INSERT INTO user_voice_settings (user_id, voice_type, speech_rate, vad_sensitivity)
-- VALUES
--     ('03f6b167-0d4d-4983-a380-54b8eb42f830', 'professional', 1.00, 'balanced'),
--     ('550e8400-e29b-41d4-a716-446655440000', 'energetic', 1.25, 'high');

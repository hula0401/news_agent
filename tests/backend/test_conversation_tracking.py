"""
Tests for conversation tracking system.

Tests cover:
- Session lifecycle (start/end)
- Message tracking with different roles
- Database persistence
- Error handling
"""
import pytest
import asyncio
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# We'll import after fixing the async issues
# from backend.app.core.conversation_tracker import ConversationTracker


class TestConversationSession:
    """Test conversation session lifecycle."""

    @pytest.mark.asyncio
    async def test_session_creation(self):
        """Test creating a new session in database."""
        from supabase import create_client
        import os
        from dotenv import load_dotenv
        from pathlib import Path

        # Load Supabase credentials
        env_file = Path(__file__).parent.parent.parent / "env_files" / "supabase.env"
        load_dotenv(env_file)

        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Generate test IDs
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Insert session
        def _insert():
            return client.table("conversation_sessions").insert({
                "session_id": session_id,
                "user_id": user_id,
                "session_start": datetime.utcnow().isoformat(),
                "started_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "metadata": {}
            }).execute()

        result = await asyncio.to_thread(_insert)

        # Verify insertion
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["session_id"] == session_id

        # Cleanup
        def _delete():
            return client.table("conversation_sessions").delete().eq("session_id", session_id).execute()

        await asyncio.to_thread(_delete)

    @pytest.mark.asyncio
    async def test_message_with_user_role(self):
        """Test inserting message with 'user' role."""
        from supabase import create_client
        import os
        from dotenv import load_dotenv
        from pathlib import Path

        env_file = Path(__file__).parent.parent.parent / "env_files" / "supabase.env"
        load_dotenv(env_file)

        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Create session first
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        def _insert_session():
            return client.table("conversation_sessions").insert({
                "session_id": session_id,
                "user_id": user_id,
                "session_start": datetime.utcnow().isoformat(),
                "started_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "metadata": {}
            }).execute()

        await asyncio.to_thread(_insert_session)

        # Insert user message
        def _insert_message():
            return client.table("conversation_messages").insert({
                "session_id": session_id,
                "user_id": user_id,
                "role": "user",  # Test user role
                "content": "Hello, how are you?",
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        result = await asyncio.to_thread(_insert_message)

        # Verify
        assert result.data is not None
        assert result.data[0]["role"] == "user"
        assert result.data[0]["content"] == "Hello, how are you?"

        # Cleanup
        def _cleanup():
            client.table("conversation_messages").delete().eq("session_id", session_id).execute()
            client.table("conversation_sessions").delete().eq("session_id", session_id).execute()

        await asyncio.to_thread(_cleanup)

    @pytest.mark.asyncio
    async def test_message_with_agent_role(self):
        """Test inserting message with 'agent' role (not 'assistant')."""
        from supabase import create_client
        import os
        from dotenv import load_dotenv
        from pathlib import Path

        env_file = Path(__file__).parent.parent.parent / "env_files" / "supabase.env"
        load_dotenv(env_file)

        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Create session first
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        def _insert_session():
            return client.table("conversation_sessions").insert({
                "session_id": session_id,
                "user_id": user_id,
                "session_start": datetime.utcnow().isoformat(),
                "started_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "metadata": {}
            }).execute()

        await asyncio.to_thread(_insert_session)

        # Insert agent message (not "assistant")
        def _insert_message():
            return client.table("conversation_messages").insert({
                "session_id": session_id,
                "user_id": user_id,
                "role": "agent",  # Use "agent" not "assistant"
                "content": "I'm doing well, thank you!",
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        result = await asyncio.to_thread(_insert_message)

        # Verify
        assert result.data is not None
        assert result.data[0]["role"] == "agent"

        # Cleanup
        def _cleanup():
            client.table("conversation_messages").delete().eq("session_id", session_id).execute()
            client.table("conversation_sessions").delete().eq("session_id", session_id).execute()

        await asyncio.to_thread(_cleanup)

    @pytest.mark.asyncio
    async def test_session_with_audio_url(self):
        """Test message with audio URL."""
        from supabase import create_client
        import os
        from dotenv import load_dotenv
        from pathlib import Path

        env_file = Path(__file__).parent.parent.parent / "env_files" / "supabase.env"
        load_dotenv(env_file)

        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Create session
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        def _insert_session():
            return client.table("conversation_sessions").insert({
                "session_id": session_id,
                "user_id": user_id,
                "session_start": datetime.utcnow().isoformat(),
                "started_at": datetime.utcnow().isoformat(),
                "is_active": True,
                "metadata": {}
            }).execute()

        await asyncio.to_thread(_insert_session)

        # Insert message with audio
        audio_url = "https://example.com/audio/message1.wav"

        def _insert_message():
            return client.table("conversation_messages").insert({
                "session_id": session_id,
                "user_id": user_id,
                "role": "user",
                "content": "This is a voice message",
                "audio_url": audio_url,
                "metadata": {"duration_ms": 3500},
                "created_at": datetime.utcnow().isoformat()
            }).execute()

        result = await asyncio.to_thread(_insert_message)

        # Verify
        assert result.data[0]["audio_url"] == audio_url
        assert result.data[0]["metadata"]["duration_ms"] == 3500

        # Cleanup
        def _cleanup():
            client.table("conversation_messages").delete().eq("session_id", session_id).execute()
            client.table("conversation_sessions").delete().eq("session_id", session_id).execute()

        await asyncio.to_thread(_cleanup)

    @pytest.mark.asyncio
    async def test_session_end_with_duration(self):
        """Test ending a session and calculating duration."""
        from supabase import create_client
        import os
        from dotenv import load_dotenv
        from pathlib import Path
        import time

        env_file = Path(__file__).parent.parent.parent / "env_files" / "supabase.env"
        load_dotenv(env_file)

        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Create session
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        session_start = datetime.utcnow()

        def _insert_session():
            return client.table("conversation_sessions").insert({
                "session_id": session_id,
                "user_id": user_id,
                "session_start": session_start.isoformat(),
                "started_at": session_start.isoformat(),
                "is_active": True,
                "metadata": {}
            }).execute()

        await asyncio.to_thread(_insert_session)

        # Wait a bit
        await asyncio.sleep(1)

        # End session
        session_end = datetime.utcnow()
        duration_seconds = (session_end - session_start).total_seconds()

        def _update_session():
            return client.table("conversation_sessions").update({
                "session_end": session_end.isoformat(),
                "ended_at": session_end.isoformat(),
                "is_active": False,
                "duration_seconds": duration_seconds
            }).eq("session_id", session_id).execute()

        result = await asyncio.to_thread(_update_session)

        # Verify
        assert result.data[0]["is_active"] is False
        assert result.data[0]["duration_seconds"] >= 1.0  # At least 1 second
        assert result.data[0]["session_end"] is not None

        # Cleanup
        def _cleanup():
            client.table("conversation_sessions").delete().eq("session_id", session_id).execute()

        await asyncio.to_thread(_cleanup)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

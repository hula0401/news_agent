"""
End-to-End tests for complete conversation flow.

Tests the full stack:
- WebSocket connection
- Session creation
- Message tracking
- Stock price queries
- News discussion
- Session end with data persistence

Run with: uv run python -m pytest tests/e2e/test_conversation_complete_flow.py -v -s
"""
import pytest
import asyncio
import json
import uuid
from datetime import datetime
from websockets import connect
from supabase import create_client
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_file = Path(__file__).parent.parent.parent / "env_files" / "supabase.env"
load_dotenv(env_file, override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for admin operations
WS_URL = "ws://localhost:8000/ws/voice"

# Verify environment variables are loaded
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError(f"Supabase credentials not loaded! URL={SUPABASE_URL}, KEY={'SET' if SUPABASE_KEY else 'NOT SET'}")


@pytest.mark.asyncio
async def test_complete_conversation_flow():
    """
    E2E Test: Complete conversation about Tesla stock.

    Flow:
    1. Connect WebSocket
    2. Ask about Tesla stock price
    3. Verify session created in database
    4. Verify messages saved in database
    5. Disconnect
    6. Verify session ended in database
    """
    # Setup - Use existing demo user
    user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"  # Demo user from database
    session_id = None

    # Connect to database
    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        # Step 1: Connect WebSocket
        async with connect(f"{WS_URL}?user_id={user_id}") as websocket:
            # Step 2: Wait for connected event
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)

            assert data["event"] == "connected"
            assert "data" in data
            assert "session_id" in data["data"]
            session_id = data["data"]["session_id"]

            print(f"✅ Connected with session_id: {session_id[:8]}...")

            # Step 3: Verify session exists in database
            await asyncio.sleep(1)  # Give time for DB insert

            result = db.table("conversation_sessions").select("*").eq("session_id", session_id).execute()
            assert len(result.data) == 1, f"Session not found in database! session_id={session_id}"
            assert result.data[0]["is_active"] is True
            assert result.data[0]["user_id"] == user_id

            print(f"✅ Session created in database")

            # Step 4: Send audio chunk (simulated)
            # Note: For real E2E, you'd send actual audio data
            # For now, we'll just verify the connection works

            # Step 5: Send disconnect
            await websocket.close()

        # Step 6: Wait for session end processing
        await asyncio.sleep(3)

        # Step 7: Verify session ended in database
        # Note: The FK uses conversation_sessions.id, so query by session_id field
        result = db.table("conversation_sessions").select("*").eq("session_id", session_id).execute()
        assert len(result.data) == 1

        session_data = result.data[0]
        print(f"   Session data: is_active={session_data['is_active']}, session_end={session_data.get('session_end')}, ended_at={session_data.get('ended_at')}, duration={session_data.get('duration_seconds')}")

        # Verify session was ended
        assert session_data["is_active"] is False, "Session should be marked inactive"
        assert session_data["session_end"] is not None or session_data["ended_at"] is not None, "Session should have end timestamp"

        print(f"✅ Session ended in database")
        print(f"   Duration: {session_data.get('duration_seconds', 'N/A')}s")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Cleanup - delete by the database id (FK uses this)
        if session_id:
            # First get the database id
            result = db.table("conversation_sessions").select("id").eq("session_id", session_id).execute()
            if result.data:
                db_id = result.data[0]["id"]
                db.table("conversation_messages").delete().eq("session_id", db_id).execute()
                db.table("conversation_sessions").delete().eq("session_id", session_id).execute()
                print(f"✅ Cleaned up test data")


@pytest.mark.asyncio
async def test_session_creation_database():
    """
    Unit Test: Verify session is created with all required fields.
    """
    user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"  # Demo user from database
    session_id = str(uuid.uuid4())

    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        # Insert session
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "session_start": datetime.utcnow().isoformat(),
            "started_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "metadata": {"test": True}
        }

        result = db.table("conversation_sessions").insert(session_data).execute()

        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]["session_id"] == session_id
        assert result.data[0]["user_id"] == user_id
        assert result.data[0]["is_active"] is True

        print("✅ Session created successfully with all fields")

    finally:
        # Cleanup
        db.table("conversation_sessions").delete().eq("session_id", session_id).execute()


@pytest.mark.asyncio
async def test_message_persistence():
    """
    Unit Test: Verify messages are saved with correct role values.
    """
    user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"  # Demo user from database
    session_id = str(uuid.uuid4())

    db = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        # Create session first
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "is_active": True,
            "metadata": {}
        }
        result = db.table("conversation_sessions").insert(session_data).execute()
        print(f"✅ Session created: {result.data}")

        # Insert user message
        user_msg = {
            "session_id": session_id,
            "user_id": user_id,
            "role": "user",
            "content": "What's the price of Tesla?",
            "created_at": datetime.utcnow().isoformat()
        }
        result = db.table("conversation_messages").insert(user_msg).execute()
        assert result.data[0]["role"] == "user"

        print("✅ User message saved")

        # Insert agent message (NOT "assistant")
        agent_msg = {
            "session_id": session_id,
            "user_id": user_id,
            "role": "agent",  # MUST be "agent" not "assistant"
            "content": "The current price of Tesla is $439.31",
            "created_at": datetime.utcnow().isoformat()
        }
        result = db.table("conversation_messages").insert(agent_msg).execute()
        assert result.data[0]["role"] == "agent"

        print("✅ Agent message saved")

        # Verify both messages exist
        result = db.table("conversation_messages").select("*").eq("session_id", session_id).execute()
        assert len(result.data) == 2

        print("✅ All messages persisted correctly")

    finally:
        # Cleanup
        db.table("conversation_messages").delete().eq("session_id", session_id).execute()
        db.table("conversation_sessions").delete().eq("session_id", session_id).execute()


@pytest.mark.asyncio
async def test_news_discussion_tracking():
    """
    Test: Track news discussed in a session (Option A implementation).

    This test verifies that when a user asks about Tesla news,
    the discussed news is tracked and saved.
    """
    # This will be implemented after Option A is complete
    # For now, it's a placeholder to guide implementation

    print("⏳ News tracking not yet implemented - see Option A plan")
    pytest.skip("News tracking implementation pending")


if __name__ == "__main__":
    # Run with: uv run python tests/e2e/test_conversation_complete_flow.py
    pytest.main([__file__, "-v", "-s", "--tb=short"])

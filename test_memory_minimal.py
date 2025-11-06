"""Minimal test - just check tracking and finalization without LLM calls."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.llm_agent.long_term_memory_supabase import LongTermMemory
from backend.app.database import get_database


async def test():
    print("=" * 80)
    print("MINIMAL MEMORY TEST")
    print("=" * 80)

    # Initialize database
    db = await get_database()
    await db.initialize()
    print("✅ Database initialized")

    # Create memory instance
    user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"
    memory = LongTermMemory(user_id=user_id, db_manager=db)
    await memory.initialize()
    print(f"✅ Memory initialized for user: {user_id}")

    # Check current notes
    print(f"\n📚 Current notes: {memory.key_notes}")

    # Start a session
    session_id = "test-session-123"
    memory.start_session(session_id)
    print(f"\n✅ Session started: {session_id}")

    # Track some conversations
    print("\n📝 Tracking conversations...")
    memory.track_conversation(
        query="What's AAPL price?",
        intent="price_check",
        symbols=["AAPL"],
        summary="AAPL is trading at $150"
    )

    memory.track_conversation(
        query="What's MSFT price?",
        intent="price_check",
        symbols=["MSFT"],
        summary="MSFT is trading at $300"
    )

    print(f"   Tracked queries: {memory.session_queries}")
    print(f"   Tracked symbols: {memory.session_symbols}")
    print(f"   Tracked intents: {memory.session_intents}")

    # Try finalization
    print("\n💾 Attempting finalization...")
    try:
        await memory.finalize_session()
        print("✅ Finalization completed")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Check if notes were updated
    await asyncio.sleep(2)
    updated_notes = await db.get_user_notes(user_id)
    print(f"\n📚 Updated notes: {updated_notes}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test())

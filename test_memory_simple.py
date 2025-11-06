"""Simple test for memory finalization - checks if usernotes updates."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.core.agent_wrapper_langgraph import get_agent
from backend.app.database import get_database


async def test_memory():
    print("=" * 80)
    print("MEMORY FINALIZATION TEST")
    print("=" * 80)

    # Initialize
    print("\n1. Initializing services...")
    agent = await get_agent()
    db = await get_database()
    await db.initialize()
    print("   ✅ Services initialized")

    # Test user
    user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"
    print(f"\n2. Test user: {user_id}")

    # Get current notes
    print("\n3. Getting current usernotes...")
    before_notes = await db.get_user_notes(user_id)
    print(f"   Before: {before_notes}")

    # Run TWO queries (price checks, not chat)
    print("\n4. Running test queries (price checks)...")

    print("   Query 1: 'What's AAPL price?'")
    result1 = await agent.process_text_command(user_id, "What's AAPL price?")
    print(f"   Intent: {result1.get('intent', 'unknown')}")

    print("   Query 2: 'What's MSFT price?'")
    result2 = await agent.process_text_command(user_id, "What's MSFT price?")
    print(f"   Intent: {result2.get('intent', 'unknown')}")

    # Check if memory is tracking
    print("\n5. Checking memory state...")
    if user_id in agent.user_memories:
        memory = agent.user_memories[user_id]
        print(f"   Session ID: {memory.current_session_id}")
        print(f"   Queries tracked: {len(memory.session_queries)}")
        print(f"   Symbols tracked: {memory.session_symbols}")
        print(f"   Intents tracked: {memory.session_intents}")

        if len(memory.session_queries) == 0:
            print("\n   ⚠️  WARNING: No queries tracked!")
            print("   This means memory.track_conversation() is not being called")
            print("   Check if queries are classified as 'chat' or 'unknown'")
    else:
        print("   ⚠️  WARNING: No memory instance for user!")

    # Manually trigger finalization
    print("\n6. Manually triggering finalization...")
    try:
        await agent.finalize_session(user_id)
        print("   ✅ finalize_session() called")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Wait for DB to commit
    await asyncio.sleep(2)

    # Check if notes updated
    print("\n7. Checking updated usernotes...")
    after_notes = await db.get_user_notes(user_id)
    print(f"   After: {after_notes}")

    # Compare
    print("\n8. Comparison:")
    if before_notes != after_notes:
        print("   ✅ USERNOTES UPDATED!")
        for key in set(list(before_notes.keys()) + list(after_notes.keys())):
            old = before_notes.get(key, "(not set)")
            new = after_notes.get(key, "(not set)")
            if old != new:
                print(f"\n   📝 {key}:")
                print(f"      Before: {old}")
                print(f"      After:  {new}")
    else:
        print("   ⚠️  NO CHANGES DETECTED")
        print("\n   Possible reasons:")
        print("   1. Memory had no tracked queries")
        print("   2. LLM didn't generate updates")
        print("   3. Queries were classified as 'chat' or 'unknown'")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_memory())

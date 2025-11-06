"""Test script for session finalization and usernotes updates."""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.core.agent_wrapper_langgraph import get_agent
from backend.app.database import get_database


async def test_memory_finalization():
    """Test that session finalization updates usernotes table."""
    print("=" * 80)
    print("SESSION FINALIZATION & USERNOTES UPDATE TEST")
    print("=" * 80)

    # Initialize services
    print("\n1. Initializing services...")
    agent = await get_agent()
    db = await get_database()
    await db.initialize()
    print("   ✅ Services initialized")

    # Use existing user ID
    test_user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"
    print(f"\n2. Test user ID: {test_user_id}")

    # Check existing usernotes
    print("\n3. Getting existing usernotes...")
    existing_notes = await db.get_user_notes(test_user_id)
    print(f"   Existing notes: {existing_notes}")

    # Run some queries to generate conversation data
    print("\n4. Running test queries...")

    queries = [
        ("What's the price of AAPL?", "price_check"),
        ("Add AAPL to my watchlist", "watchlist"),
        ("What's the price of MSFT?", "price_check"),
    ]

    for i, (query, expected_intent) in enumerate(queries, 1):
        print(f"\n   Query {i}: {query}")
        result = await agent.process_text_command(
            user_id=test_user_id,
            query=query
        )
        print(f"   Response: {result.get('response', 'No response')[:80]}...")
        print(f"   Intent: {result.get('intent', 'unknown')}")

    # Now explicitly finalize the session
    print("\n5. Finalizing session (triggering usernotes update)...")
    try:
        await agent.finalize_session(test_user_id)
        print("   ✅ Session finalized")
    except Exception as e:
        print(f"   ❌ Error finalizing session: {e}")
        import traceback
        traceback.print_exc()

    # Check if usernotes were updated
    print("\n6. Checking updated usernotes...")
    await asyncio.sleep(2)  # Give DB time to commit

    updated_notes = await db.get_user_notes(test_user_id)
    print(f"   Updated notes: {updated_notes}")

    # Compare
    print("\n7. Comparison:")
    if existing_notes != updated_notes:
        print("   ✅ USERNOTES UPDATED!")
        print(f"\n   Before: {existing_notes}")
        print(f"\n   After:  {updated_notes}")

        # Show what changed
        all_keys = set(existing_notes.keys()) | set(updated_notes.keys())
        for key in sorted(all_keys):
            old_val = existing_notes.get(key, "(not set)")
            new_val = updated_notes.get(key, "(not set)")
            if old_val != new_val:
                print(f"\n   📝 {key}:")
                print(f"      Before: {old_val}")
                print(f"      After:  {new_val}")
    else:
        print("   ⚠️  No changes detected")
        print("   This could mean:")
        print("   - Session had no queries (chat/unknown intents don't count)")
        print("   - LLM didn't generate updates")
        print("   - Database update failed")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_memory_finalization())

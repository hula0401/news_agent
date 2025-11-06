"""Test just the database upsert fix - no LLM calls."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.database import get_database


async def test():
    print("=" * 80)
    print("DATABASE UPSERT TEST")
    print("=" * 80)

    # Initialize database
    db = await get_database()
    await db.initialize()
    print("✅ Database initialized")

    # Test user
    user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"
    print(f"\n📝 Testing user: {user_id}")

    # Get current notes
    print("\n1. Getting current notes...")
    before_notes = await db.get_user_notes(user_id)
    print(f"   Before: {before_notes}")

    # Try to upsert new notes
    print("\n2. Upserting test notes...")
    test_notes = {
        "stocks": "Testing AAPL and MSFT price tracking",
        "research": "Interested in price data",
        "test": "This is a test entry"
    }

    success = await db.upsert_user_notes(user_id, test_notes)
    print(f"   Success: {success}")

    # Wait for DB to commit
    await asyncio.sleep(2)

    # Check if notes were updated
    print("\n3. Checking updated notes...")
    after_notes = await db.get_user_notes(user_id)
    print(f"   After: {after_notes}")

    # Compare
    print("\n4. Comparison:")
    if before_notes != after_notes:
        print("   ✅ NOTES UPDATED!")
    else:
        print("   ❌ NO CHANGE")

    # Try updating again (should update, not insert)
    print("\n5. Updating notes again...")
    test_notes2 = {
        **test_notes,
        "stocks": "Updated - tracking AAPL, MSFT, and GOOGL"
    }

    success2 = await db.upsert_user_notes(user_id, test_notes2)
    print(f"   Success: {success2}")

    await asyncio.sleep(2)

    final_notes = await db.get_user_notes(user_id)
    print(f"   Final: {final_notes}")

    if final_notes != after_notes:
        print("   ✅ UPDATE WORKED!")
    else:
        print("   ❌ UPDATE FAILED")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test())

"""Test if other tables have RLS issues."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.database import get_database


async def test():
    print("=" * 80)
    print("TESTING OTHER TABLES - RLS CHECK")
    print("=" * 80)

    db = await get_database()
    await db.initialize()

    test_user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"

    # Test 1: users table (update watchlist)
    print("\n1. Testing 'users' table (watchlist update)...")
    try:
        result = await db.update_user_watchlist(test_user_id, ["TEST_SYMBOL"])
        print(f"   ✅ SUCCESS - users table is editable")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test 2: Try to read from conversations table
    print("\n2. Testing 'conversations' table (read)...")
    try:
        def _read():
            return db.client.table('conversations').select('*').limit(1).execute()

        result = await asyncio.to_thread(_read)
        print(f"   ✅ SUCCESS - conversations table is readable")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test 3: Try to insert into conversations table
    print("\n3. Testing 'conversations' table (insert)...")
    try:
        def _insert():
            return db.client.table('conversations').insert({
                'user_id': test_user_id,
                'session_id': 'test-session',
                'role': 'user',
                'content': 'test message'
            }).execute()

        result = await asyncio.to_thread(_insert)
        print(f"   ✅ SUCCESS - conversations table is insertable")
    except Exception as e:
        print(f"   ❌ FAILED: {e}")

    # Test 4: user_notes table (we know this fails)
    print("\n4. Testing 'user_notes' table (insert)...")
    try:
        def _insert():
            return db.client.table('user_notes').insert({
                'user_id': test_user_id,
                'key_notes': {'test': 'data'}
            }).execute()

        result = await asyncio.to_thread(_insert)
        print(f"   ✅ SUCCESS - user_notes table is insertable")
    except Exception as e:
        error_code = str(e).split("'code': '")[1].split("'")[0] if "'code': '" in str(e) else "unknown"
        print(f"   ❌ FAILED: Error code {error_code}")
        if "42501" in str(e):
            print("   🔍 This is RLS policy violation")

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("\nIf user_notes fails with RLS but others work, it means:")
    print("- Other tables have RLS DISABLED")
    print("- user_notes has RLS ENABLED")
    print("\nThis happens when tables are created at different times")
    print("or with different settings in Supabase dashboard.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test())

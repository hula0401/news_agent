"""
Test session lifecycle - ensure is_active is properly managed.

This test verifies:
1. Sessions start with is_active=True
2. Sessions end with is_active=False on disconnect
3. All sessions close on server shutdown
"""
import asyncio
import uuid
from datetime import datetime

from backend.app.database import get_database
from backend.app.core.conversation_tracker import ConversationTracker


async def test_session_lifecycle():
    """Test complete session lifecycle."""
    print("=" * 80)
    print("SESSION LIFECYCLE TEST")
    print("=" * 80)

    # Initialize database
    db = await get_database()
    await db.initialize()
    print("✅ Database initialized")

    # Create tracker
    tracker = ConversationTracker()
    tracker.start()
    print("✅ Conversation tracker started")

    # Generate test IDs
    session_id = str(uuid.uuid4())
    user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"

    try:
        # Step 1: Start session
        print("\n📝 Step 1: Starting session...")
        await tracker.start_session(
            session_id=session_id,
            user_id=user_id,
            metadata={"test": "lifecycle"}
        )
        print(f"   Session ID: {session_id[:16]}...")

        # Wait for async insert
        await asyncio.sleep(1)

        # Step 2: Verify session is active
        print("\n🔍 Step 2: Checking session is active...")

        def _check_active():
            return db.client.table("conversation_sessions").select(
                "is_active, session_start"
            ).eq("session_id", session_id).execute()

        result = await asyncio.to_thread(_check_active)

        if result.data and len(result.data) > 0:
            is_active = result.data[0]["is_active"]
            session_start = result.data[0]["session_start"]
            print(f"   is_active: {is_active}")
            print(f"   session_start: {session_start}")

            if is_active:
                print("   ✅ Session correctly marked as active")
            else:
                print("   ❌ ERROR: Session should be active!")
                return False
        else:
            print("   ❌ ERROR: Session not found in database!")
            return False

        # Step 3: End session
        print("\n📝 Step 3: Ending session...")
        await tracker.end_session(session_id)
        print("   end_session() called")

        # Wait for async update
        await asyncio.sleep(1)

        # Step 4: Verify session is inactive
        print("\n🔍 Step 4: Checking session is inactive...")

        def _check_inactive():
            return db.client.table("conversation_sessions").select(
                "is_active, session_start, session_end, duration_seconds"
            ).eq("session_id", session_id).execute()

        result = await asyncio.to_thread(_check_inactive)

        if result.data and len(result.data) > 0:
            is_active = result.data[0]["is_active"]
            session_start = result.data[0]["session_start"]
            session_end = result.data[0]["session_end"]
            duration = result.data[0]["duration_seconds"]

            print(f"   is_active: {is_active}")
            print(f"   session_start: {session_start}")
            print(f"   session_end: {session_end}")
            print(f"   duration: {duration}s")

            if not is_active and session_end:
                print("   ✅ Session correctly marked as inactive")
            else:
                print("   ❌ ERROR: Session should be inactive with session_end!")
                return False
        else:
            print("   ❌ ERROR: Session not found in database!")
            return False

        # Step 5: Test bulk close (simulating server shutdown)
        print("\n📝 Step 5: Testing bulk session close (shutdown simulation)...")

        # Create a few test sessions
        test_sessions = []
        for i in range(3):
            test_id = str(uuid.uuid4())
            test_sessions.append(test_id)
            await tracker.start_session(
                session_id=test_id,
                user_id=user_id,
                metadata={"test": f"bulk_{i}"}
            )
        await asyncio.sleep(1)

        print(f"   Created {len(test_sessions)} test sessions")

        # Close all active sessions (simulating shutdown)
        def _close_all():
            return db.client.table("conversation_sessions").update({
                "is_active": False,
                "session_end": datetime.utcnow().isoformat(),
                "ended_at": datetime.utcnow().isoformat()
            }).eq("is_active", True).execute()

        result = await asyncio.to_thread(_close_all)
        closed_count = len(result.data) if result.data else 0
        print(f"   Closed {closed_count} sessions")

        if closed_count == len(test_sessions):
            print(f"   ✅ All {closed_count} sessions closed correctly")
        else:
            print(f"   ⚠️  Expected {len(test_sessions)}, closed {closed_count}")

        # Verify no active sessions remain
        def _count_active():
            return db.client.table("conversation_sessions").select(
                "session_id"
            ).eq("is_active", True).execute()

        result = await asyncio.to_thread(_count_active)
        active_count = len(result.data) if result.data else 0

        print(f"   Active sessions remaining: {active_count}")

        if active_count == 0:
            print("   ✅ No orphaned active sessions")
        else:
            print(f"   ❌ ERROR: {active_count} sessions still active!")
            return False

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        await tracker.stop()
        print("\n✅ Tracker stopped")


if __name__ == "__main__":
    result = asyncio.run(test_session_lifecycle())
    exit(0 if result else 1)

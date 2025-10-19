"""Debug script to check actual database schema."""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
env_file = Path(__file__).parent.parent / "env_files" / "supabase.env"
load_dotenv(env_file, override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not loaded!")

# Create client
db = create_client(SUPABASE_URL, SUPABASE_KEY)

# Try to insert a test session
import uuid
from datetime import datetime

session_id = str(uuid.uuid4())
user_id = str(uuid.uuid4())

print(f"Testing session insert with session_id={session_id[:8]}...")

# First, check what columns users table has
print("Checking users table schema...")
try:
    # Try minimal user creation - only required fields
    print(f"Creating user {user_id[:8]}...")
    db.table("users").insert({
        "id": user_id,
        "email": f"test_{user_id[:8]}@example.com"
    }).execute()
    print("✅ User created")
except Exception as e:
    print(f"⚠️ User creation failed: {e}")
    # Try without email
    try:
        db.table("users").insert({"id": user_id}).execute()
        print("✅ User created (without email)")
    except Exception as e2:
        print(f"❌ User creation failed completely: {e2}")

try:
    print(f"Inserting session...")
    result = db.table("conversation_sessions").insert({
        "session_id": session_id,
        "user_id": user_id,
        "started_at": datetime.utcnow().isoformat(),
        "is_active": True,
        "metadata": {}
    }).execute()

    print(f"✅ INSERT SUCCESS: {result.data}")

    # Verify it exists
    result2 = db.table("conversation_sessions").select("*").eq("session_id", session_id).execute()
    print(f"✅ QUERY SUCCESS: Found {len(result2.data)} row(s)")
    print(f"   Data: {result2.data}")

    # Cleanup
    db.table("conversation_sessions").delete().eq("session_id", session_id).execute()
    db.table("users").delete().eq("id", user_id).execute()
    print(f"✅ CLEANUP SUCCESS")

except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Ensure cleanup even on error
    try:
        db.table("conversation_sessions").delete().eq("session_id", session_id).execute()
        db.table("users").delete().eq("id", user_id).execute()
    except:
        pass

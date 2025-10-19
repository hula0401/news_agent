"""Test session update."""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import uuid
from datetime import datetime

# Load environment
env_file = Path(__file__).parent.parent / "env_files" / "supabase.env"
load_dotenv(env_file, override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

user_id = "03f6b167-0c4d-4983-a380-54b8eb42f830"
session_uuid = str(uuid.uuid4())

# Create session
print(f"Creating session {session_uuid[:8]}...")
result = db.table("conversation_sessions").insert({
    "session_id": session_uuid,
    "user_id": user_id,
    "started_at": datetime.utcnow().isoformat(),
    "is_active": True,
    "metadata": {}
}).execute()

session_data = result.data[0]
print(f"✅ Created: id={session_data['id'][:8]}..., session_id={session_data['session_id'][:8]}...")

# Try updating by session_id
print(f"\nUpdating by session_id={session_uuid[:8]}...")
update_result = db.table("conversation_sessions").update({
    "ended_at": datetime.utcnow().isoformat(),
    "is_active": False,
    "duration_seconds": 10.5
}).eq("session_id", session_uuid).execute()

print(f"Update result: {update_result.data}")

# Query back
result2 = db.table("conversation_sessions").select("*").eq("session_id", session_uuid).execute()
if result2.data:
    s = result2.data[0]
    print(f"\n✅ After update:")
    print(f"  is_active: {s['is_active']}")
    print(f"  ended_at: {s.get('ended_at')}")
    print(f"  duration_seconds: {s.get('duration_seconds')}")
else:
    print("❌ Session not found after update")

# Cleanup
db.table("conversation_sessions").delete().eq("session_id", session_uuid).execute()
print(f"\n✅ Cleanup done")

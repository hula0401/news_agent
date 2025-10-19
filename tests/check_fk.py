"""Check foreign key constraint."""
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
result = db.table("conversation_sessions").insert({
    "session_id": session_uuid,
    "user_id": user_id,
    "started_at": datetime.utcnow().isoformat(),
    "is_active": True,
    "metadata": {}
}).execute()

session_data = result.data[0]
print(f"Created session:")
print(f"  id: {session_data['id']}")
print(f"  session_id: {session_data['session_id']}")

# Try inserting message with session_id
try:
    print(f"\nTrying message insert with session_id={session_uuid}...")
    db.table("conversation_messages").insert({
        "session_id": session_uuid,  # Using our session_id value
        "user_id": user_id,
        "role": "user",
        "content": "test"
    }).execute()
    print("✅ SUCCESS with session_id!")
except Exception as e:
    print(f"❌ FAILED with session_id: {e}")

# Try with id column instead
try:
    print(f"\nTrying message insert with session_id={session_data['id']}...")
    db.table("conversation_messages").insert({
        "session_id": session_data['id'],  # Using the id value
        "user_id": user_id,
        "role": "user",
        "content": "test"
    }).execute()
    print("✅ SUCCESS with id!")
except Exception as e:
    print(f"❌ FAILED with id: {e}")

# Cleanup
db.table("conversation_messages").delete().eq("session_id", session_uuid).execute()
db.table("conversation_messages").delete().eq("session_id", session_data['id']).execute()
db.table("conversation_sessions").delete().eq("session_id", session_uuid).execute()
print("\n✅ Cleanup done")

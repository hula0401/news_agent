"""Check if session end was updated."""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Load environment
env_file = Path(__file__).parent.parent / "env_files" / "supabase.env"
load_dotenv(env_file, override=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

db = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get most recent session
result = db.table("conversation_sessions").select("*").order("started_at", desc=True).limit(1).execute()

if result.data:
    session = result.data[0]
    print("Most recent session:")
    print(f"  session_id: {session['session_id']}")
    print(f"  id: {session['id']}")
    print(f"  user_id: {session['user_id']}")
    print(f"  started_at: {session['started_at']}")
    print(f"  ended_at: {session.get('ended_at')}")
    print(f"  session_end: {session.get('session_end')}")
    print(f"  is_active: {session['is_active']}")
    print(f"  duration_seconds: {session.get('duration_seconds')}")
else:
    print("No sessions found")

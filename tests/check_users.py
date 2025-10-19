"""Check existing users in database."""
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

# Check existing users
print("Fetching existing users...")
try:
    result = db.table("users").select("id, email").limit(5).execute()
    if result.data:
        print(f"✅ Found {len(result.data)} user(s):")
        for user in result.data:
            print(f"   - ID: {user['id']}, Email: {user.get('email', 'N/A')}")
    else:
        print("⚠️ No users found in database")
except Exception as e:
    print(f"❌ Error fetching users: {e}")

# Check auth.users (Supabase Auth users)
print("\nFetching auth users...")
try:
    # This requires service key
    result = db.auth.admin.list_users()
    if hasattr(result, 'users') and result.users:
        print(f"✅ Found {len(result.users)} auth user(s):")
        for user in result.users[:5]:
            print(f"   - ID: {user.id}, Email: {user.email}")
    else:
        print("⚠️ No auth users found")
except Exception as e:
    print(f"⚠️ Cannot access auth users: {e}")

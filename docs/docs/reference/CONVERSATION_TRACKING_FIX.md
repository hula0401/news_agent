# Conversation Tracking Fix - Complete Solution

## Issues Found

### Issue 1: Missing `metadata` column in `conversation_sessions`
```
❌ Error: Could not find the 'metadata' column of 'conversation_sessions' in the schema cache
```

### Issue 2: Missing `audio_url` column in `conversation_messages`
```
❌ Error: Could not find the 'audio_url' column of 'conversation_messages' in the schema cache
```

### Issue 3: Missing `user_id` in message inserts
```
❌ Error: null value in column "user_id" of relation "conversation_messages" violates not-null constraint
```

### Issue 4: Wrong column names in code
Code was using `session_start`/`session_end` but database has `started_at`/`ended_at`

---

## Solutions Applied

### 1. Code Fixes (Already Applied ✅)

**File**: [backend/app/core/conversation_tracker.py](../backend/app/core/conversation_tracker.py)

#### Fix 1: Add user_id to message inserts (Line 233-241)
```python
# Get user_id from session state
session_id = message["session_id"]
user_id = None
if session_id in self.session_states:
    user_id = self.session_states[session_id].get("user_id")

await db_manager.client.table("conversation_messages").insert({
    "session_id": session_id,
    "user_id": user_id,  # ✅ Now included
    "role": message["role"],
    "content": message["content"],
    "audio_url": message.get("audio_url"),
    "metadata": message.get("metadata"),
    "created_at": message["created_at"].isoformat()
}).execute()
```

#### Fix 2: Use correct column names for session start (Line 125-130)
```python
await db_manager.client.table("conversation_sessions").insert({
    "session_id": session_id,  # ✅ Changed from "id"
    "user_id": user_id,
    "started_at": datetime.utcnow().isoformat(),  # ✅ Changed from "session_start"
    "metadata": metadata or {}
}).execute()
```

#### Fix 3: Use correct column names for session end (Line 163-166)
```python
await db_manager.client.table("conversation_sessions").update({
    "ended_at": session_end.isoformat(),  # ✅ Changed from "session_end"
    "duration_seconds": duration_seconds
}).eq("session_id", session_id).execute()  # ✅ Changed from .eq("id", ...)
```

---

### 2. Database Migration (USER ACTION REQUIRED ⚠️)

**File**: [database/fix_conversation_tables.sql](../database/fix_conversation_tables.sql)

**Apply this SQL in Supabase Dashboard** → SQL Editor → Run:

The script will:
1. ✅ Add `metadata` column to `conversation_sessions`
2. ✅ Add `audio_url` column to `conversation_messages`
3. ✅ Make `user_id` nullable in `conversation_messages` (for system messages)
4. ✅ Add proper RLS policies for both tables
5. ✅ Create helper function for safe message insertion
6. ✅ Verify all columns exist and show final schema

---

## Expected Results After Fix

### Before (Current Errors)
```
❌ Failed to save session start: Could not find the 'metadata' column
❌ Failed to save message: null value in column "user_id" violates not-null constraint
❌ Could not find the 'audio_url' column
```

### After (Expected Success)
```
✅ Started session fda86359... for user 03f6b167...
✅ Saved user message for session fda86359...
✅ Saved assistant message for session fda86359...
✅ Ended session fda86359... (duration: 45.2s, messages: 8)
```

---

## Database Schema (After Migration)

### conversation_sessions
```sql
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID UNIQUE NOT NULL,
    user_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    duration_seconds FLOAT,
    metadata JSONB DEFAULT '{}'::jsonb,  -- ✅ NEW
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### conversation_messages
```sql
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(session_id),
    user_id UUID,  -- ✅ NULLABLE (for system messages)
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    audio_url TEXT,  -- ✅ NEW
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## Testing the Fix

### 1. Apply the SQL migration
```bash
# In Supabase SQL Editor, run:
database/fix_conversation_tables.sql
```

### 2. Restart the server
```bash
make run-server
```

### 3. Start a conversation
```bash
# Open your frontend and start a voice conversation
# Or use WebSocket test client
```

### 4. Check logs (should see success messages)
```bash
tail -f /tmp/server_logs.txt | grep "session\|message"
```

Expected output:
```
✅ Started session abc12345... for user xyz98765...
✅ Saved user message for session abc12345...
✅ Saved assistant message for session abc12345...
✅ Ended session abc12345... (duration: 30.5s, messages: 4)
```

### 5. Verify in Supabase
```sql
-- Check sessions
SELECT * FROM conversation_sessions
ORDER BY started_at DESC
LIMIT 5;

-- Check messages
SELECT session_id, role, content, audio_url, created_at
FROM conversation_messages
ORDER BY created_at DESC
LIMIT 10;
```

---

## Architecture: Conversation Tracking Flow

### Session Lifecycle
```
WebSocket Connect
    ↓
start_session(session_id, user_id)
    ↓
Save to conversation_sessions
    - session_id
    - user_id
    - started_at
    - metadata (empty initially)
    ↓
Store in memory: session_states[session_id]
    - user_id
    - session_start
    - is_active: True
    - message_count: 0
    ↓
[User and Agent exchange messages]
    ↓
track_message() for each message
    ↓
Add to queue (non-blocking, ~1ms)
    ↓
Background worker saves to DB
    ↓
conversation_messages.insert()
    - session_id
    - user_id (from session_states)  ✅ Fixed
    - role
    - content
    - audio_url (if voice message)  ✅ Fixed
    ↓
WebSocket Disconnect
    ↓
end_session(session_id)
    ↓
Update conversation_sessions
    - ended_at
    - duration_seconds
    ↓
Cleanup session_states after 60s
```

### Message Queue Pattern
```
track_message()  ────────→  Queue (async, non-blocking)
                               ↓
                          Background Worker
                               ↓
                          Retry Logic (3 attempts)
                               ↓
                          Database Insert
```

**Benefits**:
- Non-blocking message tracking (~1ms overhead)
- Automatic retry with exponential backoff
- Graceful degradation on failures
- Session state cached in memory for fast lookups

---

## Common Issues & Solutions

### Issue: Session not found in state
```
⚠️ Session abc12345... not found in state
```
**Cause**: Session ended but late messages still arriving
**Solution**: 60-second grace period implemented for late messages

### Issue: user_id is None
```
❌ null value in column "user_id" violates not-null constraint
```
**Cause**: Session not properly initialized before tracking messages
**Solution**:
1. Ensure `start_session()` is called first
2. After SQL migration, user_id is nullable (allows system messages)

### Issue: Database connection not initialized
```
❌ Failed to save message: Database not initialized
```
**Solution**: Automatic initialization added to all DB operations

---

## Files Modified

### Backend Code (Already Applied ✅)
1. [backend/app/core/conversation_tracker.py](../backend/app/core/conversation_tracker.py)
   - Line 233-241: Add user_id to message inserts
   - Line 125-130: Fix session start column names
   - Line 163-166: Fix session end column names

### Database Migrations (USER ACTION REQUIRED ⚠️)
1. [database/fix_conversation_tables.sql](../database/fix_conversation_tables.sql)
   - Add `metadata` column to `conversation_sessions`
   - Add `audio_url` column to `conversation_messages`
   - Make `user_id` nullable
   - Add RLS policies
   - Create helper function

---

## Summary

### ✅ Code Fixes Applied
- Added user_id to message inserts
- Fixed column names (started_at, ended_at, session_id)
- User_id now retrieved from session_states

### ⚠️ Database Migration Required
- Run [database/fix_conversation_tables.sql](../database/fix_conversation_tables.sql) in Supabase

### 🎯 After Both Applied
- Sessions will start successfully
- Messages will save with proper user_id
- Audio URLs will be stored
- Metadata will be tracked
- No more constraint violations

---

## Next Steps

1. **Immediate**: Apply SQL migration in Supabase
2. **Test**: Start a conversation and verify logs
3. **Verify**: Check Supabase tables for new data
4. **Monitor**: Watch for any remaining errors

---

## Performance Impact

- **Message tracking**: ~1ms (non-blocking queue)
- **Database inserts**: Async background worker
- **Session state**: In-memory cache (O(1) lookups)
- **Queue size**: 10,000 messages max (configurable)

**Conclusion**: Minimal performance impact, high reliability with retry logic.

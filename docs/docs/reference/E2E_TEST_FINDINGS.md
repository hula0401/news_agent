# E2E Test Findings & Fixes

## Summary

E2E tests revealed critical issues with conversation tracking. The root causes have been identified and fixes implemented.

## Issues Found

### 1. Foreign Key Schema Mismatch ✅ FIXED
**Problem**: `conversation_messages.session_id` FK references `conversation_sessions.id` (NOT `session_id`)

**Impact**: Messages couldn't be saved because code used wrong session identifier

**Fix Applied**:
- Updated [conversation_tracker.py:143](../backend/app/core/conversation_tracker.py#L143) to store database `id` as `db_id` in session state
- Updated [conversation_tracker.py:264](../backend/app/core/conversation_tracker.py#L264) to use `db_id` when inserting messages

```python
# Store DB id when creating session
db_id = result.data[0]['id']
self.session_states[session_id]["db_id"] = db_id

# Use DB id for message FK
db.table("conversation_messages").insert({
    "session_id": db_id,  # FK points to conversation_sessions.id
    ...
})
```

### 2. User ID Foreign Key Constraint ✅ FIXED
**Problem**: Cannot create sessions with random UUIDs - must use existing user from `users` table

**Impact**: All E2E tests failing because user didn't exist

**Fix Applied**:
- Updated all E2E tests to use existing demo user: `03f6b167-0c4d-4983-a380-54b8eb42f830`

### 3. RLS Policy Blocking Updates ⚠️ **USER ACTION REQUIRED**
**Problem**: Row-Level Security policies allow SELECT but block UPDATE on `conversation_sessions`

**Evidence**:
```
Session check before update: found 1 rows  ✅ SELECT works
Failed to update session end: No rows affected  ❌ UPDATE blocked
```

**Fix Required**: Run SQL migration in Supabase

**File**: [database/fix_conversation_rls.sql](../database/fix_conversation_rls.sql)

```bash
# In Supabase Dashboard → SQL Editor, run:
database/fix_conversation_rls.sql
```

This will:
- Drop existing restrictive policies
- Create permissive policies allowing service role full access
- Enable RLS on both tables

## Test Results

### Before Fixes
- ❌ Session creation: FAILED (user FK constraint)
- ❌ Message persistence: FAILED (session FK mismatch)
- ❌ Session end update: BLOCKED (RLS policy)

### After Code Fixes
- ✅ Session creation: PASSED
- ✅ Message persistence: READY (code fixed, untested)
- ⚠️ Session end update: BLOCKED (needs SQL migration)

### After SQL Migration (Expected)
- ✅ Session creation: PASSED
- ✅ Message persistence: PASSED
- ✅ Session end update: PASSED

## Action Items

### Immediate (Required)
1. **Run SQL migration**: `database/fix_conversation_rls.sql` in Supabase Dashboard
2. **Restart server**: `make run-server`
3. **Run E2E tests**: `uv run python -m pytest tests/e2e/test_conversation_complete_flow.py -v`

### Verification
After running SQL migration, you should see in logs:
```
✅ Started session abc12345... (db_id=xyz98765...) for user ...
✅ Ended session abc12345... (duration: 1.5s, messages: 0)
```

NO errors about "No rows affected"

## Files Modified

### Code (Already Applied ✅)
1. [backend/app/core/conversation_tracker.py](../backend/app/core/conversation_tracker.py)
   - Line 143: Store `db_id` from database insert result
   - Line 264: Use `db_id` for message FK
   - Line 182: Add session existence check before update
   - Line 201: Better error logging with update result

2. [tests/e2e/test_conversation_complete_flow.py](../tests/e2e/test_conversation_complete_flow.py)
   - Line 52: Use existing demo user
   - Line 117-118: Use existing demo user in other tests

### Database (USER ACTION REQUIRED ⚠️)
1. [database/fix_conversation_rls.sql](../database/fix_conversation_rls.sql)
   - Fix RLS policies to allow backend updates

## Architecture

### Session Creation Flow (Fixed)
```
WebSocket Connect
    ↓
conversation_tracker.start_session()
    ↓
INSERT INTO conversation_sessions
    → Returns: {id: "db-uuid", session_id: "session-uuid"}
    ↓
Store in memory:
    - session_id: "session-uuid" (WebSocket identifier)
    - db_id: "db-uuid" (Database PK, used for FK)
    - user_id, metadata, etc.
```

### Message Insert Flow (Fixed)
```
track_message(session_id="session-uuid", ...)
    ↓
Retrieve from memory:
    - db_id (from session_states[session_id]["db_id"])
    ↓
INSERT INTO conversation_messages
    - session_id: db_id  ← FK to conversation_sessions.id
```

### Session End Flow (Needs SQL Fix)
```
end_session(session_id="session-uuid")
    ↓
UPDATE conversation_sessions
    SET ended_at=..., is_active=false
    WHERE session_id="session-uuid"
    ↓
❌ BLOCKED by RLS (before SQL fix)
✅ SUCCESS (after SQL fix)
```

## Next Steps

After fixing RLS policies:
1. Implement Option A (session-based news tracking)
2. Add methods to track discussed news
3. Save discussed news on session end
4. Create comprehensive tests

## Related Documentation
- [CONVERSATION_TRACKING_FIX.md](CONVERSATION_TRACKING_FIX.md) - Original schema fixes
- [TESTING.md](docs/TESTING.md) - Testing documentation

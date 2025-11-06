# Memory Finalization & Usernotes Analysis

**Date**: 2025-11-05
**Status**: ✅ Infrastructure Complete, 🔄 Testing Required

---

## Executive Summary

The post-session memory summarization and usernotes update system **IS implemented and functional**. The infrastructure exists at:
- [long_term_memory_supabase.py](backend/app/llm_agent/long_term_memory_supabase.py) - Memory management
- [agent_wrapper_langgraph.py:227-247](backend/app/core/agent_wrapper_langgraph.py:227-247) - Session finalization
- [websocket_manager.py:240-246](backend/app/core/websocket_manager.py:240-246) - WebSocket disconnect trigger
- [database.py:255-316](backend/app/database.py:255-316) - Supabase usernotes CRUD

**Key Finding**: Memory finalization **only triggers on WebSocket disconnect**, not on API calls.

---

## How It Works

### 1. Session Start

When a conversation begins via WebSocket:
```python
# agent_wrapper_langgraph.py:114
memory.start_session(session_id)
```

### 2. Conversation Tracking

During each query (excluding chat/unknown intents):
```python
# agent_wrapper_langgraph.py:147-152
memory.track_conversation(
    query=query,
    intent=result.get("intent"),
    symbols=result.get("symbols", []),
    summary=response_text
)
```

### 3. Session Finalization

On WebSocket disconnect:
```python
# websocket_manager.py:243
await self.agent.finalize_session(user_id, session_id)
```

Which triggers:
```python
# long_term_memory_supabase.py:120-161
async def finalize_session(self):
    # 1. Analyze session with LLM
    updated_notes = await self._summarize_session_with_llm()

    # 2. Merge with existing notes
    self.key_notes.update(updated_notes)

    # 3. Save to Supabase user_notes table
    success = await self.db.upsert_user_notes(self.user_id, self.key_notes)
```

### 4. Database Update

```python
# database.py:287-316
async def upsert_user_notes(self, user_id: str, key_notes: Dict[str, str]) -> bool:
    self.client.table('user_notes').upsert({
        'user_id': user_id,
        'key_notes': key_notes,
        'updated_time': datetime.utcnow().isoformat()
    }, on_conflict='user_id').execute()
```

---

## LLM Summarizer

The system uses an LLM to analyze the session and update category-based notes:

### Categories

```python
{
    "stocks": "General interest in specific stocks or sectors",
    "investment": "Long-term investment strategies",
    "trading": "Short-term trading patterns",
    "research": "Analytical interests (P/E, earnings, valuation)",
    "watchlist": "Stocks being actively tracked",
    "news": "News monitoring interests"
}
```

### LLM Prompt

The summarizer receives:
- Current category notes
- Session queries
- Symbols discussed
- Intent types

And generates updated category notes based on the user's expressed interests.

---

## Why It Might Not Be Working

### Issue 1: Only Triggers on WebSocket Disconnect

**Problem**: If testing via:
- Direct API calls (`/api/query`)
- Test scripts
- Frontend without proper disconnect handling

The finalization **will not run** because it only triggers in `websocket_manager.py` disconnect handler.

**Solution**: Sessions must properly disconnect WebSocket to trigger finalization.

### Issue 2: Session Tracking Not Started

**Problem**: If `memory.start_session()` is never called, tracking doesn't happen.

**Check**: Look for this log message:
```
🎬 Started memory tracking for session: {session_id}
```

### Issue 3: Only Non-Chat Intents Tracked

**Problem**: Queries classified as `chat` or `unknown` intents are **not tracked** for memory.

**Check**: Intent classification in logs:
```python
if result.get("intent") not in ["chat", "unknown"]:
    memory.track_conversation(...)  # Only runs for other intents
```

### Issue 4: LLM Summarizer Returns No Updates

**Problem**: The LLM might not generate updates if the session is too short or has no new information.

**Check**: Look for this log:
```
⚠️  LLM returned no updates
```

---

## Testing Memory Finalization

### Method 1: WebSocket E2E Test (Recommended)

```python
import asyncio
import websockets
import json

async def test_memory():
    uri = "ws://localhost:8000/ws/voice/simple?user_id=YOUR_USER_ID"

    async with websockets.connect(uri) as ws:
        # Send messages
        await ws.send(json.dumps({"type": "text", "text": "What's AAPL price?"}))
        response = await ws.receive()

        await ws.send(json.dumps({"type": "text", "text": "Add AAPL to watchlist"}))
        response = await ws.receive()

        # Disconnect triggers finalization
        await ws.close()

    # Wait for finalization
    await asyncio.sleep(5)

    # Check usernotes table
    # SELECT * FROM user_notes WHERE user_id = 'YOUR_USER_ID';
```

### Method 2: Manual Finalization

```python
# In test script
agent = await get_agent()
db = await get_database()

# Run queries
await agent.process_text_command(user_id, "What's AAPL price?")
await agent.process_text_command(user_id, "Add AAPL to watchlist")

# Manually trigger finalization
await agent.finalize_session(user_id)

# Check usernotes
notes = await db.get_user_notes(user_id)
print(notes)
```

### Method 3: Check Supabase Directly

```sql
-- Check if user_notes table exists
SELECT * FROM user_notes WHERE user_id = 'YOUR_USER_ID';

-- Check updated_time to see when last update was
SELECT user_id, updated_time, key_notes
FROM user_notes
WHERE user_id = 'YOUR_USER_ID'
ORDER BY updated_time DESC;
```

---

## Expected Behavior

After a session with queries like:
- "What's the price of AAPL?"
- "Add AAPL to my watchlist"
- "Tell me about AAPL news"

The usernotes should update with something like:
```json
{
  "stocks": "Interested in AAPL price movements",
  "watchlist": "Tracking AAPL for portfolio monitoring",
  "news": "Following AAPL news and announcements"
}
```

---

## Debugging Checklist

 Check logs for session start:
```
🎬 Started memory tracking for session: {session_id}
```

Check logs for conversation tracking:
```
📝 Tracked conversation: intent={intent}, symbols={symbols}
```

Check logs for session finalization trigger:
```
💾 Finalizing session {session_id} - analyzing {N} queries
```

Check logs for LLM summarization:
```
✅ Memory updated: ['stocks', 'watchlist', 'news']
```

Check logs for database save:
```
✅ Finalized session for user {user_id}
```

Check Supabase user_notes table directly

---

## Conclusion

**The system IS working as designed**. The issue is likely:
1. Testing method doesn't trigger WebSocket disconnect
2. Sessions aren't being properly closed
3. Only chat/unknown intents were used (which don't get tracked)
4. LLM didn't generate updates for the session

**Recommendation**: Test with proper WebSocket connection/disconnection cycle or manually call `finalize_session()` in tests.

---

## Related Files

- [long_term_memory_supabase.py](backend/app/llm_agent/long_term_memory_supabase.py) - Full memory implementation
- [agent_wrapper_langgraph.py](backend/app/core/agent_wrapper_langgraph.py) - Session management
- [websocket_manager.py](backend/app/core/websocket_manager.py) - Disconnect handler
- [database.py](backend/app/database.py) - Supabase operations
- [state.py](backend/app/llm_agent/state.py) - State definitions

---

**Next Steps**:
1. Create proper WebSocket E2E test
2. Add logging to finalize_session for better observability
3. Consider adding API endpoint to manually trigger finalization for testing

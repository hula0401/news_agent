# Logging System Integration Guide

**Date**: 2025-11-05
**Status**: ✅ Infrastructure Complete, 🔄 Integration Required

---

## Current State

The project has **TWO logging systems running in parallel**:

### 1. ✅ Agent Logger (JSONL) - ACTIVE

**Location**: [backend/app/llm_agent/logger.py](backend/app/llm_agent/logger.py)

**Output**: `backend/logs/agent/*/YYYYMMDD.jsonl`

**Format**: Machine-readable JSONL (one JSON object per line)

**Status**: ✅ **Fully integrated and working**

**Example**:
```json
{"session_id": "abc123", "timestamp": "2025-11-05T12:34:56", "event": "query_received", "data": {"query": "What's AAPL price?", "query_length": 18}}
{"session_id": "abc123", "timestamp": "2025-11-05T12:34:58", "stage": "intent_analysis", "prompt": "...", "response": "...", "latency_ms": 2000}
```

**Already Logging**:
- ✅ Session start/end
- ✅ LLM calls (intent analysis, response generation)
- ✅ Tool executions
- ✅ Errors

### 2. 🔄 Conversation Logger (Human-Readable) - NOT INTEGRATED

**Location**: [backend/app/utils/conversation_logger.py:314-425](backend/app/utils/conversation_logger.py:314-425)

**Output**: `backend/logs/conversations/chat_YYYYMMDD_HHMMSS.log`

**Format**: Human-readable text with separators

**Status**: 🔄 **Implemented but NOT being called**

**Example** (from old system):
```
================================================================================
LLM QUERY: intent_analyzer (glm-4.5-flash)
================================================================================
Timestamp: 2025-11-05T12:34:56.789012
Status: SUCCESS
Duration: 2861.22ms
Tokens: 1234 prompt + 567 completion = 1801 total

INPUT:
'''
System: You are a market analyst assistant...
User: what's the price of META?
'''

OUTPUT:
'''
{"intents": [{"intent": "price_check", "symbols": ["META"], ...}]}
'''
```

**Methods Implemented**:
- ✅ `log_session_start(session_id, user_id)`
- ✅ `log_llm_call(session_id, node_name, model, prompt, response, duration_ms, status)`
- ✅ `log_tool_call(session_id, tool_name, tool_input, tool_output, duration_ms, status)`

**NOT being called** - Directory exists but is empty.

---

## Why Two Logging Systems?

| Feature | Agent Logger (JSONL) | Conversation Logger (Human) |
|---------|---------------------|----------------------------|
| **Purpose** | Machine analysis, metrics, debugging | Human debugging, understanding |
| **Format** | One JSON per line | Formatted text with separators |
| **Parsing** | Easy programmatic analysis | Easy human reading |
| **Size** | Compact | Verbose |
| **Use Case** | Analytics, monitoring, CI/CD | Development, troubleshooting |

**Both are valuable** and should run in parallel!

---

## Integration Required

The conversation logger needs to be called alongside the existing agent_logger. Here's where to integrate:

### 1. Intent Analyzer Node

**File**: [backend/app/llm_agent/nodes.py:108-250](backend/app/llm_agent/nodes.py:108-250)

**Current Code** (lines 154-160):
```python
# Existing JSONL logging (KEEP THIS)
agent_logger.log_llm_call(
    stage="intent_analysis",
    prompt=full_prompt_text,
    response=response.content,
    model="glm-4.5-flash",
    latency_ms=duration_ms
)
```

**Add After** (new human-readable logging):
```python
# Add human-readable logging
from ...utils.conversation_logger import get_conversation_logger
conv_logger = get_conversation_logger()

# Log session start on first call
if not hasattr(state, '_session_logged'):
    conv_logger.log_session_start(
        session_id=state.thread_id,
        user_id=state.user_id
    )
    state._session_logged = True

# Log LLM call
conv_logger.log_llm_call(
    session_id=state.thread_id,
    node_name="intent_analyzer",
    model="glm-4.5-flash",
    prompt=full_prompt_text,
    response=response.content,
    duration_ms=duration_ms,
    status="SUCCESS" if response else "FAILED"
)
```

### 2. Parallel Fetcher Node

**File**: [backend/app/llm_agent/nodes.py:570-700](backend/app/llm_agent/nodes.py:570-700)

Find where tools are called and add logging:

```python
from ...utils.conversation_logger import get_conversation_logger
conv_logger = get_conversation_logger()

# In the tool execution loop
for api_name, api_func in api_tasks:
    input_params = {...}  # Extract actual params

    start_time = time.time()
    try:
        result = await api_func(**input_params)
        duration_ms = int((time.time() - start_time) * 1000)

        # Existing JSONL logging (KEEP)
        agent_logger.log_tool_call(...)

        # Add human-readable logging
        conv_logger.log_tool_call(
            session_id=state.thread_id,
            tool_name=api_name,
            tool_input=input_params,
            tool_output=result,
            duration_ms=duration_ms,
            status="SUCCESS"
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Log failed call
        conv_logger.log_tool_call(
            session_id=state.thread_id,
            tool_name=api_name,
            tool_input=input_params,
            tool_output=None,
            duration_ms=duration_ms,
            status="FAILED",
            error=str(e)
        )
```

### 3. Response Generator Node

**File**: [backend/app/llm_agent/nodes.py:~1200](backend/app/llm_agent/nodes.py)

Similar to intent analyzer:

```python
from ...utils.conversation_logger import get_conversation_logger
conv_logger = get_conversation_logger()

# Around LLM call
start_time = time.time()
response = await llm.ainvoke(messages)
duration_ms = int((time.time() - start_time) * 1000)

# Existing JSONL logging (KEEP)
agent_logger.log_llm_call(...)

# Add human-readable logging
conv_logger.log_llm_call(
    session_id=state.thread_id,
    node_name="response_generator",
    model="glm-4.5-flash",
    prompt=full_prompt_text,
    response=response.content,
    duration_ms=duration_ms,
    status="SUCCESS"
)
```

### 4. Watchlist Executor Node

**File**: [backend/app/llm_agent/nodes.py:356-450](backend/app/llm_agent/nodes.py:356-450)

```python
from ...utils.conversation_logger import get_conversation_logger
conv_logger = get_conversation_logger()

# Around watchlist operation
start_time = time.time()
try:
    result = await db.update_user_watchlist(...)
    duration_ms = int((time.time() - start_time) * 1000)

    conv_logger.log_tool_call(
        session_id=state.thread_id,
        tool_name="watchlist_update",
        tool_input={"action": action, "symbols": symbols},
        tool_output={"success": True, "watchlist": result},
        duration_ms=duration_ms,
        status="SUCCESS"
    )
except Exception as e:
    duration_ms = int((time.time() - start_time) * 1000)

    conv_logger.log_tool_call(
        session_id=state.thread_id,
        tool_name="watchlist_update",
        tool_input={"action": action, "symbols": symbols},
        tool_output=None,
        duration_ms=duration_ms,
        status="FAILED",
        error=str(e)
    )
```

---

## Testing After Integration

### 1. Run a Query

```bash
# Start backend
make run-server

# Run test
uv run python test_watchlist.py
```

### 2. Check Logs

```bash
# Check JSONL logs (should already exist)
ls -lt backend/logs/agent/llm/
cat backend/logs/agent/llm/$(date +%Y%m%d).jsonl | tail -5

# Check human-readable logs (should NOW be created)
ls -lt backend/logs/conversations/
cat backend/logs/conversations/chat_*.log
```

### 3. Expected Output

You should see a log file like:
```
backend/logs/conversations/chat_20251105_123456.log
```

With content:
```
================================================================================
Chat Session: chat_20251105_123456
Started: 2025-11-05T12:34:56.123456
User ID: 03f6b167-0c4d-4983-a380-54b8eb42f830
================================================================================


================================================================================
LLM QUERY: intent_analyzer (glm-4.5-flash)
================================================================================
Timestamp: 2025-11-05T12:34:57.234567
Status: SUCCESS
Duration: 1234.56ms
Tokens: 0 prompt + 0 completion = 0 total

INPUT:
'''
System: You are a market analyst assistant...
...
'''

OUTPUT:
'''
{"intents": [{"intent": "price_check", "symbols": ["META"]}]}
'''


================================================================================
TOOL EXECUTION: fetch_market_data
================================================================================
Timestamp: 2025-11-05T12:34:58.345678
Status: SUCCESS
Duration: 567.89ms

INPUT:
{
  "symbols": ["META"],
  "timeframe": "1d"
}

OUTPUT:
{
  "META": {
    "price": 640.25,
    "change_percent": 2.06
  }
}
```

---

## Reference Implementation

See the old working system for examples:
- **Old logger**: [hz_langgraph_learning/agent-dev/agent_core/logging_config.py](hz_langgraph_learning/agent-dev/agent_core/logging_config.py)
- **Old nodes with logging**: [hz_langgraph_learning/agent-dev/agent_core/nodes.py:545-568](hz_langgraph_learning/agent-dev/agent_core/nodes.py:545-568)
- **Example log**: [hz_langgraph_learning/agent-dev/logs/chat_20251103_233925.log](hz_langgraph_learning/agent-dev/logs/chat_20251103_233925.log)

---

## Common Issues

### Issue 1: Import Error

```python
# ❌ Wrong
from backend.app.utils.conversation_logger import get_conversation_logger

# ✅ Correct (relative import from nodes.py)
from ...utils.conversation_logger import get_conversation_logger
```

### Issue 2: session_id Not Available

Use `state.thread_id` as the session ID:
```python
conv_logger.log_llm_call(
    session_id=state.thread_id,  # ✅ Use thread_id
    ...
)
```

### Issue 3: Logs Not Appearing

Check:
1. Directory exists: `ls -la backend/logs/conversations/`
2. Permissions: `chmod 755 backend/logs/conversations/`
3. Logger initialized: Check for initialization logs
4. Methods being called: Add print statements

---

## Benefits of Dual Logging

Once integrated, you'll have:

1. **JSONL Logs** (`backend/logs/agent/`) - For:
   - Programmatic analysis
   - Metrics dashboards
   - CI/CD pipelines
   - Error tracking systems

2. **Human Logs** (`backend/logs/conversations/`) - For:
   - Quick debugging
   - Understanding conversation flow
   - Sharing with team members
   - Documentation examples

---

## Next Steps

1. **Integrate Logging** (following examples above)
2. **Test End-to-End**:
   ```bash
   # Run query
   uv run python test_watchlist.py

   # Check both log types
   tail -f backend/logs/agent/llm/$(date +%Y%m%d).jsonl
   tail -f backend/logs/conversations/chat_*.log
   ```
3. **Verify Format**: Compare with old system logs
4. **Document**: Update README with logging locations

---

## Summary

| Component | Status | Location |
|-----------|--------|----------|
| Agent Logger (JSONL) | ✅ Working | backend/logs/agent/ |
| Conversation Logger Infrastructure | ✅ Implemented | conversation_logger.py:314-425 |
| Conversation Logger Integration | 🔄 **TODO** | nodes.py (4 locations) |
| Test Script | ✅ Ready | test_watchlist.py |

**Estimated Integration Time**: 30-60 minutes

**Priority**: Medium-High (valuable for debugging but not blocking functionality)

---

**Reference Files**:
- [conversation_logger.py](backend/app/utils/conversation_logger.py) - Logger implementation
- [nodes.py](backend/app/llm_agent/nodes.py) - Where to integrate
- [Old working example](hz_langgraph_learning/agent-dev/agent_core/nodes.py:545-568)

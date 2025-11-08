# Session-Based Detailed Logging Integration

**Date:** 2025-11-07
**Status:** ✅ Session Logger Created, Integration Pending

---

## Overview

Created a **session-based detailed logger** that writes comprehensive human-readable logs for each conversation session in `logs/agent/session/{session_id}.log`.

This complements the existing JSONL logger:
- **Existing `AgentLogger`**: Structured JSONL logs for analysis (`logs/agent/{sessions,intents,tools,llm}/*.jsonl`)
- **New `SessionLogger`**: Detailed human-readable logs per session (`logs/agent/session/{session_id}.log`)

---

## File Created

### `backend/app/llm_agent/session_logger.py`

Comprehensive session logger with methods:
- `start_session()` - Initialize session log with header
- `log_llm_query()` - Log complete LLM prompts and responses
- `log_tool_call()` - Log tool inputs and outputs
- `log_user_query()` - Log user queries
- `log_agent_response()` - Log final agent responses
- `end_session()` - Write session footer

---

## Integration Steps

### Step 1: Import Session Logger in nodes.py

**File:** `backend/app/llm_agent/nodes.py`

Add import at top (after line 30):
```python
from .session_logger import get_session_logger
```

### Step 2: Get Session Logger Instance

Add near line 32:
```python
session_logger = get_session_logger()
```

### Step 3: Log LLM Query in Intent Analysis Node

**Location:** `analyze_intent` node, after line 154

Add after the existing `agent_logger.log_llm_call()`:
```python
# Also log to session logger
session_logger.log_llm_query(
    session_id=state.thread_id,
    model="glm-4.5-flash",
    prompt=full_prompt_text,
    response=response.content,
    duration_ms=duration_ms,
    stage="intent_analysis"
)
```

### Step 4: Log LLM Query in Response Generator Node

**Location:** `generate_response` node (around line 700-750)

Find where `agent_logger.log_llm_call()` is called and add:
```python
# Also log to session logger
session_logger.log_llm_query(
    session_id=state.thread_id,
    model="glm-4.5-flash",
    prompt=full_prompt_text,
    response=response.content,
    duration_ms=duration_ms,
    stage="summary_generator"
)
```

### Step 5: Log Tool Calls

**Location:** `fetch_data` node (around line 597)

After `agent_logger.log_tool_execution()`, add:
```python
# Also log to session logger
session_logger.log_tool_call(
    session_id=state.thread_id,
    tool_name=api_name,
    input_data=input_params,
    output_data=result,
    duration_ms=execution_time_ms
)
```

### Step 6: Start Session in Agent Wrapper

**File:** `backend/app/core/agent_wrapper_langgraph.py`

**Location:** `process_text_command()` method, after line 107

Replace the existing `agent_logger.start_session()` block with:
```python
# Start both loggers
agent_logger.start_session(
    session_id=session_id,
    user_id=user_id,
    metadata={"source": "text_command"}
)

from ..llm_agent.session_logger import get_session_logger
session_logger = get_session_logger()
session_logger.start_session(
    session_id=session_id,
    user_id=user_id,
    initial_query=query,
    metadata={"source": "text_command"}
)
```

### Step 7: Log User Query

After line 107, add:
```python
# Log user query
session_logger.log_user_query(
    session_id=session_id,
    query=query,
    source="api"
)
```

### Step 8: Log Agent Response

**Location:** After line 140 where response is ready

Add:
```python
# Log agent response
sentiment = result.get("sentiment", "neutral")
key_insights = result.get("key_insights", [])
session_logger.log_agent_response(
    session_id=session_id,
    response=response_text,
    sentiment=sentiment,
    key_insights=key_insights,
    processing_time_ms=processing_time_ms
)
```

### Step 9: End Session (Optional)

**Location:** When session ends (memory finalization or explicit end)

Add:
```python
session_logger.end_session(session_id)
```

---

## Log Format Example

After integration, logs will be written to:
```
backend/logs/agent/session/{session_id}.log
```

With this format:
```
================================================================================
Chat Session: chat_20251107_013456
Started: 2025-11-07T01:34:56.123456
Session ID: ec39a0bd-f5a4-4eb7-bbe5-88b9c0172e76
User ID: 03f6b167-0c4d-4983-a380-54b8eb42f830
Initial Query: what's the p e ratio of meta?
================================================================================


================================================================================
LLM QUERY: glm-4.5-flash (intent_analysis)
================================================================================
Timestamp: 2025-11-07T01:34:58.371758
Status: SUCCESS
Duration: 1825.34ms

INPUT:
'''
System: You are a market analyst assistant...
User: what's the p e ratio of meta?
'''

OUTPUT:
'''
{"intents": [{"intent":"research","symbols":["META"],...}]}
'''
================================================================================


================================================================================
TOOL CALL: parallel_query_research
================================================================================
Timestamp: 2025-11-07T01:35:00.123456
Status: SUCCESS
Duration: 1500.50ms

INPUT:
'''
{
  "query": "what's meta p/e ratio?",
  "checklist_queries": ["META P/E ratio", "META price to earnings"]
}
'''

OUTPUT:
'''
{
  "chunks": 5,
  "sources": [...],
  "confidence": 0.95
}
'''
================================================================================


================================================================================
LLM QUERY: glm-4.5-flash (summary_generator)
================================================================================
Timestamp: 2025-11-07T01:35:02.987654
Status: SUCCESS
Duration: 2150.75ms

INPUT:
'''
System: You are a market analyst...
Web Research Results:
1. META's P/E ratio is 28.5...
'''

OUTPUT:
'''
{"summary":"Meta's P/E ratio is 28.5...","sentiment":"neutral"}
'''
================================================================================


================================================================================
AGENT RESPONSE
================================================================================
Timestamp: 2025-11-07T01:35:03.111222
Total Processing Time: 5500.45ms
Sentiment: neutral
Key Insights:
  - Meta's P/E ratio is 28.5
  - Industry average is 30.2

Response:
Meta's P/E ratio is currently 28.5, which is slightly below the industry average...
================================================================================


================================================================================
SESSION END
================================================================================
Ended: 2025-11-07T01:35:03.222333
Duration: 7.10s
================================================================================
```

---

##Testing

After integration, test with:
```bash
# Start backend
make run-server

# Send a query via API or WebSocket
# Check log file created at:
ls -la backend/logs/agent/session/

# View log
cat backend/logs/agent/session/{session_id}.log
```

---

## Benefits

1. **Complete Session History**: All LLM queries, tool calls, and responses in one place
2. **Human-Readable**: Easy to review and debug
3. **Debugging**: Quickly identify issues in specific sessions
4. **Audit Trail**: Complete record of agent decision-making
5. **Complementary**: Works alongside existing JSONL logs

---

## Current Status

✅ **Completed:**
- Session logger module created
- All logging methods implemented
- Example usage documented

⏳ **Pending:**
- Integration into nodes.py
- Integration into agent_wrapper_langgraph.py
- Testing with live sessions

---

## Related Files

- `backend/app/llm_agent/session_logger.py` - Session logger implementation
- `backend/app/llm_agent/logger.py` - Existing JSONL logger
- `backend/app/llm_agent/nodes.py` - LangGraph nodes (needs integration)
- `backend/app/core/agent_wrapper_langgraph.py` - Agent wrapper (needs integration)

---

**Next Steps:** Complete integration following the steps above, then test with a live query to verify log format matches requirements.

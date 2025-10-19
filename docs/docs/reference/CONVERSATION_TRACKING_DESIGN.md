# Conversation Tracking Design & Trade-offs

**Version**: 1.0
**Date**: 2025-10-18
**Status**: 🔄 Design Recommendation

---

## 🐛 Current Issues

### Issue 1: Missing `loguru` Dependency ✅ FIXED
**Status**: Resolved by installing `loguru` package

### Issue 2: Scheduler Import Errors ✅ FIXED
**Status**: Resolved with `loguru` installation

### Issue 3: `conversation_messages` Not Updated 🔴 NEEDS FIX
**Problem**: Messages are not automatically saved to database after each conversation turn

**Current State**:
```python
# WebSocket conversation happens
User: "Tell me the news"
Agent: [Streams audio response]
# ❌ No database insert occurs
```

### Issue 4: `conversation_sessions` Lifecycle Issues 🔴 NEEDS FIX
**Problems**:
1. `session_end` is never updated (remains NULL)
2. `is_active` remains TRUE forever
3. No way to track session duration or completion

**Current State**:
```sql
-- All sessions look like this:
id | user_id | session_start | session_end | is_active
1  | user123 | 2025-10-18... | NULL        | TRUE
2  | user456 | 2025-10-18... | NULL        | TRUE
3  | user789 | 2025-10-18... | NULL        | TRUE
```

---

## 🎯 Design Goals

1. **Automatic Tracking**: Messages saved without manual intervention
2. **Session Lifecycle**: Clear start/end times and active state
3. **Performance**: Minimal impact on WebSocket streaming
4. **Reliability**: Handle disconnections and errors gracefully
5. **Scalability**: Work with multiple concurrent users

---

## 📋 Solution Options

### Option A: Synchronous Database Writes (Simple but Slow)

**Description**: Write to database immediately after each message exchange

```python
@websocket_manager
async def handle_voice_data(websocket, data):
    # 1. Process user audio
    user_text = await transcribe(audio)

    # 2. Save user message to DB (BLOCKS streaming)
    await db.insert_message({
        "session_id": session_id,
        "role": "user",
        "content": user_text,
        "created_at": datetime.now()
    })

    # 3. Generate response
    agent_response = await agent.generate(user_text)

    # 4. Save agent message to DB (BLOCKS streaming)
    await db.insert_message({
        "session_id": session_id,
        "role": "agent",
        "content": agent_response,
        "created_at": datetime.now()
    })

    # 5. Stream audio
    await stream_audio(agent_response)
```

**Pros**:
- ✅ Simple to implement
- ✅ Guaranteed consistency (message always saved)
- ✅ Easy to debug
- ✅ No risk of data loss

**Cons**:
- ❌ Blocks WebSocket streaming (200-500ms delay per message)
- ❌ Impacts user experience (noticeable lag)
- ❌ Database becomes bottleneck
- ❌ Cannot handle database downtime

**Trade-offs**:
- **Reliability**: HIGH ✅
- **Performance**: LOW ❌
- **User Experience**: POOR ❌
- **Complexity**: LOW ✅

**Recommendation**: ❌ **NOT RECOMMENDED** for real-time voice app

---

### Option B: Asynchronous Background Tasks (Balanced)

**Description**: Queue messages for background processing, stream immediately

```python
from asyncio import Queue

message_queue = Queue()

@websocket_manager
async def handle_voice_data(websocket, data):
    # 1. Process user audio
    user_text = await transcribe(audio)

    # 2. Queue user message (NON-BLOCKING, ~1ms)
    await message_queue.put({
        "session_id": session_id,
        "role": "user",
        "content": user_text,
        "created_at": datetime.now()
    })

    # 3. Generate and stream response IMMEDIATELY
    agent_response = await agent.generate(user_text)
    await stream_audio(agent_response)

    # 4. Queue agent message (NON-BLOCKING, ~1ms)
    await message_queue.put({
        "session_id": session_id,
        "role": "agent",
        "content": agent_response,
        "created_at": datetime.now()
    })

# Background worker (runs in separate task)
async def message_worker():
    while True:
        message = await message_queue.get()
        try:
            await db.insert_message(message)
        except Exception as e:
            # Log error, maybe retry
            logger.error(f"Failed to save message: {e}")
```

**Pros**:
- ✅ Zero impact on WebSocket streaming
- ✅ Better user experience (no lag)
- ✅ Handles database slowness gracefully
- ✅ Can batch writes for efficiency

**Cons**:
- ⚠️ Messages may be lost if server crashes before queue is processed
- ⚠️ Slightly more complex to implement
- ⚠️ Need to monitor queue depth

**Trade-offs**:
- **Reliability**: MEDIUM-HIGH ✅ (99.9% with good error handling)
- **Performance**: HIGH ✅
- **User Experience**: EXCELLENT ✅
- **Complexity**: MEDIUM ⚠️

**Recommendation**: ✅ **RECOMMENDED** - Best balance

---

### Option C: Fire-and-Forget with asyncio.create_task (Fastest)

**Description**: Launch database writes as background tasks, don't wait for completion

```python
@websocket_manager
async def handle_voice_data(websocket, data):
    # 1. Process user audio
    user_text = await transcribe(audio)

    # 2. Fire-and-forget save (NON-BLOCKING)
    asyncio.create_task(save_message({
        "session_id": session_id,
        "role": "user",
        "content": user_text
    }))

    # 3. Stream immediately
    agent_response = await agent.generate(user_text)
    await stream_audio(agent_response)

    # 4. Fire-and-forget save
    asyncio.create_task(save_message({
        "session_id": session_id,
        "role": "agent",
        "content": agent_response
    }))

async def save_message(message_data):
    try:
        await db.insert_message(message_data)
    except Exception as e:
        logger.error(f"Failed to save: {e}")
        # Could implement retry logic here
```

**Pros**:
- ✅ Absolute zero blocking
- ✅ Simplest code
- ✅ Fastest performance

**Cons**:
- ❌ No visibility into task completion
- ❌ Hard to track failures
- ❌ Messages can be lost silently
- ❌ No retry mechanism

**Trade-offs**:
- **Reliability**: MEDIUM ⚠️ (95% without retries)
- **Performance**: HIGHEST ✅
- **User Experience**: EXCELLENT ✅
- **Complexity**: LOW ✅

**Recommendation**: ⚠️ **USE WITH CAUTION** - Good for non-critical data

---

### Option D: Hybrid (In-Memory Cache + Periodic Flush)

**Description**: Store messages in memory, flush to database periodically or on session end

```python
# In-memory message buffer
session_buffers = {}

@websocket_manager
async def handle_voice_data(websocket, data):
    session_id = get_session_id()

    # Initialize buffer if needed
    if session_id not in session_buffers:
        session_buffers[session_id] = []

    # 1. Process and buffer user message (instant)
    user_text = await transcribe(audio)
    session_buffers[session_id].append({
        "role": "user",
        "content": user_text,
        "created_at": datetime.now()
    })

    # 2. Generate response
    agent_response = await agent.generate(user_text)
    session_buffers[session_id].append({
        "role": "agent",
        "content": agent_response,
        "created_at": datetime.now()
    })

    # 3. Stream immediately
    await stream_audio(agent_response)

    # 4. Flush to DB if buffer is large enough (batch write)
    if len(session_buffers[session_id]) >= 10:
        await flush_to_database(session_id)

@websocket_manager
async def on_disconnect(session_id):
    # Flush remaining messages on disconnect
    await flush_to_database(session_id)
    del session_buffers[session_id]

# Background periodic flush (every 30 seconds)
async def periodic_flush():
    while True:
        await asyncio.sleep(30)
        for session_id in list(session_buffers.keys()):
            if session_buffers[session_id]:
                await flush_to_database(session_id)
```

**Pros**:
- ✅ Zero latency during conversation
- ✅ Batch writes = better database performance
- ✅ Messages saved on disconnect
- ✅ Can recover from transient DB failures

**Cons**:
- ⚠️ Messages lost if server crashes before flush
- ⚠️ Memory usage grows with concurrent sessions
- ⚠️ Complex state management

**Trade-offs**:
- **Reliability**: MEDIUM-HIGH ✅ (99% with periodic flush)
- **Performance**: HIGHEST ✅
- **User Experience**: EXCELLENT ✅
- **Complexity**: HIGH ❌

**Recommendation**: ✅ **RECOMMENDED** for high-concurrency scenarios

---

## 🏆 Final Recommendation: Option B (Background Queue)

### Why Option B?

1. **Best Balance**: High reliability (99.9%) + excellent performance
2. **Proven Pattern**: Used by production systems (Discord, Slack, etc.)
3. **Graceful Degradation**: Handles DB issues without affecting users
4. **Observable**: Easy to monitor queue depth and success rate
5. **Recoverable**: Can implement retry logic and dead-letter queues

### Implementation Plan

```python
# backend/app/core/conversation_tracker.py
import asyncio
from typing import Optional, Dict, Any, List
from asyncio import Queue
from datetime import datetime
from loguru import logger
from ..database import db_manager

class ConversationTracker:
    """
    Tracks conversation messages and session lifecycle.

    Features:
    - Async queue for non-blocking message saves
    - Background worker for database writes
    - Session lifecycle management (start/end/active)
    - Automatic retry on failures
    """

    def __init__(self):
        self.message_queue: Queue = Queue(maxsize=10000)
        self.session_states: Dict[str, Dict[str, Any]] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    def start(self):
        """Start background worker."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("✅ Conversation tracker started")

    async def stop(self):
        """Stop background worker gracefully."""
        self._running = False
        if self._worker_task:
            await self._worker_task

        # Flush remaining messages
        await self._flush_queue()
        logger.info("✅ Conversation tracker stopped")

    async def track_message(
        self,
        session_id: str,
        role: str,
        content: str,
        audio_url: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Track a conversation message (non-blocking).

        Args:
            session_id: Conversation session ID
            role: "user" or "agent"
            content: Message text
            audio_url: Optional audio URL
            metadata: Optional metadata dict
        """
        message = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "audio_url": audio_url,
            "metadata": metadata,
            "created_at": datetime.utcnow()
        }

        try:
            # Non-blocking queue put (~1ms)
            self.message_queue.put_nowait(message)
            logger.debug(f"📝 Queued {role} message for session {session_id}")
        except asyncio.QueueFull:
            logger.error(f"❌ Message queue full! Dropping message for {session_id}")
            # Could implement overflow handling here

    async def start_session(
        self,
        session_id: str,
        user_id: str,
        metadata: Optional[Dict] = None
    ):
        """
        Start a new conversation session.

        Args:
            session_id: Unique session ID
            user_id: User ID
            metadata: Optional metadata
        """
        self.session_states[session_id] = {
            "user_id": user_id,
            "session_start": datetime.utcnow(),
            "is_active": True,
            "message_count": 0,
            "metadata": metadata or {}
        }

        # Save to database
        try:
            await db_manager.client.table("conversation_sessions").insert({
                "id": session_id,
                "user_id": user_id,
                "session_start": datetime.utcnow().isoformat(),
                "is_active": True,
                "metadata": metadata
            }).execute()

            logger.info(f"✅ Started session {session_id} for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to save session start: {e}")

    async def end_session(self, session_id: str):
        """
        End a conversation session.

        Args:
            session_id: Session ID to end
        """
        if session_id not in self.session_states:
            logger.warning(f"⚠️ Session {session_id} not found in state")
            return

        # Update state
        self.session_states[session_id]["is_active"] = False
        session_end = datetime.utcnow()

        # Calculate duration
        session_start = self.session_states[session_id]["session_start"]
        duration_seconds = (session_end - session_start).total_seconds()

        # Update database
        try:
            await db_manager.client.table("conversation_sessions").update({
                "session_end": session_end.isoformat(),
                "is_active": False,
                "duration_seconds": duration_seconds
            }).eq("id", session_id).execute()

            logger.info(
                f"✅ Ended session {session_id} "
                f"(duration: {duration_seconds:.1f}s, "
                f"messages: {self.session_states[session_id]['message_count']})"
            )

            # Cleanup state (keep for a bit for late messages)
            await asyncio.sleep(60)  # 1 minute grace period
            del self.session_states[session_id]

        except Exception as e:
            logger.error(f"❌ Failed to save session end: {e}")

    async def _worker(self):
        """Background worker that processes message queue."""
        logger.info("🔄 Message worker started")

        while self._running:
            try:
                # Get message from queue (wait up to 1 second)
                try:
                    message = await asyncio.wait_for(
                        self.message_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Save to database with retry
                await self._save_message_with_retry(message)

                # Update session message count
                session_id = message["session_id"]
                if session_id in self.session_states:
                    self.session_states[session_id]["message_count"] += 1

            except Exception as e:
                logger.error(f"❌ Worker error: {e}")

        logger.info("🛑 Message worker stopped")

    async def _save_message_with_retry(
        self,
        message: Dict[str, Any],
        max_retries: int = 3
    ):
        """Save message to database with retry logic."""
        for attempt in range(max_retries):
            try:
                await db_manager.client.table("conversation_messages").insert({
                    "session_id": message["session_id"],
                    "role": message["role"],
                    "content": message["content"],
                    "audio_url": message.get("audio_url"),
                    "metadata": message.get("metadata"),
                    "created_at": message["created_at"].isoformat()
                }).execute()

                logger.debug(
                    f"✅ Saved {message['role']} message "
                    f"for session {message['session_id']}"
                )
                return  # Success!

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"⚠️ Save failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"❌ Failed to save message after {max_retries} attempts: {e}"
                    )
                    # Could write to dead-letter queue here

    async def _flush_queue(self):
        """Flush remaining messages in queue."""
        logger.info("🔄 Flushing message queue...")
        count = 0

        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                await self._save_message_with_retry(message)
                count += 1
            except Exception as e:
                logger.error(f"❌ Error flushing message: {e}")

        logger.info(f"✅ Flushed {count} messages")

    def get_queue_depth(self) -> int:
        """Get current queue depth for monitoring."""
        return self.message_queue.qsize()

    def get_active_sessions(self) -> int:
        """Get number of active sessions."""
        return sum(
            1 for state in self.session_states.values()
            if state["is_active"]
        )


# Global instance
_conversation_tracker: Optional[ConversationTracker] = None


def get_conversation_tracker() -> ConversationTracker:
    """Get or create conversation tracker instance."""
    global _conversation_tracker

    if _conversation_tracker is None:
        _conversation_tracker = ConversationTracker()
        _conversation_tracker.start()
        logger.info("✅ Conversation tracker initialized")

    return _conversation_tracker
```

---

## 🔌 Integration Points

### 1. WebSocket Handler Integration

```python
# backend/app/core/websocket_manager.py

from .conversation_tracker import get_conversation_tracker

class WebSocketManager:
    def __init__(self):
        self.conversation_tracker = get_conversation_tracker()

    async def handle_connection(self, websocket, user_id):
        session_id = str(uuid.uuid4())

        # Start session tracking
        await self.conversation_tracker.start_session(
            session_id=session_id,
            user_id=user_id,
            metadata={"client_ip": websocket.client.host}
        )

        try:
            # Handle conversation...
            pass
        finally:
            # End session on disconnect
            await self.conversation_tracker.end_session(session_id)

    async def handle_voice_data(self, session_id, audio_data):
        # 1. Transcribe
        user_text = await self.asr.transcribe(audio_data)

        # 2. Track user message (non-blocking, ~1ms)
        await self.conversation_tracker.track_message(
            session_id=session_id,
            role="user",
            content=user_text,
            audio_url=None
        )

        # 3. Generate response
        agent_response = await self.agent.generate(user_text)

        # 4. Track agent message (non-blocking, ~1ms)
        await self.conversation_tracker.track_message(
            session_id=session_id,
            role="agent",
            content=agent_response,
            audio_url=audio_url if audio_url else None
        )

        # 5. Stream audio (no delay!)
        await self.stream_audio(agent_response)
```

### 2. FastAPI Lifecycle Integration

```python
# backend/app/main.py

from .core.conversation_tracker import get_conversation_tracker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    conversation_tracker = get_conversation_tracker()
    conversation_tracker.start()

    yield

    # Shutdown
    await conversation_tracker.stop()  # Graceful shutdown
```

---

## 📊 Monitoring and Observability

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    tracker = get_conversation_tracker()

    return {
        "status": "healthy",
        "conversation_tracker": {
            "queue_depth": tracker.get_queue_depth(),
            "active_sessions": tracker.get_active_sessions(),
            "queue_limit": 10000
        }
    }
```

### Metrics to Monitor

1. **Queue Depth**: Should stay < 100 under normal load
2. **Save Success Rate**: Should be > 99.5%
3. **Average Queue Time**: Should be < 1 second
4. **Active Sessions**: Track concurrent users

---

## 🔄 Migration Strategy

### Phase 1: Add Conversation Tracker (Week 1)
1. Create `conversation_tracker.py`
2. Integrate with WebSocket manager
3. Test with existing sessions

### Phase 2: Database Schema Updates (Week 1)
```sql
-- Add duration_seconds column
ALTER TABLE conversation_sessions
ADD COLUMN duration_seconds DECIMAL(10, 2);

-- Add index for active sessions
CREATE INDEX idx_active_sessions
ON conversation_sessions(is_active, session_start DESC)
WHERE is_active = true;
```

### Phase 3: Monitoring & Alerts (Week 2)
1. Add health check endpoint
2. Set up alerts for queue depth > 1000
3. Monitor save success rate

---

## 📋 Summary Table

| Solution | Reliability | Performance | UX | Complexity | Recommendation |
|----------|------------|-------------|----|-----------:|----------------|
| **A: Synchronous** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐ | ⭐⭐ | ❌ Not Recommended |
| **B: Background Queue** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ **RECOMMENDED** |
| **C: Fire-and-Forget** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⚠️ Use with Caution |
| **D: In-Memory Cache** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ For High Concurrency |

---

## 🎯 Recommendations

### For Your Use Case (Voice News Agent):

**Primary**: **Option B (Background Queue)**
- ✅ Best for moderate concurrency (10-100 users)
- ✅ Excellent reliability without sacrificing performance
- ✅ Easy to monitor and debug

**Alternative**: **Option D (Hybrid)** if you expect:
- 100+ concurrent users
- High message frequency (>10 msg/sec per session)
- Need to minimize database write operations

### Quick Wins:

1. **Fix loguru**: ✅ Already done
2. **Add conversation tracker**: Implement Option B
3. **Update WebSocket manager**: Integrate tracking calls
4. **Add session lifecycle**: Start/end session hooks
5. **Monitor queue**: Add health check endpoint

---

**Status**: 📝 Design Complete - Ready for Implementation
**Estimated Implementation**: 1-2 days
**Estimated Testing**: 1 day

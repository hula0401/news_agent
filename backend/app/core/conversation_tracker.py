"""
Conversation tracking with async background queue.

This module provides non-blocking message tracking and session lifecycle management
for real-time voice conversations.

Features:
- Async queue for zero-latency message saves
- Background worker with retry logic
- Session lifecycle management (start/end/active)
- Graceful shutdown with queue flush
"""
import asyncio
from typing import Optional, Dict, Any
from asyncio import Queue
from datetime import datetime
from loguru import logger
from ..database import db_manager


class ConversationTracker:
    """
    Tracks conversation messages and session lifecycle.

    Design: Background Queue (Option B)
    - Non-blocking queue puts (<1ms)
    - Background worker processes queue
    - Retry logic for reliability (99.9%)
    - Graceful shutdown with flush
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
            try:
                self._worker_task = asyncio.create_task(self._worker())
                logger.info("✅ Conversation tracker started")
            except RuntimeError:
                # No event loop running (likely during tests)
                logger.warning("⚠️ No event loop available, conversation tracker will start lazily")
                self._running = False

    async def stop(self):
        """Stop background worker gracefully."""
        logger.info("🛑 Stopping conversation tracker...")
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

        This method adds the message to a queue and returns immediately (~1ms).
        The background worker will save it to the database.

        Args:
            session_id: Conversation session ID
            role: "user" or "assistant"
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
            logger.debug(f"📝 Queued {role} message for session {session_id[:8]}...")
        except asyncio.QueueFull:
            logger.error(
                f"❌ Message queue full! Queue depth: {self.message_queue.qsize()}. "
                f"Dropping message for session {session_id}"
            )
            # In production, could write to dead-letter queue or disk

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
            metadata: Optional metadata (e.g., client_ip, device)
        """
        self.session_states[session_id] = {
            "user_id": user_id,
            "session_start": datetime.utcnow(),
            "is_active": True,
            "message_count": 0,
            "metadata": metadata or {},
            "discussed_news": [],  # Track news discussed in this session
            "discussed_stocks": set()  # Track stock symbols mentioned
        }

        # Save to database
        try:
            if not db_manager._initialized:
                await db_manager.initialize()

            # Supabase Python client execute() is synchronous, run in thread
            def _insert():
                return db_manager.client.table("conversation_sessions").insert({
                    "session_id": session_id,
                    "user_id": user_id,
                    "session_start": datetime.utcnow().isoformat(),  # DB column is session_start
                    "started_at": datetime.utcnow().isoformat(),  # Also set alias
                    "is_active": True,
                    "metadata": metadata or {}
                }).execute()

            result = await asyncio.to_thread(_insert)

            # CRITICAL: Store the database id (used for FK in messages table)
            if result.data and len(result.data) > 0:
                db_id = result.data[0]['id']
                self.session_states[session_id]["db_id"] = db_id
                logger.info(f"✅ Started session {session_id[:8]}... (db_id={db_id[:8]}...) for user {user_id}")
            else:
                logger.error(f"❌ Session created but no id returned")
        except Exception as e:
            logger.error(f"❌ Failed to save session start: {e}")

    async def end_session(self, session_id: str):
        """
        End a conversation session.

        Updates session_end, is_active=False, and calculates duration.

        Args:
            session_id: Session ID to end
        """
        if session_id not in self.session_states:
            logger.warning(f"⚠️ Session {session_id[:8]}... not found in state")
            return

        # Update state
        self.session_states[session_id]["is_active"] = False
        session_end = datetime.utcnow()

        # Calculate duration
        session_start = self.session_states[session_id]["session_start"]
        duration_seconds = (session_end - session_start).total_seconds()
        message_count = self.session_states[session_id]["message_count"]

        # Update database
        try:
            if not db_manager._initialized:
                await db_manager.initialize()

            # Debug: Check if session exists before updating
            def _check():
                return db_manager.client.table("conversation_sessions").select("id, session_id").eq("session_id", session_id).execute()

            check_result = await asyncio.to_thread(_check)
            logger.debug(f"Session check before update: found {len(check_result.data) if check_result.data else 0} rows for session_id={session_id[:8]}...")

            def _update():
                return db_manager.client.table("conversation_sessions").update({
                    "session_end": session_end.isoformat(),  # DB column is session_end
                    "ended_at": session_end.isoformat(),  # Also set alias
                    "is_active": False,
                    "duration_seconds": duration_seconds
                }).eq("session_id", session_id).execute()

            result = await asyncio.to_thread(_update)

            # Check if update succeeded
            if result.data and len(result.data) > 0:
                logger.info(
                    f"✅ Ended session {session_id[:8]}... "
                    f"(duration: {duration_seconds:.1f}s, messages: {message_count})"
                )

                # Save discussed news (Option A: Session-based tracking)
                await self._save_discussed_news(session_id)
            else:
                logger.error(
                    f"❌ Failed to update session end: No rows affected for session_id={session_id[:8]}... "
                    f"Update result: {result.data}"
                )

            # Cleanup state after grace period (for late messages)
            asyncio.create_task(self._cleanup_session_state(session_id, delay=60))

        except Exception as e:
            logger.error(f"❌ Failed to save session end: {e}")

    async def _cleanup_session_state(self, session_id: str, delay: int = 60):
        """Clean up session state after delay (allows late messages)."""
        await asyncio.sleep(delay)
        if session_id in self.session_states:
            del self.session_states[session_id]
            logger.debug(f"🧹 Cleaned up session state for {session_id[:8]}...")

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
        """
        Save message to database with exponential backoff retry.

        Args:
            message: Message data dict
            max_retries: Maximum retry attempts (default: 3)
        """
        for attempt in range(max_retries):
            try:
                if not db_manager._initialized:
                    await db_manager.initialize()

                # Get user_id and db_id from session state
                session_id = message["session_id"]
                user_id = None
                db_id = None  # FK references conversation_sessions.id, not session_id
                if session_id in self.session_states:
                    user_id = self.session_states[session_id].get("user_id")
                    db_id = self.session_states[session_id].get("db_id")

                if not db_id:
                    logger.error(f"❌ Cannot save message: db_id not found for session {session_id[:8]}...")
                    return

                def _insert_message():
                    return db_manager.client.table("conversation_messages").insert({
                        "session_id": db_id,  # FK points to conversation_sessions.id
                        "user_id": user_id,  # Include user_id from session
                        "role": message["role"],
                        "content": message["content"],
                        "audio_url": message.get("audio_url"),
                        "metadata": message.get("metadata"),
                        "created_at": message["created_at"].isoformat()
                    }).execute()

                await asyncio.to_thread(_insert_message)

                logger.debug(
                    f"✅ Saved {message['role']} message "
                    f"for session {message['session_id'][:8]}..."
                )
                return  # Success!

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
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
        """Flush remaining messages in queue on shutdown."""
        logger.info("🔄 Flushing message queue...")
        count = 0

        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                await self._save_message_with_retry(message)
                count += 1
            except Exception as e:
                logger.error(f"❌ Error flushing message: {e}")

        if count > 0:
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

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics for monitoring."""
        return {
            "queue_depth": self.get_queue_depth(),
            "queue_max_size": self.message_queue.maxsize,
            "active_sessions": self.get_active_sessions(),
            "total_sessions": len(self.session_states),
            "worker_running": self._running
        }

    def track_discussed_news(
        self,
        session_id: str,
        stock_symbol: str,
        news_title: str,
        news_url: Optional[str] = None,
        news_source: Optional[str] = None,
        published_at: Optional[str] = None
    ):
        """
        Track news article discussed in conversation (Option A: Session-based).

        Args:
            session_id: Session ID
            stock_symbol: Stock symbol (e.g., "TSLA")
            news_title: News article title
            news_url: Optional news URL
            news_source: Optional news source
            published_at: Optional publication timestamp
        """
        if session_id not in self.session_states:
            logger.warning(f"⚠️ Cannot track news: session {session_id[:8]}... not found")
            return

        # Add to discussed_news list
        news_item = {
            "stock_symbol": stock_symbol.upper(),
            "title": news_title,
            "url": news_url,
            "source": news_source,
            "published_at": published_at,
            "discussed_at": datetime.utcnow().isoformat()
        }

        self.session_states[session_id]["discussed_news"].append(news_item)
        self.session_states[session_id]["discussed_stocks"].add(stock_symbol.upper())

        logger.info(
            f"📰 Tracked news for {stock_symbol} in session {session_id[:8]}... "
            f"(total: {len(self.session_states[session_id]['discussed_news'])})"
        )

    async def _save_discussed_news(self, session_id: str):
        """
        Save all discussed news for a session to database.

        Called during end_session() to persist news discussed during conversation.

        Args:
            session_id: Session ID
        """
        if session_id not in self.session_states:
            return

        discussed_news = self.session_states[session_id].get("discussed_news", [])

        if not discussed_news:
            logger.debug(f"No news discussed in session {session_id[:8]}...")
            return

        try:
            if not db_manager._initialized:
                await db_manager.initialize()

            # Get database id for FK
            db_id = self.session_states[session_id].get("db_id")
            if not db_id:
                logger.error(f"❌ Cannot save news: db_id not found for session {session_id[:8]}...")
                return

            # Save each news item with session link
            for news in discussed_news:
                def _insert_news():
                    return db_manager.client.table("session_news").insert({
                        "session_id": db_id,  # FK to conversation_sessions.id
                        "stock_symbol": news["stock_symbol"],
                        "news_title": news["title"],
                        "news_url": news.get("url"),
                        "news_source": news.get("source"),
                        "published_at": news.get("published_at"),
                        "discussed_at": news["discussed_at"]
                    }).execute()

                try:
                    await asyncio.to_thread(_insert_news)
                except Exception as e:
                    logger.error(f"❌ Failed to save news item: {e}")
                    # Continue with other items

            logger.info(
                f"✅ Saved {len(discussed_news)} news items for session {session_id[:8]}... "
                f"(stocks: {', '.join(self.session_states[session_id]['discussed_stocks'])})"
            )

        except Exception as e:
            logger.error(f"❌ Failed to save discussed news: {e}")


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

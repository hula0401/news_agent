"""
Heartbeat-based session lifecycle monitor.

This module provides a background task that:
1. Runs every 60 seconds
2. Finds sessions with no heartbeat for >100s
3. Marks those sessions as inactive (is_active=False)
4. Updates session_end timestamp and duration
"""
import asyncio
from datetime import datetime
from typing import Optional
from loguru import logger
from ..database import db_manager


class HeartbeatMonitor:
    """Monitor for marking stale sessions as inactive based on heartbeat timeout."""

    def __init__(self, check_interval: int = 60, timeout_seconds: int = 100):
        """
        Initialize heartbeat monitor.

        Args:
            check_interval: How often to check for stale sessions (default: 60s)
            timeout_seconds: Mark session inactive if no heartbeat for this long (default: 100s)
        """
        self.check_interval = check_interval
        self.timeout_seconds = timeout_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    def start(self):
        """Start the heartbeat monitor background task."""
        if not self._running:
            self._running = True
            try:
                self._task = asyncio.create_task(self._monitor_loop())
                logger.info(
                    f"✅ Heartbeat monitor started "
                    f"(check_interval={self.check_interval}s, timeout={self.timeout_seconds}s)"
                )
            except RuntimeError:
                # No event loop running (likely during tests)
                logger.warning("⚠️ No event loop available, heartbeat monitor will start lazily")
                self._running = False

    async def stop(self):
        """Stop the heartbeat monitor gracefully."""
        logger.info("🛑 Stopping heartbeat monitor...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("✅ Heartbeat monitor stopped")

    async def _monitor_loop(self):
        """Background loop that checks for stale sessions."""
        logger.info("🔄 Heartbeat monitor loop started")

        while self._running:
            try:
                # Wait for check interval
                await asyncio.sleep(self.check_interval)

                # Check and close stale sessions
                await self._check_stale_sessions()

            except asyncio.CancelledError:
                logger.info("🛑 Heartbeat monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Heartbeat monitor error: {e}")
                # Continue running despite errors

        logger.info("🛑 Heartbeat monitor loop stopped")

    async def _check_stale_sessions(self):
        """Find and mark stale sessions as inactive."""
        try:
            if not db_manager._initialized:
                await db_manager.initialize()

            # Find sessions that are active but have stale heartbeats
            # Use retry logic with exponential backoff for transient connection errors
            max_retries = 3
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    def _find_stale():
                        return db_manager.client.table("conversation_sessions").select(
                            "id, session_id, user_id, session_start, last_heartbeat_at"
                        ).eq("is_active", True).execute()

                    result = await asyncio.to_thread(_find_stale)
                    break  # Success
                except Exception as db_error:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ DB query failed (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s: {db_error}")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise  # Re-raise on final attempt

            if not result.data:
                return

            # Filter for sessions with heartbeat timeout (>100s)
            now = datetime.utcnow()
            stale_sessions = []

            for session in result.data:
                last_heartbeat = session.get("last_heartbeat_at")
                if not last_heartbeat:
                    continue

                # Parse ISO timestamp
                last_heartbeat_dt = datetime.fromisoformat(last_heartbeat.replace("Z", "+00:00"))
                seconds_since_heartbeat = (now - last_heartbeat_dt).total_seconds()

                if seconds_since_heartbeat > self.timeout_seconds:
                    stale_sessions.append({
                        "session_id": session["session_id"],
                        "user_id": session["user_id"],
                        "session_start": session["session_start"],
                        "seconds_stale": seconds_since_heartbeat
                    })

            if not stale_sessions:
                logger.debug("💓 All active sessions have recent heartbeats")
                return

            # Mark stale sessions as inactive
            for session in stale_sessions:
                await self._close_stale_session(session)

            logger.info(
                f"💤 Marked {len(stale_sessions)} stale sessions as inactive "
                f"(no heartbeat for >{self.timeout_seconds}s)"
            )

        except Exception as e:
            logger.error(f"❌ Failed to check stale sessions: {e}")

    async def _close_stale_session(self, session_info: dict):
        """
        Mark a single stale session as inactive.

        Args:
            session_info: Dict with session_id, user_id, session_start, seconds_stale
        """
        try:
            session_id = session_info["session_id"]
            session_start = datetime.fromisoformat(
                session_info["session_start"].replace("Z", "+00:00")
            )
            session_end = datetime.utcnow()
            duration_seconds = (session_end - session_start).total_seconds()

            # Retry update with exponential backoff
            max_retries = 3
            retry_delay = 1.0

            for attempt in range(max_retries):
                try:
                    def _update():
                        return db_manager.client.table("conversation_sessions").update({
                            "is_active": False,
                            "session_end": session_end.isoformat(),
                            "ended_at": session_end.isoformat(),
                            "duration_seconds": duration_seconds
                        }).eq("session_id", session_id).execute()

                    await asyncio.to_thread(_update)
                    break  # Success
                except Exception as db_error:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ DB update failed for {session_id[:8]}... (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        raise  # Re-raise on final attempt

            logger.info(
                f"💤 Closed stale session {session_id[:8]}... "
                f"(stale for {session_info['seconds_stale']:.0f}s, duration: {duration_seconds:.1f}s)"
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to close stale session {session_info['session_id'][:8]}...: {e}"
            )


# Global instance
_heartbeat_monitor: Optional[HeartbeatMonitor] = None


def get_heartbeat_monitor() -> HeartbeatMonitor:
    """Get or create heartbeat monitor instance."""
    global _heartbeat_monitor

    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor(
            check_interval=60,  # Check every 60s
            timeout_seconds=100  # Mark inactive after 100s
        )
        logger.info("✅ Heartbeat monitor initialized")

    return _heartbeat_monitor

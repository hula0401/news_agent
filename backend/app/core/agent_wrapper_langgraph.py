"""
LangGraph Agent Wrapper for Backend Integration.

This wrapper integrates the LangGraph-based market agent with the backend,
providing a clean interface for processing queries while maintaining
ASR and TTS functionality.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class LangGraphAgentWrapper:
    """Wrapper for LangGraph market agent with database and cache integration."""

    def __init__(self):
        self.graph = None
        self.db = None
        self.cache = None
        self._initialized = False
        self.user_memories: Dict[str, Any] = {}  # user_id -> LongTermMemory instance
        self.session_chat_history: Dict[str, List] = {}  # session_id -> List[ChatMessage]

    async def initialize(self):
        """Initialize the agent wrapper with database, cache, and graph."""
        if self._initialized:
            return

        try:
            # Import here to avoid circular dependencies
            from ..database import get_database
            from ..cache import get_cache
            from ..llm_agent.graph import compile_graph

            # Initialize database and cache
            self.db = await get_database()
            self.cache = await get_cache()

            # Initialize LangGraph agent
            self.graph = compile_graph()

            self._initialized = True
            logger.info("✅ LangGraph agent wrapper initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize LangGraph agent wrapper: {e}", exc_info=True)
            raise

    async def _get_memory_for_user(self, user_id: str):
        """Get or create memory instance for user.

        Args:
            user_id: User UUID

        Returns:
            LongTermMemory instance
        """
        from ..llm_agent.long_term_memory_supabase import get_memory_for_user

        if user_id not in self.user_memories:
            memory = await get_memory_for_user(user_id)
            self.user_memories[user_id] = memory
            logger.info(f"✅ Created memory instance for user {user_id[:8]}...")

        return self.user_memories[user_id]

    async def process_text_command(
        self,
        user_id: str,
        query: str,
        session_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Process a text command through the LangGraph agent.

        Args:
            user_id: User UUID
            query: User query text
            session_id: Optional session ID (generated if not provided)
            use_cache: Whether to use cache for API calls

        Returns:
            Dict with response, intent, symbols, and raw_data
        """
        await self.initialize()

        if not session_id:
            session_id = str(uuid.uuid4())

        try:
            # Import logging system
            from ..llm_agent.logger import agent_logger

            # Start session logging
            agent_logger.start_session(
                session_id=session_id,
                user_id=user_id,
                metadata={"source": "text_command"}
            )

            # Log query received
            agent_logger.log_query_received(query, source="api")

            # Get memory for user
            memory = await self._get_memory_for_user(user_id)

            # Start memory session if not already started
            if not memory.current_session_id:
                memory.start_session(session_id)

            # Get or create chat history for this session
            if session_id not in self.session_chat_history:
                self.session_chat_history[session_id] = []

            chat_history = self.session_chat_history[session_id]

            # Prepare state with chat history
            from ..llm_agent.state import MarketState, ChatMessage
            initial_state = MarketState(
                query=query,
                user_id=user_id,
                chat_history=chat_history,
                thread_id=session_id
            )

            # Invoke graph
            start_time = asyncio.get_event_loop().time()
            result = await self.graph.ainvoke(initial_state)
            processing_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            # Update chat history with this conversation turn
            response_text = result.get("summary", "")
            chat_history.append(ChatMessage(role="user", content=query))
            chat_history.append(ChatMessage(role="assistant", content=response_text))

            # Keep only last 10 messages (5 conversation turns) to avoid context overflow
            if len(chat_history) > 10:
                self.session_chat_history[session_id] = chat_history[-10:]

            # Track in memory (if not chat/unknown intent)
            if result.get("intent") not in ["chat", "unknown"]:
                memory.track_conversation(
                    query=query,
                    intent=result.get("intent"),
                    symbols=result.get("symbols", []),
                    summary=response_text
                )

            # Log response
            agent_logger.log_response_sent(
                response=result.get("summary", ""),
                processing_time_ms=processing_time_ms,
                metadata={
                    "intent": result.get("intent"),
                    "symbols": result.get("symbols", []),
                    "num_intents": len(result.get("intents", []))
                }
            )

            return {
                "response": result.get("summary", ""),
                "intent": result.get("intent", "unknown"),
                "symbols": result.get("symbols", []),
                "raw_data": result.get("raw_data", {}),
                "intents": [
                    {
                        "intent": intent.get("intent") if isinstance(intent, dict) else intent.intent,
                        "symbols": intent.get("symbols", []) if isinstance(intent, dict) else intent.symbols,
                        "timeframe": intent.get("timeframe") if isinstance(intent, dict) else intent.timeframe
                    }
                    for intent in result.get("intents", [])
                ],
                "processing_time_ms": processing_time_ms,
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"❌ Error processing text command: {e}", exc_info=True)

            # Log error
            from ..llm_agent.logger import agent_logger
            agent_logger.log_error(
                error_type="text_command_error",
                error_message=str(e),
                traceback=None,
                context={"query": query, "user_id": user_id}
            )

            return {
                "response": "I encountered an error processing your request. Please try again.",
                "intent": "error",
                "symbols": [],
                "raw_data": {},
                "error": str(e),
                "session_id": session_id
            }

    async def process_voice_command(
        self,
        user_id: str,
        audio_data: bytes,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a voice command (transcription handled by caller).

        Note: This is a placeholder. Voice transcription should be handled
        by the WebSocket manager using ASR, then call process_text_command.

        Args:
            user_id: User UUID
            audio_data: Raw audio bytes
            session_id: Session ID

        Returns:
            Dict with response
        """
        # This should not be called directly - transcription happens in WebSocket manager
        raise NotImplementedError(
            "Voice commands should be transcribed first, then use process_text_command"
        )

    async def finalize_session(self, user_id: str, session_id: str = None):
        """Finalize user session and update long-term memory.

        Args:
            user_id: User UUID
            session_id: Session ID (optional, for cleaning up chat history)
        """
        try:
            if user_id in self.user_memories:
                memory = self.user_memories[user_id]
                await memory.finalize_session()
                logger.info(f"✅ Finalized session for user {user_id[:8]}...")

            # Clear session chat history
            if session_id and session_id in self.session_chat_history:
                del self.session_chat_history[session_id]
                logger.info(f"✅ Cleared chat history for session {session_id[:8]}...")

            # End session logging
            from ..llm_agent.logger import agent_logger
            agent_logger.end_session(
                summary={"user_id": user_id, "session_id": session_id}
            )

        except Exception as e:
            logger.error(f"❌ Error finalizing session: {e}")

    async def get_user_context(self, user_id: str) -> str:
        """Get formatted memory context for user.

        Args:
            user_id: User UUID

        Returns:
            Formatted memory context string
        """
        try:
            memory = await self._get_memory_for_user(user_id)
            return memory.get_user_context()
        except Exception as e:
            logger.error(f"❌ Error getting user context: {e}")
            return ""

    async def get_user_watchlist(self, user_id: str) -> List[str]:
        """Get user's watchlist from database.

        Args:
            user_id: User UUID

        Returns:
            List of stock symbols
        """
        await self.initialize()

        try:
            return await self.db.get_user_watchlist(user_id)
        except Exception as e:
            logger.error(f"❌ Error getting watchlist: {e}")
            return []

    async def update_watchlist(
        self,
        user_id: str,
        action: str,
        symbols: List[str] = None
    ) -> Dict[str, Any]:
        """Update user's watchlist.

        Args:
            user_id: User UUID
            action: "add", "remove", or "view"
            symbols: List of symbols (for add/remove)

        Returns:
            Dict with result
        """
        await self.initialize()

        try:
            from ..llm_agent.tools.watchlist_tools_supabase import handle_watchlist_command

            result = await handle_watchlist_command(
                user_id=user_id,
                action=action,
                symbols=symbols,
                db_manager=self.db
            )

            return result

        except Exception as e:
            logger.error(f"❌ Error updating watchlist: {e}")
            return {
                "success": False,
                "message": f"Error updating watchlist: {str(e)}",
                "watchlist": []
            }


# ====== SINGLETON INSTANCE ======
_agent_wrapper_instance: Optional[LangGraphAgentWrapper] = None


async def get_agent() -> LangGraphAgentWrapper:
    """Get or create singleton agent wrapper instance.

    Returns:
        LangGraphAgentWrapper instance
    """
    global _agent_wrapper_instance

    if _agent_wrapper_instance is None:
        _agent_wrapper_instance = LangGraphAgentWrapper()
        await _agent_wrapper_instance.initialize()

    return _agent_wrapper_instance

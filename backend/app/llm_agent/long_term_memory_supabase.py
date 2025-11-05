"""
Long-term memory system with Supabase integration.

Key Features:
1. Category-based memory stored in Supabase user_notes table
2. Post-session LLM summarizer for updating category summaries
3. User-specific memory (user_id based)
4. Async database operations

Memory Structure (stored in Supabase):
{
  "stocks": "Seeking opportunities in technology and AI sectors",
  "investment": "Researching nuclear energy private companies",
  "trading": "Monitoring META for short-term price movements",
  "research": "Interested in P/E ratios and valuation metrics",
  "watchlist": "Tracking GOOGL, META, TSLA for technology sector exposure",
  "news": "Following tech earnings reports and Fed announcements"
}

Categories:
- stocks: General interest in specific stocks or sectors
- investment: Long-term investment strategies and research
- trading: Short-term trading interests and patterns
- research: Analytical queries (P/E, earnings, fundamentals)
- watchlist: Stocks being actively tracked
- news: News interests and event monitoring
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


# ====== LLM SETUP FOR SUMMARIZER ======
def get_llm_for_summarizer():
    """Get LLM for post-session summarization."""
    return ChatOpenAI(
        model="glm-4.5-flash",
        temperature=0.7,  # Higher temperature for creative summarization
        api_key=os.environ.get("ZHIPUAI_API_KEY", ""),
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
    )


class LongTermMemory:
    """Long-term memory manager with Supabase persistence."""

    def __init__(self, user_id: str, db_manager=None):
        """Initialize memory manager for specific user.

        Args:
            user_id: User UUID
            db_manager: DatabaseManager instance (will be set during initialization)
        """
        self.user_id = user_id
        self.db = db_manager
        self.key_notes: Dict[str, str] = {}

        # Session tracking (temporary, in-memory)
        self.current_session_id: Optional[str] = None
        self.session_queries: List[str] = []
        self.session_symbols: List[str] = []
        self.session_intents: List[str] = []
        self.session_summaries: List[str] = []

    async def initialize(self):
        """Initialize database connection and load memory from Supabase."""
        if not self.db:
            from ..database import get_database
            self.db = await get_database()

        # Load existing memory from Supabase
        self.key_notes = await self.db.get_user_notes(self.user_id)
        logger.info(f"📚 Loaded memory for user {self.user_id[:8]}... - {len(self.key_notes)} categories")

    def start_session(self, session_id: str):
        """Start tracking a new session.

        Args:
            session_id: Unique session identifier
        """
        self.current_session_id = session_id
        self.session_queries = []
        self.session_symbols = []
        self.session_intents = []
        self.session_summaries = []
        logger.info(f"🎬 Started memory tracking for session: {session_id}")

    def track_conversation(
        self,
        query: str,
        intent: str,
        symbols: List[str],
        summary: str
    ):
        """Track a conversation turn during the session.

        Args:
            query: User query
            intent: Detected intent
            symbols: Symbols discussed
            summary: Agent response summary
        """
        if not self.current_session_id:
            logger.warning("⚠️  No active session - call start_session() first")
            return

        self.session_queries.append(query)
        self.session_intents.append(intent)
        self.session_symbols.extend(symbols)
        self.session_summaries.append(summary)

        logger.debug(f"📝 Tracked conversation: intent={intent}, symbols={symbols}")

    async def finalize_session(self):
        """Finalize session and update memory with LLM summarization.

        This analyzes the entire session and updates category-based key notes.
        """
        if not self.current_session_id:
            logger.warning("⚠️  No active session to finalize")
            return

        if not self.session_queries:
            logger.info("ℹ️  No queries in session - skipping memory update")
            return

        logger.info(f"💾 Finalizing session {self.current_session_id} - analyzing {len(self.session_queries)} queries")

        try:
            # Analyze session with LLM and update key notes
            updated_notes = await self._summarize_session_with_llm()

            if updated_notes:
                # Merge with existing notes
                self.key_notes.update(updated_notes)

                # Save to Supabase
                success = await self.db.upsert_user_notes(self.user_id, self.key_notes)

                if success:
                    logger.info(f"✅ Memory updated: {list(updated_notes.keys())}")
                else:
                    logger.error("❌ Failed to save memory to Supabase")
            else:
                logger.warning("⚠️  LLM returned no updates")

        except Exception as e:
            logger.error(f"❌ Error finalizing session: {e}", exc_info=True)

        # Clear session data
        self.current_session_id = None
        self.session_queries = []
        self.session_symbols = []
        self.session_intents = []
        self.session_summaries = []

    async def _summarize_session_with_llm(self) -> Dict[str, str]:
        """Use LLM to analyze session and update category-based key notes.

        Returns:
            Dict with updated category notes
        """
        llm = get_llm_for_summarizer()

        # Prepare current notes context
        current_notes_str = "\n".join([
            f"- {category}: {note}"
            for category, note in self.key_notes.items()
        ]) if self.key_notes else "(No existing notes)"

        # Prepare session context
        unique_symbols = list(set(self.session_symbols))
        unique_intents = list(set(self.session_intents))

        prompt = f"""You are analyzing a user's financial chat session to update their long-term interest profile.

**Current Category Notes**:
{current_notes_str}

**This Session's Activity**:
Queries: {self.session_queries}
Symbols Discussed: {unique_symbols}
Intent Types: {unique_intents}

**Task**: Update the category-based notes to reflect the user's evolving interests.

**Categories** (use these exact keys):
- stocks: General interest in specific stocks or sectors
- investment: Long-term investment strategies
- trading: Short-term trading patterns
- research: Analytical interests (P/E, earnings, valuation)
- watchlist: Stocks being actively tracked
- news: News monitoring interests

**Rules**:
1. Keep notes concise (max 80 characters each)
2. Only include categories where user showed interest in THIS session
3. Update existing notes if new information adds context
4. Don't remove existing notes unless contradicted by new data

**Output Format** (JSON only, no markdown):
{{"stocks": "...", "investment": "...", "research": "..."}}

If no significant interests detected, return empty object: {{}}
"""

        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            # Clean control characters
            content = ''.join(char if ord(char) >= 32 or char in ['\n', '\t', '\r'] else ' ' for char in content)

            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            # Parse JSON
            import json
            updated_notes = json.loads(content)

            logger.info(f"🧠 LLM analyzed session - {len(updated_notes)} category updates")
            return updated_notes

        except Exception as e:
            logger.error(f"❌ Error in LLM summarization: {e}")
            return {}

    def get_user_context(self) -> str:
        """Get formatted memory context for including in prompts.

        Returns:
            Formatted string with user's interests
        """
        if not self.key_notes:
            return ""

        context_lines = ["User's Long-Term Interests:"]
        for category, note in self.key_notes.items():
            context_lines.append(f"- {category.capitalize()}: {note}")

        return "\n".join(context_lines)


# ====== GLOBAL INSTANCE MANAGEMENT ======
# We maintain one instance per user_id
_memory_instances: Dict[str, LongTermMemory] = {}


async def get_memory_for_user(user_id: str) -> LongTermMemory:
    """Get or create memory instance for user.

    Args:
        user_id: User UUID

    Returns:
        LongTermMemory instance
    """
    if user_id not in _memory_instances:
        memory = LongTermMemory(user_id)
        await memory.initialize()
        _memory_instances[user_id] = memory
        logger.info(f"✅ Created new memory instance for user {user_id[:8]}...")
    return _memory_instances[user_id]


# ====== CONVENIENCE FUNCTIONS ======
async def start_session(user_id: str, session_id: str):
    """Start session tracking for user."""
    memory = await get_memory_for_user(user_id)
    memory.start_session(session_id)


async def track_conversation(
    user_id: str,
    query: str,
    intent: str,
    symbols: List[str],
    summary: str
):
    """Track conversation turn."""
    memory = await get_memory_for_user(user_id)
    memory.track_conversation(query, intent, symbols, summary)


async def finalize_session(user_id: str):
    """Finalize session and update memory."""
    memory = await get_memory_for_user(user_id)
    await memory.finalize_session()


async def get_user_context(user_id: str) -> str:
    """Get formatted memory context for user."""
    memory = await get_memory_for_user(user_id)
    return memory.get_user_context()

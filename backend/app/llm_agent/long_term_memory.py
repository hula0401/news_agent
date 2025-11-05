"""
Long-term memory system with category-based key notes.

Key Features:
1. Category-based memory (stocks, investment, trading, research, etc.)
2. Post-session LLM summarizer for updating category summaries
3. Persistent storage with JSON files
4. Trending symbols tracking

Memory Structure:
{
  "key_notes": {
    "stocks": "Seeking opportunities in technology and AI sectors",
    "investment": "Researching nuclear energy private companies",
    "trading": "Monitoring META for short-term price movements",
    "research": "Interested in P/E ratios and valuation metrics",
    "watchlist": "Tracking GOOGL, META, TSLA for technology sector exposure"
  },
  "session_history": [
    {
      "session_id": "chat_20241115_103000",
      "timestamp": "2024-01-15T10:30:00",
      "queries": ["what's meta p/e ratio?", "add TSLA to watchlist"],
      "symbols_discussed": ["META", "TSLA"],
      "main_topics": ["valuation", "watchlist management"]
    }
  ],
  "trending_symbols": ["META", "TSLA", "NVDA", "GOOGL"],
  "last_updated": "2024-01-15T10:30:00"
}

Categories:
- stocks: General interest in specific stocks or sectors
- investment: Long-term investment strategies and research
- trading: Short-term trading interests and patterns
- research: Analytical queries (P/E, earnings, fundamentals)
- watchlist: Stocks being actively tracked
- news: News interests and event monitoring
"""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# Memory file path
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory_data")
USER_PROFILE_FILE = os.path.join(MEMORY_DIR, "user_profile.json")

# Ensure memory directory exists
os.makedirs(MEMORY_DIR, exist_ok=True)


# ====== DATA STRUCTURES ======
@dataclass
class SessionSummary:
    """Summary of a chat session."""
    session_id: str
    timestamp: str
    queries: List[str] = field(default_factory=list)
    symbols_discussed: List[str] = field(default_factory=list)
    main_topics: List[str] = field(default_factory=list)
    intents: List[str] = field(default_factory=list)


@dataclass
class UserProfile:
    """User's long-term profile with category-based key notes."""
    key_notes: Dict[str, str] = field(default_factory=dict)  # Category → Summary
    session_history: List[SessionSummary] = field(default_factory=list)
    trending_symbols: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ====== SESSION-LEVEL STORAGE (TEMPORARY) ======
# Store conversation data during the session, then summarize at the end
_current_session_data = {
    "session_id": None,
    "queries": [],
    "symbols": [],
    "intents": [],
    "summaries": []
}


def start_new_session(session_id: str):
    """Initialize a new session for tracking."""
    global _current_session_data
    _current_session_data = {
        "session_id": session_id,
        "queries": [],
        "symbols": [],
        "intents": [],
        "summaries": []
    }
    logger.info(f"📝 Started tracking session: {session_id}")


def add_to_current_session(query: str, intent: str, symbols: List[str], summary: str):
    """Add conversation to current session tracking."""
    global _current_session_data

    if _current_session_data["session_id"] is None:
        logger.warning("No active session - skipping session tracking")
        return

    _current_session_data["queries"].append(query)
    _current_session_data["intents"].append(intent)
    _current_session_data["symbols"].extend(symbols)
    _current_session_data["summaries"].append(summary)

    logger.debug(f"Added to session: query={query[:50]}, intent={intent}, symbols={symbols}")


# ====== POST-SESSION LLM SUMMARIZER ======
def get_llm_for_summarizer():
    """Get LLM instance for post-session summarization."""
    try:
        return ChatOpenAI(
            model="glm-4.5-flash",
            temperature=0,
            api_key=os.environ.get("ZHIPUAI_API_KEY", ""),
            openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
        )
    except Exception as e:
        logger.warning(f"Failed to initialize LLM for summarizer: {e}")
        return None


async def summarize_session_with_llm(
    queries: List[str],
    symbols: List[str],
    intents: List[str],
    current_key_notes: Dict[str, str]
) -> Dict[str, str]:
    """
    Use LLM to update category-based key notes based on session conversations.

    Returns updated key_notes dict with categories like:
    {
      "stocks": "Seeking opportunities in technology and AI",
      "investment": "Researching nuclear energy private companies",
      ...
    }
    """
    llm = get_llm_for_summarizer()
    if not llm:
        return current_key_notes  # Fallback to existing notes

    # Format current key notes
    current_notes_str = "\n".join([f"- {cat}: {note}" for cat, note in current_key_notes.items()])
    if not current_notes_str:
        current_notes_str = "[No existing notes]"

    # Build prompt
    prompt = f"""You are analyzing a user's financial chat session to update their long-term interest profile.

**Current Category Notes**:
{current_notes_str}

**This Session's Activity**:
Queries: {queries}
Symbols Discussed: {list(set(symbols))}
Intent Types: {list(set(intents))}

**Task**: Update the category-based notes to reflect the user's evolving interests.

**Categories** (use these exact keys):
- stocks: General interest in specific stocks or sectors (e.g., "Seeking opportunities in technology and AI")
- investment: Long-term investment strategies (e.g., "Researching nuclear energy private companies")
- trading: Short-term trading patterns (e.g., "Monitoring META for day trading")
- research: Analytical interests (e.g., "Interested in P/E ratios and valuation metrics")
- watchlist: Stocks being actively tracked (e.g., "Tracking GOOGL, META for tech sector")
- news: News monitoring interests (e.g., "Following earnings announcements")

**Rules**:
1. Keep notes concise (max 80 characters each)
2. Only include categories where user showed interest
3. Update existing notes if new information adds context
4. Remove categories if no longer relevant
5. Be specific about sectors, strategies, or metrics when possible

**Output Format** (JSON only, no markdown):
{{
  "stocks": "...",
  "investment": "...",
  "research": "...",
  ...
}}

Only include categories with actual interest. Return empty dict {{}} if no meaningful interests detected."""

    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()

        # Parse JSON from response
        import re
        # Remove markdown code blocks
        if content.startswith("```"):
            code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if code_match:
                content = code_match.group(1).strip()

        # Clean control characters that cause JSON parse errors
        # Replace control chars (except \n, \t, \r) with space
        content = ''.join(char if ord(char) >= 32 or char in ['\n', '\t', '\r'] else ' ' for char in content)

        updated_notes = json.loads(content)

        # Validate it's a dict
        if not isinstance(updated_notes, dict):
            raise ValueError("LLM did not return a dict")

        logger.info(f"✅ LLM updated category notes: {list(updated_notes.keys())}")
        return updated_notes

    except Exception as e:
        logger.error(f"❌ LLM summarization failed: {e}, keeping existing notes")
        return current_key_notes


# ====== USER PROFILE MANAGEMENT ======
class UserProfileManager:
    """Manage user's long-term profile with category-based key notes."""

    def __init__(self, filepath: str = USER_PROFILE_FILE):
        self.filepath = filepath
        self.profile = UserProfile()
        self.load()

    def load(self):
        """Load user profile from file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r") as f:
                    data = json.load(f)

                # Load session history
                session_history = []
                for item in data.get("session_history", []):
                    session_history.append(SessionSummary(
                        session_id=item["session_id"],
                        timestamp=item["timestamp"],
                        queries=item.get("queries", []),
                        symbols_discussed=item.get("symbols_discussed", []),
                        main_topics=item.get("main_topics", []),
                        intents=item.get("intents", [])
                    ))

                self.profile = UserProfile(
                    key_notes=data.get("key_notes", {}),
                    session_history=session_history,
                    trending_symbols=data.get("trending_symbols", []),
                    last_updated=data.get("last_updated", datetime.utcnow().isoformat())
                )

                logger.info(f"Loaded user profile: {len(self.profile.key_notes)} categories, {len(self.profile.session_history)} sessions")
            except Exception as e:
                logger.error(f"Error loading user profile: {e}")
                self.profile = UserProfile()
        else:
            self.profile = UserProfile()

    def save(self):
        """Save user profile to file."""
        try:
            data = {
                "key_notes": self.profile.key_notes,
                "session_history": [asdict(s) for s in self.profile.session_history],
                "trending_symbols": self.profile.trending_symbols,
                "last_updated": datetime.utcnow().isoformat()
            }

            with open(self.filepath, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved user profile: {len(self.profile.key_notes)} categories")
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")

    async def finalize_session(self):
        """
        Finalize the current session and update profile.

        Called at the end of a chat session to:
        1. Summarize session with LLM
        2. Update category-based key notes
        3. Update trending symbols
        4. Save to disk
        """
        global _current_session_data

        if not _current_session_data["session_id"]:
            logger.warning("No active session to finalize")
            return

        session_id = _current_session_data["session_id"]
        queries = _current_session_data["queries"]
        symbols = list(set(_current_session_data["symbols"]))
        intents = list(set(_current_session_data["intents"]))

        if not queries:
            logger.info("Empty session - skipping finalization")
            return

        logger.info(f"🎯 Finalizing session {session_id}: {len(queries)} queries, {len(symbols)} symbols")

        # Use LLM to update category notes
        updated_notes = await summarize_session_with_llm(
            queries=queries,
            symbols=symbols,
            intents=intents,
            current_key_notes=self.profile.key_notes
        )

        self.profile.key_notes = updated_notes

        # Add session to history
        session_summary = SessionSummary(
            session_id=session_id,
            timestamp=datetime.utcnow().isoformat(),
            queries=queries,
            symbols_discussed=symbols,
            main_topics=[],  # Could extract from summaries
            intents=intents
        )
        self.profile.session_history.append(session_summary)

        # Keep only last 20 sessions
        if len(self.profile.session_history) > 20:
            self.profile.session_history = self.profile.session_history[-20:]

        # Update trending symbols (last 10 sessions)
        recent_sessions = self.profile.session_history[-10:]
        symbol_counts = {}
        for session in recent_sessions:
            for symbol in session.symbols_discussed:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

        # Sort by frequency
        self.profile.trending_symbols = sorted(symbol_counts.keys(), key=lambda x: symbol_counts[x], reverse=True)[:10]

        # Save to disk
        self.save()

        logger.info(f"✅ Session finalized: Updated {len(self.profile.key_notes)} categories")
        logger.info(f"   Key Notes: {self.profile.key_notes}")
        logger.info(f"   Trending: {self.profile.trending_symbols[:5]}")

        # Reset session data
        _current_session_data = {
            "session_id": None,
            "queries": [],
            "symbols": [],
            "intents": [],
            "summaries": []
        }

    def get_context_summary(self) -> str:
        """Get formatted summary for LLM context."""
        if not self.profile.key_notes:
            return ""

        lines = []
        for category, note in self.profile.key_notes.items():
            lines.append(f"**{category}**: {note}")

        if self.profile.trending_symbols:
            lines.append(f"\n**Trending Symbols**: {', '.join(self.profile.trending_symbols[:5])}")

        return "\n".join(lines)


# ====== GLOBAL INSTANCE ======
profile_manager = UserProfileManager()


# ====== HELPER FUNCTIONS ======
def start_session(session_id: str):
    """Start a new session for tracking."""
    start_new_session(session_id)


def track_conversation(query: str, intent: str, symbols: List[str], summary: str):
    """Track a conversation in the current session."""
    add_to_current_session(query, intent, symbols, summary)


async def finalize_session():
    """Finalize the current session and update long-term memory."""
    await profile_manager.finalize_session()


def get_user_context() -> str:
    """Get user's long-term interests for LLM context."""
    profile_manager.load()  # Reload to get latest
    return profile_manager.get_context_summary()


def load_user_profile() -> UserProfile:
    """Load user's profile."""
    profile_manager.load()
    return profile_manager.profile

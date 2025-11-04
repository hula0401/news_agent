"""
State schemas for the Market Assistant Agent.

Defines typed state objects that flow through the LangGraph DAG.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from datetime import datetime


@dataclass
class MarketDataItem:
    """Standardized market data structure."""
    symbol: str
    price: Optional[float] = None
    change_percent: Optional[float] = None
    volume: Optional[int] = None
    timestamp: Optional[str] = None
    source: str = ""  # "alphavantage" or "polygon"
    interval: str = "daily"  # "1min", "5min", "daily", etc.
    metadata: Dict = field(default_factory=dict)  # Extra fields (open, high, low, close, etc.)


@dataclass
class NewsItem:
    """Standardized news article structure."""
    title: str
    summary: str
    url: str
    source: str
    published_at: str
    sentiment: Optional[str] = None  # "positive", "negative", "neutral"
    symbols: List[str] = field(default_factory=list)
    source_website: str = "unknown"  # Domain name extracted from URL
    category: str = "general"  # News category: general, monetary_policy, economic_indicators, political, international, calendar


@dataclass
class ChecklistItem:
    """Single checklist item for tracking research query completion."""
    query: str  # The search query to execute (e.g., "TSLA P/E ratio", "META earnings")
    symbols: List[str] = field(default_factory=list)  # Symbols associated with this query
    keywords: List[str] = field(default_factory=list)  # Keywords for this specific query
    completed: bool = False  # Whether this query has been executed
    result_count: int = 0  # Number of results found for this query
    timestamp_completed: Optional[str] = None  # When this item was marked complete


@dataclass
class IntentItem:
    """Single intent with its context."""
    intent: Literal["price_check", "news_search", "market_summary", "comparison", "research", "chat", "unknown"]
    symbols: List[str] = field(default_factory=list)
    timeframe: str = "1d"
    reasoning: str = ""
    keywords: List[str] = field(default_factory=list)  # For research intent: extracted keywords (e.g., ["P/E ratio", "earnings"])


@dataclass
class ChatMessage:
    """Single message in chat history."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MarketState:
    """
    Main state object flowing through the LangGraph.

    Workflow:
    1. query → intent_analyzer → intents (list of IntentItem)
    2. intents → tool_selector → selected_tools
    3. selected_tools → parallel_fetcher → raw_data
    4. raw_data → data_merger → merged_data
    5. merged_data → summarizer → summary
    6. summary → memory_writer → memory_id
    """

    # Input
    query: str = ""
    output_mode: Literal["voice", "text"] = "voice"  # Default is voice (oral output)

    # Chat history (for maintaining context in conversations)
    thread_id: Optional[str] = None  # Conversation thread identifier
    chat_history: List[ChatMessage] = field(default_factory=list)  # Previous messages in this thread

    # Intent analysis output (supports multiple intents)
    intents: List[IntentItem] = field(default_factory=list)

    # Research checklist (for tracking parallel query execution)
    research_checklist: List[ChecklistItem] = field(default_factory=list)

    # Legacy fields (for backward compatibility, derived from first intent)
    intent: Literal["price_check", "news_search", "market_summary", "comparison", "research", "chat", "unknown"] = "unknown"
    symbols: List[str] = field(default_factory=list)  # Extracted ticker symbols
    timeframe: str = "1d"  # "1min", "5min", "1h", "1d", "1w", "1mo"
    keywords: List[str] = field(default_factory=list)  # Extracted keywords for research queries (e.g., ["P/E ratio", "earnings", "valuation"])

    # Tool selection output
    selected_tools: List[str] = field(default_factory=list)  # ["price", "news", "comparison"]

    # API selection output (decided by parallel_fetcher subagent)
    selected_apis: Dict[str, List[str]] = field(default_factory=dict)  # {"price": ["yfinance"], "news": ["alphavantage"]}

    # Data fetching output
    raw_data: Dict[str, List[Dict]] = field(default_factory=dict)  # {"yfinance": [...], "alphavantage": [...]}

    # Data merging output
    market_data: List[MarketDataItem] = field(default_factory=list)
    news_data: List[NewsItem] = field(default_factory=list)

    # Web research output (for news queries)
    research_chunks: List[Dict] = field(default_factory=list)  # Content chunks from browsed URLs
    research_citations: List[str] = field(default_factory=list)  # Source URLs
    research_confidence: float = 0.0  # Confidence score (0-1)

    # LLM summarization output
    summary: str = ""

    # Memory persistence
    memory_id: Optional[str] = None

    # Metadata
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None

    # Execution config
    timeout_seconds: float = 10.0
    max_retries: int = 2
    enable_caching: bool = True
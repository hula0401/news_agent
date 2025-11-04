"""
Agent core package.

Main components for the market analysis agent.
"""
from .nodes import (
    node_intent_analyzer,
    node_tool_selector,
    node_parallel_fetcher,
    node_response_generator,
)
from .graph import build_graph, run_market_agent
from .state import MarketState, MarketDataItem, NewsItem, IntentItem, ChatMessage
from .memory import save_query, get_recent_queries, watchlist, query_history
from .prompts import (
    get_intent_analyzer_prompt,
    get_response_generator_prompt,
    get_chat_response_prompt,
    GENERAL_SYSTEM_PROMPT,
)
from .symbol_validator import validate_and_correct_symbols, get_correction_message

__all__ = [
    # Nodes
    "node_intent_analyzer",
    "node_tool_selector",
    "node_parallel_fetcher",
    "node_response_generator",
    # Graph
    "build_graph",
    "run_market_agent",
    # State
    "MarketState",
    "MarketDataItem",
    "NewsItem",
    "IntentItem",
    "ChatMessage",
    # Memory
    "save_query",
    "get_recent_queries",
    "watchlist",
    "query_history",
    # Prompts
    "get_intent_analyzer_prompt",
    "get_response_generator_prompt",
    "get_chat_response_prompt",
    "GENERAL_SYSTEM_PROMPT",
    # Symbol Validator
    "validate_and_correct_symbols",
    "get_correction_message",
]

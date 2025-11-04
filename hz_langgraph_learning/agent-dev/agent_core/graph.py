"""
LangGraph main graph definition for Market Assistant Agent.

Builds the DAG with conditional routing and parallel execution.
"""

import os
import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv()

from agent_core.state import MarketState
from agent_core.nodes import (
    node_intent_analyzer,
    node_tool_selector,
    node_parallel_fetcher,
    node_web_research,  # Web research for news articles
    node_general_research,  # General research for any topic
    node_response_generator,  # Combined node (replaces data_merger + summarizer + memory_writer)
)

logger = logging.getLogger(__name__)

# ====== LANGSMITH TRACING SETUP ======
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
if LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = "market-assistant-agent"
    logger.info("LangSmith tracing enabled for project: market-assistant-agent")
else:
    logger.warning("LANGSMITH_API_KEY not found. Tracing disabled.")


# ====== CONDITIONAL ROUTING ======
def route_after_intent(state: MarketState) -> Literal["chat_response", "general_research", "tool_selector"]:
    """
    Route after intent analysis based on intent types.

    Routes:
    - chat/unknown → chat_response
    - research → general_research
    - market intents → tool_selector
    """
    intents = state.intents

    # Check if any intent is 'research'
    has_research = any(intent.intent == "research" for intent in intents)

    # Check if all intents are conversational (chat or unknown)
    is_all_conversational = all(intent.intent in ["chat", "unknown"] for intent in intents)

    if is_all_conversational:
        logger.info("All intents are chat/unknown - routing directly to response generator")
        return "chat_response"
    elif has_research:
        logger.info("Research intent detected - routing to general research")
        return "general_research"
    else:
        logger.info("Market data intents detected - routing to tool selector")
        return "tool_selector"


def should_fetch_data(state: MarketState) -> Literal["fetch_data", "END"]:
    """
    Route based on whether we have tools selected.

    If no tools selected, we shouldn't be here (graph routing error).
    """
    if not state.selected_tools or not state.symbols:
        logger.error("No tools or symbols in tool_selector - this shouldn't happen!")
        return "END"
    return "fetch_data"


def should_research(state: MarketState) -> Literal["web_research", "response_generator"]:
    """
    Decide if we need web research after fetching data.

    Only run web research if:
    - Intent is news_search
    - We have news data in raw_data (before merger)
    """
    # Check raw_data for news since news_data is not populated yet
    has_news = False
    if state.raw_data:
        news_sources = ["alphavantage_news", "tavily", "general_market_news"]
        for source in news_sources:
            if source in state.raw_data and len(state.raw_data[source]) > 0:
                has_news = True
                break

    if state.intent == "news_search" and has_news:
        logger.info(f"News data available in raw_data - routing to web research")
        return "web_research"
    else:
        logger.info(f"Skipping web research (intent={state.intent}, has_news={has_news}) - routing to response generator")
        return "response_generator"


# ====== GRAPH CONSTRUCTION ======
def build_graph() -> StateGraph:
    """
    Build the Market Assistant LangGraph.

    Graph Structure with Web Research:
    ┌───────────────────┐
    │  START            │
    └────────┬──────────┘
             │
             ▼
    ┌────────────────────┐
    │ intent_analyzer    │  ← Parse query → extract intents + symbols
    └────────┬───────────┘
             │
             ▼
    ┌────────────────────┐
    │  [Conditional]     │  ← If chat/unknown → chat_response
    └────────┬───────────┘  ← Else → tool_selector
             │
      ┌──────┴──────┐
      ▼             ▼
   [chat]      ┌────────────────────┐
      │        │  tool_selector     │  ← Select tools based on market intents
      │        └────────┬───────────┘
      │                 │
      │                 ▼
      │        ┌────────────────────┐
      │        │ parallel_fetcher   │  ← Fetch from APIs in parallel
      │        └────────┬───────────┘
      │                 │
      │                 ▼
      │        ┌────────────────────┐
      │        │  [Conditional]     │  ← If news_search + news_data → web_research
      │        └────────┬───────────┘  ← Else → response_generator
      │                 │
      │         ┌───────┴────────┐
      │         ▼                ▼
      │    ┌─────────────┐      │
      │    │web_research │      │  ← Browse URLs with Playwright (news only)
      │    └──────┬──────┘      │
      │           │             │
      │           └──────┬──────┘
      │                  │
      └──────────────────┘
                         │
                         ▼
                ┌────────────────────┐
                │ response_generator │  ← Merge + Summarize + Save Memory (combined)
                └────────┬───────────┘
                         │
                         ▼
                ┌────────────────────┐
                │  END               │
                └────────────────────┘

    All nodes are async for concurrent execution.
    """
    # Initialize StateGraph with MarketState type
    graph = StateGraph(MarketState)

    # Add nodes
    graph.add_node("intent_analyzer", node_intent_analyzer)
    graph.add_node("tool_selector", node_tool_selector)
    graph.add_node("parallel_fetcher", node_parallel_fetcher)
    graph.add_node("web_research", node_web_research)  # Web research for stock news
    graph.add_node("general_research", node_general_research)  # General research for any topic
    graph.add_node("response_generator", node_response_generator)  # Combined node

    # Add edges
    graph.add_edge(START, "intent_analyzer")

    # Conditional routing after intent analysis
    # - chat/unknown → response_generator
    # - research → general_research
    # - market intents → tool_selector
    graph.add_conditional_edges(
        "intent_analyzer",
        route_after_intent,
        {
            "chat_response": "response_generator",
            "general_research": "general_research",
            "tool_selector": "tool_selector",
        },
    )

    # General research goes directly to response generator
    graph.add_edge("general_research", "response_generator")

    # Tool selector always goes to parallel fetcher (if we're here, we have market intents)
    graph.add_edge("tool_selector", "parallel_fetcher")

    # After fetching data, conditionally go to web research or response generator
    # If news_search + news_data → web_research
    # Otherwise → response_generator
    graph.add_conditional_edges(
        "parallel_fetcher",
        should_research,
        {
            "web_research": "web_research",
            "response_generator": "response_generator",
        },
    )

    # After web research, go to response generator
    graph.add_edge("web_research", "response_generator")

    # Response generator always goes to END
    graph.add_edge("response_generator", END)

    return graph


# ====== GRAPH COMPILATION ======
def compile_graph():
    """Compile the graph for execution."""
    graph = build_graph()
    return graph.compile()


# ====== MAIN INVOCATION ======
async def run_market_agent(query: str, **kwargs) -> MarketState:
    """
    Main entry point to run the market agent.

    Args:
        query: User's market query (e.g., "What's Tesla's stock price?")
        **kwargs: Optional overrides for state config (output_mode, timeout_seconds, enable_caching, etc.)

    Returns:
        Final MarketState with summary and optional memory_id

    Example:
        >>> result = await run_market_agent("Compare NVDA and AMD stock prices", output_mode="text")
        >>> print(result.summary)
    """
    app = compile_graph()

    # Initialize state
    initial_state = MarketState(query=query, **kwargs)

    # Execute graph
    try:
        final_state_dict = await app.ainvoke(initial_state)

        # Convert dict back to MarketState
        final_state = MarketState(**final_state_dict)

        logger.info(f"Agent execution complete. Memory ID: {final_state.memory_id}")
        return final_state

    except Exception as e:
        logger.error(f"Agent execution error: {e}")
        return MarketState(query=query, error=str(e))


if __name__ == "__main__":
    import asyncio

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Example queries
    queries = [
        "What's Tesla's current stock price?",
        "Compare NVDA and AMD performance",
        "Latest news on Apple earnings",
        "Hello, how are you?",  # Chat intent
        "what's the price of GLD, what happened to it",  # Multiple intents
    ]

    async def main():
        for query in queries:
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print(f"{'='*80}")

            result = await run_market_agent(query, output_mode="voice")

            if result.error:
                print(f"❌ Error: {result.error}")
            else:
                print(f"✅ Intents: {[intent.intent for intent in result.intents]}")
                print(f"✅ Symbols: {result.symbols}")
                print(f"✅ Tools: {result.selected_tools}")
                print(f"\n📊 Summary:\n{result.summary}")
                print(f"\n💾 Memory ID: {result.memory_id}")

    asyncio.run(main())

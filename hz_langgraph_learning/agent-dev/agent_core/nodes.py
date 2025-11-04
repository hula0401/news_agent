"""
LangGraph nodes for the Market Assistant Agent.

Each node is an async function that receives and updates MarketState.
"""

import os
import asyncio
import logging
import time
from typing import List
from datetime import datetime, timezone
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

from agent_core.state import MarketState, MarketDataItem, NewsItem, IntentItem, ChatMessage
from agent_core.tools.tools import fetch_all_market_data, fetch_general_market_news
from agent_core.memory import save_query, watchlist, get_recent_queries
from agent_core.prompts import (
    get_intent_analyzer_prompt,
    get_response_generator_prompt,
    get_chat_response_prompt,
    GENERAL_SYSTEM_PROMPT,
)
from agent_core.logging_config import get_structured_logger

logger = logging.getLogger(__name__)
# Note: structured_logger is fetched dynamically to get current chat session

# ====== LLM SETUP ======
llm = ChatOpenAI(
    model="glm-4.5-flash",
    temperature=0,
    api_key=os.environ.get("ZHIPUAI_API_KEY", ""),
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
)


# ====== STRUCTURED OUTPUT SCHEMAS ======
class IntentOutput(BaseModel):
    """Structured output for intent analysis."""

    intent: str = Field(description="Intent type: price_check, news_search, chat")
    symbols: List[str] = Field(description="List of ticker symbols extracted from query (e.g., ['TSLA', 'NVDA'])")
    timeframe: str = Field(description="Timeframe: 1min, 5min, 1h, 1d (default), 1w, 1mo, 2y")
    reasoning: str = Field(description="Brief reasoning for the intent classification")


# ====== NODE 1: INTENT ANALYZER ======
INTENT_INSTRUCTIONS = """You are a market data analyst assistant. Analyze the user's query and extract ALL intents.

**IMPORTANT**: A single query can have MULTIPLE intents. For example:
- "what's the price of GLD, what happened to it" → TWO intents: [price_check for GLD, news_search for GLD]
- "Compare NVDA vs AMD and tell me latest news" → TWO intents: [comparison for NVDA+AMD, news_search for NVDA+AMD]

**Intent Types**:
   - price_check: User wants current/recent price of specific stock(s)
   - news_search: User wants news/updates about stock(s)
   - chat: Casual conversation, greetings, or questions unrelated to market data

**Symbols**: Extract ticker symbols (e.g., "TSLA", "NVDA", "AMD"). If none mentioned, return empty list.

**Timeframe**: Extract time period:
   - "1min", "5min" for intraday
   - "1d" (default) for daily
   - "1w" for weekly
   - "1mo" for monthly
   - "2y" for 2-year historical

Examples:
- "What's Tesla's stock price?" → [{"intent": "price_check", "symbols": ["TSLA"], "timeframe": "1d"}]
- "what's the price of GLD, what happened to it" → [{"intent": "price_check", "symbols": ["GLD"], "timeframe": "1d"}, {"intent": "news_search", "symbols": ["GLD"], "timeframe": "1d"}]
- "Compare NVDA and AMD performance" → [{"intent": "comparison", "symbols": ["NVDA", "AMD"], "timeframe": "1d"}]
- "Hello, how are you?" → [{"intent": "chat", "symbols": [], "timeframe": "1d"}]
- "What's the weather today?" → [{"intent": "chat", "symbols": [], "timeframe": "1d"}]

Be precise and identify ALL intents in the query."""


async def node_intent_analyzer(state: MarketState) -> MarketState:
    """
    Analyze user query to extract ALL intents (supports multiple intents per query).

    Updates state fields:
    - intents: List[IntentItem] (NEW - supports multiple intents)
    - intent: str (legacy - first intent for backward compatibility)
    - symbols: List[str] (legacy - merged symbols from all intents)
    - timeframe: str (legacy - from first intent)
    """
    query = state.query

    if not query:
        logger.warning("Empty query received")
        state.intent = "unknown"
        state.intents = [IntentItem(intent="unknown", symbols=[], timeframe="1d")]
        state.error = "Empty query"
        return state

    try:
        import json
        import re

        # Get prompt with chat history
        prompt = get_intent_analyzer_prompt(state.chat_history)
        full_prompt = f"""{GENERAL_SYSTEM_PROMPT}

{prompt}

User query: {query}"""

        logger.info(f"🤖 Calling LLM for intent analysis: {query[:50]}...")

        # Prepare full prompt for logging
        full_messages = [
            SystemMessage(content=GENERAL_SYSTEM_PROMPT),
            HumanMessage(content=f"{prompt}\n\nUser query: {query}")
        ]
        full_prompt_text = f"System: {GENERAL_SYSTEM_PROMPT}\n\nUser: {prompt}\n\nUser query: {query}"

        # Measure LLM call time
        start_time = time.time()
        response = await llm.ainvoke(full_messages)
        duration_ms = (time.time() - start_time) * 1000

        # Log detailed LLM query
        get_structured_logger().log_llm_query(
            model="glm-4.5-flash",
            prompt=full_prompt_text,
            response=response.content,
            duration_ms=duration_ms,
        )

        logger.info(f"✅ LLM response received ({duration_ms:.0f}ms, {len(response.content)} chars)")

        # Extract JSON from response
        content = response.content.strip()
        result_dict = None

        # Strategy 1: Try parsing whole content first (most reliable)
        try:
            result_dict = json.loads(content)
        except:
            pass

        # Strategy 2: Look for JSON in markdown code block
        if not result_dict:
            try:
                code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                if code_block_match:
                    result_dict = json.loads(code_block_match.group(1))
            except:
                pass

        # Strategy 3: Find any JSON object with "intents" key
        if not result_dict:
            try:
                # More flexible regex - match any JSON object containing "intents"
                json_match = re.search(r'\{.*?"intents".*?\[.*?\].*?\}', content, re.DOTALL)
                if json_match:
                    result_dict = json.loads(json_match.group())
            except:
                pass

        # Fallback: create default structure
        if not result_dict:
            logger.warning(f"Failed to parse JSON from LLM. Content: {content[:300]}")
            result_dict = {"intents": [{"intent": "unknown", "symbols": [], "timeframe": "1d", "reasoning": "parsing failed"}]}

        # Parse intents
        intents_data = result_dict.get("intents", [])

        # Handle legacy single-intent format
        if not intents_data and "intent" in result_dict:
            intents_data = [{
                "intent": result_dict.get("intent", "unknown"),
                "symbols": result_dict.get("symbols", []),
                "timeframe": result_dict.get("timeframe", "1d"),
                "reasoning": result_dict.get("reasoning", "")
            }]

        # Validate and correct symbols
        from agent_core.symbol_validator import validate_and_correct_symbols, get_correction_message

        # Create IntentItem objects with validated symbols
        intents = []
        all_symbols = []
        correction_messages = []

        for intent_data in intents_data:
            # Get original symbols
            original_symbols = intent_data.get("symbols", [])

            # Validate and correct symbols
            corrected_symbols, correction_info = validate_and_correct_symbols(original_symbols)

            # Track correction messages
            correction_msg = get_correction_message(correction_info)
            if correction_msg:
                correction_messages.append(correction_msg)

            intent_item = IntentItem(
                intent=intent_data.get("intent", "unknown"),
                symbols=corrected_symbols,  # Use corrected symbols
                timeframe=intent_data.get("timeframe", "1d"),
                reasoning=intent_data.get("reasoning", ""),
                keywords=intent_data.get("keywords", [])  # Extract keywords from LLM response
            )
            intents.append(intent_item)
            all_symbols.extend(intent_item.symbols)

        # Remove duplicates from all_symbols
        all_symbols = list(dict.fromkeys(all_symbols))

        # Log symbol corrections if any
        if correction_messages:
            for msg in correction_messages:
                logger.info(f"🔧 Symbol Correction: {msg}")

        # Set state fields
        state.intents = intents

        # Legacy fields (for backward compatibility)
        if intents:
            state.intent = intents[0].intent
            state.symbols = all_symbols
            state.timeframe = intents[0].timeframe
            state.keywords = intents[0].keywords  # Save keywords from first intent
        else:
            state.intent = "unknown"
            state.symbols = []
            state.timeframe = "1d"
            state.keywords = []

        logger.info(f"✅ Detected {len(intents)} intent(s):")
        for i, intent in enumerate(intents, 1):
            keywords_str = f" - Keywords: {intent.keywords}" if intent.keywords else ""
            logger.info(f"  {i}. {intent.intent} - Symbols: {intent.symbols} - Timeframe: {intent.timeframe}{keywords_str}")

        # Generate research checklist for research intents
        from agent_core.state import ChecklistItem
        research_checklist = []

        for intent in intents:
            if intent.intent == "research" and intent.keywords:
                # For multi-symbol + multi-keyword queries, create a checklist item for each combination
                # Example: "meta and nvda p/e ratio" -> ["META P/E ratio", "NVDA P/E ratio"]
                # Example: "tsla p/e and earnings" -> ["TSLA P/E ratio", "TSLA earnings"]

                if intent.symbols:
                    # Multiple symbols: create one checklist item per symbol
                    for symbol in intent.symbols:
                        query_text = f"{symbol} {' '.join(intent.keywords[:2])}"  # Use first 2 keywords
                        research_checklist.append(ChecklistItem(
                            query=query_text,
                            symbols=[symbol],
                            keywords=intent.keywords,
                            completed=False,
                            result_count=0,
                        ))
                else:
                    # No symbols: use keywords directly
                    query_text = ' '.join(intent.keywords[:3])  # Use first 3 keywords
                    research_checklist.append(ChecklistItem(
                        query=query_text,
                        symbols=[],
                        keywords=intent.keywords,
                        completed=False,
                        result_count=0,
                    ))

        state.research_checklist = research_checklist

        if research_checklist:
            logger.info(f"📋 Generated {len(research_checklist)} checklist items:")
            for i, item in enumerate(research_checklist, 1):
                logger.info(f"   {i}. {item.query} (symbols: {item.symbols})")

        state.query = query
        return state

    except Exception as e:
        logger.error(f"❌ Intent analysis error: {e}", exc_info=True)
        state.intent = "unknown"
        state.intents = [IntentItem(intent="unknown", symbols=[], timeframe="1d")]
        state.symbols = []
        state.timeframe = "1d"
        state.error = str(e)
        return state


# ====== NODE 2: TOOL SELECTOR ======
async def node_tool_selector(state: MarketState) -> MarketState:
    """
    Select which tools to use based on ALL intents.

    Routing logic (per intent):
    - price_check → alphavantage + polygon
    - news_search → news
    - chat → no tools (will use conversational LLM)
    - unknown → no tools

    Merges tools from all intents (deduplicates).
    Updates state.selected_tools
    """
    intents = state.intents
    all_tools = set()

    logger.info(f"Selecting tools for {len(intents)} intent(s)...")

    for intent_item in intents:
        intent = intent_item.intent

        if intent in ["price_check", "comparison"]:
            # yfinance is now a standalone tool (explicit selection)
            all_tools.update(["yfinance", "alphavantage", "polygon"])
            logger.info(f"  - {intent}: added price tools (yfinance, alphavantage, polygon)")
        elif intent == "news_search":
            all_tools.add("news")
            logger.info(f"  - {intent}: added news tool")
        else:
            logger.warning(f"  - {intent}: unknown, no tools selected")

    tools = list(all_tools)
    logger.info(f"✅ Final tool selection: {tools}")

    state.selected_tools = tools
    return state


# ====== NODE 3: PARALLEL FETCHER (DECISION-MAKING SUBAGENT) ======
async def node_parallel_fetcher(state: MarketState) -> MarketState:
    """
    Parallel Fetcher Subagent - Intelligently selects and executes APIs.

    Decision-making logic:
    1. For stock prices: Prioritize yfinance (fast, free) → Alpha Vantage → Polygon.io
    2. For news: Use Tavily search
    3. Executes selected APIs in parallel
    4. Logs which APIs were chosen and which returned data
    5. Populates state.selected_apis for transparency

    Updates:
    - state.selected_apis: Dict mapping tool type to API list
    - state.raw_data: Results from all APIs
    """
    from agent_core.tools.tools import (
        fetch_yfinance_quote,
        fetch_alphavantage_quote,
        fetch_polygon_previous_close,
        fetch_market_news,
        fetch_general_market_news,
        yf,
    )

    symbols = state.symbols
    tools = state.selected_tools
    timeout = state.timeout_seconds
    use_cache = state.enable_caching

    logger.info(f"🔍 Parallel Fetcher Subagent: Analyzing API selection for {symbols}")

    # Note: We don't early-return if symbols is empty anymore, because we want to fetch general market news
    if not tools:
        logger.warning("No tools selected, skipping fetch")
        state.raw_data = {}
        state.selected_apis = {}
        return state

    # DECISION MAKING: Select specific APIs based on tools
    selected_apis = {}
    api_tasks = []

    try:
        # Strategy for price/market data
        if any(tool in tools for tool in ["yfinance", "alphavantage", "polygon", "price", "comparison"]):
            price_apis = []

            # Priority 1: yfinance (if explicitly selected in tools)
            if "yfinance" in tools and yf is not None:
                price_apis.append("yfinance")
                for symbol in symbols:
                    api_tasks.append(("yfinance", fetch_yfinance_quote(symbol, use_cache)))
                logger.info("✅ API Decision: yfinance selected (standalone tool - fast & free)")

            # Priority 2: Alpha Vantage
            if "alphavantage" in tools:
                price_apis.append("alphavantage")
                for symbol in symbols:
                    api_tasks.append(("alphavantage", fetch_alphavantage_quote(symbol, use_cache)))
                logger.info("✅ API Decision: Alpha Vantage selected (secondary)")

            # Priority 3: Polygon.io (backup)
            if "polygon" in tools:
                price_apis.append("polygon")
                for symbol in symbols:
                    api_tasks.append(("polygon", fetch_polygon_previous_close(symbol, use_cache)))
                logger.info("✅ API Decision: Polygon.io selected (tertiary)")

            if price_apis:
                selected_apis["price"] = price_apis

        # Strategy for news: Try AlphaVantage first, fallback to Tavily, plus general market news
        if "news" in tools:
            news_apis = []

            # Priority 1: AlphaVantage news (more financial-focused)
            from agent_core.tools.tools import AlphaIntelligence, fetch_alphavantage_news
            if AlphaIntelligence is not None and symbols:
                news_apis.append("alphavantage_news")
                api_tasks.append(("alphavantage_news", fetch_alphavantage_news(symbols, limit=10, use_cache=use_cache)))
                logger.info("✅ API Decision: AlphaVantage News selected (primary - financial focus)")

            # Priority 2: Tavily for symbol-specific news
            if symbols:
                news_apis.append("tavily")
                api_tasks.append(("tavily", fetch_market_news(symbols, limit=10, use_cache=use_cache)))
                logger.info("✅ API Decision: Tavily selected (secondary - symbol-specific)")

            # Priority 3: General market news (macro, economic, political)
            news_apis.append("general_market_news")
            api_tasks.append(("general_market_news", fetch_general_market_news(limit=10, use_cache=use_cache)))
            logger.info("✅ API Decision: General Market News selected (macro/econ/political)")

            selected_apis["news"] = news_apis

        # Log final API selection decision
        logger.info(f"📊 Final API Selection: {selected_apis}")
        state.selected_apis = selected_apis

        # Execute all API calls in parallel with timing
        logger.info(f"🚀 Executing {len(api_tasks)} parallel API calls...")

        start_time = time.time()
        results = await asyncio.wait_for(
            asyncio.gather(*[task for _, task in api_tasks], return_exceptions=True),
            timeout=timeout,
        )
        total_duration_ms = (time.time() - start_time) * 1000

        logger.info(f"✅ All API calls completed in {total_duration_ms:.0f}ms")

        # Organize results by API source and log each tool call
        raw_data = {}
        for i, (api_name, _) in enumerate(api_tasks):
            result = results[i]

            # Determine input parameters for this tool
            if api_name in ["yfinance", "alphavantage", "polygon"]:
                input_params = {"symbols": symbols, "use_cache": use_cache}
            elif api_name in ["alphavantage_news", "tavily"]:
                input_params = {"symbols": symbols, "limit": 10, "use_cache": use_cache}
            elif api_name == "general_market_news":
                input_params = {"limit": 10, "use_cache": use_cache}
            else:
                input_params = {}

            if isinstance(result, Exception):
                logger.error(f"❌ {api_name} failed: {result}")

                # Log failed tool call
                get_structured_logger().log_tool_call(
                    tool_name=api_name,
                    input_data=input_params,
                    output_data=None,
                    duration_ms=None,
                    error=result,
                )
                continue

            if api_name not in raw_data:
                raw_data[api_name] = []

            logger.info(f"📦 {api_name}: result type={type(result)}, is_list={isinstance(result, list)}, len={len(result) if isinstance(result, list) else 'N/A'}")

            if isinstance(result, list):
                raw_data[api_name].extend(result)
            elif result:  # Non-empty dict
                raw_data[api_name].append(result)

            # Log successful tool call
            get_structured_logger().log_tool_call(
                tool_name=api_name,
                input_data=input_params,
                output_data=result,
                duration_ms=total_duration_ms / len(api_tasks),  # Approximate per-tool time
            )

        # Log which APIs successfully returned data (with actual content in debug mode)
        for api_name, data in raw_data.items():
            if data:
                logger.info(f"✅ {api_name}: Retrieved {len(data)} data points")

                # Log actual tool results content for debugging
                if logger.isEnabledFor(logging.DEBUG):
                    import json
                    logger.debug(f"📄 {api_name} FULL RESULTS:")
                    logger.debug(json.dumps(data, indent=2, default=str))
                else:
                    # Even in INFO mode, show a preview of the data
                    for idx, item in enumerate(data[:3]):  # Show first 3 items
                        if isinstance(item, dict):
                            # Show key fields for preview
                            if "title" in item:  # News item
                                logger.info(f"   [{idx+1}] 📰 {item.get('title', 'N/A')[:80]}...")
                            elif "symbol" in item:  # Market data
                                logger.info(f"   [{idx+1}] 💰 {item.get('symbol')}: ${item.get('price', 'N/A')}")
                            else:
                                logger.info(f"   [{idx+1}] {str(item)[:100]}...")
                    if len(data) > 3:
                        logger.info(f"   ... and {len(data) - 3} more items")
            else:
                logger.warning(f"⚠️  {api_name}: No data returned")

        logger.info(f"✅ Parallel fetch complete: {len(raw_data)} APIs returned data")

        state.raw_data = raw_data

    except asyncio.TimeoutError:
        logger.error(f"❌ Fetch timeout after {timeout}s")
        state.error = f"Data fetch timeout ({timeout}s)"
        state.raw_data = {}
    except Exception as e:
        logger.error(f"❌ Fetch error: {e}", exc_info=True)
        state.error = str(e)
        state.raw_data = {}

    return state


# ====== NODE 3.5: WEB RESEARCH (OPTIONAL) ======
async def node_web_research(state: MarketState) -> MarketState:
    """
    Perform web research on news articles (triggered for news_search intent).

    Browses URLs from news_data using Playwright, extracts content, and scores relevance.

    Flow:
    1. Check if news_search intent and news_data available
    2. Convert news items to research format
    3. Run research loop (multi-hop browsing)
    4. Update state with research results

    State updates:
    - state.research_chunks: List of content chunks with scores
    - state.research_citations: List of source URLs
    - state.research_confidence: Overall confidence score (0-1)
    """
    # Only run for news_search intent
    if state.intent != "news_search":
        logger.info("⏭️  Skipping web research (not news_search)")
        return state

    # Extract news items from raw_data (before merger)
    # Priority: Tavily first (symbol-specific), then AlphaVantage, then general news
    raw_data = state.raw_data
    news_items = []

    if raw_data:
        # Prioritize sources by relevance
        news_sources = ["tavily", "alphavantage_news", "general_market_news"]
        for source in news_sources:
            if source not in raw_data:
                continue

            for item in raw_data[source]:
                if not item or not item.get("url"):
                    continue

                news_items.append({
                    "title": item.get("title", ""),
                    "url": item["url"],
                    "source_website": item.get("source_website", "unknown"),
                })

                # Limit to top 5 articles total
                if len(news_items) >= 5:
                    break

            if len(news_items) >= 5:
                break

    if not news_items:
        logger.info("⏭️  Skipping web research (no news items in raw_data)")
        return state

    logger.info(f"🌐 Starting web research for {len(news_items)} news items")

    try:
        # Import here to avoid circular dependencies
        from agent_core.tools.web_research import research_loop

        # Run research loop
        research_result = await research_loop(
            news_items=news_items,
            query=state.query,
            max_hops=2,  # Allow up to 2 browsing hops
            max_urls=3,  # Browse 3 URLs per hop
        )

        # Update state with research results
        state.research_chunks = research_result["content_chunks"]
        state.research_citations = research_result["citations"]
        state.research_confidence = research_result["confidence"]

        logger.info(
            f"✅ Web research complete: {len(state.research_chunks)} chunks, "
            f"confidence={state.research_confidence:.2f}"
        )

        # Log research summary
        get_structured_logger().log_tool_call(
            tool_name="web_research",
            input_data={
                "query": state.query,
                "news_items": len(news_items),
                "max_hops": 2,
                "max_urls": 3,
            },
            output_data={
                "chunks": len(state.research_chunks),
                "citations": state.research_citations,
                "confidence": state.research_confidence,
            },
            duration_ms=0,  # Timing handled internally
        )

    except Exception as e:
        logger.error(f"❌ Web research error: {e}", exc_info=True)
        # Don't fail the whole pipeline - just skip research
        state.research_chunks = []
        state.research_citations = []
        state.research_confidence = 0.0

    return state


# ====== NODE 3.6: GENERAL RESEARCH (OPTIONAL) ======
async def node_general_research(state: MarketState) -> MarketState:
    """
    Perform general research on any topic (not stock-specific).

    **NEW: Uses checklist-based parallel query execution**

    Triggers for "research" intent queries like:
    - "is that related to earnings call?"
    - "what is AI spending?"
    - "tell me about product launches"
    - "meta and nvda p/e ratio" -> Executes 2 parallel queries: ["META P/E ratio", "NVDA P/E ratio"]

    Uses Tavily search + Playwright browsing for general topics.
    Each checklist query gets minimum 5 Tavily results.

    State updates:
    - state.research_chunks: List of content chunks with scores
    - state.research_citations: List of source URLs
    - state.research_confidence: Overall confidence score (0-1)
    - state.research_checklist: Updated with completion status
    """
    # Only run for research intent
    if state.intent != "research":
        logger.info("⏭️  Skipping general research (not research intent)")
        return state

    logger.info(f"🔬 Starting general research for query: {state.query}")

    try:
        # Check if we have a checklist to execute
        if state.research_checklist and len(state.research_checklist) > 0:
            # NEW: Use parallel query execution with checklist
            from agent_core.tools.general_research import parallel_query_research
            from datetime import datetime

            logger.info(f"📋 Executing {len(state.research_checklist)} queries in parallel")

            # Convert checklist to dict format for parallel execution
            checklist_items = [
                {
                    "query": item.query,
                    "symbols": item.symbols,
                    "keywords": item.keywords,
                }
                for item in state.research_checklist
            ]

            # Execute all queries in parallel with minimum 5 results each
            research_result = await parallel_query_research(
                checklist_items=checklist_items,
                min_results_per_query=5,  # Minimum 5 Tavily results per query
                max_browse_per_query=3,   # Browse top 3 URLs per query
                min_confidence=0.4,
            )

            # Update checklist with completion status
            checklist_results = research_result.get("checklist_results", [])
            for i, result in enumerate(checklist_results):
                if i < len(state.research_checklist):
                    state.research_checklist[i].completed = True
                    state.research_checklist[i].result_count = result.get("search_count", 0)
                    state.research_checklist[i].timestamp_completed = datetime.now(timezone.utc).isoformat()

            # Update state with combined results
            state.research_chunks = research_result["content_chunks"]
            state.research_citations = research_result["sources"]
            state.research_confidence = research_result["confidence"]

            logger.info(
                f"✅ Parallel research complete: {len(state.research_chunks)} chunks from "
                f"{len(checklist_items)} queries, confidence={state.research_confidence:.2f}"
            )

            # Log checklist completion
            for i, item in enumerate(state.research_checklist, 1):
                status = "✓" if item.completed else "✗"
                logger.info(f"   {status} {i}. {item.query} ({item.result_count} results)")

            # Log research summary
            get_structured_logger().log_tool_call(
                tool_name="parallel_query_research",
                input_data={
                    "query": state.query,
                    "checklist_queries": [item.query for item in state.research_checklist],
                    "min_results_per_query": 5,
                    "max_browse_per_query": 3,
                },
                output_data={
                    "chunks": len(state.research_chunks),
                    "sources": state.research_citations,
                    "confidence": state.research_confidence,
                    "queries_executed": research_result.get("queries_executed", []),
                    "summary": research_result["summary"],
                },
                duration_ms=0,  # Timing handled internally
            )

        else:
            # Fallback: No checklist, use legacy general_research
            from agent_core.tools.general_research import general_research

            logger.info("⚠️  No checklist found, using legacy general research")

            research_result = await general_research(
                query=state.query,
                symbols=state.symbols,
                llm_keywords=state.keywords,
                max_results=10,
                max_browse=5,
                min_confidence=0.4,
            )

            state.research_chunks = research_result["content_chunks"]
            state.research_citations = research_result["sources"]
            state.research_confidence = research_result["confidence"]

            logger.info(
                f"✅ General research complete: {len(state.research_chunks)} chunks, "
                f"confidence={state.research_confidence:.2f}"
            )

    except Exception as e:
        logger.error(f"❌ General research error: {e}", exc_info=True)
        # Don't fail the whole pipeline - just skip research
        state.research_chunks = []
        state.research_citations = []
        state.research_confidence = 0.0

    return state


# ====== NODE 4: DATA MERGER ======
async def node_data_merger(state: MarketState) -> MarketState:
    """
    Merge and deduplicate data from multiple sources.

    Consolidates data into:
    - state.market_data: List[MarketDataItem]
    - state.news_data: List[NewsItem]

    Deduplication strategy:
    - For market data: prefer most recent timestamp
    - For news: deduplicate by URL
    """
    raw_data = state.raw_data
    market_data = []
    news_data = []

    # Process market data (yfinance, alphavantage, polygon)
    market_sources = ["yfinance", "alphavantage", "polygon"]
    symbol_data_map = {}  # {symbol: [MarketDataItem]}

    for source in market_sources:
        if source not in raw_data:
            continue

        for item in raw_data[source]:
            if not item:  # Skip empty responses
                continue

            symbol = item.get("symbol", "")
            if not symbol:
                continue

            market_item = MarketDataItem(
                symbol=symbol,
                price=item.get("price"),
                change_percent=item.get("change_percent"),
                volume=item.get("volume"),
                timestamp=item.get("timestamp"),
                source=item.get("source", source),
                interval=item.get("interval", "daily"),
                metadata=item.get("metadata", {}),
            )

            if symbol not in symbol_data_map:
                symbol_data_map[symbol] = []
            symbol_data_map[symbol].append(market_item)

    # Deduplicate: keep most recent per symbol
    for symbol, items in symbol_data_map.items():
        # Sort by timestamp descending
        items_sorted = sorted(
            items, key=lambda x: x.timestamp if x.timestamp else "", reverse=True
        )
        market_data.append(items_sorted[0])  # Keep most recent

    # Process news data (alphavantage_news, tavily, general_market_news)
    news_sources = ["alphavantage_news", "tavily", "general_market_news"]
    seen_urls = set()

    logger.info(f"Processing news from sources: {[s for s in news_sources if s in raw_data]}")
    for source in news_sources:
        if source not in raw_data:
            continue

        logger.info(f"Processing {len(raw_data[source])} items from {source}")
        for item in raw_data[source]:
            if not item:  # Skip empty responses
                continue

            url = item.get("url", "")
            if url and url not in seen_urls:
                news_item = NewsItem(
                    title=item.get("title", ""),
                    summary=item.get("summary", ""),
                    url=url,
                    source=item.get("source", "unknown"),
                    published_at=item.get("published_at", ""),
                    sentiment=item.get("sentiment"),
                    symbols=item.get("symbols", []),
                    source_website=item.get("source_website", "unknown"),
                    category=item.get("category", "general"),
                )
                news_data.append(news_item)
                seen_urls.add(url)

    logger.info(f"Merged data: {len(market_data)} market items, {len(news_data)} news items")

    state.market_data = market_data
    state.news_data = news_data
    return state


# ====== NODE 5: SUMMARIZER ======
def get_summary_instructions(output_mode: str) -> str:
    """Get summary instructions based on output mode."""

    base_instructions = """You are a professional market analyst assistant. You can:
1. Provide market insights based on real-time data
2. Answer general questions and have casual conversations
3. Adapt your communication style based on the output format

"""

    if output_mode == "voice":
        # Oral output - conversational, natural flow
        return base_instructions + """
**OUTPUT MODE: VOICE (Oral)**

Your response will be read aloud, so:
- Use natural, conversational language (like you're talking to a friend)
- Avoid heavy formatting (minimal markdown, no complex tables)
- Use shorter sentences and natural transitions
- Say numbers naturally ("two hundred fifty dollars" or "$250")
- Be concise but warm and engaging
- For greetings/chat: Be friendly and conversational

Example voice output:
"Hey! Tesla is currently trading at about 250 dollars and 50 cents, up 2.3 percent from yesterday. The volume looks strong at 15.2 million shares, which shows there's a lot of investor interest right now. The recent news has been pretty positive, especially around their Q4 earnings expectations. Overall, the short-term trend is looking good."

For chat/greetings: "Hello! I'm your market assistant. I can help you check stock prices, get the latest financial news, or just chat about markets. What would you like to know?"
"""
    else:
        # Text output - structured, professional
        return base_instructions + """
**OUTPUT MODE: TEXT (Written)**

Your response will be read on screen, so:
- Use proper markdown formatting (bold, bullets, sections)
- Include specific numbers and data points
- Structure information clearly with headers
- Use tables if comparing multiple items
- Be concise but comprehensive (~200 words)
- Cite sources when referencing news

Example text output:
**Market Analysis for TSLA**

Tesla (TSLA) is currently trading at **$250.50**, up **2.3%** from the previous close. Volume is strong at **15.2M shares**, indicating high investor interest.

**Key Insights:**
- Price broke above the 50-day moving average, signaling bullish momentum
- Recent news highlights strong Q4 earnings expectations
- Sentiment: Positive

**Outlook:** Short-term trend remains positive with continued volume support. Watch for resistance at $255.

*Data sources: Alpha Vantage, Polygon.io*

For chat/greetings: Use warm but professional tone with minimal formatting.
"""


async def node_summarizer(state: MarketState) -> MarketState:
    """
    Generate LLM-based summary adapting to output mode and handling chat intents.

    Supports:
    - Voice output (oral, conversational)
    - Text output (written, structured)
    - Chat intents (greetings, casual conversation)
    - Multiple intents (combines all data into one response)

    Updates state.summary
    """
    query = state.query
    output_mode = state.output_mode
    intents = state.intents
    market_data = state.market_data
    news_data = state.news_data

    # Check if this is a pure chat query (no market data needed)
    is_chat_only = all(intent.intent == "chat" for intent in intents)

    if is_chat_only or (not market_data and not news_data and any(intent.intent == "chat" for intent in intents)):
        # Handle conversational queries directly
        try:
            instructions = get_summary_instructions(output_mode)
            prompt = f"""{instructions}

User query: {query}

This is a conversational query (no market data needed). Please respond in a friendly, helpful way appropriate for {output_mode} mode.
Respond naturally (no JSON format needed for chat)."""

            logger.info(f"🤖 Generating conversational response ({output_mode} mode)...")

            # Measure LLM call time
            start_time = time.time()
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            duration_ms = (time.time() - start_time) * 1000

            # Log detailed LLM query
            get_structured_logger().log_llm_query(
                model="glm-4.5-flash",
                prompt=prompt,
                response=response.content,
                duration_ms=duration_ms,
            )

            state.summary = response.content.strip()
            logger.info(f"✅ Generated chat response ({duration_ms:.0f}ms, {len(state.summary)} chars)")
            return state

        except Exception as e:
            logger.error(f"❌ Chat response error: {e}", exc_info=True)
            state.summary = "I'm here to help! I can check stock prices, get news, or just chat. What would you like to know?"
            return state

    # Check if we have any data to summarize (market, news, or research)
    if not market_data and not news_data and not state.research_chunks:
        logger.warning("No data to summarize")
        if output_mode == "voice":
            state.summary = "I couldn't find any data for your request. Could you try rephrasing or ask about a different stock?"
        else:
            state.summary = "No data available for the requested query."
        return state

    # Format data for LLM
    market_data_str = "\n".join(
        [
            f"- {item.symbol}: ${item.price}, {item.change_percent:+.2f}%, Volume: {item.volume:,} ({item.source})"
            for item in market_data
        ]
    )

    news_data_str = "\n".join(
        [f"- [{item.title}]({item.url}) - {item.summary} (source: {item.source_website})" for item in news_data[:5]]
    )

    intents_str = ', '.join([intent.intent for intent in intents])

    try:
        import json
        import re

        # Use centralized prompt with chat history
        prompt = get_response_generator_prompt(
            chat_history=state.chat_history,
            query=query,
            market_data=market_data_str,
            news_data=news_data_str,
            intents=intents_str,
            output_mode=output_mode
        )

        logger.info(f"🤖 Generating summary ({output_mode} mode, {len(intents)} intent(s))...")

        # Prepare full prompt for logging
        full_messages = [
            SystemMessage(content=GENERAL_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        full_prompt_text = f"System: {GENERAL_SYSTEM_PROMPT}\n\nUser: {prompt}"

        # Measure LLM call time
        start_time = time.time()
        response = await llm.ainvoke(full_messages)
        duration_ms = (time.time() - start_time) * 1000

        # Log detailed LLM query (COMPLETE input/output - NO TRUNCATION)
        get_structured_logger().log_llm_query(
            model="glm-4.5-flash (summary_generator)",
            prompt=full_prompt_text,
            response=response.content,
            duration_ms=duration_ms,
        )

        logger.info(f"✅ Summary LLM response received ({duration_ms:.0f}ms, {len(response.content)} chars)")

        # Extract JSON from response
        content = response.content.strip()

        # Check if content is empty
        if not content:
            raise ValueError("LLM returned empty response")

        # Remove markdown code blocks if present
        if content.startswith("```"):
            # Extract content between ```json and ``` or ``` and ```
            code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if code_match:
                content = code_match.group(1).strip()

        # Try to parse the whole content as JSON first
        try:
            result_dict = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            json_match = re.search(r'\{[^\{]*"summary".*?\}', content, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    result_dict = json.loads(json_str)
                except json.JSONDecodeError:
                    # If still fails, treat as raw text
                    logger.warning(f"LLM response not in valid JSON format, using raw content as summary")
                    result_dict = {
                        "summary": content,
                        "key_insights": [],
                        "sentiment": "neutral"
                    }
            else:
                # No JSON found, treat as raw text
                logger.warning(f"No JSON found in LLM response, using raw content as summary")
                result_dict = {
                    "summary": content,
                    "key_insights": [],
                    "sentiment": "neutral"
                }

        # Format final summary based on output mode
        if output_mode == "voice":
            # Voice: minimal formatting, natural flow
            summary = result_dict['summary']
            # Optionally append insights conversationally
            if result_dict.get('key_insights'):
                summary += " Here are the key takeaways: " + ". ".join(result_dict['key_insights'])
        else:
            # Text: structured with markdown
            summary = f"{result_dict['summary']}\n\n**Key Insights:**\n"
            summary += "\n".join([f"- {insight}" for insight in result_dict.get('key_insights', [])])
            summary += f"\n\n**Overall Sentiment:** {result_dict.get('sentiment', 'neutral')}"

        logger.info(f"✅ Generated summary ({len(summary)} chars, {output_mode} mode)")
        state.summary = summary

    except Exception as e:
        logger.error(f"❌ Summarization error: {e}", exc_info=True)
        state.error = str(e)
        if output_mode == "voice":
            state.summary = "Sorry, I had trouble analyzing that data. Could you try asking again?"
        else:
            state.summary = "Error generating summary."

    return state


# ====== NODE 6: MEMORY WRITER ======
async def node_memory_writer(state: MarketState) -> MarketState:
    """
    Persist summary and context to long-term memory.

    Features:
    1. Save query to history
    2. Check for price alerts on watchlist items
    3. Update watchlist if mentioned in query

    Updates state.memory_id
    """
    summary = state.summary
    query = state.query
    intent = state.intent
    symbols = state.symbols
    timestamp = state.timestamp

    # Generate memory ID
    memory_id = f"mem_{datetime.now(timezone.utc).timestamp()}"

    # Save query to history
    save_query(query, intent, symbols, summary, memory_id)
    logger.info(f"Query saved to history with ID: {memory_id}")

    # Check price alerts for watchlist items
    alerts = []
    for symbol in symbols:
        if watchlist.get(symbol):  # Symbol is in watchlist
            # Find current price from market data
            for item in state.market_data:
                if item.symbol == symbol and item.price:
                    triggered_alerts = watchlist.check_alerts(symbol, item.price)
                    alerts.extend(triggered_alerts)

    if alerts:
        logger.info(f"Price alerts triggered: {alerts}")
        # Append alerts to summary
        state.summary += "\n\n**Price Alerts:**\n" + "\n".join(alerts)

    state.memory_id = memory_id
    return state


# ====== COMBINED NODE: RESPONSE GENERATOR ======
async def node_response_generator(state: MarketState) -> MarketState:
    """
    Combined node that:
    1. Merges and deduplicates data from multiple sources (data_merger)
    2. Generates LLM-based summary (summarizer)
    3. Optionally persists to memory (memory_writer)

    Returns the overall reply to user and optional memory.
    This simplifies the graph by combining 3 nodes into one.
    """
    # STEP 1: DATA MERGING (from node_data_merger)
    raw_data = state.raw_data
    market_data = []
    news_data = []

    if raw_data:
        # Process market data (yfinance, alphavantage, polygon)
        market_sources = ["yfinance", "alphavantage", "polygon"]
        symbol_data_map = {}  # {symbol: [MarketDataItem]}

        for source in market_sources:
            if source not in raw_data:
                continue

            for item in raw_data[source]:
                if not item:  # Skip empty responses
                    continue

                symbol = item.get("symbol", "")
                if not symbol:
                    continue

                market_item = MarketDataItem(
                    symbol=symbol,
                    price=item.get("price"),
                    change_percent=item.get("change_percent"),
                    volume=item.get("volume"),
                    timestamp=item.get("timestamp"),
                    source=item.get("source", source),
                    interval=item.get("interval", "daily"),
                    metadata=item.get("metadata", {}),
                )

                if symbol not in symbol_data_map:
                    symbol_data_map[symbol] = []
                symbol_data_map[symbol].append(market_item)

        # Deduplicate: keep most recent per symbol
        for symbol, items in symbol_data_map.items():
            # Sort by timestamp descending
            items_sorted = sorted(
                items, key=lambda x: x.timestamp if x.timestamp else "", reverse=True
            )
            market_data.append(items_sorted[0])  # Keep most recent

        # Process news data (alphavantage_news, tavily, general_market_news)
        news_sources = ["alphavantage_news", "tavily", "general_market_news"]
        seen_urls = set()

        for source in news_sources:
            if source not in raw_data:
                continue

            for item in raw_data[source]:
                if not item:  # Skip empty responses
                    continue

                url = item.get("url", "")
                if url and url not in seen_urls:
                    news_item = NewsItem(
                        title=item.get("title", ""),
                        summary=item.get("summary", ""),
                        url=url,
                        source=item.get("source", "unknown"),
                        published_at=item.get("published_at", ""),
                        sentiment=item.get("sentiment"),
                        symbols=item.get("symbols", []),
                        source_website=item.get("source_website", "unknown"),
                        category=item.get("category", "general"),
                    )
                    news_data.append(news_item)
                    seen_urls.add(url)

        logger.info(f"Merged data: {len(market_data)} market items, {len(news_data)} news items")

        # Log merged data content
        if market_data:
            logger.info(f"📊 Merged Market Data:")
            for item in market_data:
                logger.info(f"   • {item.symbol}: ${item.price} ({item.change_percent:+.2f}%) vol={item.volume} [{item.source}]")

        if news_data:
            logger.info(f"📰 Merged News Data:")
            for idx, item in enumerate(news_data[:5], 1):  # Show first 5
                symbols_str = f"[{','.join(item.symbols)}]" if item.symbols else "[General]"
                logger.info(f"   [{idx}] {symbols_str} {item.title[:70]}...")
                logger.info(f"       {item.summary[:100]}...")
            if len(news_data) > 5:
                logger.info(f"   ... and {len(news_data) - 5} more news items")

        state.market_data = market_data
        state.news_data = news_data

    # STEP 2: SUMMARIZATION (from node_summarizer)
    query = state.query
    output_mode = state.output_mode
    intents = state.intents

    # Check if this is a pure chat query (no market data needed)
    is_chat_only = all(intent.intent == "chat" for intent in intents)

    if is_chat_only or (not market_data and not news_data and any(intent.intent == "chat" for intent in intents)):
        # Handle conversational queries directly
        try:
            # Use centralized chat prompt with chat history
            prompt = get_chat_response_prompt(state.chat_history, query, output_mode)

            logger.info(f"Generating conversational response ({output_mode} mode)...")
            response = await llm.ainvoke([
                SystemMessage(content=GENERAL_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ])

            state.summary = response.content.strip()
            logger.info(f"✅ Generated chat response ({len(state.summary)} chars)")

            # No memory for pure chat
            return state

        except Exception as e:
            logger.error(f"❌ Chat response error: {e}", exc_info=True)
            state.summary = "I'm here to help! I can check stock prices, get news, or just chat. What would you like to know?"
            return state

    # ====== CHECKLIST COMPLETION WAIT ======
    # If we have a research checklist, wait for all items to complete or timeout (2 minutes)
    if state.research_checklist and len(state.research_checklist) > 0:
        import asyncio

        logger.info(f"📋 Checking research checklist completion ({len(state.research_checklist)} items)...")

        # Check if all checklist items are completed
        all_completed = all(item.completed for item in state.research_checklist)

        if not all_completed:
            logger.warning("⚠️  Not all checklist items completed!")
            incomplete_items = [item.query for item in state.research_checklist if not item.completed]
            logger.warning(f"   Incomplete: {incomplete_items}")

            # Wait up to 2 minutes (120 seconds) for completion
            max_wait_time = 120.0  # 2 minutes
            wait_interval = 0.5  # Check every 0.5 seconds
            elapsed_time = 0.0

            logger.info(f"⏳ Waiting up to {max_wait_time}s for checklist completion...")

            while elapsed_time < max_wait_time:
                # Check if all items are now completed
                all_completed = all(item.completed for item in state.research_checklist)
                if all_completed:
                    logger.info(f"✅ All checklist items completed after {elapsed_time:.1f}s")
                    break

                # Wait and increment
                await asyncio.sleep(wait_interval)
                elapsed_time += wait_interval

            if not all_completed:
                logger.warning(f"⏱️  Timeout reached ({max_wait_time}s). Proceeding with available data.")
                incomplete_count = len([item for item in state.research_checklist if not item.completed])
                logger.warning(f"   {incomplete_count}/{len(state.research_checklist)} items incomplete")
        else:
            logger.info("✅ All checklist items already completed")

        # Log final checklist status
        logger.info("📋 Final checklist status:")
        for i, item in enumerate(state.research_checklist, 1):
            status = "✓" if item.completed else "✗"
            logger.info(f"   {status} {i}. {item.query} ({item.result_count} results)")

    # Check if we have any data to summarize (market, news, or research)
    if not market_data and not news_data and not state.research_chunks:
        logger.warning("No data to summarize")
        if output_mode == "voice":
            state.summary = "I couldn't find any data for your request. Could you try rephrasing or ask about a different stock?"
        else:
            state.summary = "No data available for the requested query."
        return state

    # Format data for LLM
    market_data_str = "\n".join(
        [
            f"- {item.symbol}: ${item.price}, {item.change_percent:+.2f}%, Volume: {item.volume:,} ({item.source})"
            for item in market_data
        ]
    )

    # Use research chunks if available (from web research), otherwise use news summaries
    if state.research_chunks and len(state.research_chunks) > 0:
        # Build detailed news context from web research
        news_data_str = "Web Research Results:\n"
        for idx, chunk in enumerate(state.research_chunks[:5], 1):  # Top 5 chunks
            content_preview = chunk["content"][:300] + "..." if len(chunk["content"]) > 300 else chunk["content"]
            news_data_str += f"{idx}. {content_preview}\n   Source: {chunk['url']}\n\n"

        # Add confidence note
        if state.research_confidence < 0.6:
            news_data_str += "\nNote: Research confidence is low - limited relevant sources found.\n"

        # Add citations
        if state.research_citations:
            news_data_str += f"\nSources ({len(state.research_citations)} total):\n"
            for url in state.research_citations[:3]:  # Top 3 citations
                news_data_str += f"- {url}\n"
    else:
        # Fallback to news summaries
        news_data_str = "\n".join(
            [f"- [{item.title}]({item.url}) - {item.summary} (source: {item.source_website})" for item in news_data]
        )

    intents_str = ', '.join([intent.intent for intent in intents])

    try:
        import json
        import re

        # Use centralized prompt with chat history
        prompt = get_response_generator_prompt(
            chat_history=state.chat_history,
            query=query,
            market_data=market_data_str,
            news_data=news_data_str,
            intents=intents_str,
            output_mode=output_mode
        )

        logger.info(f"🤖 Generating summary ({output_mode} mode, {len(intents)} intent(s))...")

        # Prepare full prompt for logging
        full_messages = [
            SystemMessage(content=GENERAL_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        full_prompt_text = f"System: {GENERAL_SYSTEM_PROMPT}\n\nUser: {prompt}"

        # Measure LLM call time
        start_time = time.time()
        response = await llm.ainvoke(full_messages)
        duration_ms = (time.time() - start_time) * 1000

        # Log detailed LLM query (COMPLETE input/output - NO TRUNCATION)
        get_structured_logger().log_llm_query(
            model="glm-4.5-flash (summary_generator)",
            prompt=full_prompt_text,
            response=response.content,
            duration_ms=duration_ms,
        )

        logger.info(f"✅ Summary LLM response received ({duration_ms:.0f}ms, {len(response.content)} chars)")

        # Extract JSON from response
        content = response.content.strip()

        # Check if content is empty
        if not content:
            raise ValueError("LLM returned empty response")

        # Remove markdown code blocks if present
        if content.startswith("```"):
            # Extract content between ```json and ``` or ``` and ```
            code_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if code_match:
                content = code_match.group(1).strip()

        # Try to parse the whole content as JSON first
        try:
            result_dict = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            json_match = re.search(r'\{[^\{]*"summary".*?\}', content, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    result_dict = json.loads(json_str)
                except json.JSONDecodeError:
                    # If still fails, treat as raw text
                    logger.warning(f"LLM response not in valid JSON format, using raw content as summary")
                    result_dict = {
                        "summary": content,
                        "key_insights": [],
                        "sentiment": "neutral"
                    }
            else:
                # No JSON found, treat as raw text
                logger.warning(f"No JSON found in LLM response, using raw content as summary")
                result_dict = {
                    "summary": content,
                    "key_insights": [],
                    "sentiment": "neutral"
                }

        # Format final summary based on output mode
        if output_mode == "voice":
            # Voice: minimal formatting, natural flow
            summary = result_dict['summary']
            # Optionally append insights conversationally
            if result_dict.get('key_insights'):
                summary += " Here are the key takeaways: " + ". ".join(result_dict['key_insights'])
        else:
            # Text: structured with markdown
            summary = f"{result_dict['summary']}\n\n**Key Insights:**\n"
            summary += "\n".join([f"- {insight}" for insight in result_dict.get('key_insights', [])])
            summary += f"\n\n**Overall Sentiment:** {result_dict.get('sentiment', 'neutral')}"

        logger.info(f"✅ Generated summary ({len(summary)} chars, {output_mode} mode)")
        state.summary = summary

    except Exception as e:
        logger.error(f"❌ Summarization error: {e}", exc_info=True)
        state.error = str(e)
        if output_mode == "voice":
            state.summary = "Sorry, I had trouble analyzing that data. Could you try asking again?"
        else:
            state.summary = "Error generating summary."
        return state

    # STEP 3: MEMORY PERSISTENCE (from node_memory_writer) - OPTIONAL
    # Only save to memory if we have meaningful data (not for pure chat)
    if market_data or news_data:
        intent = state.intent
        symbols = state.symbols

        # Generate memory ID
        memory_id = f"mem_{datetime.now(timezone.utc).timestamp()}"

        # Save query to history
        save_query(query, intent, symbols, state.summary, memory_id)
        logger.info(f"Query saved to history with ID: {memory_id}")

        # Check price alerts for watchlist items
        alerts = []
        for symbol in symbols:
            if watchlist.get(symbol):  # Symbol is in watchlist
                # Find current price from market data
                for item in state.market_data:
                    if item.symbol == symbol and item.price:
                        triggered_alerts = watchlist.check_alerts(symbol, item.price)
                        alerts.extend(triggered_alerts)

        if alerts:
            logger.info(f"Price alerts triggered: {alerts}")
            # Append alerts to summary
            if output_mode == "voice":
                state.summary += " " + " ".join(alerts)
            else:
                state.summary += "\n\n**Price Alerts:**\n" + "\n".join(alerts)

        state.memory_id = memory_id
    else:
        logger.info("Skipping memory save for chat-only query")
        state.memory_id = None

    return state

"""
Example usage and test script for Market Assistant Agent.

Demonstrates various query types and streaming capabilities.
"""

import asyncio
import logging
import os
from agent_core.graph import run_market_agent, compile_graph
from agent_core.state import MarketState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ====== SIMPLE USAGE ======
async def simple_example():
    """Basic single query execution."""
    print("\n" + "=" * 80)
    print("SIMPLE EXAMPLE: Single Query")
    print("=" * 80)

    query = "What's Tesla's current stock price?"
    result = await run_market_agent(query)

    if result.error:
        print(f"❌ Error: {result.error}")
    else:
        print(f"✅ Intent: {result.intent}")
        print(f"✅ Symbols: {result.symbols}")
        print(f"✅ Timeframe: {result.timeframe}")
        print(f"✅ Tools Used: {result.selected_tools}")
        print(f"\n📊 Market Data:")
        for item in result.market_data:
            print(f"  - {item.symbol}: ${item.price} ({item.change_percent:+.2f}%) [Source: {item.source}]")
        print(f"\n📝 Summary:\n{result.summary}")
        print(f"\n💾 Memory ID: {result.memory_id}")


# ====== BATCH QUERIES ======
async def batch_example():
    """Execute multiple queries in sequence."""
    print("\n" + "=" * 80)
    print("BATCH EXAMPLE: Multiple Queries")
    print("=" * 80)

    queries = [
        "What's AAPL stock price?",
        "Compare NVDA and AMD performance",
        "Latest news on Microsoft",
        "Market summary for tech stocks",
    ]

    results = []
    for query in queries:
        print(f"\n🔍 Query: {query}")
        result = await run_market_agent(query, timeout_seconds=15.0)
        results.append((query, result))

        if result.error:
            print(f"   ❌ Error: {result.error}")
        else:
            print(f"   ✅ Intent: {result.intent}, Symbols: {result.symbols}")
            print(f"   ✅ Summary: {result.summary[:100]}...")

    print(f"\n📊 Completed {len(results)} queries")


# ====== PARALLEL QUERIES ======
async def parallel_example():
    """Execute multiple queries in parallel."""
    print("\n" + "=" * 80)
    print("PARALLEL EXAMPLE: Concurrent Queries")
    print("=" * 80)

    queries = [
        "What's TSLA price?",
        "What's NVDA price?",
        "What's AMD price?",
        "What's AAPL price?",
    ]

    # Run all queries concurrently
    tasks = [run_market_agent(query) for query in queries]
    results = await asyncio.gather(*tasks)

    print("\n📊 Results:")
    for query, result in zip(queries, results):
        if result.error:
            print(f"  {query}: ❌ {result.error}")
        else:
            symbol = result.symbols[0] if result.symbols else "N/A"
            price = result.market_data[0].price if result.market_data else "N/A"
            print(f"  {query}: ✅ {symbol} @ ${price}")


# ====== STREAMING EXAMPLE (PLACEHOLDER) ======
async def streaming_example():
    """
    Demonstrate streaming execution (future enhancement).

    In production, you can stream intermediate node outputs:
    - Stream intent analysis
    - Stream each tool's results as they arrive
    - Stream summary generation token by token
    """
    print("\n" + "=" * 80)
    print("STREAMING EXAMPLE (Placeholder)")
    print("=" * 80)

    app = compile_graph()
    query = "Compare TSLA and NVDA"

    print(f"🔍 Query: {query}")
    print("\n📡 Streaming node outputs:\n")

    initial_state = MarketState(query=query)

    # For streaming, use astream() instead of ainvoke()
    async for event in app.astream(initial_state):
        # Event format: {node_name: state_update}
        for node_name, state_update in event.items():
            if node_name == "intent_analyzer":
                print(f"  ✅ Intent analyzed: {state_update.get('intent', 'unknown')}")
            elif node_name == "parallel_fetcher":
                print(f"  ✅ Data fetched from {len(state_update.get('raw_data', {}))} sources")
            elif node_name == "summarizer":
                summary = state_update.get('summary', '')
                print(f"  ✅ Summary generated ({len(summary)} chars)")

    print("\n📊 Streaming complete")


# ====== CUSTOM CONFIG EXAMPLE ======
async def custom_config_example():
    """Demonstrate custom configuration options."""
    print("\n" + "=" * 80)
    print("CUSTOM CONFIG EXAMPLE")
    print("=" * 80)

    query = "What's Apple's stock price?"

    # Custom config with longer timeout and caching disabled
    result = await run_market_agent(
        query,
        timeout_seconds=20.0,
        max_retries=3,
        enable_caching=False,  # Force fresh data
    )

    if not result.error:
        print(f"✅ Query: {query}")
        print(f"✅ Execution time: ~{result.timeout_seconds}s timeout")
        print(f"✅ Cache enabled: {result.enable_caching}")
        print(f"✅ Result: {result.summary[:150]}...")


# ====== ERROR HANDLING EXAMPLE ======
async def error_handling_example():
    """Demonstrate graceful error handling."""
    print("\n" + "=" * 80)
    print("ERROR HANDLING EXAMPLE")
    print("=" * 80)

    # Test with invalid/empty query
    invalid_queries = [
        "",  # Empty query
        "random gibberish that makes no sense",  # No symbols
        "What's the price of INVALIDTICKER?",  # Invalid ticker
    ]

    for query in invalid_queries:
        print(f"\n🔍 Query: '{query}'")
        result = await run_market_agent(query)

        if result.error:
            print(f"   ❌ Error (expected): {result.error}")
        elif result.intent == "unknown":
            print(f"   ⚠️  Unknown intent, no action taken")
        else:
            print(f"   ✅ Handled: {result.intent}")


# ====== MAIN TEST RUNNER ======
async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "MARKET ASSISTANT AGENT - EXAMPLES" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    # Check environment variables
    if not os.getenv("ZHIPUAI_API_KEY"):
        print("⚠️  Warning: ZHIPUAI_API_KEY not set. Using mock responses.")

    if not os.getenv("ALPHAVANTAGE_API_KEY"):
        print("⚠️  Warning: ALPHAVANTAGE_API_KEY not set. Using 'demo' key (rate-limited).")

    if not os.getenv("POLYGON_API_KEY"):
        print("⚠️  Warning: POLYGON_API_KEY not set. Polygon.io calls will fail.")

    # Run examples
    try:
        await simple_example()
        await batch_example()
        await parallel_example()
        await streaming_example()
        await custom_config_example()
        await error_handling_example()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"Example execution error: {e}", exc_info=True)

    print("\n" + "=" * 80)
    print("✅ All examples completed")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

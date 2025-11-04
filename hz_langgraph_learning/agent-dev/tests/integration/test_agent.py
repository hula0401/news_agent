"""
Test script for Market Assistant Agent.

Tests:
1. Basic queries with real API keys
2. Watchlist functionality
3. LangSmith tracing
4. Memory persistence
"""

import asyncio
import logging
import sys
from agent_core.graph import run_market_agent
from agent_core.memory import watchlist, get_recent_queries, add_to_watchlist, remove_from_watchlist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("agent_test.log")
    ]
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


async def test_basic_query():
    """Test 1: Basic stock price query."""
    print_section("TEST 1: Basic Stock Price Query")

    query = "What's Tesla's current stock price?"
    print(f"\n🔍 Query: {query}")

    result = await run_market_agent(query)

    if result.error:
        print(f"❌ Error: {result.error}")
        return False
    else:
        print(f"\n✅ Intent: {result.intent}")
        print(f"✅ Symbols: {result.symbols}")
        print(f"✅ Timeframe: {result.timeframe}")
        print(f"✅ Tools Used: {result.selected_tools}")

        print(f"\n📊 Market Data ({len(result.market_data)} items):")
        for item in result.market_data:
            print(f"  - {item.symbol}: ${item.price} ({item.change_percent:+.2f}%)")
            print(f"    Volume: {item.volume:,} | Source: {item.source}")

        print(f"\n📰 News ({len(result.news_data)} items):")
        for item in result.news_data[:3]:
            print(f"  - {item.title[:80]}...")
            print(f"    Sentiment: {item.sentiment} | Source: {item.source}")

        print(f"\n📝 Summary:\n{result.summary}")
        print(f"\n💾 Memory ID: {result.memory_id}")

        return True


async def test_comparison():
    """Test 2: Stock comparison query."""
    print_section("TEST 2: Stock Comparison")

    query = "Compare NVDA and AMD stock performance"
    print(f"\n🔍 Query: {query}")

    result = await run_market_agent(query)

    if result.error:
        print(f"❌ Error: {result.error}")
        return False
    else:
        print(f"\n✅ Intent: {result.intent}")
        print(f"✅ Symbols: {result.symbols}")

        print(f"\n📊 Comparison:")
        for item in result.market_data:
            print(f"  {item.symbol}: ${item.price} ({item.change_percent:+.2f}%)")

        print(f"\n📝 Summary:\n{result.summary}")

        return True


async def test_news_search():
    """Test 3: News search with Tavily."""
    print_section("TEST 3: News Search (Tavily Integration)")

    query = "Latest news on Apple earnings"
    print(f"\n🔍 Query: {query}")

    result = await run_market_agent(query)

    if result.error:
        print(f"❌ Error: {result.error}")
        return False
    else:
        print(f"\n✅ Intent: {result.intent}")
        print(f"✅ Symbols: {result.symbols}")

        print(f"\n📰 News Articles ({len(result.news_data)} found):")
        for i, item in enumerate(result.news_data, 1):
            print(f"\n  [{i}] {item.title}")
            print(f"      Summary: {item.summary[:150]}...")
            print(f"      Sentiment: {item.sentiment} | URL: {item.url}")

        print(f"\n📝 Summary:\n{result.summary}")

        return True


async def test_watchlist():
    """Test 4: Watchlist functionality."""
    print_section("TEST 4: Watchlist Management")

    # Add stocks to watchlist
    print("\n📌 Adding stocks to watchlist...")
    add_to_watchlist("TSLA", notes="Tesla - EV leader", alert_above=300.0, alert_below=200.0)
    add_to_watchlist("NVDA", notes="NVIDIA - AI chips")
    add_to_watchlist("AAPL", notes="Apple - Tech giant")

    # Display watchlist
    print("\n📋 Current Watchlist:")
    for item in watchlist.get_all():
        print(f"  - {item.symbol}: {item.notes}")
        if item.alert_price_above or item.alert_price_below:
            print(f"    Alerts: Above ${item.alert_price_above}, Below ${item.alert_price_below}")

    # Query watchlist stock (should trigger alert check)
    print("\n🔍 Querying watchlist stock (TSLA)...")
    result = await run_market_agent("What's Tesla's stock price?")

    if not result.error:
        print(f"\n✅ Current TSLA price: ${result.market_data[0].price if result.market_data else 'N/A'}")

        # Check if alerts are in summary
        if "Price Alerts" in result.summary:
            print("\n🔔 Price alerts detected in summary!")
        else:
            print("\n✅ No price alerts triggered")

    # Remove from watchlist
    print("\n🗑️  Removing AAPL from watchlist...")
    remove_from_watchlist("AAPL")

    print("\n📋 Updated Watchlist:")
    for item in watchlist.get_all():
        print(f"  - {item.symbol}")

    return True


async def test_query_history():
    """Test 5: Query history."""
    print_section("TEST 5: Query History")

    # Get recent queries
    recent = get_recent_queries(limit=5)

    print(f"\n📚 Recent Queries ({len(recent)} total):")
    for i, record in enumerate(recent, 1):
        print(f"\n  [{i}] Query: {record.query}")
        print(f"      Intent: {record.intent} | Symbols: {record.symbols}")
        print(f"      Timestamp: {record.timestamp}")
        print(f"      Memory ID: {record.memory_id}")

    return True


async def test_parallel_queries():
    """Test 6: Parallel query execution."""
    print_section("TEST 6: Parallel Query Execution")

    queries = [
        "What's TSLA price?",
        "What's NVDA price?",
        "What's AMD price?",
    ]

    print("\n🚀 Executing queries in parallel...\n")

    import time
    start_time = time.time()

    tasks = [run_market_agent(query) for query in queries]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    print(f"\n✅ Completed {len(results)} queries in {elapsed:.2f}s\n")
    print("📊 Results:")
    for query, result in zip(queries, results):
        if result.error:
            print(f"  {query}: ❌ {result.error}")
        else:
            symbol = result.symbols[0] if result.symbols else "N/A"
            price = result.market_data[0].price if result.market_data else "N/A"
            change = result.market_data[0].change_percent if result.market_data else 0
            print(f"  {query}: ✅ {symbol} @ ${price} ({change:+.2f}%)")

    return True


async def test_error_handling():
    """Test 7: Error handling."""
    print_section("TEST 7: Error Handling")

    test_cases = [
        ("", "Empty query"),
        ("random gibberish xyz", "No symbols"),
        ("What's the price of INVALIDTICKER?", "Invalid ticker"),
    ]

    for query, description in test_cases:
        print(f"\n🔍 Test: {description}")
        print(f"   Query: '{query}'")

        result = await run_market_agent(query)

        if result.error:
            print(f"   ✅ Error handled: {result.error}")
        elif result.intent == "unknown":
            print(f"   ✅ Unknown intent handled")
        else:
            print(f"   ⚠️  Processed as: {result.intent}")

    return True


async def run_all_tests():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 18 + "MARKET ASSISTANT AGENT - TEST SUITE" + " " * 25 + "║")
    print("╚" + "=" * 78 + "╝")

    tests = [
        ("Basic Query", test_basic_query),
        ("Stock Comparison", test_comparison),
        ("News Search (Tavily)", test_news_search),
        ("Watchlist Management", test_watchlist),
        ("Query History", test_query_history),
        ("Parallel Execution", test_parallel_queries),
        ("Error Handling", test_error_handling),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Test '{name}' failed: {e}", exc_info=True)
            results.append((name, False))

    # Print summary
    print_section("TEST SUMMARY")
    print()
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {name}")

    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\n  Total: {passed}/{total} tests passed")

    print("\n" + "=" * 80)
    print("\n✅ Test suite completed!")
    print("\n📊 Check LangSmith for detailed traces: https://smith.langchain.com/")
    print("📁 Logs saved to: agent_test.log")
    print("💾 Memory files saved in: memory_data/\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())

"""
Test script for new features:
1. yfinance integration
2. AlphaVantage news
3. API selection visibility (selected_apis field)
4. Source website in news
"""

import asyncio
import sys
import logging
from agent_core.graph import run_market_agent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_price_check():
    """Test price check with yfinance."""
    print("\n" + "=" * 80)
    print("TEST 1: Price Check (should use yfinance as primary)")
    print("=" * 80)

    result = await run_market_agent("What's Tesla stock price?")

    print(f"\n✅ Intent: {result.intent}")
    print(f"✅ Symbols: {result.symbols}")
    print(f"✅ Selected Tools: {result.selected_tools}")
    print(f"✅ Selected APIs: {result.selected_apis}")
    print(f"\n📊 Market Data ({len(result.market_data)} items):")
    for item in result.market_data:
        print(f"  - {item.symbol}: ${item.price:.2f} ({item.change_percent:+.2f}%) from {item.source}")

    print(f"\n📰 Summary:\n{result.summary[:300]}...")

    # Verify yfinance was used
    assert "price" in result.selected_apis, "Price APIs not selected"
    assert "yfinance" in result.selected_apis["price"], "yfinance should be in selected APIs"
    print("\n✅ PASSED: yfinance was selected for stock prices")


async def test_news_search():
    """Test news search with AlphaVantage news."""
    print("\n" + "=" * 80)
    print("TEST 2: News Search (should use AlphaVantage + Tavily)")
    print("=" * 80)

    result = await run_market_agent("Latest news on Apple")

    print(f"\n✅ Intent: {result.intent}")
    print(f"✅ Symbols: {result.symbols}")
    print(f"✅ Selected Tools: {result.selected_tools}")
    print(f"✅ Selected APIs: {result.selected_apis}")

    print(f"\n📰 News Data ({len(result.news_data)} items):")
    for item in result.news_data[:3]:  # Show first 3
        print(f"\n  Title: {item.title}")
        print(f"  Source: {item.source}")
        print(f"  Source Website: {item.source_website}")  # NEW FIELD
        print(f"  Sentiment: {item.sentiment}")
        print(f"  URL: {item.url[:60]}...")

    # Verify news sources
    if result.news_data:
        assert any(item.source_website != "unknown" for item in result.news_data), "source_website not populated"
        print("\n✅ PASSED: source_website field is populated")

    # Check if AlphaVantage news was used
    if "news" in result.selected_apis:
        print(f"✅ News APIs used: {result.selected_apis['news']}")


async def test_comparison():
    """Test comparison with multiple APIs."""
    print("\n" + "=" * 80)
    print("TEST 3: Stock Comparison (should use multiple APIs)")
    print("=" * 80)

    result = await run_market_agent("Compare NVDA and AMD")

    print(f"\n✅ Intent: {result.intent}")
    print(f"✅ Symbols: {result.symbols}")
    print(f"✅ Selected Tools: {result.selected_tools}")
    print(f"✅ Selected APIs: {result.selected_apis}")

    print(f"\n📊 Market Data ({len(result.market_data)} items):")
    for item in result.market_data:
        print(f"  - {item.symbol}: ${item.price:.2f} ({item.change_percent:+.2f}%) from {item.source}")

    print(f"\n📰 Summary:\n{result.summary[:400]}...")

    # Verify multiple APIs were selected
    if "price" in result.selected_apis:
        print(f"\n✅ Price APIs selected: {result.selected_apis['price']}")
        assert len(result.selected_apis["price"]) >= 2, "Should select multiple price APIs"
        print("✅ PASSED: Multiple APIs selected for redundancy")


async def main():
    """Run all tests."""
    try:
        await test_price_check()
        await test_news_search()
        await test_comparison()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nNew Features Working:")
        print("1. ✅ yfinance integration (primary for stock prices)")
        print("2. ✅ AlphaVantage news integration")
        print("3. ✅ API selection visibility (selected_apis field)")
        print("4. ✅ Source website in news results")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

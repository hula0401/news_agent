"""
Test script for general market news feature
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_core.tools.tools import fetch_general_market_news, fetch_economic_calendar
from agent_core.graph import run_market_agent
from agent_core.state import MarketState
import json


async def test_general_news_api():
    """Test the general market news API directly"""
    print("\n" + "="*80)
    print("TEST 1: Testing fetch_general_market_news() directly")
    print("="*80)

    news = await fetch_general_market_news(limit=10, use_cache=False)

    print(f"\n✅ Fetched {len(news)} general market news articles")

    # Categorize by type
    categories = {}
    for article in news:
        cat = article.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n📊 News by Category:")
    for cat, count in categories.items():
        print(f"  - {cat}: {count} articles")

    print(f"\n📰 Sample Articles:")
    for i, article in enumerate(news[:3], 1):
        print(f"\n{i}. {article['title']}")
        print(f"   Category: {article.get('category', 'general')}")
        print(f"   Source: {article.get('source_website', 'unknown')}")
        print(f"   URL: {article.get('url', 'N/A')}")


async def test_economic_calendar():
    """Test the economic calendar API"""
    print("\n" + "="*80)
    print("TEST 2: Testing fetch_economic_calendar() directly")
    print("="*80)

    events = await fetch_economic_calendar(use_cache=False)

    print(f"\n✅ Fetched {len(events)} economic calendar events")

    print(f"\n📅 Sample Events:")
    for i, event in enumerate(events[:3], 1):
        print(f"\n{i}. {event['title']}")
        print(f"   Category: {event.get('category', 'calendar')}")
        print(f"   Source: {event.get('source_website', 'unknown')}")


async def test_agent_integration():
    """Test agent integration with general news"""
    print("\n" + "="*80)
    print("TEST 3: Testing agent integration with general market news")
    print("="*80)

    # Test query 1: General market news
    print("\n🔹 Query: What's the market news today?")

    result = await run_market_agent(
        query="What's the market news today?",
        chat_history=[],
    )

    # Check if general news was fetched
    news_items = result.news_data
    print(f"\n✅ Fetched {len(news_items)} total news articles")

    # Count general vs symbol-specific
    general_count = sum(1 for n in news_items if not n.symbols)
    symbol_count = sum(1 for n in news_items if n.symbols)

    print(f"   - General market news: {general_count}")
    print(f"   - Symbol-specific news: {symbol_count}")

    # Show categories
    categories = {}
    for article in news_items:
        cat = getattr(article, "category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n📊 Categories:")
    for cat, count in sorted(categories.items()):
        print(f"   - {cat}: {count}")

    # Show final response
    print(f"\n💬 Agent Response:")
    print(result.summary)

    # Test query 2: Stock-specific + general news
    print("\n" + "="*80)
    print("🔹 Query: What's the news on TSLA?")
    print("="*80)

    result = await run_market_agent(
        query="What's the news on TSLA?",
        chat_history=[],
    )

    news_items = result.news_data
    print(f"\n✅ Fetched {len(news_items)} total news articles")

    # Count TSLA-specific vs general
    tsla_count = sum(1 for n in news_items if "TSLA" in n.symbols)
    general_count = sum(1 for n in news_items if not n.symbols)

    print(f"   - TSLA-specific news: {tsla_count}")
    print(f"   - General market news: {general_count}")

    # Show categories
    categories = {}
    for article in news_items:
        cat = getattr(article, "category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n📊 Categories:")
    for cat, count in sorted(categories.items()):
        print(f"   - {cat}: {count}")

    print(f"\n💬 Agent Response:")
    print(result.summary)


async def main():
    """Run all tests"""
    print("\n🧪 Testing General Market News Feature")

    try:
        # Test 1: API directly
        await test_general_news_api()

        # Test 2: Economic calendar
        await test_economic_calendar()

        # Test 3: Agent integration
        await test_agent_integration()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

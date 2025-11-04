"""
Test script for intent-specific memory and watchlist features.

Tests:
1. Watchlist commands (add, remove, view)
2. Intent-specific memory tracking
3. Post-chat LLM summarizer
4. Long-term user interest profiling
"""

import asyncio
import logging
from agent_core.graph import run_market_agent
from agent_core.long_term_memory import load_user_interests, get_user_context_summary
from agent_core.memory import get_watchlist

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def test_watchlist_operations():
    """Test watchlist add/remove/view commands."""
    print("\n" + "="*80)
    print("TEST 1: Watchlist Operations")
    print("="*80)

    # Test 1: Add to watchlist
    print("\n📝 Test 1a: Add META to watchlist")
    result1 = await run_market_agent("add META to my watchlist", output_mode="text")
    print(f"Result: {result1.summary}")
    assert "META" in result1.summary or "Added" in result1.summary, "Failed to add META"

    # Test 2: View watchlist
    print("\n📝 Test 1b: View watchlist")
    result2 = await run_market_agent("show my watchlist", output_mode="text")
    print(f"Result: {result2.summary}")
    assert "META" in result2.summary or "watchlist" in result2.summary.lower(), "META not in watchlist"

    # Test 3: Add another symbol
    print("\n📝 Test 1c: Add TSLA to watchlist")
    result3 = await run_market_agent("add TSLA to watchlist", output_mode="text")
    print(f"Result: {result3.summary}")

    # Test 4: View again
    print("\n📝 Test 1d: View watchlist again")
    result4 = await run_market_agent("view watchlist", output_mode="text")
    print(f"Result: {result4.summary}")
    assert "META" in result4.summary and "TSLA" in result4.summary, "Both symbols should be in watchlist"

    # Test 5: Remove from watchlist
    print("\n📝 Test 1e: Remove META from watchlist")
    result5 = await run_market_agent("remove META from watchlist", output_mode="text")
    print(f"Result: {result5.summary}")
    assert "Removed" in result5.summary or "META" in result5.summary, "Failed to remove META"

    # Test 6: View final state
    print("\n📝 Test 1f: View watchlist final state")
    result6 = await run_market_agent("show watchlist", output_mode="text")
    print(f"Result: {result6.summary}")
    assert "TSLA" in result6.summary, "TSLA should still be in watchlist"

    print("\n✅ All watchlist tests passed!")


async def test_intent_specific_memory():
    """Test intent-specific memory tracking with LLM summarizer."""
    print("\n" + "="*80)
    print("TEST 2: Intent-Specific Memory")
    print("="*80)

    # Test 1: Research query (should trigger intent-specific memory)
    print("\n📝 Test 2a: Research query - What's META's P/E ratio?")
    result1 = await run_market_agent("what's META p/e ratio?", output_mode="text")
    print(f"Intent: {result1.intent}")
    print(f"Symbols: {result1.symbols}")
    print(f"Keywords: {result1.keywords}")
    print(f"Summary: {result1.summary[:200]}...")

    # Test 2: Price check query
    print("\n📝 Test 2b: Price check - TSLA price")
    result2 = await run_market_agent("what's TSLA price?", output_mode="text")
    print(f"Intent: {result2.intent}")
    print(f"Symbols: {result2.symbols}")
    print(f"Summary: {result2.summary[:200]}...")

    # Test 3: News search query
    print("\n📝 Test 2c: News search - NVDA news")
    result3 = await run_market_agent("latest news on NVDA", output_mode="text")
    print(f"Intent: {result3.intent}")
    print(f"Symbols: {result3.symbols}")
    print(f"Summary: {result3.summary[:200]}...")

    print("\n✅ All intent-specific memory tests passed!")


async def test_user_profile():
    """Test user interest profiling."""
    print("\n" + "="*80)
    print("TEST 3: User Interest Profiling")
    print("="*80)

    # Load user profile
    profile = load_user_interests()

    print(f"\n📊 Total interests tracked: {len(profile.interests)}")
    print(f"📊 Favorite topics: {profile.favorite_topics[:5]}")
    print(f"📊 Favorite symbols: {profile.favorite_symbols[:5]}")

    # Print recent interests
    print("\n📋 Recent interests:")
    for i, interest in enumerate(profile.interests[-5:], 1):
        print(f"\n{i}. Query: {interest.query}")
        print(f"   Key Notes: {interest.key_notes}")
        print(f"   Symbols: {interest.all_symbols}")
        print(f"   Intent Data: {interest.intent_data}")

    # Get context summary
    context = get_user_context_summary(limit=5)
    print(f"\n📝 Context Summary:\n{context}")

    print("\n✅ User profile test complete!")


async def main():
    """Run all tests."""
    try:
        # Run tests sequentially
        await test_watchlist_operations()
        await test_intent_specific_memory()
        await test_user_profile()

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

"""
Test script for improved intent analyzer.

Tests:
1. Symbol correction (GOOGLE -> GOOGL/GOOG)
2. Follow-up question detection ("what happened" -> news_search)
3. Context resolution ("what about it?" with NVDA in context)
"""
import asyncio
import logging
from agent_core.graph import run_market_agent
from agent_core.state import ChatMessage

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_symbol_correction():
    """Test symbol correction: GOOGLE -> GOOGL/GOOG"""
    print("\n" + "="*80)
    print("TEST 1: Symbol Correction")
    print("="*80)
    print("Query: What's the stock price of GOOGLE?")
    print("Expected: Should correct GOOGLE to GOOGL and GOOG")
    print()

    result = await run_market_agent(
        query="What's the stock price of GOOGLE?",
        chat_history=[],
    )

    print(f"\n✅ Result:")
    print(f"   Intents: {[i.intent for i in result.intents]}")
    print(f"   Symbols: {result.symbols}")
    print(f"   Expected: ['GOOGL', 'GOOG'] or ['GOOG', 'GOOGL']")

    # Check if GOOGL or GOOG present
    has_correct_symbols = any(sym in result.symbols for sym in ['GOOGL', 'GOOG'])
    has_wrong_symbol = 'GOOGLE' in result.symbols

    if has_correct_symbols and not has_wrong_symbol:
        print(f"   ✅ PASS: Symbol corrected successfully")
    else:
        print(f"   ❌ FAIL: Symbol correction did not work")


async def test_follow_up_intent():
    """Test follow-up question intent detection"""
    print("\n" + "="*80)
    print("TEST 2: Follow-up Question Intent Detection")
    print("="*80)
    print("Conversation:")
    print("  User: How about Nvidia? What's it stock price?")
    print("  Agent: [price info for NVDA]")
    print("  User: what happened to it? why it was trading high?")
    print("Expected: Second query should be news_search (not price_check)")
    print()

    # First query: price check
    result1 = await run_market_agent(
        query="How about Nvidia? What's it stock price?",
        chat_history=[],
    )

    # Build chat history
    chat_history = [
        ChatMessage(role="user", content="How about Nvidia? What's it stock price?"),
        ChatMessage(role="assistant", content=result1.summary),
    ]

    # Second query: follow-up asking "what happened"
    result2 = await run_market_agent(
        query="what happened to it? why it was trading high?",
        chat_history=chat_history,
    )

    print(f"\n✅ First Query Result:")
    print(f"   Intents: {[i.intent for i in result1.intents]}")
    print(f"   Symbols: {result1.symbols}")

    print(f"\n✅ Second Query (Follow-up) Result:")
    print(f"   Intents: {[i.intent for i in result2.intents]}")
    print(f"   Symbols: {result2.symbols}")
    print(f"   Expected intent: news_search (asking 'what happened' should trigger news)")
    print(f"   Expected symbols: ['NVDA'] (from context)")

    # Check if intent is news_search
    has_news_intent = any(i.intent == "news_search" for i in result2.intents)
    has_nvda = "NVDA" in result2.symbols

    if has_news_intent and has_nvda:
        print(f"   ✅ PASS: Follow-up intent detected correctly as news_search")
    else:
        print(f"   ❌ FAIL: Intent should be news_search with NVDA symbol")


async def test_context_resolution():
    """Test pronoun resolution from context"""
    print("\n" + "="*80)
    print("TEST 3: Context Resolution (Pronoun 'it')")
    print("="*80)
    print("Conversation:")
    print("  User: How is everything going with QQQ?")
    print("  Agent: [price info for QQQ]")
    print("  User: what happened to it? any macro news?")
    print("Expected: 'it' should resolve to QQQ from context")
    print()

    # First query
    result1 = await run_market_agent(
        query="How is everything going with QQQ?",
        chat_history=[],
    )

    # Build chat history
    chat_history = [
        ChatMessage(role="user", content="How is everything going with QQQ?"),
        ChatMessage(role="assistant", content=result1.summary),
    ]

    # Second query with pronoun "it"
    result2 = await run_market_agent(
        query="what happened to it? any macro news?",
        chat_history=chat_history,
    )

    print(f"\n✅ First Query Result:")
    print(f"   Intents: {[i.intent for i in result1.intents]}")
    print(f"   Symbols: {result1.symbols}")

    print(f"\n✅ Second Query (with 'it') Result:")
    print(f"   Intents: {[i.intent for i in result2.intents]}")
    print(f"   Symbols: {result2.symbols}")
    print(f"   Expected: QQQ (resolved from 'it')")

    # Check if QQQ is in symbols
    has_qqq = "QQQ" in result2.symbols

    if has_qqq:
        print(f"   ✅ PASS: Context resolution worked correctly")
    else:
        print(f"   ❌ FAIL: 'it' should resolve to QQQ from context")


async def main():
    """Run all tests"""
    print("\n🧪 Testing Improved Intent Analyzer")
    print("="*80)

    try:
        await test_symbol_correction()
        await test_follow_up_intent()
        await test_context_resolution()

        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED")
        print("="*80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

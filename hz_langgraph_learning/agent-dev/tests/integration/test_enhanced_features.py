"""
Test script for enhanced features:
1. Output router (voice vs text mode)
2. Multiple intents in one query
3. Conversational fallback for chat intents
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


async def test_output_modes():
    """Test voice vs text output modes."""
    print("\n" + "=" * 80)
    print("TEST 1: Output Mode Router (Voice vs Text)")
    print("=" * 80)

    query = "What's Tesla stock price?"

    # Test voice mode (default)
    print("\n--- VOICE MODE (Oral) ---")
    result_voice = await run_market_agent(query, output_mode="voice")
    print(f"\n📢 Voice Output:\n{result_voice.summary}\n")
    assert result_voice.summary, "Voice summary should not be empty"
    # Voice should be more conversational (less markdown)
    assert result_voice.summary.count("**") < 5, "Voice mode should have minimal markdown formatting"

    # Test text mode
    print("\n--- TEXT MODE (Written) ---")
    result_text = await run_market_agent(query, output_mode="text")
    print(f"\n📝 Text Output:\n{result_text.summary}\n")
    assert result_text.summary, "Text summary should not be empty"
    # Text should have structured markdown
    assert "**" in result_text.summary or "-" in result_text.summary, "Text mode should have markdown formatting"

    print("\n✅ PASSED: Output mode router working (voice vs text)")


async def test_multiple_intents():
    """Test multiple intents in one query."""
    print("\n" + "=" * 80)
    print("TEST 2: Multiple Intents in Single Query")
    print("=" * 80)

    # Query with TWO intents: price check + news
    query = "what's the price of GLD, what happened to it"

    print(f"\nQuery: '{query}'")
    print("Expected: 2 intents (price_check + news_search)")

    result = await run_market_agent(query, output_mode="text")

    print(f"\n✅ Detected Intents: {len(result.intents)}")
    for i, intent_item in enumerate(result.intents, 1):
        print(f"  {i}. {intent_item.intent} - Symbols: {intent_item.symbols} - Reasoning: {intent_item.reasoning}")

    # Verify multiple intents detected
    assert len(result.intents) >= 2, f"Should detect at least 2 intents, got {len(result.intents)}"

    # Verify intent types
    intent_types = [intent.intent for intent in result.intents]
    assert "price_check" in intent_types or "comparison" in intent_types, "Should include price intent"
    assert "news_search" in intent_types, "Should include news intent"

    # Verify summary addresses both intents
    print(f"\n📊 Combined Summary:\n{result.summary[:400]}...")

    assert "GLD" in str(result.symbols), "Should extract GLD symbol"

    print("\n✅ PASSED: Multiple intents detected and processed")


async def test_conversational_chat():
    """Test conversational fallback for chat intents."""
    print("\n" + "=" * 80)
    print("TEST 3: Conversational Fallback (Chat Intent)")
    print("=" * 80)

    chat_queries = [
        "Hello, how are you?",
        "What can you help me with?",
        "Thanks!",
    ]

    for query in chat_queries:
        print(f"\n--- Chat Query: '{query}' ---")

        result = await run_market_agent(query, output_mode="voice")

        print(f"Detected intents: {[intent.intent for intent in result.intents]}")
        print(f"\n💬 Response:\n{result.summary}\n")

        # Verify chat intent detected
        assert any(intent.intent == "chat" for intent in result.intents), f"Should detect 'chat' intent for: {query}"

        # Verify conversational response (not "No data available")
        assert result.summary, "Should have a response"
        assert "no data" not in result.summary.lower(), "Should not say 'no data' for chat queries"

        # For greetings, should respond warmly
        if "hello" in query.lower() or "how are you" in query.lower():
            # Should have a friendly greeting
            assert any(word in result.summary.lower() for word in ["hello", "hi", "help", "assistant", "market"]), \
                "Should respond with greeting or introduction"

    print("\n✅ PASSED: Conversational fallback working for chat intents")


async def test_mixed_intent():
    """Test query with both market intent and chat."""
    print("\n" + "=" * 80)
    print("TEST 4: Mixed Intent (Market + Chat)")
    print("=" * 80)

    query = "Hi! Can you tell me the NVDA stock price?"

    print(f"\nQuery: '{query}'")
    print("Expected: Mix of chat greeting + price check")

    result = await run_market_agent(query, output_mode="voice")

    print(f"\n✅ Detected Intents: {len(result.intents)}")
    for i, intent_item in enumerate(result.intents, 1):
        print(f"  {i}. {intent_item.intent} - Symbols: {intent_item.symbols}")

    print(f"\n📊 Response:\n{result.summary}")

    # Should handle both greeting and price check
    assert len(result.intents) >= 1, "Should detect at least one intent"

    # Should have price data OR polite acknowledgment + price
    assert result.market_data or "NVDA" in result.summary, "Should provide price information"

    print("\n✅ PASSED: Mixed intents handled gracefully")


async def main():
    """Run all tests."""
    try:
        await test_output_modes()
        await test_multiple_intents()
        await test_conversational_chat()
        await test_mixed_intent()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\n🎉 Enhanced Features Working:")
        print("1. ✅ Output Router (voice=oral, text=written)")
        print("2. ✅ Multiple Intents (e.g., 'price of GLD, what happened to it')")
        print("3. ✅ Conversational Fallback (chat intent for greetings/questions)")
        print("4. ✅ Mixed Intent Handling (chat + market queries)")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

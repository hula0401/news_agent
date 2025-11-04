"""Quick test for chat history fix"""

import asyncio
import logging
from agent_core.graph import run_market_agent
from agent_core.state import ChatMessage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

async def main():
    print("\n" + "=" * 80)
    print("QUICK TEST: Chat History with Pronoun Resolution")
    print("=" * 80)

    # First query
    print("\nQuery 1: 'Tell me stock price of TSLA'")
    result1 = await run_market_agent("Tell me stock price of TSLA", output_mode="voice")
    print(f"\nResponse 1: {result1.summary[:200]}...")

    # Build chat history
    chat_history = [
        ChatMessage(role="user", content="Tell me stock price of TSLA"),
        ChatMessage(role="assistant", content=result1.summary),
    ]

    print(f"\n\nChat History Created:")
    print(f"  1. User: Tell me stock price of TSLA")
    print(f"  2. Agent: {result1.summary[:100]}...")

    # Follow-up query with pronoun
    print(f"\n\nQuery 2: 'What happened to it' (should resolve 'it' to TSLA)")
    result2 = await run_market_agent(
        "What happened to it",
        chat_history=chat_history,
        thread_id="test_thread",
        output_mode="voice"
    )

    print(f"\n✅ Detected Intents: {[i.intent for i in result2.intents]}")
    print(f"✅ Symbols: {result2.symbols}")
    print(f"\nResponse 2: {result2.summary}")

    # Check if it worked
    if "TSLA" in str(result2.symbols) or "tsla" in result2.summary.lower():
        print("\n\n✅ SUCCESS: Agent correctly resolved 'it' to TSLA!")
    else:
        print("\n\n❌ FAILED: Agent did not resolve 'it' to TSLA")
        print(f"   Intents: {result2.intents}")
        print(f"   Symbols: {result2.symbols}")

if __name__ == "__main__":
    asyncio.run(main())

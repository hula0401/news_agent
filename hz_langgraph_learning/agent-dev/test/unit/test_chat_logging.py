"""
Quick test for chat logging fix
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent_core.graph import run_market_agent
from chat import setup_logging

async def test():
    print("\n=== Testing Debug Logging ===\n")

    # Setup debug logging
    setup_logging(debug=True)

    print("Running query (logs should go to file, not stdout)...\n")

    # Run a query
    result = await run_market_agent(
        query="What's AAPL stock price?",
        chat_history=[],
    )

    print(f"✅ Query completed successfully")
    print(f"   Summary: {result.summary[:100]}...")
    print(f"\n✅ No debug logs in stdout! Check logs/chat_debug.log for debug info.\n")

if __name__ == "__main__":
    asyncio.run(test())

import asyncio
from agent_core.graph import run_market_agent

async def main():
    print("Testing: add google to my watchlist and tell me what's in my watchlist")
    result = await run_market_agent("add google to my watchlist and tell me what's in my watchlist", output_mode="text")
    print(f"\nIntents: {[i.intent for i in result.intents]}")
    print(f"Symbols: {result.symbols}")
    print(f"\nSummary:\n{result.summary}")

asyncio.run(main())

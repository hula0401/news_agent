"""
Test enhanced logging with actual tool results and memory content
"""
import asyncio
import logging
from agent_core.graph import run_market_agent

# Setup logging to see the enhanced output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    print("\n" + "="*80)
    print("Testing Enhanced Logging - Tool Results & Memory Content")
    print("="*80 + "\n")

    # Test query with both price and news
    result = await run_market_agent(
        query="What's the latest on NVDA? Show me price and news",
        chat_history=[],
    )

    print("\n" + "="*80)
    print("✅ Check logs above for:")
    print("   • Tool results with actual data (prices, news titles)")
    print("   • Merged data content (market data & news)")
    print("   • Memory save with full query details")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

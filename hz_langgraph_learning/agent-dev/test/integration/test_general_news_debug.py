"""
Quick debug test for general market news
"""
import asyncio
import logging
from agent_core.graph import run_market_agent

# Enable debug logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    print("\n" + "="*80)
    print("DEBUG TEST: What's the market news today?")
    print("="*80 + "\n")

    result = await run_market_agent(
        query="What's the market news today?",
        chat_history=[],
    )

    print(f"\n{'='*80}")
    print("RESULT:")
    print(f"{'='*80}")
    print(f"Intents: {[i.intent for i in result.intents]}")
    print(f"Symbols: {result.symbols}")
    print(f"Selected tools: {result.selected_tools}")
    print(f"Selected APIs: {result.selected_apis}")
    print(f"Market data items: {len(result.market_data)}")
    print(f"News data items: {len(result.news_data)}")

    for i, news in enumerate(result.news_data[:3], 1):
        print(f"\n{i}. {news.title}")
        print(f"   Symbols: {news.symbols}")
        print(f"   Category: {getattr(news, 'category', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())

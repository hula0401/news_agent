#!/usr/bin/env python3
"""
Test the specific failing query from user:
"how was the p/e ratio of tsla? How was its latest earning?"

This query should detect TWO research intents:
1. P/E ratio with keywords ["P/E ratio", "price to earnings ratio", "valuation"]
2. Latest earnings with keywords ["earnings", "latest earnings", "quarterly earnings"]

The agent should run BOTH research calls and merge the results.
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from agent_core.graph import run_market_agent


async def main():
    query = "how was the p/e ratio of tsla? How was its latest earning?"

    print(f"\n{'='*80}")
    print("MULTI-INTENT RESEARCH TEST")
    print(f"{'='*80}")
    print(f"\nQuery: {query}")
    print("\nExpected Behavior:")
    print("1. Intent Analyzer detects TWO research intents")
    print("2. Intent 1: P/E ratio with keywords ['P/E ratio', 'price to earnings ratio', 'valuation']")
    print("3. Intent 2: Latest earnings with keywords ['earnings', 'latest earnings', 'quarterly earnings']")
    print("4. General Research Node runs BOTH research calls")
    print("5. Results merged: ~8-10 chunks total (4-5 per intent)")
    print("6. Summary includes BOTH P/E ratio AND earnings information")
    print(f"\n{'='*80}\n")

    result = await run_market_agent(query, output_mode="text")

    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}\n")

    print(f"Intent: {result.intent}")
    print(f"Symbols: {result.symbols}")
    print(f"Keywords (first intent): {result.keywords}")
    print(f"\nAll Intents Detected:")
    for i, intent in enumerate(result.intents, 1):
        print(f"  {i}. {intent.intent}")
        print(f"     Symbols: {intent.symbols}")
        print(f"     Keywords: {intent.keywords}")
        print(f"     Reasoning: {intent.reasoning}")

    print(f"\nResearch Results:")
    print(f"  Chunks: {len(result.research_chunks)}")
    print(f"  Sources: {len(result.research_citations)}")
    print(f"  Confidence: {result.research_confidence:.2f}")

    if result.research_chunks:
        print(f"\nTop Research Chunks:")
        for idx, chunk in enumerate(result.research_chunks[:5], 1):
            preview = chunk["content"][:150] + "..." if len(chunk["content"]) > 150 else chunk["content"]
            print(f"\n  [{idx}] Score: {chunk['score']:.2f}")
            print(f"      Title: {chunk['title']}")
            print(f"      {preview}")
            print(f"      URL: {chunk['url']}")

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")
    print(result.summary)

    # Verification
    print(f"\n{'='*80}")
    print("VERIFICATION")
    print(f"{'='*80}\n")

    checks = {
        "Two research intents detected": len([i for i in result.intents if i.intent == "research"]) == 2,
        "TSLA symbol detected": "TSLA" in result.symbols,
        "Research chunks found": len(result.research_chunks) > 0,
        "Multiple chunks (>=5)": len(result.research_chunks) >= 5,
        "High confidence (>=0.7)": result.research_confidence >= 0.7,
        "P/E ratio in summary": any(keyword in result.summary.lower() for keyword in ["p/e", "pe ratio", "price to earnings"]),
        "Earnings in summary": any(keyword in result.summary.lower() for keyword in ["earning", "quarterly"]),
    }

    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")

    all_passed = all(checks.values())

    print(f"\n{'='*80}")
    if all_passed:
        print("🎉 ALL CHECKS PASSED!")
        print("\nFix Summary:")
        print("✅ Multi-intent detection working")
        print("✅ Each intent processed separately with its own keywords")
        print("✅ Results merged successfully")
        print("✅ Summary includes both P/E and earnings information")
        return 0
    else:
        print("⚠️  SOME CHECKS FAILED")
        failed_checks = [check for check, passed in checks.items() if not passed]
        print(f"\nFailed: {', '.join(failed_checks)}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

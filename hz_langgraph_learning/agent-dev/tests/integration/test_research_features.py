#!/usr/bin/env python3
"""
Comprehensive test suite for general research features.

Tests keyword extraction, query reformulation, and research capabilities
with varied prompts across different categories.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from agent_core.graph import run_market_agent


class TestCase:
    def __init__(self, query, category, expected_intent, expected_symbols, expected_keyword_hints, description):
        self.query = query
        self.category = category
        self.expected_intent = expected_intent
        self.expected_symbols = expected_symbols
        self.expected_keyword_hints = expected_keyword_hints
        self.description = description


# Comprehensive test cases across different categories
TEST_CASES = [
    # === Financial Metrics (P/E, P/B, EPS, etc.) ===
    TestCase(
        query="what is meta p/e ratio?",
        category="Financial Metrics - P/E Ratio",
        expected_intent="research",
        expected_symbols=["META"],
        expected_keyword_hints=["p/e", "pe", "ratio", "price", "earnings", "valuation"],
        description="Direct P/E ratio query"
    ),
    TestCase(
        query="tell me google's price to earnings",
        category="Financial Metrics - P/E Ratio",
        expected_intent="research",
        expected_symbols=["GOOGL"],
        expected_keyword_hints=["price", "earnings", "p/e", "ratio"],
        description="Natural language P/E query"
    ),
    TestCase(
        query="what's the PE of Apple?",
        category="Financial Metrics - P/E Ratio",
        expected_intent="research",
        expected_symbols=["AAPL"],
        expected_keyword_hints=["pe", "p/e", "ratio", "earnings"],
        description="Informal PE query"
    ),
    TestCase(
        query="show me Tesla's EPS",
        category="Financial Metrics - EPS",
        expected_intent="research",
        expected_symbols=["TSLA"],
        expected_keyword_hints=["eps", "earnings", "per share"],
        description="Earnings per share query"
    ),
    TestCase(
        query="what is nvidia's price to book ratio?",
        category="Financial Metrics - P/B Ratio",
        expected_intent="research",
        expected_symbols=["NVDA"],
        expected_keyword_hints=["price", "book", "p/b", "ratio"],
        description="Price to book ratio query"
    ),
    TestCase(
        query="tell me about microsoft's debt to equity",
        category="Financial Metrics - Debt",
        expected_intent="research",
        expected_symbols=["MSFT"],
        expected_keyword_hints=["debt", "equity", "leverage", "ratio"],
        description="Debt ratio query"
    ),
    TestCase(
        query="what's amazon's operating margin?",
        category="Financial Metrics - Margins",
        expected_intent="research",
        expected_symbols=["AMZN"],
        expected_keyword_hints=["operating", "margin", "profit"],
        description="Operating margin query"
    ),

    # === Earnings & Events ===
    TestCase(
        query="how was meta earning call?",
        category="Earnings - Call",
        expected_intent="research",
        expected_symbols=["META"],
        expected_keyword_hints=["earning", "call", "quarterly", "report"],
        description="Earnings call query"
    ),
    TestCase(
        query="when was meta's last earnings call?",
        category="Earnings - Timing",
        expected_intent="research",
        expected_symbols=["META"],
        expected_keyword_hints=["earning", "call", "last", "when"],
        description="Earnings call timing query"
    ),
    TestCase(
        query="what did apple announce in their quarterly report?",
        category="Earnings - Content",
        expected_intent="research",
        expected_symbols=["AAPL"],
        expected_keyword_hints=["quarterly", "report", "announce", "earnings"],
        description="Quarterly report content query"
    ),
    TestCase(
        query="google q3 earnings results",
        category="Earnings - Results",
        expected_intent="research",
        expected_symbols=["GOOGL"],
        expected_keyword_hints=["q3", "earnings", "results", "quarterly"],
        description="Quarterly earnings results"
    ),

    # === Valuation & Analysis ===
    TestCase(
        query="is tesla overvalued?",
        category="Valuation - Assessment",
        expected_intent="research",
        expected_symbols=["TSLA"],
        expected_keyword_hints=["overvalued", "valuation", "price", "value"],
        description="Valuation assessment query"
    ),
    TestCase(
        query="tell me about nvidia's valuation metrics",
        category="Valuation - Metrics",
        expected_intent="research",
        expected_symbols=["NVDA"],
        expected_keyword_hints=["valuation", "metrics", "price", "value"],
        description="Valuation metrics query"
    ),
    TestCase(
        query="what's meta's market cap?",
        category="Valuation - Market Cap",
        expected_intent="research",
        expected_symbols=["META"],
        expected_keyword_hints=["market", "cap", "valuation", "value"],
        description="Market capitalization query"
    ),

    # === Performance & Growth ===
    TestCase(
        query="how is amazon's revenue growth?",
        category="Performance - Revenue Growth",
        expected_intent="research",
        expected_symbols=["AMZN"],
        expected_keyword_hints=["revenue", "growth", "sales", "yoy"],
        description="Revenue growth query"
    ),
    TestCase(
        query="what's microsoft's profit trend?",
        category="Performance - Profit",
        expected_intent="research",
        expected_symbols=["MSFT"],
        expected_keyword_hints=["profit", "trend", "earnings", "income"],
        description="Profit trend query"
    ),
    TestCase(
        query="show me google's quarterly revenue",
        category="Performance - Revenue",
        expected_intent="research",
        expected_symbols=["GOOGL"],
        expected_keyword_hints=["quarterly", "revenue", "sales"],
        description="Quarterly revenue query"
    ),

    # === Dividends & Returns ===
    TestCase(
        query="what's apple's dividend yield?",
        category="Dividends - Yield",
        expected_intent="research",
        expected_symbols=["AAPL"],
        expected_keyword_hints=["dividend", "yield", "payout", "return"],
        description="Dividend yield query"
    ),
    TestCase(
        query="does microsoft pay dividends?",
        category="Dividends - Payment",
        expected_intent="research",
        expected_symbols=["MSFT"],
        expected_keyword_hints=["dividend", "pay", "payout"],
        description="Dividend payment query"
    ),

    # === General Information (no symbols) ===
    TestCase(
        query="what is an earnings call?",
        category="General - Definition",
        expected_intent="research",
        expected_symbols=[],
        expected_keyword_hints=["earning", "call", "quarterly", "report"],
        description="General definition query"
    ),
    TestCase(
        query="explain P/E ratio",
        category="General - Explanation",
        expected_intent="research",
        expected_symbols=[],
        expected_keyword_hints=["p/e", "ratio", "price", "earnings", "valuation"],
        description="Financial concept explanation"
    ),
    TestCase(
        query="what is AI spending?",
        category="General - Topic",
        expected_intent="research",
        expected_symbols=[],
        expected_keyword_hints=["ai", "spending", "investment", "capital"],
        description="General topic query"
    ),

    # === Multi-Symbol Queries ===
    TestCase(
        query="compare p/e ratios of meta and google",
        category="Multi-Symbol - Comparison",
        expected_intent="research",
        expected_symbols=["META", "GOOGL"],
        expected_keyword_hints=["p/e", "ratio", "compare", "valuation"],
        description="Multi-symbol comparison"
    ),

    # === Multi-Intent Queries (Critical Test Cases) ===
    TestCase(
        query="how was the p/e ratio of tsla? How was its latest earning?",
        category="Multi-Intent - P/E + Earnings",
        expected_intent="research",
        expected_symbols=["TSLA"],
        expected_keyword_hints=["p/e", "ratio", "earnings", "latest", "quarterly"],
        description="Multi-intent: P/E ratio + earnings (previously failed)"
    ),
    TestCase(
        query="what is apple's eps and tell me about their earnings call",
        category="Multi-Intent - EPS + Earnings Call",
        expected_intent="research",
        expected_symbols=["AAPL"],
        expected_keyword_hints=["eps", "earnings", "call"],
        description="Multi-intent: EPS + earnings call"
    ),
    TestCase(
        query="google's valuation and revenue growth",
        category="Multi-Intent - Valuation + Growth",
        expected_intent="research",
        expected_symbols=["GOOGL"],
        expected_keyword_hints=["valuation", "revenue", "growth"],
        description="Multi-intent: Valuation + revenue growth"
    ),
]


async def run_test(test_case: TestCase) -> dict:
    """Run a single test case."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_case.description}")
    print(f"Category: {test_case.category}")
    print(f"{'='*80}")
    print(f"Query: \"{test_case.query}\"")
    print()

    try:
        result = await run_market_agent(test_case.query, output_mode="text")

        # Extract results
        intent = result.intent
        symbols = result.symbols
        keywords = result.keywords
        research_chunks = len(result.research_chunks)
        confidence = result.research_confidence
        summary = result.summary

        # Check intent
        intent_ok = intent == test_case.expected_intent
        print(f"Intent: {intent} {'✅' if intent_ok else f'❌ (expected {test_case.expected_intent})'}")

        # Check symbols
        symbols_ok = set(symbols) == set(test_case.expected_symbols) or (not test_case.expected_symbols and not symbols)
        print(f"Symbols: {symbols} {'✅' if symbols_ok else f'❌ (expected {test_case.expected_symbols})'}")

        # Check keywords
        keywords_str = " ".join(keywords).lower()
        matching_hints = [hint for hint in test_case.expected_keyword_hints if hint.lower() in keywords_str]
        keywords_ok = len(matching_hints) > 0 if test_case.expected_keyword_hints else True
        print(f"Keywords: {keywords}")
        if matching_hints:
            print(f"  Matched hints: {matching_hints} ✅")
        elif test_case.expected_keyword_hints:
            print(f"  No matching hints found ❌ (expected hints containing: {test_case.expected_keyword_hints})")

        # Check research results
        research_ok = research_chunks > 0 and confidence > 0.4
        print(f"Research: {research_chunks} chunks, confidence {confidence:.2f} {'✅' if research_ok else '❌'}")

        # Show summary preview
        summary_preview = summary[:200] + "..." if len(summary) > 200 else summary
        print(f"\nSummary ({len(summary)} chars):")
        print(f"{summary_preview}")

        # Overall result
        all_ok = intent_ok and symbols_ok and keywords_ok and research_ok
        result_str = "✅ PASS" if all_ok else "❌ FAIL"
        print(f"\n{result_str}")

        return {
            "test_case": test_case,
            "intent_ok": intent_ok,
            "symbols_ok": symbols_ok,
            "keywords_ok": keywords_ok,
            "research_ok": research_ok,
            "all_ok": all_ok,
            "confidence": confidence,
            "chunks": research_chunks,
        }

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return {
            "test_case": test_case,
            "intent_ok": False,
            "symbols_ok": False,
            "keywords_ok": False,
            "research_ok": False,
            "all_ok": False,
            "error": str(e),
        }


async def main():
    """Run all test cases."""
    print("\n" + "="*80)
    print("RESEARCH FEATURES TEST SUITE")
    print("="*80)
    print(f"\nTotal test cases: {len(TEST_CASES)}")
    print(f"Categories: {len(set(tc.category for tc in TEST_CASES))}")
    print()

    results = []
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\nRunning test {i}/{len(TEST_CASES)}...")
        result = await run_test(test_case)
        results.append(result)

    # Summary
    print("\n\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(1 for r in results if r.get("all_ok", False))
    failed = len(results) - passed

    print(f"\nTotal: {len(results)}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")

    # Category breakdown
    print("\nBy Category:")
    categories = {}
    for r in results:
        cat = r["test_case"].category
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if r.get("all_ok", False):
            categories[cat]["passed"] += 1

    for cat in sorted(categories.keys()):
        stats = categories[cat]
        print(f"  {cat}: {stats['passed']}/{stats['total']}")

    # Failed tests
    if failed > 0:
        print("\nFailed Tests:")
        for r in results:
            if not r.get("all_ok", False):
                tc = r["test_case"]
                print(f"  ❌ {tc.category} - {tc.description}")
                print(f"     Query: \"{tc.query}\"")
                if "error" in r:
                    print(f"     Error: {r['error']}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

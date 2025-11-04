#!/usr/bin/env python3
"""
Test checklist-based parallel query execution.

Tests:
1. Multi-symbol P/E query: "meta and nvda p/e ratio"
   - Should create 2 checklist items: ["META P/E ratio", "NVDA P/E ratio"]
   - Each query should get minimum 5 Tavily results
   - Queries execute in parallel

2. Multi-intent query: "tsla p/e and latest earnings"
   - Should create 2 checklist items: ["TSLA P/E ratio", "TSLA earnings"]
   - Each gets 5+ results
   - Executes in parallel
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.graph import run_market_agent


async def test_multi_symbol_pe():
    """Test: meta and nvda p/e ratio"""
    print("\n" + "="*80)
    print("TEST 1: Multi-symbol P/E query")
    print("Query: 'what are the p/e ratios of meta and nvda?'")
    print("="*80)

    result = await run_market_agent(
        "what are the p/e ratios of meta and nvda?",
        output_mode="text"
    )

    print("\n--- RESULTS ---")
    print(f"Intents detected: {len(result.intents)}")
    for i, intent in enumerate(result.intents, 1):
        print(f"  {i}. {intent.intent} - Symbols: {intent.symbols} - Keywords: {intent.keywords}")

    print(f"\nChecklist items: {len(result.research_checklist)}")
    for i, item in enumerate(result.research_checklist, 1):
        status = "✓" if item.completed else "✗"
        print(f"  {status} {i}. {item.query}")
        print(f"      Symbols: {item.symbols}")
        print(f"      Results: {item.result_count}")
        print(f"      Completed: {item.timestamp_completed}")

    print(f"\nResearch chunks: {len(result.research_chunks)}")
    print(f"Citations: {len(result.research_citations)}")
    print(f"Confidence: {result.research_confidence:.2f}")

    print(f"\n--- SUMMARY ---")
    print(result.summary)

    # Validation checks
    checks = {
        "Has research checklist": len(result.research_checklist) > 0,
        "Checklist has 2 items (META + NVDA)": len(result.research_checklist) == 2,
        "All checklist items completed": all(item.completed for item in result.research_checklist),
        "Each item has >= 5 results": all(item.result_count >= 5 for item in result.research_checklist),
        "META in checklist": any("META" in item.query for item in result.research_checklist),
        "NVDA in checklist": any("NVDA" in item.query for item in result.research_checklist),
        "P/E in summary": any(keyword in result.summary.lower() for keyword in ["p/e", "pe ratio", "price to earnings"]),
        "Both META and NVDA in summary": "META" in result.summary and "NVDA" in result.summary,
    }

    print("\n--- VALIDATION ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}: {passed}")

    all_passed = all(checks.values())
    print(f"\n{'='*80}")
    print(f"TEST 1: {'PASSED ✅' if all_passed else 'FAILED ❌'}")
    print(f"{'='*80}")

    return all_passed


async def test_multi_intent_tsla():
    """Test: tsla p/e and earnings"""
    print("\n" + "="*80)
    print("TEST 2: Multi-intent query (P/E + Earnings)")
    print("Query: 'what is tsla p/e ratio and its latest earnings?'")
    print("="*80)

    result = await run_market_agent(
        "what is tsla p/e ratio and its latest earnings?",
        output_mode="text"
    )

    print("\n--- RESULTS ---")
    print(f"Intents detected: {len(result.intents)}")
    for i, intent in enumerate(result.intents, 1):
        print(f"  {i}. {intent.intent} - Symbols: {intent.symbols} - Keywords: {intent.keywords}")

    print(f"\nChecklist items: {len(result.research_checklist)}")
    for i, item in enumerate(result.research_checklist, 1):
        status = "✓" if item.completed else "✗"
        print(f"  {status} {i}. {item.query}")
        print(f"      Symbols: {item.symbols}")
        print(f"      Results: {item.result_count}")
        print(f"      Completed: {item.timestamp_completed}")

    print(f"\nResearch chunks: {len(result.research_chunks)}")
    print(f"Citations: {len(result.research_citations)}")
    print(f"Confidence: {result.research_confidence:.2f}")

    print(f"\n--- SUMMARY ---")
    print(result.summary)

    # Validation checks
    checks = {
        "Has research checklist": len(result.research_checklist) > 0,
        "Checklist has items": len(result.research_checklist) >= 1,
        "All checklist items completed": all(item.completed for item in result.research_checklist),
        "Each item has >= 5 results": all(item.result_count >= 5 for item in result.research_checklist),
        "TSLA in checklist": any("TSLA" in item.query for item in result.research_checklist),
        "P/E in summary": any(keyword in result.summary.lower() for keyword in ["p/e", "pe ratio", "price to earnings"]),
        "Earnings in summary": any(keyword in result.summary.lower() for keyword in ["earning", "quarterly", "revenue"]),
        "Has research chunks": len(result.research_chunks) > 0,
    }

    print("\n--- VALIDATION ---")
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}: {passed}")

    all_passed = all(checks.values())
    print(f"\n{'='*80}")
    print(f"TEST 2: {'PASSED ✅' if all_passed else 'FAILED ❌'}")
    print(f"{'='*80}")

    return all_passed


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CHECKLIST-BASED PARALLEL QUERY EXECUTION TESTS")
    print("="*80)

    test_results = []

    # Test 1: Multi-symbol P/E
    try:
        result1 = await test_multi_symbol_pe()
        test_results.append(("Multi-symbol P/E", result1))
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        test_results.append(("Multi-symbol P/E", False))

    # Test 2: Multi-intent TSLA
    try:
        result2 = await test_multi_intent_tsla()
        test_results.append(("Multi-intent TSLA", result2))
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        test_results.append(("Multi-intent TSLA", False))

    # Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(result for _, result in test_results)
    print(f"\n{'='*80}")
    print(f"OVERALL: {'ALL TESTS PASSED ✅' if all_passed else 'SOME TESTS FAILED ❌'}")
    print(f"{'='*80}")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

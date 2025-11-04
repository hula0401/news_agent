#!/usr/bin/env python3
"""
Quick test for checklist generation (no actual API calls).

Just tests that the intent analyzer generates the correct checklist.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.state import MarketState
from agent_core.nodes import node_intent_analyzer


async def test_checklist_generation():
    """Test that checklist is generated correctly"""
    print("\n" + "="*80)
    print("CHECKLIST GENERATION TEST")
    print("="*80)

    # Test 1: Multi-symbol P/E query
    print("\n--- TEST 1: Multi-symbol P/E ---")
    print("Query: 'what are the p/e ratios of meta and nvda?'")

    state1 = MarketState(query="what are the p/e ratios of meta and nvda?")
    state1 = await node_intent_analyzer(state1)

    print(f"\nIntents: {len(state1.intents)}")
    for i, intent in enumerate(state1.intents, 1):
        print(f"  {i}. {intent.intent} - Symbols: {intent.symbols} - Keywords: {intent.keywords}")

    print(f"\nChecklist: {len(state1.research_checklist)} items")
    for i, item in enumerate(state1.research_checklist, 1):
        print(f"  {i}. Query: '{item.query}'")
        print(f"      Symbols: {item.symbols}")
        print(f"      Keywords: {item.keywords}")

    check1 = {
        "Checklist exists": len(state1.research_checklist) > 0,
        "Has 2 items": len(state1.research_checklist) == 2,
        "META in checklist": any("META" in item.query for item in state1.research_checklist),
        "NVDA in checklist": any("NVDA" in item.query for item in state1.research_checklist),
    }

    print("\n✓ Checks:")
    for name, passed in check1.items():
        print(f"  {'✅' if passed else '❌'} {name}")

    # Test 2: Single symbol multi-keywords
    print("\n--- TEST 2: Single symbol, multiple keywords ---")
    print("Query: 'what is tsla p/e ratio and latest earnings?'")

    state2 = MarketState(query="what is tsla p/e ratio and latest earnings?")
    state2 = await node_intent_analyzer(state2)

    print(f"\nIntents: {len(state2.intents)}")
    for i, intent in enumerate(state2.intents, 1):
        print(f"  {i}. {intent.intent} - Symbols: {intent.symbols} - Keywords: {intent.keywords}")

    print(f"\nChecklist: {len(state2.research_checklist)} items")
    for i, item in enumerate(state2.research_checklist, 1):
        print(f"  {i}. Query: '{item.query}'")
        print(f"      Symbols: {item.symbols}")
        print(f"      Keywords: {item.keywords}")

    check2 = {
        "Checklist exists": len(state2.research_checklist) > 0,
        "Has items": len(state2.research_checklist) >= 1,
        "TSLA in checklist": any("TSLA" in item.query for item in state2.research_checklist),
    }

    print("\n✓ Checks:")
    for name, passed in check2.items():
        print(f"  {'✅' if passed else '❌'} {name}")

    # Final summary
    all_checks = {**check1, **check2}
    all_passed = all(all_checks.values())

    print("\n" + "="*80)
    print(f"RESULT: {'ALL PASSED ✅' if all_passed else 'SOME FAILED ❌'}")
    print("="*80)

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(test_checklist_generation())
    sys.exit(0 if success else 1)

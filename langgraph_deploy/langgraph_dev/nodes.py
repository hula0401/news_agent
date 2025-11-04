from __future__ import annotations

import asyncio
from typing import Dict, List
import uuid

from .state import GraphState
from .tools.adapters import fetch_alpha_intel, fetch_reddit
from .tools.normalizers import to_news_item_alpha, to_news_item_reddit
from .memory import conversation_memory
from .summarize import summarize_briefs, stream_summarize


def _stamp_ids(state: GraphState) -> None:
    if not getattr(state, 'thread_id', None):
        state.thread_id = f"th_{uuid.uuid4().hex[:8]}"
    state.ckpt_id = f"ck_{uuid.uuid4().hex[:8]}"


def node_normalizer(state: GraphState) -> GraphState:
    # Placeholder for ASR/Text normalization per Mermaid
    _stamp_ids(state)
    return state


def node_intent_router(state: GraphState) -> GraphState:
    text = state.query.lower()
    # Preferences/Stocks detection (kept for completeness)
    if any(k in text for k in ["add topic", "remove topic", "preferred topics", "watchlist", "add stock", "remove stock"]):
        state.intent = "preferences"
        state.selected_sources = []
        _stamp_ids(state)
        return state
    if any(k in text for k in ["stock price", "price of", "ticker "]):
        state.intent = "stocks"
        state.selected_sources = ["alpha_intel"]
        _stamp_ids(state)
        return state

    state.intent = "news"
    mentions_reddit = "reddit" in text
    mentions_alpha = any(k in text for k in ["alpha", "alphaintelligence", "alpha intelligence"])  # rare
    if mentions_reddit and not mentions_alpha:
        state.selected_sources = ["reddit"]
    elif mentions_reddit and mentions_alpha:
        state.selected_sources = ["alpha_intel", "reddit"]
    else:
        state.selected_sources = ["alpha_intel"]
    _stamp_ids(state)
    return state


def node_policy_rules(state: GraphState) -> GraphState:
    # Here we could adjust timeouts/topk per policy; defaults already in state
    _stamp_ids(state)
    return state


async def node_fan_out_fetch(state: GraphState) -> GraphState:
    if state.intent != "news":
        _stamp_ids(state)
        return state

    topic = _extract_topic(state.query)
    tasks: List[asyncio.Task] = []

    if "alpha_intel" in state.selected_sources:
        tasks.append(asyncio.create_task(fetch_alpha_intel(topic, state.topk_alpha)))
    if "reddit" in state.selected_sources:
        tasks.append(asyncio.create_task(fetch_reddit(state.query, state.topk_reddit_only)))

    batches: List[List[Dict]] = []
    for t in tasks:
        try:
            items = await asyncio.wait_for(t, timeout=state.timeout_seconds)
        except Exception:
            try:
                items = await asyncio.wait_for(t.get_coro(), timeout=state.timeout_seconds)  # type: ignore[attr-defined]
            except Exception:
                items = []
        batches.append(items)

    # Ensure we always write results directly into the state
    state.raw_results = {}
    for batch in batches:
        for it in batch:
            src = it.get('source', 'unknown')
            state.raw_results.setdefault(src, []).append(it)
    _stamp_ids(state)
    return state


def node_collector(state: GraphState) -> GraphState:
    # Already merged in raw_results during fan-out
    _stamp_ids(state)
    return state


def node_dedup_rerank(state: GraphState) -> GraphState:
    def sort_list(lst: List[Dict]) -> List[Dict]:
        return sorted(lst, key=lambda x: (int(x.get('score', 0)), str(x.get('title',''))), reverse=True)

    alpha = sort_list(state.raw_results.get('alpha_intel', []))
    reddit = sort_list(state.raw_results.get('reddit', []))

    if state.selected_sources == ["reddit"]:
        state.items = reddit[:state.topk_reddit_only]
        _stamp_ids(state)
        return state

    result: List[Dict] = []
    result.extend(alpha[:state.topk_alpha])
    if 'reddit' in state.selected_sources:
        result.extend(reddit[:state.topk_reddit_when_both])
    state.items = result
    _stamp_ids(state)
    return state


def node_integrator(state: GraphState) -> GraphState:
    # Placeholder for LLM integration/aggregation (kept simple)
    _stamp_ids(state)
    return state


def node_output_planner(state: GraphState) -> GraphState:
    # Placeholder for voice/text style decisions
    _stamp_ids(state)
    return state


async def node_nlg(state: GraphState) -> GraphState:
    chunks = []
    async for chunk in stream_summarize(state.items, state.query):
        chunks.append(chunk)
    final_text = "".join(chunks) if chunks else await summarize_briefs(state.items)
    state.final_text = final_text
    conversation_memory.add(state.query, final_text, state.items, _extract_topic(state.query))
    _stamp_ids(state)
    return state


def node_tts(state: GraphState) -> GraphState:
    # Placeholder; actual TTS handled by voice pipeline elsewhere
    # If audio was generated elsewhere, ensure it's stored on the state
    _stamp_ids(state)
    return state


def _extract_topic(user_input: str) -> str:
    user_lower = user_input.lower()
    topic_keywords = {
        'technology': ['tech', 'technology', 'ai', 'artificial intelligence', 'nvidia', 'apple', 'google'],
        'crypto': ['crypto', 'bitcoin', 'blockchain', 'binance'],
        'finance': ['stock', 'price', 'trading', 'market', 'financial'],
        'energy': ['oil', 'gas', 'energy', 'renewable'],
        'politics': ['trump', 'pelosi', 'congress', 'government'],
    }
    for topic, keywords in topic_keywords.items():
        if any(keyword in user_lower for keyword in keywords):
            return topic
    return 'general'



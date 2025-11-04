# LangGraph Dev Pipeline (News)

Experimental LangGraph-based news pipeline for development and prototyping. It routes a query, fetches from sources in parallel, ranks, and generates a concise summary text. This module is self-contained under `langgraph_dev/` and does not affect the production agent.

---

## What’s here

- Orchestrated with LangGraph (`StateGraph`)
- Nodes: normalizer → intent_router → policy_rules → fan_out_fetch → collector → dedup_rerank → integrator → output_planner → nlg → tts
- State schema aligned to PRD (query, intent, selected_sources, raw_results, items, final_text, memory_refs)
- Default source: AlphaIntelligence (dev MCP adapter)
- Opt-in source: Reddit (dev adapter; enable by mentioning “reddit” in the query)

---

## Requirements

- Python 3.10+
- Project dependencies installed (uses repo root `pyproject.toml`)
- Optional: `ZHIPUAI_API_KEY` for LLM-based streaming summaries (falls back to simple bullet summary if missing)

Install deps from repo root:
```bash
uv sync --frozen
```

---

## Quick start (CLI)

Run the pipeline directly with a query:
```bash
uv run python -m langgraph_dev.run "latest ai news"
```
Examples:
- Default AlphaIntelligence only:
```bash
uv run python -m langgraph_dev.run "nvidia earnings"
```
- Reddit opt-in:
```bash
uv run python -m langgraph_dev.run "what does reddit say about bitcoin?"
```

Output prints the graph state keys and the synthesized `final_text`.

---

## Programmatic usage

```python
import asyncio
from langgraph_dev.state import GraphState
from langgraph_dev.graph import build_app

async def main():
    app = build_app()
    state = GraphState(query="latest technology news")
    out = await app.ainvoke(state)
    print(out.final_text)

asyncio.run(main())
```

---

## State schema

```python
# langgraph_dev/state.py
from dataclasses import dataclass, field

@dataclass
class GraphState:
    query: str = ""
    intent: str = "other"                    # "news" | "preferences" | "stocks" | "other"
    selected_sources: list[str] = field(default_factory=list)
    raw_results: dict[str, list[dict]] = field(default_factory=dict)
    items: list[dict] = field(default_factory=list)
    final_text: str = ""
    memory_refs: list[dict] = field(default_factory=list)
    # Policy / ranking
    timeout_seconds: float = 8.0
    retries: int = 1
    topk_alpha: int = 2
    topk_reddit_only: int = 3
    topk_reddit_when_both: int = 2
```

---

## Node flow

- normalizer: placeholder for text normalization
- intent_router: sets `intent` and `selected_sources`
  - Default: `["alpha_intel"]`
  - Mentions “reddit”: `["reddit"]` (or `["alpha_intel","reddit"]` if both requested)
  - Preferences/Stocks keywords route away from news path
- policy_rules: placeholder for timeouts/top‑K adjustments
- fan_out_fetch: fetches from selected sources in parallel (timeouts + single retry)
- collector: merges results into `raw_results`
- dedup_rerank: sorts by `(score desc, title)` and selects Top‑K per policy
- integrator, output_planner: placeholders for aggregation/planning
- nlg: generates `final_text` (streams via LLM if key present; otherwise simple summary)
- tts: placeholder (voice handled elsewhere)

---

## Environment variables

- `ZHIPUAI_API_KEY` (optional) – enables LLM streaming summarization in `nlg`

If not set, the pipeline falls back to a simple bullet summary.

---

## Source selection and ranking

- Default source: AlphaIntelligence only → Top‑2 items
- Explicit Reddit request: Reddit only → Top‑3 items
- If both requested: AlphaIntelligence Top‑2 + Reddit Top‑2

---

## Troubleshooting

- No output or empty results: try a broader query (e.g., “technology news”).
- Slow or timeout: the fan‑out fetch uses an 8s timeout per task; results may be partial if a source is slow.
- No LLM key: you will still get a non‑LLM summary.

---

## Development notes

- Graph builder: `langgraph_dev/graph.py` (returns a compiled runnable)
- Nodes: `langgraph_dev/nodes.py`
- Summarization: `langgraph_dev/summarize.py`
- State: `langgraph_dev/state.py`
- Dev adapters/tools: `langgraph_dev/mcp/`, `langgraph_dev/tools/`

You can iterate on nodes and state without impacting the production agent. The module is designed to be embedded later behind an API or agent wrapper once finalized.

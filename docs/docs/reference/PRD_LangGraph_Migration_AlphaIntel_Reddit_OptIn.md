# PRD — Migration to LangGraph (AlphaIntelligence default, Reddit MCP opt‑in)

## 1) Executive Summary
**What’s changing:** We are migrating the orchestration layer from a **LangChain tool-calling agent** to a **LangGraph-based agent** with explicit nodes/edges and robust parallelism.  
**What stays the same:** All **current rules and behaviors** for news retrieval via **AlphaIntelligence (MCP)** remain **as-is** and become the default path.  
**What’s added:** A **Reddit MCP** tool is introduced **only when the user explicitly asks for Reddit**; otherwise it is not consulted.  
**Why:** Improve reliability (timeouts/partial results), observability, and future extensibility for additional MCP sources without changing user-facing behavior for AlphaIntelligence flows.

**Primary KPIs**
- p99 response time (text query) ≤ **3.0 s** (warm LLM)
- At-least-one-source success rate ≥ **98%**
- Partial success with degraded sources ≥ **95%**
- Deep-dive follow-up latency ≤ **1.0 s** (cached)

---

## 2) Scope
### In-Scope
- Replace LangChain agent loop with **LangGraph** stateful graph.
- Keep **AlphaIntelligence** as the **default news source** with existing retrieval & summarization rules (“streamline” path).
- Add **Reddit via MCP** as **opt-in** (only when the user asks for “Reddit”).

### Out-of-Scope
- ASR/TTS redesign (assumed existing).
- UI redesign.
- Advanced cross-source ranking research (pragmatic heuristics only initially).

---

## 3) Migration Overview — From LangChain to LangGraph
### 3.1 Key Differences
| Aspect | LangChain (current) | LangGraph (target) |
|---|---|---|
| Orchestration | Implicit tool-calling loop | **Explicit DAG** with nodes/edges |
| Concurrency | Limited/implicit | **Parallel fetchers** with fan-out/fan-in |
| State | Prompt-embedded | **Structured graph state** (query, items, memory refs, etc.) |
| Reliability | Harder to isolate failures | **Per-node timeouts/retries**, partial results |
| Extensibility | Tool wiring spread in agent | **Source registry + adapters (MCP)** |
| Observability | Sparse | **Per-node metrics**, per-source counters |

### 3.2 What we keep
- AlphaIntelligence rules and behavior for fetching & summarizing news.
- Deep-dive cache behavior (“tell me more” on an item).
- Preference & watchlist tools (add/remove/list).

### 3.3 What we change
- Routing, fetching, ranking, and synthesis are turned into **LangGraph nodes** with explicit **edges** and **policies**.
- **Reddit MCP** added as a **separate, opt-in source** only when requested by the user.

---

## 4) Graph Design (Nodes, Edges, State)
### 4.1 State Schema
```python
state = {
  "query": str,                 # user text intent (from ASR or UI)
  "intent": str,                # "news" | "preferences" | "stocks"
  "selected_sources": [str],    # e.g., ["alpha_intel"] or ["alpha_intel", "reddit"]
  "raw_results": dict,          # per-source raw payloads
  "items": list,                # normalized NewsItem[*]
  "final_text": str,            # synthesized answer
  "memory_refs": list[dict],    # items kept for deep-dive follow-ups
}
```
`NewsItem = { source, title, url, score, snippet }`

### 4.2 Nodes
1. **Router**  
   - Inputs: `query`  
   - Outputs: `intent`, `selected_sources`  
   - Rules:  
     - If user explicitly mentions “Reddit”, `selected_sources = ["reddit"] (+ "alpha_intel" only if also mentioned)`.  
     - Otherwise, **default to AlphaIntelligence only** (`selected_sources = ["alpha_intel"]`).  
     - Preferences/Watchlist requests route to **Preferences** branch.

2. **Fetch (parallel composite)**  
   - Sub-nodes:  
     - `FetchAlphaIntelligenceMCP` (default)  
     - `FetchRedditMCP` (**only executed when user asked for Reddit**)  
   - Policies: **8s timeout**, 1 retry with jitter, per-source isolation.  
   - Writes: `raw_results[source]`

3. **Rank**  
   - Normalize `raw_results` to `NewsItem` list per source.  
   - Ranking heuristic: `score desc, title`.  
   - **Top-K**:  
     - Default AlphaIntelligence-only: `k=2`  
     - Reddit opt-in: `k=3` for Reddit if Reddit is the *only* requested source; otherwise `k=2` per source

4. **Summarize**  
   - Build **voice-friendly** bullet summary + links.  
   - Persist `memory_refs` for deep-dives.  
   - (Pluggable) reuse current brief + deep-dive rephrasing pipeline.

5. **Preferences** (conditional)  
   - For add/remove/list preferred topics and watchlist stocks.  
   - Returns textual confirmation/result and bypasses fetch/rank.

### 4.3 Edges
- `ENTRY → Router`  
- `Router → Preferences` (if intent == preferences)  
- `Router → Fetch` (else)  
- `Fetch → Rank → Summarize → END`  
- `Preferences → END`

---

## 5) Tools & Adapters
### 5.1 AlphaIntelligence (Default; Keep Current Rules)
- **Type:** MCP tool (existing).  
- **Contract (example):** `alpha_news({ query: str | topics: str | None, limit: int }) -> list[{ title, url, score, snippet }]`  
- **Behavior:** Preserve **all current retrieval & summarization behaviors** (“streamline” rules).  
- **Usage policy:** Always used **by default** when user does **not** specify Reddit.

### 5.2 Reddit MCP (Opt-in Only)
- **Type:** MCP tool via `MCPToolAdapter.from_server_url("ws://<reddit-mcp>")`  
- **Contract (example):** `search_reddit({ query: str, limit: int }) -> list[{ title, url, score, snippet }]`  
- **Usage policy:** **Only** when the user explicitly mentions “Reddit” (e.g., “what does Reddit say about …”).

### 5.3 Other Existing Tools (Back-Compat)
- `get_stock_price(ticker)`, preference tools (`add/remove/get preferred topics`, `add/remove/get watchlist`), and any other previously exposed tools **must continue to work**.  
- If a tool affects **news retrieval**, prefer migrating behind **MCP** for consistency; otherwise invoke it under the **Preferences/Utility** branch.

### 5.4 Source Registry
```python
SOURCE_REGISTRY = {
  "alpha_intel": { "kind": "mcp", "tools": MCPToolAdapter.from_server_url("ws://<alpha-intel-mcp>"), "top_k_default": 2 },
  "reddit":      { "kind": "mcp", "tools": MCPToolAdapter.from_server_url("ws://<reddit-mcp>"),      "top_k_default": 2 },
  # future: "hn", "x", "google_news", ...
}
```

---

## 6) Interaction Rules
- **Default behavior (no source mentioned):** Use **AlphaIntelligence only**; return top-2 items + summary.  
- **Explicit Reddit request:** Use **Reddit MCP** (and AlphaIntelligence only if user also asked for it).  
- **Deep-dive:** “Tell me more about #N” returns cached 3–4 sentence explanation.  
- **Preferences/Watchlist:** Reuse existing commands unchanged.

---

## 7) Error Handling & Resilience
- **Per-source timeouts** (8s) + **single retry** (500–800 ms jitter).  
- Partial failure returns partial results (e.g., AlphaIntelligence still answers if Reddit fails).  
- Defensive normalization for any schema/JSON mismatch.

---

## 8) Telemetry & Logging
- Node timings (router/fetch/rank/summarize).  
- Per-source counters: success, timeout, empty, exception.  
- Query stats (privacy-safe), average items per source.

---

## 9) Security & Compliance
- Minimal memory refs (title/url/snippet/source).  
- Rate-limiting per MCP; keys & endpoints in config.

---

## 10) Rollout Plan
1. **Phase 1:** Implement graph with **AlphaIntelligence default** + **Reddit opt-in**; internal scripted tests.  
2. **Phase 2:** Plug in existing brief + deep-dive summarization; load tests and p99 checks.  
3. **Phase 3:** Add metrics dashboards; canary to subset of voice sessions.  
4. **Phase 4:** Evaluate additional MCPs; extend registry.

---

## 11) Acceptance Criteria
- A1: Query without “Reddit” → AlphaIntelligence-only top-2 + summary.  
- A2: Query with “Reddit …” → Reddit-only top-3 (unless user also requested AlphaIntelligence) + summary.  
- A3: Reddit fails → AlphaIntelligence still returns a valid answer.  
- A4: “Tell me more about #2” → 3–4 sentence deep-dive from cache.  
- A5: All previously used tools remain callable with unchanged UX.

---

## 12) Risks & Mitigations
- MCP schema drift → strict normalizers + contract tests.  
- Rate limits → backoff, adjust `limit`.  
- Latency spikes → staggered timeouts, partial early return.  
- Cross-source score bias → add simple min-max/z-score later if we enable multi-source by default again.

---

## 13) Dev Notes (Hand-off)
**Current layout (development under langgraph_dev)**
```
news_agent/
  langgraph_dev/
    state.py               # GraphState schema (query/intent/sources/items/final_text/memory_refs)
    nodes.py               # Router, parallel fetch, rank, and orchestration entrypoints
    graph.py               # Graph assembly and execution helpers
    summarize.py           # brief + deep-dive synthesis
    memory.py              # dev memory helpers
    mcp/                   # MCP adapters (dev)
    tools/                 # Tool adapters (dev)
```
**Tests**
- Router unit tests (default AlphaIntelligence; Reddit opt-in).  
- Normalizer & ranker unit tests.  
- Preferences tool tests.  
- Integration tests with MCP sandboxes and fixed fixtures.

---

## Appendix A — Current Implementation Alignment (Graph-ready Pipeline)

This appendix documents the design that is implemented in the repository today. It supersedes conflicting parts of the draft above.

### A.1 Overview
- We implemented a graph-ready async pipeline under `langgraph_dev/` and wired it into development workflows.
- Flow: Router → Parallel Fetch (AlphaIntelligence default; Reddit opt‑in) → Rank (Top‑K) → Summarize (briefs + deep‑dive cache) → Memory.
- Preferences/Watchlist/Stocks continue through the existing tools path outside of the graph.

### A.2 State (`GraphState`)
Defined in `langgraph_dev/state.py`:
```python
{
  "query": str,
  "intent": str,                # "news" | "preferences" | "stocks" | "other"
  "selected_sources": [str],    # ["alpha_intel"] or ["alpha_intel","reddit"] or ["reddit"]
  "raw_results": dict,          # source -> list[NewsItem]
  "items": list,                # ranked list[NewsItem]
  "final_text": str,            # synthesized answer
  "memory_refs": list[dict],
}
```
`NewsItem = { source, title, url, score, snippet }`

### A.3 Nodes
1) DeepDive Pre‑Check (in `NewsAgent.get_response`): returns cached deep‑dive if user asks to "tell me more".  
2) Router (`langgraph_dev/nodes.py:route_intent_and_sources`)  
   - Default sources: `["alpha_intel"]`  
   - If query mentions “Reddit”: `["reddit"]` or `["alpha_intel","reddit"]` if both are requested  
   - Preferences/Watchlist/Stocks: handled by legacy tools path.  
3) Fetch (parallel) in `langgraph_dev/nodes.py:NewsPipeline.run`  
   - AlphaIntelligence: `langgraph_dev/mcp/alphaintel.py`  
   - Reddit: handled via dev adapter under `langgraph_dev/tools/` (MCP adapter planned)  
   - Policies: 8s timeout per task, single retry, per‑source isolation.  
4) Rank in `NewsPipeline._rank_items`  
   - Alpha-only: top‑2; Reddit-only: top‑3; Both: top‑2 per source.  
5) Summarize in `NewsAgent.process_fetched_news`  
   - Brief summaries immediately; deep‑dives generated async and cached.  
6) Memory (`conversation_memory.add_context`).

### A.4 Edges
- ENTRY → DeepDive? → (yes) Summarize deep‑dive → Memory → END  
- ENTRY → DeepDive? → (no) Router  
- Router (intent=news) → Fetch → Rank → Summarize → Memory → END  
- Router (preferences/watchlist/stocks/other) → Legacy Tools (AgentExecutor) → Memory → END

### A.5 Tools & Adapters
- AlphaIntelligence adapter: `langgraph_dev/mcp/alphaintel.py`  
- Reddit adapter: `langgraph_dev/tools/` (dev) until `langgraph_dev/mcp/reddit.py` is available  
- Legacy tools (unchanged): stock price, preference/watchlist management.

### A.6 Mermaid — Current Agent Flow (Input → Output)
```mermaid
flowchart TD
  A[Input query] --> B{DeepDive?
  conversation_memory}
  B -- yes --> C[LLM deep-dive on cached item] --> Z[Output]
  B -- no --> R[Router
  route_intent_and_sources]

  R -- intent=news --> F[Fetch (parallel)]
  F -->|AlphaIntelligence| F1[tools/alphaintel_adapter.fetch_alpha_intel]
  F -->|Reddit (opt-in)| F2[tools/reddit_adapter.fetch_reddit]
  F1 --> G[Rank (Top-K)]
  F2 --> G
  G --> H[Summarize
  NewsAgent.process_fetched_news
  (briefs + cache deep-dives)]
  H --> I[Add to memory]
  I --> Z

  R -- preferences/watchlist/stocks/other --> T[LangChain AgentExecutor
  tools: get_stock_price,
  add/remove/list topics,
  add/remove/list watchlist]
  T --> I2[Add to memory] --> Z
```

### A.7 Acceptance Criteria (Aligned)
- Query without “Reddit” → AlphaIntelligence‑only top‑2 + brief summaries.  
- Query with “Reddit …” → Reddit‑only top‑3; if both requested → top‑2 per source.  
- Source failure still returns partial results if any source succeeds.  
- “Tell me more about #N” → 3–4 sentence deep‑dive from cache.  
- Preference/watchlist/stock tools remain callable with unchanged UX.

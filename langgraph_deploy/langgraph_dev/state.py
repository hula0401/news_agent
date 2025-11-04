from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GraphState:
    """State shared across LangGraph nodes (aligned with PRD and Mermaid)."""

    query: str = ""
    intent: str = "other"  # "news" | "preferences" | "stocks" | "other"
    selected_sources: List[str] = field(default_factory=list)
    raw_results: Dict[str, List[dict]] = field(default_factory=dict)
    items: List[dict] = field(default_factory=list)
    final_text: str = ""
    audio_url: Optional[str] = None
    memory_refs: List[dict] = field(default_factory=list)
    # Traceability / reproducibility (avoid reserved channel names)
    ckpt_id: Optional[str] = None
    thread_id: Optional[str] = None
    meta: Dict[str, str] = field(default_factory=dict)
    # Policy/Rules
    timeout_seconds: float = 8.0
    retries: int = 1
    topk_alpha: int = 10
    topk_reddit_only: int = 10
    topk_reddit_when_both: int = 10


def initial_state(query: str) -> GraphState:
    return GraphState(query=query)



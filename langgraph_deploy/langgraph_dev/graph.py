from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .state import GraphState
from .nodes import (
    node_normalizer,
    node_intent_router,
    node_policy_rules,
    node_fan_out_fetch,
    node_collector,
    node_dedup_rerank,
    node_integrator,
    node_output_planner,
    node_nlg,
    node_tts,
)


def build_app() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("normalizer", node_normalizer)
    graph.add_node("intent_router", node_intent_router)
    graph.add_node("policy_rules", node_policy_rules)
    graph.add_node("fan_out_fetch", node_fan_out_fetch)
    graph.add_node("collector", node_collector)
    graph.add_node("dedup_rerank", node_dedup_rerank)
    graph.add_node("integrator", node_integrator)
    graph.add_node("output_planner", node_output_planner)
    graph.add_node("nlg", node_nlg)
    graph.add_node("tts", node_tts)

    graph.add_edge(START, "normalizer")
    graph.add_edge("normalizer", "intent_router")

    def _route_edges(state: GraphState):
        return "policy_rules" if state.intent == "news" else END

    graph.add_conditional_edges("intent_router", _route_edges, {"policy_rules": "policy_rules", END: END})

    graph.add_edge("policy_rules", "fan_out_fetch")
    graph.add_edge("fan_out_fetch", "collector")
    graph.add_edge("collector", "dedup_rerank")
    graph.add_edge("dedup_rerank", "integrator")
    graph.add_edge("integrator", "output_planner")
    graph.add_edge("output_planner", "nlg")
    graph.add_edge("nlg", "tts")
    graph.add_edge("tts", END)

    from langchain_core.runnables.graph import MermaidDrawMethod
    from pathlib import Path
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()
    builder = graph.compile(checkpointer=checkpointer)

    #png_bytes = builder.get_graph().draw_mermaid_png(
    #    draw_method=MermaidDrawMethod.PYPPETEER,  # ← local browser render
    #   max_retries=5,
    #    retry_delay=2.0,
    #    #width=1600,
    #    #height=1200,
    #    background_color="transparent",
    #)
    #out_path = Path("langgraph_design.png")
    #out_path.parent.mkdir(parents=True, exist_ok=True)
    #out_path.write_bytes(png_bytes)

    return builder



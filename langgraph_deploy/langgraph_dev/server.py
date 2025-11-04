"""
FastAPI wrapper for LangGraph Voice-Activated News Agent.
Run with:
    uvicorn langgraph_dev.server:app --host 0.0.0.0 --port 8000
"""

import asyncio
from fastapi import FastAPI, Query
from langgraph_dev.run import main as run_graph

app = FastAPI(title="Voice-Activated News Agent", version="1.0.0")

@app.get("/")
def home():
    return {
        "message": "✅ Voice-Activated News Agent is running",
        "usage": "Try /query?q=latest+ai+news"
    }

@app.get("/query")
async def query_agent(q: str = Query("latest ai news", description="User query")):
    """
    Run the LangGraph agent asynchronously with the provided query string.
    Example:
        GET /query?q=latest ai news
    """
    result = await run_graph(q)
    return {"query": q, "result_keys": list(result.keys()), "final_text": result.get("final_text", "")}

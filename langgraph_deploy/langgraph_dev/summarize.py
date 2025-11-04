from __future__ import annotations

from typing import List, Dict, AsyncGenerator
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


async def summarize_briefs(items: List[Dict]) -> str:
    # Minimal placeholder summary to avoid pulling LLMs here.
    if not items:
        return "No results found."
    briefs = []
    for i, it in enumerate(items):
        title = it.get('title') or 'Untitled'
        briefs.append(f"{i+1}. {title}")
    return "Here are the latest news headlines:\n" + "\n".join(briefs)


def _build_lc_messages(items: List[Dict], query_text: str):
    bullet_lines = []
    references = []
    for it in items:
        title = it.get('title') or ''
        src = it.get('source') or ''
        url = it.get('url') or ''
        snippet = it.get('snippet') or ''

        bullet_lines.append(f"{src}: {snippet}")
        references.append([src, title, url])
    content = (
        "Answer the query into a concise, voice-friendly paragraph, based on Summarize the following news items. The query is: " + (query_text or '') + "."
        "Include key takeaways and avoid redundancy. Items:\n" + "\n".join(bullet_lines)
    )
    print("\ninput message:\n", content,"\n")
    return [
        SystemMessage(content="You are a helpful assistant that writes concise, factual summaries with sources."),
        HumanMessage(content=content),
    ]


async def stream_summarize(items: List[Dict], query_text: str = "") -> AsyncGenerator[str, None]:
    """Stream summary via GLM-4.5-Flash using langchain_openai ChatOpenAI.

    Falls back to a non-LLM summary if ChatOpenAI or API key is unavailable.
    """
    if ChatOpenAI is None or SystemMessage is None or HumanMessage is None:
        yield await summarize_briefs(items)
        print("either ChatOpenAI or SystemMessage or HumanMessage is not set")
        return

    api_key = os.getenv("ZHIPUAI_API_KEY", "")
    if not api_key:
        print("ZHIPUAI_API_KEY is not set")
        yield await summarize_briefs(items)
        return

    llm = ChatOpenAI(
        model="glm-4.5-flash",
        temperature=0,
        api_key=api_key,
        openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
        max_tokens=500,
    )

    messages = _build_lc_messages(items, query_text)

    async for chunk in llm.astream(messages):
        text = getattr(chunk, "content", "")
        if text:
            yield text


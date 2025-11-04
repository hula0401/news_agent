from __future__ import annotations

from typing import List, Dict, Optional
import asyncio

from ..mcp.alphaintel import fetch_news as _alpha_fetch
from ..mcp.reddit import search_posts as _reddit_search
from .normalizers import to_news_item_alpha, to_news_item_reddit


async def fetch_alpha_intel(topic: Optional[str], limit: int = 8) -> List[Dict]:
    raw = _alpha_fetch(topic, limit)
    return [to_news_item_alpha(r) for r in raw]


async def fetch_reddit(query: str, limit: int = 30) -> List[Dict]:
    raw = await _reddit_search(query, limit)
    return [to_news_item_reddit(r) for r in raw]



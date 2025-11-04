from __future__ import annotations

from typing import List, Dict, Optional
import os
import asyncio

try:
    import praw
    import requests
except Exception:  # pragma: no cover
    praw = None  # type: ignore
    requests = None  # type: ignore


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def make_readonly_reddit():
    if praw is None:
        return None
    client_id = _env("REDDIT_CLIENT_ID")
    client_secret = _env("REDDIT_CLIENT_SECRET")
    user_agent = _env("REDDIT_USER_AGENT", "lg-agent/0.1")
    if not client_id or not client_secret:
        return None
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        check_for_async=False,
    )
    reddit.read_only = True
    return reddit


def search_posts_sync(query: str, limit: int = 30) -> List[Dict]:
    reddit = make_readonly_reddit()
    if reddit is None:
        return []
    results: List[Dict] = []
    for s in reddit.subreddit("all").search(query, sort="relevance", time_filter="year", limit=limit):
        results.append({
            'title': s.title,
            'url': f"https://www.reddit.com{s.permalink}" if getattr(s, 'permalink', None) else s.url,
            'score': int(getattr(s, 'score', 0) or 0),
            'snippet': s.url,
        })
    return results


async def search_posts(query: str, limit: int = 30) -> List[Dict]:
    return await asyncio.to_thread(search_posts_sync, query, limit)



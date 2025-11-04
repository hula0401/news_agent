from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time


@dataclass
class ContextItem:
    timestamp: float
    user_input: str
    agent_response: str
    news_items: List[Dict[str, Any]]
    topic: Optional[str]


class ConversationMemory:
    def __init__(self, max_items: int = 10):
        self.max_items = max_items
        self.items: List[ContextItem] = []

    def add(self, user_input: str, agent_response: str, news_items: List[Dict], topic: Optional[str]):
        self.items.append(ContextItem(time.time(), user_input, agent_response, news_items, topic))
        if len(self.items) > self.max_items:
            self.items = self.items[-self.max_items:]

    def latest_news(self) -> Optional[List[Dict]]:
        for c in reversed(self.items):
            if c.news_items:
                return c.news_items
        return None


conversation_memory = ConversationMemory()



from __future__ import annotations

from typing import Dict


def to_news_item_alpha(row: Dict) -> Dict:
    return {
        'source': 'alpha_intel',
        'title': row.get('title', ''),
        'url': row.get('url', ''),
        'score': int(row.get('score', 0) or 0),
        'snippet': row.get('summary', ''),
    }


def to_news_item_reddit(row: Dict) -> Dict:
    return {
        'source': 'reddit',
        'title': row.get('title', ''),
        'url': row.get('url', ''),
        'score': int(row.get('score', 0) or 0),
        'snippet': row.get('snippet', ''),
    }



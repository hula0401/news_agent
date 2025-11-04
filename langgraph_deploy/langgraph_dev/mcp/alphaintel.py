from __future__ import annotations

from typing import List, Dict, Optional

from alpha_vantage.alphaintelligence import AlphaIntelligence

import os


def get_api_key() -> str:
    return os.getenv("ALPHAVANTAGE_API_KEY", "")


def fetch_news(topic: Optional[str], limit: int = 8) -> List[Dict]:
    key = get_api_key()

    if not key:
        print('ALPHAVANTAGE_API_KEY is not set','\n')
        return []
    topics = topic if topic and topic != 'general' else None
    # Prefer JSON to avoid pandas dependency; fallback to pandas if needed

    try:
        ai = AlphaIntelligence(key=key, output_format='pandas')
        news_df, _ = ai.get_news_sentiment(topics=topics, limit=limit)
        if news_df is None or news_df.empty:
            print('news_df is None or news_df.empty','\n')
            return []
        results: List[Dict] = []

        for _, row in news_df.iterrows():
            title = row.get('title')
            if not title:
                continue
            summary = row.get('summary')
            url = row.get('url') or row.get('source_url') or ''
            #score_val = row.get('relevance_score') if 'relevance_score' in row else None
            #try:
            #    score = int(float(score_val)) if score_val is not None else 0
            #except Exception:
            #    score = 0
            results.append({
                'title': str(title),
                'url': str(url) if url else '',
                'summary': str(summary) if summary else '',
                #'score': score,
            })
        return results
    except Exception:
        print('fetch news failed from AlphaIntelligence')
        return []



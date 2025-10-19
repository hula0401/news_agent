"""News aggregation service for multi-source fetching."""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from ..external.finnhub_client import get_finnhub_client
from ..external.polygon_client import get_polygon_client
from ..external.news_api_client import get_newsapi_client


class NewsAggregator:
    """
    Multi-source news aggregation with intelligent deduplication.

    Features:
    - Concurrent fetching from multiple sources
    - 85% title similarity deduplication
    - Reliability-weighted ranking
    - Fallback logic for source failures
    """

    def __init__(self):
        self.finnhub = get_finnhub_client()
        self.polygon = get_polygon_client()
        self.newsapi = get_newsapi_client()

        # Source reliability scores (0-1)
        self.source_reliability = {
            "finnhub": 0.90,
            "polygon": 0.92,
            "newsapi": 0.80,
            "federal_reserve": 1.0,
            "reuters": 0.95,
            "cnbc": 0.85,
            "marketwatch": 0.82
        }

    async def initialize(self):
        """Initialize news aggregator (placeholder for future async init)."""
        # Clients are already initialized in __init__
        # This method exists for API consistency with other services
        pass

    async def aggregate_stock_news(
        self,
        symbol: str,
        limit: int = 10,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Aggregate news for a specific stock from multiple sources.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of articles
            days_back: Number of days to look back

        Returns:
            Aggregated and deduplicated news articles
        """
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)

        # Fetch from all sources concurrently
        tasks = [
            self._fetch_finnhub_stock_news(symbol, from_date, to_date),
            self._fetch_polygon_stock_news(symbol, limit),
            self._fetch_newsapi_stock_news(symbol, from_date, to_date)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine all news
        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                print(f"❌ News fetch error: {result}")

        # Deduplicate, rank, and limit
        unique_news = self.deduplicate_by_similarity(all_news, threshold=0.85)
        ranked_news = self.rank_by_reliability(unique_news)

        return ranked_news[:limit]

    async def aggregate_market_news(
        self,
        category: str = "business",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Aggregate general market news from multiple sources.

        Args:
            category: News category
            limit: Maximum number of articles

        Returns:
            Aggregated market news
        """
        tasks = [
            self._fetch_finnhub_market_news(category),
            self._fetch_newsapi_headlines(category)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)

        # Deduplicate and rank
        unique_news = self.deduplicate_by_similarity(all_news, threshold=0.85)
        ranked_news = self.rank_by_reliability(unique_news)

        return ranked_news[:limit]

    async def search_news(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search news across all sources.

        Args:
            query: Search query
            from_date: Start date
            to_date: End date
            limit: Maximum results

        Returns:
            Search results
        """
        if not to_date:
            to_date = datetime.now()
        if not from_date:
            from_date = to_date - timedelta(days=7)

        # Search NewsAPI (primary search source)
        results = await self.newsapi.search_everything(
            query=query,
            from_date=from_date,
            to_date=to_date,
            page_size=limit
        )

        # Deduplicate and rank
        unique_news = self.deduplicate_by_similarity(results, threshold=0.85)
        ranked_news = self.rank_by_reliability(unique_news)

        return ranked_news[:limit]

    def deduplicate_by_similarity(
        self,
        articles: List[Dict[str, Any]],
        threshold: float = 0.85
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate articles using title similarity.

        Args:
            articles: List of articles
            threshold: Similarity threshold (0-1)

        Returns:
            Deduplicated list
        """
        unique_articles = []
        seen_titles = []

        for article in articles:
            title = article.get("title", "").lower().strip()

            if not title:
                continue

            # Check similarity with all seen titles
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = SequenceMatcher(None, title, seen_title).ratio()
                if similarity >= threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.append(title)

        return unique_articles

    def rank_by_reliability(
        self,
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rank articles by source reliability and recency.

        Args:
            articles: List of articles

        Returns:
            Ranked list
        """
        def calculate_score(article: Dict[str, Any]) -> float:
            # Get source reliability
            source_api = article.get("source_api", "unknown")
            reliability = self.source_reliability.get(source_api, 0.5)

            # Calculate recency score (exponential decay, 7-day half-life)
            published_at = article.get("published_at")
            if isinstance(published_at, datetime):
                days_old = (datetime.now() - published_at).days
                recency_score = 0.5 ** (days_old / 7)  # Exponential decay
            else:
                recency_score = 0.5

            # Combined score (60% reliability, 40% recency)
            return (reliability * 0.6) + (recency_score * 0.4)

        # Sort by score (descending)
        ranked = sorted(articles, key=calculate_score, reverse=True)

        return ranked

    # ==================== Source-Specific Fetch Methods ====================

    async def _fetch_finnhub_stock_news(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch stock news from Finnhub."""
        try:
            return await self.finnhub.get_company_news(
                symbol,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d")
            )
        except Exception as e:
            print(f"❌ Finnhub stock news error: {e}")
            return []

    async def _fetch_polygon_stock_news(
        self,
        symbol: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Fetch stock news from Polygon."""
        try:
            return await self.polygon.get_ticker_news(symbol, limit=limit)
        except Exception as e:
            print(f"❌ Polygon stock news error: {e}")
            return []

    async def _fetch_newsapi_stock_news(
        self,
        symbol: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch stock news from NewsAPI."""
        try:
            return await self.newsapi.search_everything(
                query=symbol,
                from_date=from_date,
                to_date=to_date,
                page_size=10
            )
        except Exception as e:
            print(f"❌ NewsAPI stock news error: {e}")
            return []

    async def _fetch_finnhub_market_news(
        self,
        category: str
    ) -> List[Dict[str, Any]]:
        """Fetch market news from Finnhub."""
        try:
            return await self.finnhub.get_market_news(category=category)
        except Exception as e:
            print(f"❌ Finnhub market news error: {e}")
            return []

    async def _fetch_newsapi_headlines(
        self,
        category: str
    ) -> List[Dict[str, Any]]:
        """Fetch headlines from NewsAPI."""
        try:
            return await self.newsapi.get_top_headlines(
                country="us",
                category=category,
                page_size=20
            )
        except Exception as e:
            print(f"❌ NewsAPI headlines error: {e}")
            return []


# Global instance
_news_aggregator: Optional[NewsAggregator] = None


def get_news_aggregator() -> NewsAggregator:
    """Get or create news aggregator instance."""
    global _news_aggregator
    if _news_aggregator is None:
        _news_aggregator = NewsAggregator()
    return _news_aggregator

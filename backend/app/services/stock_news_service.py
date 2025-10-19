"""Stock news service with LIFO stack management."""
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..db.stock_news import StockNewsDB
from ..cache import cache_manager
from ..lfu_cache.lfu_manager import get_lfu_cache
from ..external.finnhub_client import get_finnhub_client
from ..external.polygon_client import get_polygon_client
from ..database import db_manager


class StockNewsService:
    """
    Stock news service with LIFO stack management.

    Features:
    - LIFO stack (Latest 5 on Top) with Redis caching
    - Multi-source news aggregation (Finnhub + Polygon)
    - Automatic archival of position 6+
    - Deduplication by title similarity
    """

    def __init__(self):
        self.stock_news_db = None  # Will be initialized in initialize()
        self.finnhub = get_finnhub_client()
        self.polygon = get_polygon_client()
        self.lfu_cache = None

    async def initialize(self):
        """Initialize service dependencies."""
        if not db_manager._initialized:
            await db_manager.initialize()

        if not cache_manager._initialized:
            await cache_manager.initialize()

        # Initialize StockNewsDB AFTER db_manager is initialized
        self.stock_news_db = StockNewsDB(db_manager.client)
        self.lfu_cache = await get_lfu_cache()

    async def get_stock_news(
        self,
        symbol: str,
        limit: int = 5,
        refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get top N news from LIFO stack with smart fallback: Redis → Database → API.

        Priority:
        1. Redis cache (if data is fresh, < 2 minutes)
        2. Database LIFO stack (recent articles)
        3. External APIs (aggregate from multiple sources)

        Args:
            symbol: Stock ticker symbol
            limit: Number of articles (max 5 for stack)
            refresh: Force cache refresh (skip Redis/DB, go straight to API)

        Returns:
            News response with articles and metadata
        """
        if not self.lfu_cache:
            await self.initialize()

        cache_key = f"stock:news:{symbol.upper()}"
        start_time = time.time()

        # Step 1: Try Redis cache first (unless refresh requested)
        if not refresh:
            cached_news = await cache_manager.get(cache_key)
            if cached_news:
                # Check if data is fresh (< 2 minutes old)
                cache_time = cached_news.get("cached_at")
                if cache_time:
                    if isinstance(cache_time, str):
                        cache_time = datetime.fromisoformat(cache_time.replace('Z', '+00:00'))

                    age_minutes = (datetime.now() - cache_time).total_seconds() / 60

                    if age_minutes < 2:  # Fresh data
                        # Track LFU access
                        await self.lfu_cache.track_access(cache_key, "stock_news")

                        return {
                            "symbol": symbol.upper(),
                            "news": cached_news.get("news", [])[:limit],
                            "total_count": len(cached_news.get("news", [])),
                            "last_updated": cache_time,
                            "source": "redis",
                            "cache_hit": True,
                            "age_minutes": round(age_minutes, 2),
                            "response_time_ms": int((time.time() - start_time) * 1000)
                        }

        # Step 2: Try Database LIFO stack
        if not refresh:
            db_news = await self.stock_news_db.get_news_stack(symbol, limit)

            if db_news:
                # Format news items
                news_items = [self._format_news_item(item) for item in db_news]

                # Check freshness of database data
                if news_items:
                    latest_published = news_items[0].get("published_at")
                    if isinstance(latest_published, str):
                        latest_published = datetime.fromisoformat(latest_published.replace('Z', '+00:00'))

                    age_minutes = (datetime.now() - latest_published).total_seconds() / 60

                    # Use DB data if it's reasonably fresh (< 5 minutes)
                    if age_minutes < 5:
                        # Store in Redis for next time (2-minute TTL)
                        cache_data = {
                            "news": news_items,
                            "cached_at": datetime.now().isoformat()
                        }
                        await cache_manager.set(cache_key, cache_data, ttl=120)

                        # Track LFU access
                        await self.lfu_cache.track_access(cache_key, "stock_news")

                        return {
                            "symbol": symbol.upper(),
                            "news": news_items,
                            "total_count": len(news_items),
                            "last_updated": datetime.now(),
                            "source": "database",
                            "cache_hit": False,
                            "age_minutes": round(age_minutes, 2),
                            "response_time_ms": int((time.time() - start_time) * 1000)
                        }

        # Step 3: Fetch from external APIs (last resort or if refresh requested)
        fresh_news = await self._fetch_from_external_apis(symbol, limit)

        if fresh_news:
            # Push articles to database LIFO stack
            for article in fresh_news[:limit]:  # Top N only
                try:
                    news_data = {
                        'symbol': symbol,
                        'title': article.get('title'),
                        'summary': article.get('summary') or article.get('description'),
                        'url': article.get('url'),
                        'source_name': article.get('source', {}).get('name', 'Unknown'),
                        'published_at': article.get('published_at'),
                        'sentiment_score': article.get('sentiment_score')
                    }
                    await self.stock_news_db.push_news_to_stack(symbol, news_data)
                except Exception as e:
                    print(f"❌ Error pushing news to stack: {e}")

            # Store in Redis cache (2-minute TTL)
            cache_data = {
                "news": fresh_news,
                "cached_at": datetime.now().isoformat()
            }
            await cache_manager.set(cache_key, cache_data, ttl=120)

            # Track LFU access
            await self.lfu_cache.track_access(cache_key, "stock_news")

            return {
                "symbol": symbol.upper(),
                "news": fresh_news,
                "total_count": len(fresh_news),
                "last_updated": datetime.now(),
                "source": "api",
                "cache_hit": False,
                "age_minutes": 0,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }

        return {
            "symbol": symbol.upper(),
            "news": [],
            "total_count": 0,
            "last_updated": datetime.now(),
            "cache_hit": False,
            "response_time_ms": int((time.time() - start_time) * 1000)
        }

    async def push_news_to_stack(
        self,
        symbol: str,
        news_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Push new news to position 1 (top of stack).

        Args:
            symbol: Stock ticker symbol
            news_data: News article data

        Returns:
            Created article with archived ID if any
        """
        if not self.lfu_cache:
            await self.initialize()

        # Push to database (handles stack shifting and archival)
        result = await self.stock_news_db.push_news_to_stack(symbol, news_data)

        if result:
            # Invalidate cache to force refresh
            cache_key = f"stock:news:{symbol.upper()}:stack"
            await cache_manager.delete(cache_key)

            return {
                "id": result.get("id"),
                "symbol": symbol.upper(),
                "position_in_stack": 1,
                "archived_article_id": result.get("archived_article_id"),
                "created_at": result.get("created_at", datetime.now())
            }

        return None

    async def _fetch_from_external_apis(
        self,
        symbol: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from external APIs (Finnhub + Polygon).

        Args:
            symbol: Stock ticker symbol
            limit: Number of articles

        Returns:
            List of news articles
        """
        all_news = []

        # Fetch from Finnhub
        try:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)

            finnhub_news = await self.finnhub.get_company_news(
                symbol,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d")
            )
            all_news.extend(finnhub_news)
        except Exception as e:
            print(f"❌ Finnhub news fetch failed for {symbol}: {e}")

        # Fetch from Polygon
        try:
            polygon_news = await self.polygon.get_ticker_news(symbol, limit=10)
            all_news.extend(polygon_news)
        except Exception as e:
            print(f"❌ Polygon news fetch failed for {symbol}: {e}")

        # Deduplicate and sort by date
        unique_news = self._deduplicate_news(all_news)
        unique_news.sort(key=lambda x: x.get("published_at", datetime.min), reverse=True)

        return unique_news[:limit]

    def _deduplicate_news(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate news articles by title similarity (85% threshold).

        Args:
            articles: List of news articles

        Returns:
            Deduplicated list
        """
        from difflib import SequenceMatcher

        unique_articles = []
        seen_titles = []

        for article in articles:
            title = article.get("title", "").lower()

            if not title:
                continue

            # Check similarity with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = SequenceMatcher(None, title, seen_title).ratio()
                if similarity > 0.85:  # 85% similarity threshold
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.append(title)

        return unique_articles

    def _format_news_item(self, db_item: Dict[str, Any]) -> Dict[str, Any]:
        """Format database news item for API response."""
        source_data = db_item.get("news_sources", {})

        return {
            "id": db_item.get("id"),
            "title": db_item.get("title"),
            "summary": db_item.get("summary"),
            "url": db_item.get("url"),
            "published_at": db_item.get("published_at"),
            "source": {
                "id": source_data.get("id"),
                "name": source_data.get("name"),
                "reliability_score": source_data.get("reliability_score")
            },
            "sentiment_score": db_item.get("sentiment_score"),
            "topics": db_item.get("topics", []),
            "is_breaking": db_item.get("is_breaking", False),
            "position_in_stack": db_item.get("position_in_stack")
        }

    async def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get news from Redis cache."""
        try:
            # Get from list (LIFO stack)
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                return cached_data
        except Exception as e:
            print(f"❌ Cache get error for {cache_key}: {e}")

        return None

    async def _store_in_cache(
        self,
        cache_key: str,
        news_items: List[Dict[str, Any]],
        ttl: int = 900
    ):
        """Store news in Redis cache."""
        try:
            await cache_manager.set(cache_key, news_items, ttl)
        except Exception as e:
            print(f"❌ Cache set error for {cache_key}: {e}")


# Global instance
_stock_news_service: Optional[StockNewsService] = None


async def get_stock_news_service() -> StockNewsService:
    """Get or create stock news service instance."""
    global _stock_news_service
    if _stock_news_service is None:
        _stock_news_service = StockNewsService()
        await _stock_news_service.initialize()
    return _stock_news_service

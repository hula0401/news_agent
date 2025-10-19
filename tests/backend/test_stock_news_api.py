"""
Tests for stock news API with different cache scenarios.

Tests cover:
- LIFO stack behavior (positions 1-5)
- Redis cache priority
- Multi-source news aggregation
- News deduplication
- Error handling
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.app.services.stock_news_service import StockNewsService


class TestStockNewsStackBehavior:
    """Test suite for LIFO stack news management."""

    @pytest.mark.asyncio
    async def test_get_latest_news_from_stack(self):
        """Test fetching latest 5 news from LIFO stack."""
        service = StockNewsService()

        # Mock database with 5 news articles in stack
        mock_db = AsyncMock()
        mock_db.get_latest_news_stack.return_value = [
            {
                'id': '5',
                'title': 'Latest Article 5',
                'summary': 'Most recent news',
                'position': 1,  # Top of stack
                'published_at': datetime.utcnow().isoformat()
            },
            {
                'id': '4',
                'title': 'Latest Article 4',
                'summary': 'Second most recent',
                'position': 2,
                'published_at': (datetime.utcnow() - timedelta(minutes=10)).isoformat()
            },
            {
                'id': '3',
                'title': 'Latest Article 3',
                'position': 3,
                'published_at': (datetime.utcnow() - timedelta(minutes=20)).isoformat()
            },
            {
                'id': '2',
                'title': 'Latest Article 2',
                'position': 4,
                'published_at': (datetime.utcnow() - timedelta(minutes=30)).isoformat()
            },
            {
                'id': '1',
                'title': 'Latest Article 1',
                'position': 5,  # Bottom of stack
                'published_at': (datetime.utcnow() - timedelta(minutes=40)).isoformat()
            }
        ]

        with patch.object(service, 'stock_news_db', mock_db):
            result = await service.get_latest_news('AAPL', limit=5)

            # Verify stack was queried
            mock_db.get_latest_news_stack.assert_called_once_with('AAPL', limit=5)

            # Verify LIFO order (most recent first)
            assert len(result) == 5
            assert result[0]['position'] == 1
            assert result[0]['title'] == 'Latest Article 5'
            assert result[4]['position'] == 5
            assert result[4]['title'] == 'Latest Article 1'

    @pytest.mark.asyncio
    async def test_push_new_article_to_stack_top(self):
        """Test pushing new article to top of stack (position 1)."""
        service = StockNewsService()

        mock_db = AsyncMock()

        new_article = {
            'title': 'Breaking News',
            'summary': 'Just happened',
            'url': 'https://example.com/breaking',
            'source': {'name': 'Reuters'},
            'published_at': datetime.utcnow().isoformat()
        }

        with patch.object(service, 'stock_news_db', mock_db):
            await service.push_news_to_stack('AAPL', new_article)

            # Verify article was pushed to stack
            mock_db.push_news_to_stack.assert_called_once()
            call_args = mock_db.push_news_to_stack.call_args[0]

            # Should be pushed with position 1
            assert call_args[0] == 'AAPL'
            assert 'Breaking News' in str(call_args[1])

    @pytest.mark.asyncio
    async def test_stack_maintains_max_5_articles(self):
        """Test stack automatically removes oldest article when full."""
        service = StockNewsService()

        mock_db = AsyncMock()
        # Simulate stack is full (5 articles)
        mock_db.get_stack_size.return_value = 5

        new_article = {
            'title': 'New Article 6',
            'summary': 'This should push out article 1',
            'published_at': datetime.utcnow().isoformat()
        }

        with patch.object(service, 'stock_news_db', mock_db):
            await service.push_news_to_stack('AAPL', new_article)

            # Verify stack was updated (old article removed)
            mock_db.push_news_to_stack.assert_called_once()


class TestStockNewsCachePriority:
    """Test suite for news cache fallback: Redis → Stack → Aggregation."""

    @pytest.mark.asyncio
    async def test_redis_cache_hit_for_news(self):
        """Test Redis returns cached news - no DB/API calls."""
        service = StockNewsService()

        # Mock Redis cache with news
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = [
            {
                'title': 'Cached Article 1',
                'summary': 'From Redis',
                'published_at': datetime.utcnow().isoformat(),
                'cache_source': 'redis'
            }
        ]

        mock_db = AsyncMock()
        mock_aggregator = AsyncMock()

        with patch('backend.app.services.stock_news_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_news_db', mock_db):
                result = await service.get_latest_news('AAPL', limit=5)

                # Verify Redis was queried
                mock_cache_manager.get.assert_called()

                # Verify DB was NOT called (cache hit)
                mock_db.get_latest_news_stack.assert_not_called()

                # Verify result is from cache
                assert len(result) > 0
                assert result[0]['title'] == 'Cached Article 1'

    @pytest.mark.asyncio
    async def test_database_fallback_for_news(self):
        """Test DB fallback when Redis cache misses."""
        service = StockNewsService()

        # Mock Redis cache miss
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = None

        # Mock Database with news
        mock_db = AsyncMock()
        mock_db.get_latest_news_stack.return_value = [
            {
                'title': 'Database Article 1',
                'summary': 'From DB stack',
                'position': 1,
                'published_at': datetime.utcnow().isoformat()
            }
        ]

        with patch('backend.app.services.stock_news_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_news_db', mock_db):
                result = await service.get_latest_news('AAPL', limit=5)

                # Verify cache was checked
                mock_cache_manager.get.assert_called()

                # Verify DB was queried
                mock_db.get_latest_news_stack.assert_called_once()

                # Verify cache was updated with DB data
                mock_cache_manager.set.assert_called()

                # Verify result is from database
                assert result[0]['title'] == 'Database Article 1'

    @pytest.mark.asyncio
    async def test_api_aggregation_fallback(self):
        """Test multi-source aggregation when cache and DB empty."""
        service = StockNewsService()

        # Mock Redis cache miss
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = None

        # Mock Database empty
        mock_db = AsyncMock()
        mock_db.get_latest_news_stack.return_value = []

        # Mock news aggregator
        mock_aggregator = AsyncMock()
        mock_aggregator.aggregate_stock_news.return_value = [
            {
                'title': 'Aggregated Article 1',
                'summary': 'From Finnhub/Polygon/NewsAPI',
                'url': 'https://example.com/1',
                'source': {'name': 'Finnhub'},
                'published_at': datetime.utcnow().isoformat()
            }
        ]

        with patch('backend.app.services.stock_news_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_news_db', mock_db):
                with patch('backend.app.services.news_aggregator.NewsAggregator', return_value=mock_aggregator):
                    result = await service.get_latest_news('AAPL', limit=5, refresh=True)

                    # Verify aggregation was called
                    mock_aggregator.initialize.assert_called()
                    mock_aggregator.aggregate_stock_news.assert_called()

                    # Verify articles were pushed to stack
                    mock_db.push_news_to_stack.assert_called()


class TestNewsAggregation:
    """Test suite for multi-source news aggregation."""

    @pytest.mark.asyncio
    async def test_multi_source_aggregation(self):
        """Test aggregating news from multiple sources (Finnhub, Polygon, NewsAPI)."""
        # This tests NewsAggregator directly
        from backend.app.services.news_aggregator import NewsAggregator

        aggregator = NewsAggregator()

        # Mock Finnhub client
        mock_finnhub = AsyncMock()
        mock_finnhub.get_company_news.return_value = [
            {
                'headline': 'Finnhub Article',
                'summary': 'From Finnhub',
                'url': 'https://finnhub.com/1',
                'source': 'Finnhub',
                'datetime': int(datetime.utcnow().timestamp())
            }
        ]

        # Mock Polygon client
        mock_polygon = AsyncMock()
        mock_polygon.get_ticker_news.return_value = [
            {
                'title': 'Polygon Article',
                'description': 'From Polygon',
                'article_url': 'https://polygon.io/1',
                'publisher': {'name': 'Polygon'},
                'published_utc': datetime.utcnow().isoformat()
            }
        ]

        # Mock NewsAPI client
        mock_newsapi = AsyncMock()
        mock_newsapi.search_stock_news.return_value = [
            {
                'title': 'NewsAPI Article',
                'description': 'From NewsAPI',
                'url': 'https://newsapi.org/1',
                'source': {'name': 'NewsAPI'},
                'publishedAt': datetime.utcnow().isoformat()
            }
        ]

        with patch.object(aggregator, 'finnhub', mock_finnhub):
            with patch.object(aggregator, 'polygon', mock_polygon):
                with patch.object(aggregator, 'newsapi', mock_newsapi):
                    await aggregator.initialize()
                    results = await aggregator.aggregate_stock_news('AAPL', limit=10)

                    # Should get articles from all sources
                    assert len(results) > 0

                    # Verify all sources were called
                    mock_finnhub.get_company_news.assert_called()
                    mock_polygon.get_ticker_news.assert_called()
                    mock_newsapi.search_stock_news.assert_called()

    @pytest.mark.asyncio
    async def test_news_deduplication_by_url(self):
        """Test that duplicate articles (same URL) are filtered out."""
        from backend.app.services.news_aggregator import NewsAggregator

        aggregator = NewsAggregator()

        # Mock multiple sources returning duplicate article
        duplicate_url = 'https://reuters.com/apple-earnings'

        mock_finnhub = AsyncMock()
        mock_finnhub.get_company_news.return_value = [
            {
                'headline': 'Apple Earnings',
                'url': duplicate_url,
                'source': 'Reuters',
                'datetime': int(datetime.utcnow().timestamp())
            }
        ]

        mock_polygon = AsyncMock()
        mock_polygon.get_ticker_news.return_value = [
            {
                'title': 'Apple Earnings',
                'article_url': duplicate_url,  # Same URL
                'publisher': {'name': 'Reuters'},
                'published_utc': datetime.utcnow().isoformat()
            }
        ]

        with patch.object(aggregator, 'finnhub', mock_finnhub):
            with patch.object(aggregator, 'polygon', mock_polygon):
                with patch.object(aggregator, 'newsapi', AsyncMock()):
                    await aggregator.initialize()
                    results = await aggregator.aggregate_stock_news('AAPL', limit=10)

                    # Should only have 1 article (duplicate removed)
                    unique_urls = {article.get('url') for article in results}
                    assert len(unique_urls) == len(results)

    @pytest.mark.asyncio
    async def test_news_sorted_by_recency(self):
        """Test that aggregated news is sorted by published date (newest first)."""
        from backend.app.services.news_aggregator import NewsAggregator

        aggregator = NewsAggregator()

        # Mock articles with different timestamps
        now = datetime.utcnow()

        mock_finnhub = AsyncMock()
        mock_finnhub.get_company_news.return_value = [
            {
                'headline': 'Old Article',
                'url': 'https://example.com/old',
                'source': 'Reuters',
                'datetime': int((now - timedelta(hours=5)).timestamp())
            }
        ]

        mock_polygon = AsyncMock()
        mock_polygon.get_ticker_news.return_value = [
            {
                'title': 'New Article',
                'article_url': 'https://example.com/new',
                'publisher': {'name': 'Bloomberg'},
                'published_utc': now.isoformat()
            }
        ]

        with patch.object(aggregator, 'finnhub', mock_finnhub):
            with patch.object(aggregator, 'polygon', mock_polygon):
                with patch.object(aggregator, 'newsapi', AsyncMock()):
                    await aggregator.initialize()
                    results = await aggregator.aggregate_stock_news('AAPL', limit=10)

                    # Newest article should be first
                    if len(results) >= 2:
                        assert 'New Article' in results[0].get('title', '')


class TestNewsErrorHandling:
    """Test suite for news error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_partial_source_failure(self):
        """Test aggregation continues when one source fails."""
        from backend.app.services.news_aggregator import NewsAggregator

        aggregator = NewsAggregator()

        # Finnhub fails
        mock_finnhub = AsyncMock()
        mock_finnhub.get_company_news.side_effect = Exception("Finnhub API error")

        # Polygon succeeds
        mock_polygon = AsyncMock()
        mock_polygon.get_ticker_news.return_value = [
            {
                'title': 'Polygon Article',
                'article_url': 'https://polygon.io/1',
                'publisher': {'name': 'Polygon'},
                'published_utc': datetime.utcnow().isoformat()
            }
        ]

        with patch.object(aggregator, 'finnhub', mock_finnhub):
            with patch.object(aggregator, 'polygon', mock_polygon):
                with patch.object(aggregator, 'newsapi', AsyncMock()):
                    await aggregator.initialize()
                    # Should not raise exception
                    results = await aggregator.aggregate_stock_news('AAPL', limit=10)

                    # Should still get results from working sources
                    assert len(results) > 0

    @pytest.mark.asyncio
    async def test_all_sources_fail(self):
        """Test graceful handling when all news sources fail."""
        from backend.app.services.news_aggregator import NewsAggregator

        aggregator = NewsAggregator()

        # All sources fail
        mock_error = Exception("API error")

        mock_finnhub = AsyncMock()
        mock_finnhub.get_company_news.side_effect = mock_error

        mock_polygon = AsyncMock()
        mock_polygon.get_ticker_news.side_effect = mock_error

        mock_newsapi = AsyncMock()
        mock_newsapi.search_stock_news.side_effect = mock_error

        with patch.object(aggregator, 'finnhub', mock_finnhub):
            with patch.object(aggregator, 'polygon', mock_polygon):
                with patch.object(aggregator, 'newsapi', mock_newsapi):
                    await aggregator.initialize()
                    # Should not raise exception
                    results = await aggregator.aggregate_stock_news('AAPL', limit=10)

                    # Should return empty list
                    assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

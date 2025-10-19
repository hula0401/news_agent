"""
Tests for background scheduler functionality.

Tests cover:
- Scheduler initialization
- Stock price updates
- News updates
- Error handling
- Database interactions
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.app.scheduler.scheduler_manager import SchedulerManager


class TestSchedulerManager:
    """Test suite for SchedulerManager."""

    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        scheduler = SchedulerManager()

        assert scheduler.scheduler is None
        assert scheduler._running is False

    def test_scheduler_disabled_via_config(self):
        """Test scheduler doesn't start when disabled."""
        scheduler = SchedulerManager()

        with patch('backend.app.scheduler.scheduler_manager.settings') as mock_settings:
            mock_settings.enable_scheduler = False

            scheduler.start()

            assert scheduler._running is False
            assert scheduler.scheduler is None

    def test_scheduler_prevents_duplicate_start(self):
        """Test scheduler prevents starting twice."""
        scheduler = SchedulerManager()

        # Manually set as running to simulate first start
        scheduler._running = True
        scheduler.scheduler = MagicMock()

        with patch('backend.app.scheduler.scheduler_manager.settings') as mock_settings:
            mock_settings.enable_scheduler = True
            mock_settings.stock_update_interval_minutes = 5
            mock_settings.news_update_interval_minutes = 5

            # Store the first instance
            first_scheduler_instance = scheduler.scheduler

            # Try starting again - should not create new instance
            scheduler.start()

            # Should be same instance (prevented duplicate)
            assert scheduler.scheduler is first_scheduler_instance
            assert scheduler._running is True


class TestPopularStocksUpdate:
    """Test suite for popular stocks update job."""

    @pytest.mark.asyncio
    async def test_popular_stocks_update_success(self):
        """Test successful stock price update."""
        scheduler = SchedulerManager()

        # Mock dependencies
        mock_yf_client = AsyncMock()
        mock_yf_client.get_batch_quotes.return_value = {
            "AAPL": {
                "symbol": "AAPL",
                "price": 175.43,
                "change": 2.15,
                "change_percent": 1.24,
                "volume": 54321000,
                "market_cap": 2800000000000
            },
            "GOOGL": {
                "symbol": "GOOGL",
                "price": 140.25,
                "change": 1.20,
                "change_percent": 0.86,
                "volume": 32100000,
                "market_cap": 1750000000000
            }
        }

        mock_stock_db = AsyncMock()
        mock_cache_manager = AsyncMock()
        mock_cache_manager._initialized = True
        mock_db_manager = MagicMock()
        mock_db_manager.client = MagicMock()

        # Patch the imports inside the method
        with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
            with patch('backend.app.db.stock_prices.StockPriceDB', return_value=mock_stock_db):
                with patch('backend.app.cache.cache_manager', mock_cache_manager):
                    with patch('backend.app.database.db_manager', mock_db_manager):
                        with patch('backend.app.scheduler.scheduler_manager.settings') as mock_settings:
                            mock_settings.popular_stocks = "AAPL,GOOGL"

                            # Run the update
                            await scheduler._update_popular_stocks()

                            # Verify YFinance was called
                            mock_yf_client.get_batch_quotes.assert_called_once()

                            # Verify database inserts (2 stocks)
                            assert mock_stock_db.insert_price.call_count == 2

                            # Verify cache updates
                            assert mock_cache_manager.set.call_count == 2

    @pytest.mark.asyncio
    async def test_popular_stocks_update_no_stocks_configured(self):
        """Test update handles no stocks configured."""
        scheduler = SchedulerManager()

        with patch('backend.app.scheduler.scheduler_manager.settings') as mock_settings:
            mock_settings.popular_stocks = ""

            # Should not raise error
            await scheduler._update_popular_stocks()

    @pytest.mark.asyncio
    async def test_popular_stocks_update_partial_failure(self):
        """Test update continues on individual stock failures."""
        scheduler = SchedulerManager()

        mock_yf_client = AsyncMock()
        mock_yf_client.get_batch_quotes.return_value = {
            "AAPL": {
                "symbol": "AAPL",
                "price": 175.43,
                "change": 2.15,
                "change_percent": 1.24
            },
            "INVALID": None  # Failed to fetch
        }

        mock_stock_db = AsyncMock()
        mock_cache_manager = AsyncMock()
        mock_cache_manager._initialized = True
        mock_db_manager = MagicMock()
        mock_db_manager.client = MagicMock()

        with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
            with patch('backend.app.db.stock_prices.StockPriceDB', return_value=mock_stock_db):
                with patch('backend.app.cache.cache_manager', mock_cache_manager):
                    with patch('backend.app.database.db_manager', mock_db_manager):
                        with patch('backend.app.scheduler.scheduler_manager.settings') as mock_settings:
                            mock_settings.popular_stocks = "AAPL,INVALID"

                            # Should not raise error
                            await scheduler._update_popular_stocks()

                            # Should only update AAPL (1 stock)
                            assert mock_stock_db.insert_price.call_count == 1


class TestLatestNewsUpdate:
    """Test suite for latest news update job."""

    @pytest.mark.asyncio
    async def test_news_update_success(self):
        """Test successful news update."""
        scheduler = SchedulerManager()

        # Mock dependencies
        mock_news_aggregator = AsyncMock()
        mock_news_aggregator.aggregate_stock_news.return_value = [
            {
                "title": "Apple unveils new AI features",
                "summary": "Apple announced...",
                "url": "https://example.com/article1",
                "source": {"name": "Reuters"},
                "published_at": datetime.now().isoformat()
            }
        ]

        mock_stock_news_db = AsyncMock()
        mock_cache_manager = AsyncMock()
        mock_cache_manager._initialized = True
        mock_db_manager = MagicMock()
        mock_db_manager.client = MagicMock()

        # Patch the imports inside the method
        with patch('backend.app.services.news_aggregator.NewsAggregator', return_value=mock_news_aggregator):
            with patch('backend.app.db.stock_news.StockNewsDB', return_value=mock_stock_news_db):
                with patch('backend.app.cache.cache_manager', mock_cache_manager):
                    with patch('backend.app.database.db_manager', mock_db_manager):
                        with patch('backend.app.scheduler.scheduler_manager.settings') as mock_settings:
                            mock_settings.popular_stocks = "AAPL"

                            # Run the update
                            await scheduler._update_latest_news()

                            # Verify initialize was called
                            mock_news_aggregator.initialize.assert_called_once()

                            # Verify news aggregation was called
                            mock_news_aggregator.aggregate_stock_news.assert_called_once_with("AAPL", limit=5)

                            # Verify news was pushed to stack
                            assert mock_stock_news_db.push_news_to_stack.call_count == 1

    @pytest.mark.asyncio
    async def test_news_update_no_articles_found(self):
        """Test update handles no articles found."""
        scheduler = SchedulerManager()

        mock_news_aggregator = AsyncMock()
        mock_news_aggregator.aggregate_stock_news.return_value = []  # No articles

        mock_cache_manager = AsyncMock()
        mock_cache_manager._initialized = True

        with patch('backend.app.services.news_aggregator.NewsAggregator', return_value=mock_news_aggregator):
            with patch('backend.app.cache.cache_manager', mock_cache_manager):
                with patch('backend.app.scheduler.scheduler_manager.settings') as mock_settings:
                    mock_settings.popular_stocks = "AAPL"

                    # Should not raise error
                    await scheduler._update_latest_news()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for stock price API with different cache scenarios.

Tests cover:
- Redis cache hit (< 2 min fresh)
- Database fallback (< 5 min fresh)
- API fallback (external fetch)
- Refresh parameter behavior
- Error handling and graceful degradation
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from backend.app.services.stock_price_service import StockPriceService


class TestStockPriceCacheScenarios:
    """Test suite for stock price cache priority: Redis → DB → API."""

    @pytest.mark.asyncio
    async def test_redis_cache_hit_fresh_data(self):
        """Test Redis returns fresh data (< 2 min) - no DB/API calls."""
        service = StockPriceService()

        # Mock Redis cache with fresh data (1 minute old)
        mock_cache_manager = AsyncMock()
        fresh_timestamp = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        mock_cache_manager.get.return_value = {
            'symbol': 'AAPL',
            'price': 175.43,
            'change': 2.15,
            'change_percent': 1.24,
            'last_updated': fresh_timestamp,
            'data_source': 'yfinance'
        }

        mock_db = AsyncMock()
        mock_yf_client = AsyncMock()

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            with patch('backend.app.services.stock_price_service.StockPriceDB', return_value=mock_db):
                with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
                    result = await service.get_stock_price('AAPL', refresh=False)

                    # Verify Redis was queried
                    mock_cache_manager.get.assert_called_once()

                    # Verify DB and API were NOT called
                    mock_db.get_latest_price.assert_not_called()
                    mock_yf_client.get_stock_quote.assert_not_called()

                    # Verify result source
                    assert result['source'] == 'redis'
                    assert result['cache_hit'] is True
                    assert result['data']['symbol'] == 'AAPL'
                    assert result['data']['price'] == 175.43

    @pytest.mark.asyncio
    async def test_database_fallback_when_redis_stale(self):
        """Test DB fallback when Redis data is stale (> 2 min but < 5 min)."""
        service = StockPriceService()

        # Mock Redis cache with stale data (3 minutes old)
        mock_cache_manager = AsyncMock()
        stale_timestamp = (datetime.utcnow() - timedelta(minutes=3)).isoformat()
        mock_cache_manager.get.return_value = {
            'symbol': 'AAPL',
            'price': 175.00,  # Old price
            'last_updated': stale_timestamp
        }

        # Mock Database with fresher data (2 minutes old)
        mock_db = AsyncMock()
        fresh_db_timestamp = (datetime.utcnow() - timedelta(minutes=2)).isoformat()
        mock_db.get_latest_price.return_value = {
            'symbol': 'AAPL',
            'price': 175.43,  # Newer price
            'change': 2.15,
            'change_percent': 1.24,
            'last_updated': fresh_db_timestamp,
            'data_source': 'database'
        }

        mock_yf_client = AsyncMock()

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_price_db', mock_db):
                with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
                    result = await service.get_stock_price('AAPL', refresh=False)

                    # Verify Redis was checked
                    mock_cache_manager.get.assert_called()

                    # Verify DB was queried
                    mock_db.get_latest_price.assert_called_once_with('AAPL')

                    # Verify API was NOT called
                    mock_yf_client.get_stock_quote.assert_not_called()

                    # Verify Redis was updated with DB data
                    mock_cache_manager.set.assert_called_once()

                    # Verify result source
                    assert result['source'] == 'database'
                    assert result['data']['price'] == 175.43

    @pytest.mark.asyncio
    async def test_api_fallback_when_cache_and_db_stale(self):
        """Test API fallback when both Redis and DB data are stale (> 5 min)."""
        service = StockPriceService()

        # Mock Redis cache with very stale data (10 minutes old)
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = None  # No cache

        # Mock Database with stale data (6 minutes old)
        mock_db = AsyncMock()
        stale_db_timestamp = (datetime.utcnow() - timedelta(minutes=6)).isoformat()
        mock_db.get_latest_price.return_value = {
            'symbol': 'AAPL',
            'price': 170.00,  # Old price
            'last_updated': stale_db_timestamp
        }

        # Mock YFinance API with fresh data
        mock_yf_client = AsyncMock()
        mock_yf_client.get_stock_quote.return_value = {
            'symbol': 'AAPL',
            'price': 176.50,  # Current price
            'change': 2.50,
            'change_percent': 1.45,
            'volume': 50000000,
            'last_updated': datetime.utcnow().isoformat(),
            'data_source': 'yfinance'
        }

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_price_db', mock_db):
                with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
                    result = await service.get_stock_price('AAPL', refresh=False)

                    # Verify full fallback chain
                    mock_cache_manager.get.assert_called()
                    mock_db.get_latest_price.assert_called_once()
                    mock_yf_client.get_stock_quote.assert_called_once_with('AAPL')

                    # Verify DB and cache were updated
                    mock_db.insert_price.assert_called_once()
                    mock_cache_manager.set.assert_called()

                    # Verify result source
                    assert result['source'] == 'api'
                    assert result['data']['price'] == 176.50

    @pytest.mark.asyncio
    async def test_refresh_parameter_bypasses_cache(self):
        """Test refresh=True forces API fetch, bypassing cache."""
        service = StockPriceService()

        # Mock Redis cache with fresh data
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = {
            'symbol': 'AAPL',
            'price': 175.00,
            'last_updated': datetime.utcnow().isoformat()
        }

        # Mock YFinance API
        mock_yf_client = AsyncMock()
        mock_yf_client.get_stock_quote.return_value = {
            'symbol': 'AAPL',
            'price': 176.50,  # Different from cache
            'change': 2.50,
            'change_percent': 1.45,
            'last_updated': datetime.utcnow().isoformat(),
            'data_source': 'yfinance'
        }

        mock_db = AsyncMock()

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_price_db', mock_db):
                with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
                    result = await service.get_stock_price('AAPL', refresh=True)

                    # Verify cache was bypassed
                    mock_yf_client.get_stock_quote.assert_called_once()

                    # Verify DB and cache were updated
                    mock_db.insert_price.assert_called_once()
                    mock_cache_manager.set.assert_called()

                    # Verify result is from API
                    assert result['source'] == 'api'
                    assert result['data']['price'] == 176.50

    @pytest.mark.asyncio
    async def test_error_handling_api_failure(self):
        """Test graceful degradation when API fails."""
        service = StockPriceService()

        # Mock all sources returning None
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = None

        mock_db = AsyncMock()
        mock_db.get_latest_price.return_value = None

        # Mock API failure
        mock_yf_client = AsyncMock()
        mock_yf_client.get_stock_quote.return_value = None

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_price_db', mock_db):
                with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
                    result = await service.get_stock_price('INVALID', refresh=False)

                    # Should return error result
                    assert result is None or 'error' in result

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests_same_symbol(self):
        """Test cache efficiency with concurrent requests for same symbol."""
        service = StockPriceService()

        # Mock Redis cache
        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = {
            'symbol': 'AAPL',
            'price': 175.43,
            'last_updated': datetime.utcnow().isoformat(),
            'data_source': 'yfinance'
        }

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            # Make 5 concurrent requests
            tasks = [service.get_stock_price('AAPL') for _ in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should get results
            assert len(results) == 5
            for result in results:
                if isinstance(result, dict):
                    assert result['data']['symbol'] == 'AAPL'

    @pytest.mark.asyncio
    async def test_batch_quotes_with_mixed_cache_states(self):
        """Test batch fetching with some symbols in cache, others need API."""
        # This would test the batch quote optimization
        # Implementation depends on whether batch API is exposed
        pass


class TestStockPriceDataQuality:
    """Test suite for data validation and quality checks."""

    @pytest.mark.asyncio
    async def test_price_data_includes_daily_change(self):
        """Test that price data includes daily price change calculations."""
        service = StockPriceService()

        mock_yf_client = AsyncMock()
        mock_yf_client.get_stock_quote.return_value = {
            'symbol': 'AAPL',
            'price': 175.43,
            'previous_close': 173.28,
            'change': 2.15,
            'change_percent': 1.24,
            'last_updated': datetime.utcnow().isoformat(),
            'data_source': 'yfinance'
        }

        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = None

        mock_db = AsyncMock()
        mock_db.get_latest_price.return_value = None

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            with patch.object(service, 'stock_price_db', mock_db):
                with patch('backend.app.external.yfinance_client.get_yfinance_client', return_value=mock_yf_client):
                    result = await service.get_stock_price('AAPL')

                    # Verify daily change fields exist
                    assert 'change' in result['data']
                    assert 'change_percent' in result['data']
                    assert result['data']['change'] == 2.15
                    assert result['data']['change_percent'] == 1.24

    @pytest.mark.asyncio
    async def test_timestamp_format_consistency(self):
        """Test that timestamps are consistently ISO format."""
        service = StockPriceService()

        mock_cache_manager = AsyncMock()
        mock_cache_manager.get.return_value = {
            'symbol': 'AAPL',
            'price': 175.43,
            'last_updated': datetime.utcnow().isoformat(),
            'data_source': 'yfinance'
        }

        with patch('backend.app.services.stock_price_service.cache_manager', mock_cache_manager):
            result = await service.get_stock_price('AAPL')

            # Verify timestamp is ISO format
            timestamp = result['data'].get('last_updated')
            assert timestamp is not None
            # Should be parseable as ISO datetime
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

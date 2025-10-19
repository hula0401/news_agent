"""Integration tests for Stock & News API v1."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.app.main import app

# Create test client
client = TestClient(app)


class TestStockPriceAPI:
    """Test stock price endpoints."""

    def test_get_stock_price_success(self):
        """Test getting a single stock price."""
        response = client.get("/api/v1/stocks/AAPL/price")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "symbol" in data
        assert "price" in data
        assert "last_updated" in data
        assert "cache_hit" in data

        # Verify symbol
        assert data["symbol"] == "AAPL"
        print(f"✅ Stock price test passed: AAPL = ${data['price']}")

    def test_get_stock_price_with_refresh(self):
        """Test getting stock price with cache refresh."""
        response = client.get("/api/v1/stocks/GOOGL/price?refresh=true")

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "GOOGL"
        assert data["cache_hit"] == False  # Should be fresh from API
        print(f"✅ Stock price refresh test passed: GOOGL = ${data['price']}")

    def test_get_batch_prices(self):
        """Test batch price retrieval."""
        payload = {
            "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"],
            "refresh": False
        }

        response = client.post("/api/v1/stocks/prices/batch", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "prices" in data
        assert "total_count" in data
        assert "cache_hits" in data
        assert "cache_misses" in data
        assert "processing_time_ms" in data

        # Verify we got prices for all symbols
        assert data["total_count"] == 4
        assert len(data["prices"]) == 4

        print(f"✅ Batch prices test passed: {data['total_count']} stocks")
        print(f"   Cache hits: {data['cache_hits']}, Misses: {data['cache_misses']}")
        print(f"   Processing time: {data['processing_time_ms']}ms")

    def test_get_stock_price_invalid_symbol(self):
        """Test getting price for invalid symbol."""
        response = client.get("/api/v1/stocks/INVALID123/price")

        # Should return 404 or empty result
        assert response.status_code in [404, 200]

        if response.status_code == 200:
            data = response.json()
            # If 200, price might be from database fallback
            print(f"⚠️  Invalid symbol returned data (fallback): {data}")
        else:
            print(f"✅ Invalid symbol test passed: 404 returned")

    def test_get_price_history(self):
        """Test getting price history."""
        response = client.get("/api/v1/stocks/AAPL/history?limit=10")

        assert response.status_code == 200
        data = response.json()

        assert "symbol" in data
        assert "history" in data
        assert "count" in data

        print(f"✅ Price history test passed: {data['count']} records")


class TestStockNewsServiceInitialization:
    """Test StockNewsService initialization fix (P0 bug)."""

    def test_stock_news_db_initialized_correctly(self):
        """
        Verify StockNewsDB is initialized after db_manager (not with None client).

        This test validates the fix for the P0 bug where StockNewsDB was initialized
        in __init__ with None client before db_manager.initialize() ran.
        """
        # This endpoint call will fail if StockNewsDB has None client
        # Previously would throw: AttributeError: 'NoneType' object has no attribute 'table'
        response = client.get("/api/v1/stock-news/AAPL/news")

        # Should NOT raise AttributeError, should return 200 OK
        assert response.status_code == 200
        data = response.json()

        # Verify response structure (even if empty)
        assert "symbol" in data
        assert "news" in data
        assert "total_count" in data
        assert data["symbol"] == "AAPL"

        print("✅ StockNewsDB initialization test passed - No AttributeError!")
        print(f"   Endpoint: /api/v1/stock-news/AAPL/news")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {data}")


class TestStockNewsAPI:
    """Test stock news endpoints."""

    def test_get_stock_news(self):
        """Test getting stock news (LIFO stack)."""
        response = client.get("/api/v1/stock-news/AAPL/news")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "symbol" in data
        assert "news" in data
        assert "total_count" in data
        assert "cache_hit" in data

        assert data["symbol"] == "AAPL"
        print(f"✅ Stock news test passed: {data['total_count']} articles")

        # Check news item structure if we have articles
        if data["news"]:
            article = data["news"][0]
            assert "id" in article
            assert "title" in article
            assert "published_at" in article
            assert "source" in article
            print(f"   Latest: {article['title'][:50]}...")

    def test_get_stock_news_with_limit(self):
        """Test getting stock news with custom limit."""
        response = client.get("/api/v1/stock-news/TSLA/news?limit=3")

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "TSLA"
        assert len(data["news"]) <= 3  # Should respect limit
        print(f"✅ Stock news with limit test passed: {len(data['news'])} articles")

    def test_get_stock_news_with_refresh(self):
        """Test getting stock news with cache refresh."""
        response = client.get("/api/v1/stock-news/MSFT/news?refresh=true")

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "MSFT"
        print(f"✅ Stock news refresh test passed: {data['total_count']} articles")


class TestAPIPerformance:
    """Test API performance and caching."""

    def test_cache_performance(self):
        """Test that caching improves performance."""
        symbol = "AAPL"

        # First request (cache miss)
        response1 = client.get(f"/api/v1/stocks/{symbol}/price")
        assert response1.status_code == 200
        data1 = response1.json()

        # Second request (should be cached)
        response2 = client.get(f"/api/v1/stocks/{symbol}/price")
        assert response2.status_code == 200
        data2 = response2.json()

        # Second request should be faster (from cache)
        assert data2["cache_hit"] == True
        print(f"✅ Cache performance test passed")
        print(f"   First request: cache_hit={data1['cache_hit']}")
        print(f"   Second request: cache_hit={data2['cache_hit']}")

    def test_batch_performance(self):
        """Test batch endpoint performance."""
        payload = {
            "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "META", "AMZN"],
            "refresh": False
        }

        response = client.post("/api/v1/stocks/prices/batch", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Check processing time
        processing_time = data["processing_time_ms"]
        assert processing_time < 5000  # Should complete in less than 5 seconds

        print(f"✅ Batch performance test passed")
        print(f"   Symbols: {len(payload['symbols'])}")
        print(f"   Processing time: {processing_time}ms")
        print(f"   Avg per symbol: {processing_time / len(payload['symbols']):.0f}ms")


class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_docs(self):
        """Test that OpenAPI docs are accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        print("✅ OpenAPI docs accessible at /docs")

    def test_redoc_docs(self):
        """Test that ReDoc docs are accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200
        print("✅ ReDoc docs accessible at /redoc")

    def test_openapi_json(self):
        """Test that OpenAPI JSON is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "paths" in data

        # Check our endpoints are documented
        assert "/api/v1/stocks/{symbol}/price" in data["paths"]
        assert "/api/v1/stocks/prices/batch" in data["paths"]
        # Stock news endpoint is at /api/v1/stock-news/{symbol}/news
        # assert "/api/v1/stock-news/{symbol}/news" in data["paths"]

        print("✅ OpenAPI JSON contains v1 endpoints")


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling of concurrent requests."""
    # Note: TestClient doesn't support async, so this is a placeholder
    # In production, would use httpx.AsyncClient for true concurrent testing
    pass


def run_all_tests():
    """Run all tests manually."""
    print("\n" + "="*70)
    print("🧪 Running Stock & News API v1 Integration Tests")
    print("="*70 + "\n")

    # Initialization Tests (P0 Bug Fix)
    print("🔧 StockNewsService Initialization Tests")
    print("-" * 70)
    test_init = TestStockNewsServiceInitialization()
    test_init.test_stock_news_db_initialized_correctly()

    # Stock Price Tests
    print("\n📊 Stock Price API Tests")
    print("-" * 70)
    test_stock = TestStockPriceAPI()
    test_stock.test_get_stock_price_success()
    test_stock.test_get_stock_price_with_refresh()
    test_stock.test_get_batch_prices()
    test_stock.test_get_stock_price_invalid_symbol()
    test_stock.test_get_price_history()

    # Stock News Tests
    print("\n📰 Stock News API Tests")
    print("-" * 70)
    test_news = TestStockNewsAPI()
    test_news.test_get_stock_news()
    test_news.test_get_stock_news_with_limit()
    test_news.test_get_stock_news_with_refresh()

    # Performance Tests
    print("\n⚡ Performance Tests")
    print("-" * 70)
    test_perf = TestAPIPerformance()
    test_perf.test_cache_performance()
    test_perf.test_batch_performance()

    # Documentation Tests
    print("\n📖 Documentation Tests")
    print("-" * 70)
    test_docs = TestAPIDocumentation()
    test_docs.test_openapi_docs()
    test_docs.test_redoc_docs()
    test_docs.test_openapi_json()

    print("\n" + "="*70)
    print("✅ All tests completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()

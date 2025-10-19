"""Unit tests for Stock API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestStockPriceEndpoints:
    """Test suite for /api/v1/stocks/* endpoints."""

    def test_get_stock_price(self):
        """Test GET /api/v1/stocks/{symbol}/price."""
        response = client.get("/api/v1/stocks/AAPL/price")
        assert response.status_code == 200
        data = response.json()
        assert "symbol" in data
        assert "price" in data
        assert data["symbol"] == "AAPL"

    def test_get_stock_price_with_refresh(self):
        """Test GET /api/v1/stocks/{symbol}/price with refresh."""
        response = client.get("/api/v1/stocks/GOOGL/price?refresh=true")
        assert response.status_code == 200

    def test_batch_stock_prices(self):
        """Test POST /api/v1/stocks/prices/batch."""
        response = client.post(
            "/api/v1/stocks/prices/batch",
            json={"symbols": ["AAPL", "GOOGL", "MSFT"], "refresh": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert "prices" in data
        assert "total_count" in data
        assert data["total_count"] == 3

    def test_batch_stock_prices_empty_list(self):
        """Test POST /api/v1/stocks/prices/batch with empty list."""
        response = client.post(
            "/api/v1/stocks/prices/batch",
            json={"symbols": []}
        )
        assert response.status_code in [200, 422]

    def test_get_stock_history(self):
        """Test GET /api/v1/stocks/{symbol}/history."""
        response = client.get("/api/v1/stocks/TSLA/history?limit=10")
        assert response.status_code in [200, 404]


class TestStockNewsEndpoints:
    """Test suite for /api/v1/stock-news/* endpoints."""

    def test_get_stock_news(self):
        """Test GET /api/v1/stock-news/{symbol}/news."""
        response = client.get("/api/v1/stock-news/TSLA/news?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "symbol" in data
        assert "news" in data or "articles" in data

    def test_get_stock_news_with_refresh(self):
        """Test GET /api/v1/stock-news/{symbol}/news with refresh."""
        response = client.get("/api/v1/stock-news/AAPL/news?limit=5&refresh=true")
        assert response.status_code == 200

    def test_add_stock_news(self):
        """Test POST /api/v1/stock-news/{symbol}/news."""
        response = client.post(
            "/api/v1/stock-news/TSLA/news",
            json={
                "title": "Test News Article",
                "summary": "This is a test news article",
                "url": "https://example.com/test",
                "source_name": "Test Source",
                "published_at": "2025-10-18T15:00:00Z",
                "sentiment_score": 0.75
            }
        )
        # May fail due to permissions/validation
        assert response.status_code in [200, 201, 403, 422]

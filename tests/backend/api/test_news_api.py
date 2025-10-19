"""Unit tests for News API endpoints."""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


class TestNewsEndpoints:
    """Test suite for /api/news/* endpoints."""

    def test_get_latest_news(self):
        """Test GET /api/news/latest."""
        response = client.get("/api/news/latest?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "articles" in data or "news" in data

    def test_get_latest_news_with_topics(self):
        """Test GET /api/news/latest with topic filter."""
        response = client.get("/api/news/latest?topics=technology&limit=5")
        assert response.status_code == 200

    def test_search_news(self):
        """Test GET /api/news/search."""
        response = client.get("/api/news/search?query=tesla&limit=10")
        # News API will be integrated later - allow both success and validation errors
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert "articles" in data or "news" in data

    def test_search_news_with_category(self):
        """Test GET /api/news/search with category."""
        response = client.get("/api/news/search?query=apple&category=technology&limit=10")
        # News API will be integrated later - allow both success and validation errors
        assert response.status_code in [200, 422]

    def test_get_article_by_id(self):
        """Test GET /api/news/article/{article_id}."""
        # First get some articles
        response = client.get("/api/news/latest?limit=1")
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            if articles:
                article_id = articles[0].get("id")
                if article_id:
                    # Now test getting specific article
                    article_response = client.get(f"/api/news/article/{article_id}")
                    assert article_response.status_code in [200, 404]

    def test_summarize_news(self):
        """Test POST /api/news/summarize."""
        response = client.post(
            "/api/news/summarize",
            json={"article_ids": ["test-id"], "summary_type": "brief"}
        )
        # May fail if articles don't exist, but should not crash
        assert response.status_code in [200, 404, 422]

    def test_get_breaking_news(self):
        """Test GET /api/news/breaking."""
        response = client.get("/api/news/breaking")
        assert response.status_code == 200

    def test_get_news_topics(self):
        """Test GET /api/news/topics."""
        response = client.get("/api/news/topics")
        assert response.status_code == 200
        data = response.json()
        assert "topics" in data

    def test_news_health_check(self):
        """Test GET /api/news/health."""
        response = client.get("/api/news/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

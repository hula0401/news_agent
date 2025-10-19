"""NewsAPI client for general business and economic news."""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..config import get_settings

settings = get_settings()


class NewsAPIClient:
    """
    NewsAPI client for general news.

    Free tier: 100 requests/day
    Documentation: https://newsapi.org/docs
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.newsapi_api_key
        self.base_url = "https://newsapi.org/v2"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_top_headlines(
        self,
        country: str = "us",
        category: str = "business",
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get top headlines.

        Args:
            country: Country code (us, gb, etc.)
            category: Category (business, technology, etc.)
            page_size: Number of results

        Returns:
            List of news articles
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/top-headlines",
                params={
                    "country": country,
                    "category": category,
                    "pageSize": page_size,
                    "apiKey": self.api_key
                }
            )

            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])

                return [
                    {
                        "external_id": article.get("url", ""),  # Use URL as ID
                        "title": article.get("title", ""),
                        "summary": article.get("description", ""),
                        "content": article.get("content", ""),
                        "url": article.get("url", ""),
                        "published_at": datetime.fromisoformat(
                            article.get("publishedAt", "").replace("Z", "+00:00")
                        ) if article.get("publishedAt") else datetime.now(),
                        "author": article.get("author", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "image": article.get("urlToImage", ""),
                        "category": category,
                        "country": country,
                        "source_api": "newsapi"
                    }
                    for article in articles
                ]

            return []

        except Exception as e:
            print(f"❌ NewsAPI top headlines error: {e}")
            return []

    async def search_everything(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search all articles.

        Args:
            query: Search query
            from_date: Start date
            to_date: End date
            language: Language code
            sort_by: Sort order (publishedAt, relevancy, popularity)
            page_size: Number of results

        Returns:
            List of news articles
        """
        try:
            # Default to last 7 days if not specified
            if not to_date:
                to_date = datetime.now()
            if not from_date:
                from_date = to_date - timedelta(days=7)

            params = {
                "q": query,
                "from": from_date.strftime("%Y-%m-%d"),
                "to": to_date.strftime("%Y-%m-%d"),
                "language": language,
                "sortBy": sort_by,
                "pageSize": page_size,
                "apiKey": self.api_key
            }

            response = await self.client.get(
                f"{self.base_url}/everything",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                articles = data.get("articles", [])

                return [
                    {
                        "external_id": article.get("url", ""),
                        "title": article.get("title", ""),
                        "summary": article.get("description", ""),
                        "content": article.get("content", ""),
                        "url": article.get("url", ""),
                        "published_at": datetime.fromisoformat(
                            article.get("publishedAt", "").replace("Z", "+00:00")
                        ) if article.get("publishedAt") else datetime.now(),
                        "author": article.get("author", ""),
                        "source": article.get("source", {}).get("name", ""),
                        "image": article.get("urlToImage", ""),
                        "query": query,
                        "source_api": "newsapi"
                    }
                    for article in articles
                ]

            return []

        except Exception as e:
            print(f"❌ NewsAPI search error for '{query}': {e}")
            return []

    async def get_sources(
        self,
        category: Optional[str] = None,
        language: str = "en",
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available news sources.

        Args:
            category: Category filter
            language: Language filter
            country: Country filter

        Returns:
            List of news sources
        """
        try:
            params = {"language": language, "apiKey": self.api_key}

            if category:
                params["category"] = category
            if country:
                params["country"] = country

            response = await self.client.get(
                f"{self.base_url}/sources",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                sources = data.get("sources", [])

                return [
                    {
                        "id": source.get("id", ""),
                        "name": source.get("name", ""),
                        "description": source.get("description", ""),
                        "url": source.get("url", ""),
                        "category": source.get("category", ""),
                        "language": source.get("language", ""),
                        "country": source.get("country", "")
                    }
                    for source in sources
                ]

            return []

        except Exception as e:
            print(f"❌ NewsAPI sources error: {e}")
            return []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global instance
_newsapi_client: Optional[NewsAPIClient] = None


def get_newsapi_client() -> NewsAPIClient:
    """Get or create NewsAPI client instance."""
    global _newsapi_client
    if _newsapi_client is None:
        _newsapi_client = NewsAPIClient()
    return _newsapi_client

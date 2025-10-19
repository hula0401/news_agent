"""Polygon.io API client for stock data and news."""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..config import get_settings

settings = get_settings()


class PolygonClient:
    """
    Polygon.io API client.

    Free tier: 5 API calls/minute
    Documentation: https://polygon.io/docs/stocks/getting-started
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.polygon_api_key
        self.base_url = "https://api.polygon.io"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_last_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the last quote for a stock.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Quote data with price information
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/v2/last/trade/{symbol.upper()}",
                params={"apiKey": self.api_key}
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", {})

                return {
                    "symbol": symbol.upper(),
                    "price": results.get("p"),  # Price
                    "size": results.get("s"),   # Size
                    "timestamp": datetime.fromtimestamp(results.get("t", 0) / 1000),  # Milliseconds
                    "source": "polygon"
                }

            return None

        except Exception as e:
            print(f"❌ Polygon quote error for {symbol}: {e}")
            return None

    async def get_previous_close(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get previous day's close for a stock.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Previous close data
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/v2/aggs/ticker/{symbol.upper()}/prev",
                params={"adjusted": "true", "apiKey": self.api_key}
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if results:
                    result = results[0]
                    return {
                        "symbol": symbol.upper(),
                        "close": result.get("c"),
                        "high": result.get("h"),
                        "low": result.get("l"),
                        "open": result.get("o"),
                        "volume": result.get("v"),
                        "timestamp": datetime.fromtimestamp(result.get("t", 0) / 1000),
                        "source": "polygon"
                    }

            return None

        except Exception as e:
            print(f"❌ Polygon previous close error for {symbol}: {e}")
            return None

    async def get_ticker_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get news for a specific ticker or general market news.

        Args:
            symbol: Stock ticker symbol (optional)
            limit: Maximum number of articles

        Returns:
            List of news articles
        """
        try:
            params = {"limit": limit, "apiKey": self.api_key}

            if symbol:
                params["ticker"] = symbol.upper()

            response = await self.client.get(
                f"{self.base_url}/v2/reference/news",
                params=params
            )

            if response.status_code == 200:
                data = response.json()
                articles = data.get("results", [])

                return [
                    {
                        "id": article.get("id", ""),
                        "external_id": article.get("id", ""),
                        "title": article.get("title", ""),
                        "summary": article.get("description", ""),
                        "url": article.get("article_url", ""),
                        "published_at": datetime.fromisoformat(
                            article.get("published_utc", "").replace("Z", "+00:00")
                        ) if article.get("published_utc") else datetime.now(),
                        "author": article.get("author", ""),
                        "publisher": article.get("publisher", {}).get("name", ""),
                        "image": article.get("image_url", ""),
                        "keywords": article.get("keywords", []),
                        "related_symbols": article.get("tickers", []),
                        "source_api": "polygon"
                    }
                    for article in articles
                ]

            return []

        except Exception as e:
            print(f"❌ Polygon news error: {e}")
            return []

    async def get_ticker_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get ticker details including company info.

        Args:
            symbol: Stock ticker symbol

        Returns:
            Ticker details
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/v3/reference/tickers/{symbol.upper()}",
                params={"apiKey": self.api_key}
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", {})

                return {
                    "symbol": symbol.upper(),
                    "name": results.get("name", ""),
                    "market": results.get("market", ""),
                    "locale": results.get("locale", ""),
                    "primary_exchange": results.get("primary_exchange", ""),
                    "type": results.get("type", ""),
                    "active": results.get("active", False),
                    "currency_name": results.get("currency_name", ""),
                    "market_cap": results.get("market_cap"),
                    "phone_number": results.get("phone_number", ""),
                    "description": results.get("description", ""),
                    "homepage_url": results.get("homepage_url", ""),
                    "total_employees": results.get("total_employees"),
                    "list_date": results.get("list_date", ""),
                    "branding": results.get("branding", {}),
                    "source": "polygon"
                }

            return None

        except Exception as e:
            print(f"❌ Polygon ticker details error for {symbol}: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global instance
_polygon_client: Optional[PolygonClient] = None


def get_polygon_client() -> PolygonClient:
    """Get or create Polygon client instance."""
    global _polygon_client
    if _polygon_client is None:
        _polygon_client = PolygonClient()
    return _polygon_client

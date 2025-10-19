"""Finnhub API client for stock prices and news."""
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..config import get_settings

settings = get_settings()


class FinnhubClient:
    """
    Finnhub API client.

    Free tier: 60 API calls/minute
    Documentation: https://finnhub.io/docs/api
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.finnhub_api_key
        self.base_url = "https://finnhub.io/api/v1"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time stock quote.

        Args:
            symbol: Stock ticker symbol (e.g., AAPL)

        Returns:
            Quote data with current price, change, etc.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/quote",
                params={"symbol": symbol.upper(), "token": self.api_key}
            )

            if response.status_code == 200:
                data = response.json()
                # Finnhub returns: c (current), d (change), dp (percent change), h (high), l (low), etc.
                return {
                    "symbol": symbol.upper(),
                    "price": data.get("c"),
                    "change": data.get("d"),
                    "change_percent": data.get("dp"),
                    "high": data.get("h"),
                    "low": data.get("l"),
                    "open": data.get("o"),
                    "previous_close": data.get("pc"),
                    "timestamp": datetime.fromtimestamp(data.get("t", 0)),
                    "source": "finnhub"
                }

            return None

        except Exception as e:
            print(f"❌ Finnhub quote error for {symbol}: {e}")
            return None

    async def get_company_news(
        self,
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get company news for a specific symbol.

        Args:
            symbol: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of news articles
        """
        try:
            # Default to last 7 days if not specified
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            if not from_date:
                from_datetime = datetime.now()
                from_datetime = from_datetime.replace(day=from_datetime.day - 7)
                from_date = from_datetime.strftime("%Y-%m-%d")

            response = await self.client.get(
                f"{self.base_url}/company-news",
                params={
                    "symbol": symbol.upper(),
                    "from": from_date,
                    "to": to_date,
                    "token": self.api_key
                }
            )

            if response.status_code == 200:
                articles = response.json()
                return [
                    {
                        "id": str(article.get("id", "")),
                        "external_id": str(article.get("id", "")),
                        "title": article.get("headline", ""),
                        "summary": article.get("summary", ""),
                        "url": article.get("url", ""),
                        "published_at": datetime.fromtimestamp(article.get("datetime", 0)),
                        "source": article.get("source", ""),
                        "category": article.get("category", ""),
                        "image": article.get("image", ""),
                        "related_symbols": [symbol.upper()],
                        "source_api": "finnhub"
                    }
                    for article in articles[:20]  # Limit to 20
                ]

            return []

        except Exception as e:
            print(f"❌ Finnhub news error for {symbol}: {e}")
            return []

    async def get_market_news(
        self,
        category: str = "general",
        min_id: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get general market news.

        Args:
            category: News category (general, forex, crypto, merger)
            min_id: Minimum news ID to fetch

        Returns:
            List of market news articles
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/news",
                params={
                    "category": category,
                    "minId": min_id,
                    "token": self.api_key
                }
            )

            if response.status_code == 200:
                articles = response.json()
                return [
                    {
                        "id": str(article.get("id", "")),
                        "external_id": str(article.get("id", "")),
                        "title": article.get("headline", ""),
                        "summary": article.get("summary", ""),
                        "url": article.get("url", ""),
                        "published_at": datetime.fromtimestamp(article.get("datetime", 0)),
                        "source": article.get("source", ""),
                        "category": category,
                        "image": article.get("image", ""),
                        "source_api": "finnhub"
                    }
                    for article in articles[:20]
                ]

            return []

        except Exception as e:
            print(f"❌ Finnhub market news error: {e}")
            return []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global instance
_finnhub_client: Optional[FinnhubClient] = None


def get_finnhub_client() -> FinnhubClient:
    """Get or create Finnhub client instance."""
    global _finnhub_client
    if _finnhub_client is None:
        _finnhub_client = FinnhubClient()
    return _finnhub_client

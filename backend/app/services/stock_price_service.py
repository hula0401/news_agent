"""Stock price service with LFU caching and multi-source fetching."""
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
from ..db.stock_prices import StockPriceDB
from ..lfu_cache.lfu_manager import LFUCacheManager
from ..cache import cache_manager
from ..external.finnhub_client import get_finnhub_client
from ..external.polygon_client import get_polygon_client
from ..database import db_manager


class StockPriceService:
    """
    Stock price service with intelligent caching.

    Features:
    - LFU cache with 60s TTL (market hours) / 300s (after hours)
    - Multi-source fallback (Finnhub → Polygon → AlphaVantage)
    - Database persistence for historical tracking
    """

    def __init__(self):
        self.stock_price_db: Optional[StockPriceDB] = None
        self.lfu_cache: Optional[LFUCacheManager] = None
        self.finnhub = get_finnhub_client()
        self.polygon = get_polygon_client()

    async def initialize(self):
        """Initialize service dependencies."""
        if not db_manager._initialized:
            await db_manager.initialize()

        if not cache_manager._initialized:
            await cache_manager.initialize()

        # Initialize stock price DB with initialized client
        self.stock_price_db = StockPriceDB(db_manager.client)

        # Import LFU cache manager
        from ..lfu_cache.lfu_manager import get_lfu_cache
        self.lfu_cache = await get_lfu_cache()

    async def get_stock_price(
        self,
        symbol: str,
        refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get stock price with smart fallback: Redis → Database → API.

        Priority:
        1. Redis cache (if data is fresh, < 2 minutes)
        2. Database (recent data within acceptable staleness)
        3. External API (yfinance, finnhub, polygon)

        Args:
            symbol: Stock ticker symbol
            refresh: Force cache refresh (skip Redis/DB, go straight to API)

        Returns:
            Stock price data with cache metadata
        """
        if not self.lfu_cache:
            await self.initialize()

        cache_key = f"stock:price:{symbol.upper()}"
        start_time = time.time()

        # Step 1: Try Redis cache first (unless refresh requested)
        if not refresh:
            cached_data = await cache_manager.get(cache_key)
            if cached_data:
                # Check if data is fresh (< 2 minutes old)
                last_updated = cached_data.get("last_updated")
                if last_updated:
                    if isinstance(last_updated, str):
                        last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))

                    # Ensure timezone-aware
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)

                    age_minutes = (datetime.now(timezone.utc) - last_updated).total_seconds() / 60

                    if age_minutes < 2:  # Fresh data
                        # Track LFU access
                        await self.lfu_cache.track_access(cache_key, "stock_price")

                        return {
                            **cached_data,
                            "source": "redis",
                            "cache_hit": True,
                            "age_minutes": round(age_minutes, 2),
                            "response_time_ms": int((time.time() - start_time) * 1000)
                        }

        # Step 2: Try Database (check for recent data)
        if not refresh:
            db_price = await self.stock_price_db.get_latest_price(symbol)
            if db_price:
                last_updated = db_price.get("last_updated")
                if isinstance(last_updated, str):
                    last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))

                # Ensure timezone-aware
                if last_updated.tzinfo is None:
                    last_updated = last_updated.replace(tzinfo=timezone.utc)

                age_minutes = (datetime.now(timezone.utc) - last_updated).total_seconds() / 60

                # Use DB data if it's reasonably fresh (< 5 minutes)
                if age_minutes < 5:
                    # Store in Redis for next time (2-minute TTL)
                    await cache_manager.set(cache_key, db_price, ttl=120)

                    # Track LFU access
                    await self.lfu_cache.track_access(cache_key, "stock_price")

                    return {
                        **db_price,
                        "source": "database",
                        "cache_hit": False,
                        "age_minutes": round(age_minutes, 2),
                        "response_time_ms": int((time.time() - start_time) * 1000)
                    }

        # Step 3: Fetch from external APIs (last resort or if refresh requested)
        price_data = await self._fetch_from_external_apis(symbol)

        if price_data:
            # Store in database for history
            await self.stock_price_db.insert_price({
                "symbol": symbol.upper(),
                "price": price_data.get("price"),
                "change": price_data.get("change"),
                "change_percent": price_data.get("change_percent"),
                "volume": price_data.get("volume"),
                "market_cap": price_data.get("market_cap"),
                "high_52_week": price_data.get("high_52_week"),
                "low_52_week": price_data.get("low_52_week"),
                "last_updated": datetime.now(timezone.utc).isoformat(),  # Use UTC timestamp
                "data_source": price_data.get("data_source", "external")
            })

            # Store in Redis cache (2-minute TTL)
            await cache_manager.set(cache_key, price_data, ttl=120)

            # Track LFU access
            await self.lfu_cache.track_access(cache_key, "stock_price")

            return {
                **price_data,
                "source": "api",
                "cache_hit": False,
                "age_minutes": 0,
                "response_time_ms": int((time.time() - start_time) * 1000)
            }

        # Last fallback: Use stale DB data if available
        db_price = await self.stock_price_db.get_latest_price(symbol)
        if db_price:
            last_updated = db_price.get("last_updated")
            if isinstance(last_updated, str):
                last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))

            # Ensure timezone-aware
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)

            age_minutes = (datetime.now(timezone.utc) - last_updated).total_seconds() / 60

            return {
                **db_price,
                "source": "database_stale",
                "cache_hit": False,
                "stale": True,
                "age_minutes": round(age_minutes, 2),
                "response_time_ms": int((time.time() - start_time) * 1000)
            }

        return None

    async def get_multiple_prices(
        self,
        symbols: List[str],
        refresh: bool = False
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get prices for multiple symbols (batch operation).

        Args:
            symbols: List of stock ticker symbols
            refresh: Force cache refresh

        Returns:
            Dictionary mapping symbol to price data
        """
        results = {}

        # Fetch prices concurrently (simplified - could use asyncio.gather)
        for symbol in symbols:
            price_data = await self.get_stock_price(symbol, refresh)
            results[symbol.upper()] = price_data

        return results

    async def _fetch_from_external_apis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch price from external APIs with fallback.

        Priority: YFinance → Finnhub → Polygon

        YFinance is prioritized because it provides:
        - Daily price changes based on yesterday's close
        - More complete data (52-week high/low, PE ratio, etc.)
        - Free and reliable

        Args:
            symbol: Stock ticker symbol

        Returns:
            Price data or None
        """
        # Try YFinance first (best for daily changes and complete data)
        try:
            from ..external.yfinance_client import get_yfinance_client
            yf_client = await get_yfinance_client()
            yf_data = await yf_client.get_stock_quote(symbol)

            if yf_data and yf_data.get("price"):
                return yf_data  # Already formatted correctly
        except Exception as e:
            print(f"❌ YFinance fetch failed for {symbol}: {e}")

        # Try Finnhub as fallback
        try:
            finnhub_data = await self.finnhub.get_quote(symbol)
            if finnhub_data and finnhub_data.get("price"):
                return {
                    "symbol": symbol.upper(),
                    "price": finnhub_data.get("price"),
                    "change": finnhub_data.get("change"),
                    "change_percent": finnhub_data.get("change_percent"),
                    "high": finnhub_data.get("high"),
                    "low": finnhub_data.get("low"),
                    "open": finnhub_data.get("open"),
                    "previous_close": finnhub_data.get("previous_close"),
                    "volume": None,  # Finnhub doesn't provide volume in quote
                    "data_source": "finnhub",
                    "last_updated": datetime.now(timezone.utc)
                }
        except Exception as e:
            print(f"❌ Finnhub fetch failed for {symbol}: {e}")

        # Try Polygon as last resort
        try:
            polygon_quote = await self.polygon.get_last_quote(symbol)
            polygon_prev = await self.polygon.get_previous_close(symbol)

            if polygon_quote and polygon_prev:
                current_price = polygon_quote.get("price")
                prev_close = polygon_prev.get("close")

                change = current_price - prev_close if current_price and prev_close else None
                change_percent = (change / prev_close * 100) if change and prev_close else None

                return {
                    "symbol": symbol.upper(),
                    "price": current_price,
                    "change": change,
                    "change_percent": change_percent,
                    "high": polygon_prev.get("high"),
                    "low": polygon_prev.get("low"),
                    "open": polygon_prev.get("open"),
                    "previous_close": prev_close,
                    "volume": polygon_prev.get("volume"),
                    "data_source": "polygon",
                    "last_updated": datetime.now(timezone.utc)
                }
        except Exception as e:
            print(f"❌ Polygon fetch failed for {symbol}: {e}")

        return None

    def _is_market_hours(self) -> bool:
        """
        Check if market is currently open.

        Simplified: Monday-Friday, 9:30 AM - 4:00 PM ET

        Returns:
            True if market is open
        """
        now = datetime.now(timezone.utc)

        # Check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Check market hours (simplified - doesn't account for holidays)
        # In production, would use a proper market calendar
        hour = now.hour
        return 9 <= hour < 16  # Rough approximation for ET

    async def get_price_history(
        self,
        symbol: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a symbol.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of records

        Returns:
            List of historical prices
        """
        return await self.stock_price_db.get_price_history(symbol, limit)


# Global instance
_stock_price_service: Optional[StockPriceService] = None


async def get_stock_price_service() -> StockPriceService:
    """Get or create stock price service instance."""
    global _stock_price_service
    if _stock_price_service is None:
        _stock_price_service = StockPriceService()
        await _stock_price_service.initialize()
    return _stock_price_service

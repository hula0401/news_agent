"""
Tool adapters for market data APIs.

Provides async wrappers for Alpha Vantage and Polygon.io APIs
with standardized output format and error handling.
"""

import os
import asyncio
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Optional yfinance import
try:
    import yfinance as yf
except ImportError:
    yf = None
    logger.warning("yfinance not installed. Install with: uv pip install yfinance")


# ====== CACHE LAYER ======
_cache: Dict[str, tuple] = {}  # {cache_key: (data, timestamp)}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cache_key(api: str, endpoint: str, params: Dict) -> str:
    """Generate cache key from API call parameters."""
    param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{api}:{endpoint}:{param_str}"


def _get_cached(cache_key: str) -> Optional[Dict]:
    """Retrieve cached data if still valid."""
    if cache_key in _cache:
        data, timestamp = _cache[cache_key]
        if (datetime.utcnow() - timestamp).total_seconds() < CACHE_TTL_SECONDS:
            logger.info(f"Cache hit: {cache_key}")
            return data
        else:
            del _cache[cache_key]  # Expired
    return None


def _set_cache(cache_key: str, data: Dict):
    """Store data in cache with timestamp."""
    _cache[cache_key] = (data, datetime.utcnow())


# ====== RATE LIMITER ======
class RateLimiter:
    """Simple rate limiter: max 5 requests per minute per API."""

    def __init__(self, max_calls: int = 5, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls: Dict[str, List[datetime]] = {}

    async def acquire(self, api_name: str):
        """Wait if rate limit exceeded."""
        now = datetime.utcnow()
        if api_name not in self.calls:
            self.calls[api_name] = []

        # Remove old timestamps outside the window
        self.calls[api_name] = [
            t for t in self.calls[api_name] if (now - t).total_seconds() < self.window_seconds
        ]

        if len(self.calls[api_name]) >= self.max_calls:
            # Calculate wait time
            oldest = self.calls[api_name][0]
            wait_time = self.window_seconds - (now - oldest).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached for {api_name}. Waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self.calls[api_name].append(datetime.utcnow())


rate_limiter = RateLimiter()


# ====== ALPHA VANTAGE ADAPTER ======
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "demo")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


async def fetch_alphavantage_quote(symbol: str, use_cache: bool = True) -> Dict:
    """
    Fetch current quote for a symbol from Alpha Vantage.

    Returns:
        {
            "symbol": "TSLA",
            "price": 250.5,
            "change_percent": 2.3,
            "volume": 1000000,
            "timestamp": "2025-01-23T10:30:00Z",
            "source": "alphavantage",
            "interval": "realtime",
            "metadata": {"open": 245.0, "high": 252.0, "low": 244.0, "prev_close": 245.0}
        }
    """
    cache_key = _get_cache_key("alphavantage", "quote", {"symbol": symbol})

    # Check cache
    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    # Rate limit
    await rate_limiter.acquire("alphavantage")

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10) as response:
                data = await response.json()

                if "Global Quote" not in data:
                    logger.error(f"Alpha Vantage error for {symbol}: {data}")
                    return {}

                quote = data["Global Quote"]
                result = {
                    "symbol": quote.get("01. symbol", symbol),
                    "price": float(quote.get("05. price", 0)),
                    "change_percent": float(quote.get("10. change percent", "0").rstrip("%")),
                    "volume": int(quote.get("06. volume", 0)),
                    "timestamp": quote.get("07. latest trading day", ""),
                    "source": "alphavantage",
                    "interval": "realtime",
                    "metadata": {
                        "open": float(quote.get("02. open", 0)),
                        "high": float(quote.get("03. high", 0)),
                        "low": float(quote.get("04. low", 0)),
                        "prev_close": float(quote.get("08. previous close", 0)),
                    },
                }

                # Cache result
                if use_cache:
                    _set_cache(cache_key, result)

                return result

    except Exception as e:
        logger.error(f"Alpha Vantage API error for {symbol}: {e}")
        return {}


async def fetch_alphavantage_intraday(symbol: str, interval: str = "5min", use_cache: bool = True) -> List[Dict]:
    """
    Fetch intraday time series from Alpha Vantage.

    Args:
        interval: "1min", "5min", "15min", "30min", "60min"

    Returns:
        List of price points (most recent first)
    """
    cache_key = _get_cache_key("alphavantage", "intraday", {"symbol": symbol, "interval": interval})

    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    await rate_limiter.acquire("alphavantage")

    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=10) as response:
                data = await response.json()

                time_series_key = f"Time Series ({interval})"
                if time_series_key not in data:
                    logger.error(f"Alpha Vantage intraday error for {symbol}: {data}")
                    return []

                time_series = data[time_series_key]
                results = []

                for timestamp, values in list(time_series.items())[:20]:  # Last 20 points
                    results.append({
                        "symbol": symbol,
                        "price": float(values["4. close"]),
                        "volume": int(values["5. volume"]),
                        "timestamp": timestamp,
                        "source": "alphavantage",
                        "interval": interval,
                        "metadata": {
                            "open": float(values["1. open"]),
                            "high": float(values["2. high"]),
                            "low": float(values["3. low"]),
                        },
                    })

                if use_cache:
                    _set_cache(cache_key, results)

                return results

    except Exception as e:
        logger.error(f"Alpha Vantage intraday error for {symbol}: {e}")
        return []


# ====== POLYGON.IO ADAPTER ======
POLYGON_API_KEY = os.getenv("POLYGON_IO_KEY", "")
POLYGON_BASE_URL = "https://api.polygon.io"


async def fetch_polygon_previous_close(symbol: str, use_cache: bool = True) -> Dict:
    """
    Fetch previous day's close from Polygon.io.

    Returns:
        Same format as Alpha Vantage adapter for consistency
    """
    cache_key = _get_cache_key("polygon", "prev_close", {"symbol": symbol})

    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    await rate_limiter.acquire("polygon")

    url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/prev"
    params = {"apiKey": POLYGON_API_KEY}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                data = await response.json()

                if data.get("status") != "OK" or not data.get("results"):
                    logger.error(f"Polygon error for {symbol}: {data}")
                    return {}

                result_data = data["results"][0]
                result = {
                    "symbol": symbol,
                    "price": result_data.get("c", 0),  # close
                    "change_percent": ((result_data.get("c", 0) - result_data.get("o", 0)) / result_data.get("o", 1)) * 100,
                    "volume": result_data.get("v", 0),
                    "timestamp": datetime.fromtimestamp(result_data.get("t", 0) / 1000).isoformat(),
                    "source": "polygon",
                    "interval": "daily",
                    "metadata": {
                        "open": result_data.get("o", 0),
                        "high": result_data.get("h", 0),
                        "low": result_data.get("l", 0),
                        "vwap": result_data.get("vw", 0),
                    },
                }

                if use_cache:
                    _set_cache(cache_key, result)

                return result

    except Exception as e:
        logger.error(f"Polygon API error for {symbol}: {e}")
        return {}


async def fetch_polygon_aggregates(
    symbol: str, timespan: str = "day", limit: int = 30, use_cache: bool = True
) -> List[Dict]:
    """
    Fetch aggregate bars from Polygon.io.

    Args:
        timespan: "minute", "hour", "day", "week", "month"
        limit: Number of bars to return

    Returns:
        List of aggregated data points
    """
    cache_key = _get_cache_key("polygon", "aggregates", {"symbol": symbol, "timespan": timespan, "limit": limit})

    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    await rate_limiter.acquire("polygon")

    # Date range: last 'limit' periods
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    start_date = (datetime.utcnow() - timedelta(days=limit * 2)).strftime("%Y-%m-%d")

    url = f"{POLYGON_BASE_URL}/v2/aggs/ticker/{symbol}/range/1/{timespan}/{start_date}/{end_date}"
    params = {"apiKey": POLYGON_API_KEY, "limit": limit}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                data = await response.json()

                if data.get("status") != "OK" or not data.get("results"):
                    logger.error(f"Polygon aggregates error for {symbol}: {data}")
                    return []

                results = []
                for bar in data["results"][:limit]:
                    results.append({
                        "symbol": symbol,
                        "price": bar.get("c", 0),
                        "volume": bar.get("v", 0),
                        "timestamp": datetime.fromtimestamp(bar.get("t", 0) / 1000).isoformat(),
                        "source": "polygon",
                        "interval": timespan,
                        "metadata": {
                            "open": bar.get("o", 0),
                            "high": bar.get("h", 0),
                            "low": bar.get("l", 0),
                            "vwap": bar.get("vw", 0),
                            "transactions": bar.get("n", 0),
                        },
                    })

                if use_cache:
                    _set_cache(cache_key, results)

                return results

    except Exception as e:
        logger.error(f"Polygon aggregates error for {symbol}: {e}")
        return []


# ====== YFINANCE ADAPTER ======
async def fetch_yfinance_quote(symbol: str, use_cache: bool = True) -> Dict:
    """
    Fetch current quote for a symbol using yfinance.

    Returns:
        {
            "symbol": "TSLA",
            "price": 250.5,
            "change_percent": 2.3,
            "volume": 1000000,
            "timestamp": "2025-01-23T10:30:00Z",
            "source": "yfinance",
            "interval": "1d",
            "metadata": {"open": 245.0, "high": 252.0, "low": 244.0, "prev_close": 245.0}
        }
    """
    if yf is None:
        logger.warning("yfinance not available - skipping")
        return {}

    cache_key = _get_cache_key("yfinance", "quote", {"symbol": symbol})

    # Check cache
    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    # Rate limit
    await rate_limiter.acquire("yfinance")

    try:
        # Run yfinance in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        stock = await loop.run_in_executor(None, yf.Ticker, symbol)
        hist = await loop.run_in_executor(None, lambda: stock.history(period="1d"))

        if hist.empty:
            logger.warning(f"No data returned from yfinance for {symbol}")
            return {}

        # Get latest data
        latest = hist.iloc[-1]
        latest_price = float(latest['Close'])
        prev_close = float(hist.iloc[-2]['Close']) if len(hist) > 1 else latest_price
        change_percent = ((latest_price - prev_close) / prev_close * 100) if prev_close else 0

        result = {
            "symbol": symbol,
            "price": latest_price,
            "change_percent": change_percent,
            "volume": int(latest['Volume']),
            "timestamp": latest.name.isoformat() if hasattr(latest.name, 'isoformat') else datetime.utcnow().isoformat(),
            "source": "yfinance",
            "interval": "1d",
            "metadata": {
                "open": float(latest['Open']),
                "high": float(latest['High']),
                "low": float(latest['Low']),
                "prev_close": prev_close,
            },
        }

        # Cache result
        if use_cache:
            _set_cache(cache_key, result)

        logger.info(f"✅ yfinance: {symbol} @ ${latest_price:.2f}")
        return result

    except Exception as e:
        logger.error(f"yfinance error for {symbol}: {e}")
        return {}


# ====== ALPHAVANTAGE NEWS ADAPTER ======
# Optional AlphaIntelligence import
try:
    from alpha_vantage.alphaintelligence import AlphaIntelligence
except ImportError:
    AlphaIntelligence = None  # type: ignore
    logger.warning("alpha-vantage not installed. Install with: uv pip install alpha-vantage")


async def fetch_alphavantage_news(symbols: List[str], limit: int = 10, use_cache: bool = True) -> List[Dict]:
    """
    Fetch news articles using Alpha Vantage AlphaIntelligence API.

    Args:
        symbols: List of ticker symbols to search news for
        limit: Max number of news articles to return (default: 10)
        use_cache: Use cached results if available

    Returns:
        List of news items in standardized format
    """
    if AlphaIntelligence is None:
        logger.warning("AlphaIntelligence not available - skipping")
        return []

    if not symbols:
        return []

    # Create cache key based on symbols
    cache_key = _get_cache_key("alphavantage_news", "search", {"symbols": ",".join(symbols), "limit": limit})

    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    await rate_limiter.acquire("alphavantage_news")

    try:
        # Run AlphaIntelligence in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        ai = await loop.run_in_executor(
            None, lambda: AlphaIntelligence(key=ALPHA_VANTAGE_API_KEY, output_format='pandas')
        )

        # Build topics query from symbols
        topics = ",".join(symbols)

        # Fetch news with topics filter
        news_df, _ = await loop.run_in_executor(
            None, lambda: ai.get_news_sentiment(topics=topics, limit=limit)
        )

        if news_df.empty:
            logger.warning(f"No news returned from AlphaVantage for {symbols}")
            return []

        results = []
        for _, row in news_df.head(limit).iterrows():
            # Extract sentiment score
            sentiment_score = float(row.get('overall_sentiment_score', 0))
            if sentiment_score > 0.15:
                sentiment = "positive"
            elif sentiment_score < -0.15:
                sentiment = "negative"
            else:
                sentiment = "neutral"

            # Extract source from URL
            url = row.get('url', '')
            source_website = urlparse(url).netloc if url else "unknown"

            results.append({
                "title": row.get('title', ''),
                "summary": row.get('summary', '')[:300],  # First 300 chars
                "url": url,
                "source": "alphavantage",
                "source_website": source_website,
                "published_at": row.get('time_published', ''),
                "sentiment": sentiment,
                "symbols": symbols,
            })

        if use_cache:
            _set_cache(cache_key, results)

        logger.info(f"✅ AlphaVantage News: Fetched {len(results)} articles")
        return results

    except Exception as e:
        logger.error(f"AlphaVantage news error: {e}")
        return []


# ====== TAVILY SEARCH ADAPTER ======
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


async def fetch_market_news(symbols: List[str], limit: int = 10, use_cache: bool = True) -> List[Dict]:
    """
    Fetch news articles for given symbols using Tavily Search API.

    Args:
        symbols: List of ticker symbols
        limit: Max number of news articles to return (default: 10)
        use_cache: Use cached results if available

    Returns:
        List of news items in standardized format
    """
    if not symbols:
        return []

    cache_key = _get_cache_key("tavily", "search", {"symbols": ",".join(symbols), "limit": limit})

    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    await rate_limiter.acquire("tavily")

    # Build search query
    query = " OR ".join([f"{symbol} stock" for symbol in symbols])

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": limit,
                "include_domains": ["finance.yahoo.com", "reuters.com", "bloomberg.com", "cnbc.com"],
            }

            async with session.post("https://api.tavily.com/search", json=payload, timeout=10) as response:
                data = await response.json()

                if "results" not in data:
                    logger.error(f"Tavily API error: {data}")
                    return []

                results = []
                for item in data["results"][:limit]:
                    # Simple sentiment analysis based on keywords
                    content = (item.get("content", "") + " " + item.get("title", "")).lower()
                    sentiment = "neutral"
                    if any(word in content for word in ["surge", "gain", "bull", "profit", "growth"]):
                        sentiment = "positive"
                    elif any(word in content for word in ["drop", "fall", "bear", "loss", "decline"]):
                        sentiment = "negative"

                    # Extract source website from URL
                    url = item.get("url", "")
                    source_website = urlparse(url).netloc if url else "unknown"

                    results.append({
                        "title": item.get("title", ""),
                        "summary": item.get("content", "")[:300],  # First 300 chars
                        "url": url,
                        "source": "tavily",
                        "source_website": source_website,  # Added source website
                        "published_at": datetime.utcnow().isoformat(),
                        "sentiment": sentiment,
                        "symbols": symbols,
                    })

                if use_cache:
                    _set_cache(cache_key, results)

                logger.info(f"Fetched {len(results)} news articles from Tavily")
                return results

    except Exception as e:
        logger.error(f"Tavily API error: {e}")
        return []


async def fetch_general_market_news(limit: int = 10, use_cache: bool = True) -> List[Dict]:
    """
    Fetch general market news including macro, economic, and political news.

    Topics covered:
    - Federal Reserve / Central Banks
    - Economic indicators (GDP, inflation, employment)
    - Political events affecting markets
    - Global market trends
    - Sector rotation

    Args:
        limit: Max number of news articles to return
        use_cache: Use cached results if available

    Returns:
        List of news items in standardized format
    """
    cache_key = _get_cache_key("general_news", "market", {"limit": limit})

    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    await rate_limiter.acquire("tavily")

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=TAVILY_API_KEY)

        # Search queries for different news categories
        queries = [
            "stock market news today",
            "Federal Reserve interest rates economic policy",
            "inflation GDP employment economic indicators",
            "global markets international trade",
            "market volatility investor sentiment"
        ]

        all_results = []

        for query in queries[:3]:  # Limit to 3 queries to avoid rate limits
            try:
                response = await asyncio.to_thread(
                    client.search,
                    query=query,
                    search_depth="basic",
                    max_results=3,  # 3 per query = 9 total
                    include_domains=["bloomberg.com", "reuters.com", "wsj.com", "cnbc.com", "ft.com"]
                )

                if "results" in response:
                    for item in response["results"]:
                        content = item.get("content", "") + " " + item.get("title", "")

                        # Simple sentiment analysis
                        sentiment = "neutral"
                        if any(word in content.lower() for word in ["surge", "rally", "bull", "gain", "profit", "growth", "optimistic"]):
                            sentiment = "positive"
                        elif any(word in content.lower() for word in ["drop", "fall", "bear", "loss", "decline", "recession", "pessimistic"]):
                            sentiment = "negative"

                        url = item.get("url", "")
                        source_website = urlparse(url).netloc if url else "unknown"

                        # Categorize news
                        category = "general"
                        if any(word in content.lower() for word in ["fed", "federal reserve", "interest rate", "powell"]):
                            category = "monetary_policy"
                        elif any(word in content.lower() for word in ["inflation", "cpi", "gdp", "employment", "jobs"]):
                            category = "economic_indicators"
                        elif any(word in content.lower() for word in ["election", "congress", "policy", "regulation"]):
                            category = "political"
                        elif any(word in content.lower() for word in ["china", "europe", "global", "international"]):
                            category = "international"

                        all_results.append({
                            "title": item.get("title", ""),
                            "summary": item.get("content", "")[:300],
                            "url": url,
                            "source": "tavily",
                            "source_website": source_website,
                            "published_at": datetime.utcnow().isoformat(),
                            "sentiment": sentiment,
                            "symbols": [],  # General news, no specific symbols
                            "category": category,
                        })

            except Exception as e:
                logger.warning(f"Error fetching news for query '{query}': {e}")
                continue

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for item in all_results:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                unique_results.append(item)

        # Limit results
        unique_results = unique_results[:limit]

        if use_cache:
            _set_cache(cache_key, unique_results)

        logger.info(f"✅ Fetched {len(unique_results)} general market news articles")
        return unique_results

    except Exception as e:
        logger.error(f"General market news error: {e}")
        return []


async def fetch_economic_calendar(use_cache: bool = True) -> List[Dict]:
    """
    Fetch upcoming economic events (simplified version using news search).

    Returns news about upcoming economic events like:
    - FOMC meetings
    - Earnings releases
    - Economic data releases
    - Policy announcements

    Returns:
        List of upcoming events/news
    """
    cache_key = _get_cache_key("economic_calendar", "events", {})

    if use_cache:
        cached = _get_cached(cache_key)
        if cached:
            return cached

    await rate_limiter.acquire("tavily")

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=TAVILY_API_KEY)

        query = "upcoming FOMC meeting earnings calendar economic data release schedule"

        response = await asyncio.to_thread(
            client.search,
            query=query,
            search_depth="basic",
            max_results=5
        )

        results = []
        if "results" in response:
            for item in response["results"]:
                url = item.get("url", "")
                source_website = urlparse(url).netloc if url else "unknown"

                results.append({
                    "title": item.get("title", ""),
                    "summary": item.get("content", "")[:300],
                    "url": url,
                    "source": "tavily",
                    "source_website": source_website,
                    "published_at": datetime.utcnow().isoformat(),
                    "sentiment": "neutral",
                    "symbols": [],
                    "category": "calendar",
                })

        if use_cache:
            _set_cache(cache_key, results)

        logger.info(f"✅ Fetched {len(results)} economic calendar items")
        return results

    except Exception as e:
        logger.error(f"Economic calendar error: {e}")
        return []


# ====== PARALLEL FETCHER ======
async def fetch_all_market_data(
    symbols: List[str], tools: List[str], timeframe: str = "1d", use_cache: bool = True
) -> Dict[str, List[Dict]]:
    """
    Fetch data from multiple sources in parallel.

    Args:
        symbols: List of ticker symbols
        tools: List of tool names to use ["alphavantage", "polygon", "news"]
        timeframe: "1min", "5min", "1h", "1d", "1w"

    Returns:
        {
            "alphavantage": [...],
            "polygon": [...],
            "news": [...]
        }
    """
    tasks = {}

    for tool in tools:
        if tool == "alphavantage":
            # Fetch quotes for all symbols
            tasks["alphavantage"] = asyncio.gather(
                *[fetch_alphavantage_quote(symbol, use_cache) for symbol in symbols], return_exceptions=True
            )

        elif tool == "polygon":
            # Fetch previous close for all symbols
            tasks["polygon"] = asyncio.gather(
                *[fetch_polygon_previous_close(symbol, use_cache) for symbol in symbols], return_exceptions=True
            )

        elif tool == "news":
            tasks["news"] = fetch_market_news(symbols)

    # Execute all tasks in parallel
    results = await asyncio.gather(*[tasks[tool] for tool in tools], return_exceptions=True)

    # Map results back to tool names
    output = {}
    for i, tool in enumerate(tools):
        result = results[i]
        if isinstance(result, Exception):
            logger.error(f"Error fetching {tool}: {result}")
            output[tool] = []
        else:
            output[tool] = result if isinstance(result, list) else [result]

    return output

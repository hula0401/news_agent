"""Yahoo Finance client for stock data and daily price changes."""
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import yfinance as yf
from loguru import logger


class YFinanceClient:
    """Client for Yahoo Finance stock data."""

    def __init__(self):
        """Initialize Yahoo Finance client."""
        self.session = None

    async def get_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current stock quote with daily price change.

        Args:
            symbol: Stock ticker symbol (e.g., AAPL, GOOGL)

        Returns:
            Dict with current price, change, change_percent, volume, etc.
            None if error occurs
        """
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._fetch_quote_sync, symbol)
            return data
        except Exception as e:
            logger.error(f"❌ YFinance quote error for {symbol}: {e}")
            return None

    def _fetch_quote_sync(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Synchronous fetch (called in executor)."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # Get historical data for yesterday's close
            hist = ticker.history(period="2d")

            if hist.empty or len(hist) < 1:
                logger.warning(f"⚠️ No historical data for {symbol}")
                return None

            # Current price and previous close
            current_price = info.get('currentPrice') or info.get('regularMarketPrice')
            if not current_price and len(hist) > 0:
                current_price = hist['Close'].iloc[-1]

            # Previous close (yesterday)
            previous_close = info.get('previousClose')
            if not previous_close and len(hist) > 1:
                previous_close = hist['Close'].iloc[-2]
            elif not previous_close and len(hist) == 1:
                # If only 1 day of data, use that as previous close
                previous_close = hist['Close'].iloc[0]

            if not current_price or not previous_close:
                logger.warning(f"⚠️ Missing price data for {symbol}")
                return None

            # Calculate change and change_percent
            change = current_price - previous_close
            change_percent = (change / previous_close) * 100

            # Extract other data
            volume = info.get('volume') or (hist['Volume'].iloc[-1] if len(hist) > 0 else None)
            market_cap = info.get('marketCap')

            # 52-week high/low
            high_52_week = info.get('fiftyTwoWeekHigh')
            low_52_week = info.get('fiftyTwoWeekLow')

            # PE ratio and dividend yield
            pe_ratio = info.get('trailingPE') or info.get('forwardPE')
            dividend_yield = info.get('dividendYield')

            result = {
                'symbol': symbol.upper(),
                'price': float(current_price),
                'previous_close': float(previous_close),
                'change': float(change),
                'change_percent': float(change_percent),
                'volume': int(volume) if volume else None,
                'market_cap': int(market_cap) if market_cap else None,
                'high_52_week': float(high_52_week) if high_52_week else None,
                'low_52_week': float(low_52_week) if low_52_week else None,
                'pe_ratio': float(pe_ratio) if pe_ratio else None,
                'dividend_yield': float(dividend_yield) if dividend_yield else None,
                'last_updated': datetime.utcnow().isoformat(),
                'data_source': 'yfinance'
            }

            logger.info(f"✅ YFinance fetched {symbol}: ${current_price:.2f} ({change_percent:+.2f}%)")
            return result

        except Exception as e:
            logger.error(f"❌ Error fetching {symbol} from YFinance: {e}")
            return None

    async def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get quotes for multiple symbols.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dict mapping symbol to quote data
        """
        results = {}

        # Fetch concurrently
        tasks = [self.get_stock_quote(symbol) for symbol in symbols]
        quotes = await asyncio.gather(*tasks, return_exceptions=True)

        for symbol, quote in zip(symbols, quotes):
            if isinstance(quote, dict):
                results[symbol] = quote
            elif isinstance(quote, Exception):
                logger.error(f"❌ Error fetching {symbol}: {quote}")
            else:
                logger.warning(f"⚠️ No data for {symbol}")

        return results

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get historical price data.

        Args:
            symbol: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            List of historical data points
        """
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                self._fetch_historical_sync,
                symbol,
                period,
                interval
            )
            return data
        except Exception as e:
            logger.error(f"❌ YFinance historical error for {symbol}: {e}")
            return None

    def _fetch_historical_sync(
        self,
        symbol: str,
        period: str,
        interval: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Synchronous historical fetch."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return None

            # Convert to list of dicts
            result = []
            for idx, row in hist.iterrows():
                result.append({
                    'timestamp': idx.isoformat(),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume']),
                })

            return result

        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {e}")
            return None


# Global client instance
_yfinance_client: Optional[YFinanceClient] = None


async def get_yfinance_client() -> YFinanceClient:
    """Get or create Yahoo Finance client instance."""
    global _yfinance_client

    if _yfinance_client is None:
        _yfinance_client = YFinanceClient()
        logger.info("✅ Yahoo Finance client initialized")

    return _yfinance_client

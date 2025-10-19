"""Database operations for stock prices."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from supabase import Client


class StockPriceDB:
    """Database operations for stock prices with LFU tracking."""

    def __init__(self, client: Client):
        self.client = client

    async def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent stock price for a symbol.

        Args:
            symbol: Stock ticker symbol (e.g., AAPL)

        Returns:
            Stock price data or None if not found
        """
        try:
            def _fetch():
                return (
                    self.client
                    .table('stock_prices')
                    .select('*')
                    .eq('symbol', symbol.upper())
                    .order('last_updated', desc=True)
                    .limit(1)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            print(f"❌ Error getting latest price for {symbol}: {e}")
            return None

    async def insert_price(self, price_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Insert new stock price data.

        Args:
            price_data: Dictionary containing price information

        Returns:
            Inserted data or None on error
        """
        try:
            def _insert():
                return self.client.table('stock_prices').insert(price_data).execute()

            result = await asyncio.to_thread(_insert)

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            print(f"❌ Error inserting price data: {e}")
            return None

    async def get_price_history(
        self,
        symbol: str,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical price data for a symbol.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of records
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of price records
        """
        try:
            def _fetch():
                query = (
                    self.client
                    .table('stock_prices')
                    .select('*')
                    .eq('symbol', symbol.upper())
                )

                if start_date:
                    query = query.gte('last_updated', start_date.isoformat())
                if end_date:
                    query = query.lte('last_updated', end_date.isoformat())

                return query.order('last_updated', desc=True).limit(limit).execute()

            result = await asyncio.to_thread(_fetch)
            return result.data or []

        except Exception as e:
            print(f"❌ Error getting price history for {symbol}: {e}")
            return []

    async def get_multiple_latest_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get latest prices for multiple symbols.

        Args:
            symbols: List of stock ticker symbols

        Returns:
            Dictionary mapping symbol to price data
        """
        try:
            def _fetch():
                return (
                    self.client
                    .table('stock_prices')
                    .select('*')
                    .in_('symbol', [s.upper() for s in symbols])
                    .order('last_updated', desc=True)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)

            # Group by symbol and keep only latest
            prices_by_symbol = {}
            if result.data:
                for row in result.data:
                    symbol = row['symbol']
                    if symbol not in prices_by_symbol:
                        prices_by_symbol[symbol] = row

            return prices_by_symbol

        except Exception as e:
            print(f"❌ Error getting multiple prices: {e}")
            return {}

    async def update_price(self, symbol: str, price_data: Dict[str, Any]) -> bool:
        """
        Update existing stock price or insert if not exists.

        Args:
            symbol: Stock ticker symbol
            price_data: Updated price data

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use upsert functionality
            price_data['symbol'] = symbol.upper()

            def _upsert():
                return (
                    self.client
                    .table('stock_prices')
                    .upsert(price_data, on_conflict='symbol,last_updated')
                    .execute()
                )

            result = await asyncio.to_thread(_upsert)
            return result.data is not None

        except Exception as e:
            print(f"❌ Error updating price for {symbol}: {e}")
            return False

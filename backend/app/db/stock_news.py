"""Database operations for stock news with LIFO stack management."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from supabase import Client


class StockNewsDB:
    """Database operations for stock news with LIFO stack (Latest 5 on Top)."""

    def __init__(self, client: Client):
        self.client = client

    async def get_news_stack(self, symbol: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the top N news articles from the stack (positions 1-5).

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of articles (default 5)

        Returns:
            List of news articles ordered by position (1 = newest)
        """
        try:
            def _fetch():
                return (
                    self.client
                    .table('stock_news')
                    .select('*, news_sources(*)')
                    .eq('symbol', symbol.upper())
                    .eq('is_archived', False)
                    .not_.is_('position_in_stack', 'null')
                    .order('position_in_stack', desc=False)
                    .limit(limit)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)
            return result.data or []

        except Exception as e:
            print(f"❌ Error getting news stack for {symbol}: {e}")
            return []

    async def push_news_to_stack(
        self,
        symbol: str,
        news_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Push new news article to position 1 (top of stack).
        Shifts existing articles down and archives position 6+.

        Args:
            symbol: Stock ticker symbol
            news_data: News article data

        Returns:
            Created news article with archived article ID if any
        """
        try:
            # Step 1: Shift existing articles down (5->6, 4->5, 3->4, 2->3, 1->2)
            def _shift_down():
                return (
                    self.client
                    .rpc('shift_stock_news_down', {'stock_symbol': symbol.upper()})
                    .execute()
                )

            await asyncio.to_thread(_shift_down)

            # Step 2: Insert new article at position 1
            news_data['symbol'] = symbol.upper()
            news_data['position_in_stack'] = 1
            news_data['is_archived'] = False

            def _insert():
                return self.client.table('stock_news').insert(news_data).execute()

            result = await asyncio.to_thread(_insert)

            # Step 3: Archive articles at position 6+
            archived_id = await self._archive_overflow(symbol)

            if result.data:
                article = result.data[0]
                article['archived_article_id'] = archived_id
                return article

            return None

        except Exception as e:
            print(f"❌ Error pushing news to stack for {symbol}: {e}")
            return None

    async def _archive_overflow(self, symbol: str) -> Optional[str]:
        """
        Archive news articles at position 6 and beyond.

        Args:
            symbol: Stock ticker symbol

        Returns:
            ID of archived article or None
        """
        try:
            # Find articles at position > 5
            def _find_overflow():
                return (
                    self.client
                    .table('stock_news')
                    .select('id')
                    .eq('symbol', symbol.upper())
                    .eq('is_archived', False)
                    .gt('position_in_stack', 5)
                    .execute()
                )

            overflow_result = await asyncio.to_thread(_find_overflow)

            if overflow_result.data:
                article_ids = [row['id'] for row in overflow_result.data]

                # Archive them
                def _archive():
                    return (
                        self.client
                        .table('stock_news')
                        .update({
                            'position_in_stack': None,
                            'is_archived': True,
                            'archived_at': datetime.now().isoformat()
                        })
                        .in_('id', article_ids)
                        .execute()
                    )

                await asyncio.to_thread(_archive)
                return article_ids[0] if article_ids else None

            return None

        except Exception as e:
            print(f"❌ Error archiving overflow for {symbol}: {e}")
            return None

    async def get_archived_news(
        self,
        symbol: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get archived news articles for a symbol.

        Args:
            symbol: Stock ticker symbol
            limit: Maximum number of articles
            offset: Pagination offset

        Returns:
            List of archived news articles
        """
        try:
            def _fetch():
                return (
                    self.client
                    .table('stock_news')
                    .select('*, news_sources(*)')
                    .eq('symbol', symbol.upper())
                    .eq('is_archived', True)
                    .order('archived_at', desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)
            return result.data or []

        except Exception as e:
            print(f"❌ Error getting archived news for {symbol}: {e}")
            return []

    async def get_news_by_id(self, news_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific news article by ID.

        Args:
            news_id: News article ID

        Returns:
            News article data or None
        """
        try:
            def _fetch():
                return (
                    self.client
                    .table('stock_news')
                    .select('*, news_sources(*)')
                    .eq('id', news_id)
                    .limit(1)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            print(f"❌ Error getting news by ID {news_id}: {e}")
            return None

    async def search_news(
        self,
        symbol: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_archived: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search stock news with filters.

        Args:
            symbol: Optional stock ticker symbol filter
            keywords: Optional keywords to search in title/summary
            start_date: Optional start date filter
            end_date: Optional end date filter
            include_archived: Whether to include archived articles
            limit: Maximum number of results

        Returns:
            List of matching news articles
        """
        try:
            def _search():
                query = self.client.table('stock_news').select('*, news_sources(*)')

                if symbol:
                    query = query.eq('symbol', symbol.upper())

                if not include_archived:
                    query = query.eq('is_archived', False)

                if start_date:
                    query = query.gte('published_at', start_date.isoformat())

                if end_date:
                    query = query.lte('published_at', end_date.isoformat())

                # Note: Text search would need full-text search capability
                # For now, we'll return ordered by date
                return query.order('published_at', desc=True).limit(limit).execute()

            result = await asyncio.to_thread(_search)
            return result.data or []

        except Exception as e:
            print(f"❌ Error searching news: {e}")
            return []

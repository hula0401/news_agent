"""Database operations for economic news."""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
from supabase import Client


class EconomicNewsDB:
    """Database operations for economic news (Fed, politics, indicators)."""

    def __init__(self, client: Client):
        self.client = client

    async def get_economic_news(
        self,
        categories: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        impact_level: Optional[str] = None,
        breaking_only: bool = False,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get economic news with filters.

        Args:
            categories: Filter by categories (federal_reserve, politics, etc.)
            regions: Filter by regions (us, eu, china, etc.)
            impact_level: Filter by impact level (low, medium, high)
            breaking_only: Only return breaking news
            limit: Maximum number of articles
            offset: Pagination offset

        Returns:
            List of economic news articles
        """
        try:
            def _fetch():
                query = self.client.table('economic_news').select('*, news_sources(*)')

                if categories:
                    query = query.in_('category', categories)

                if regions:
                    query = query.in_('region', regions)

                if impact_level:
                    query = query.eq('impact_level', impact_level)

                if breaking_only:
                    query = query.eq('is_breaking', True)

                return (
                    query
                    .order('published_at', desc=True)
                    .range(offset, offset + limit - 1)
                    .execute()
                )

            result = await asyncio.to_thread(_fetch)
            return result.data or []

        except Exception as e:
            print(f"❌ Error getting economic news: {e}")
            return []

    async def get_federal_reserve_news(
        self,
        news_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get Federal Reserve announcements.

        Args:
            news_type: Filter by type (fomc_statement, speech, minutes, etc.)
            limit: Maximum number of announcements

        Returns:
            List of Fed announcements
        """
        try:
            def _fetch():
                query = (
                    self.client
                    .table('economic_news')
                    .select('*, news_sources(*)')
                    .eq('category', 'federal_reserve')
                )

                # Note: Would need additional type field for precise filtering
                # For now, filter by category

                return query.order('published_at', desc=True).limit(limit).execute()

            result = await asyncio.to_thread(_fetch)
            return result.data or []

        except Exception as e:
            print(f"❌ Error getting Fed news: {e}")
            return []

    async def get_politics_news(
        self,
        regions: Optional[List[str]] = None,
        impact_level: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get political news with economic impact.

        Args:
            regions: Filter by regions
            impact_level: Filter by impact level
            limit: Maximum number of articles

        Returns:
            List of political news articles
        """
        try:
            def _fetch():
                query = (
                    self.client
                    .table('economic_news')
                    .select('*, news_sources(*)')
                    .eq('category', 'politics')
                )

                if regions:
                    query = query.in_('region', regions)

                if impact_level:
                    query = query.eq('impact_level', impact_level)

                return query.order('published_at', desc=True).limit(limit).execute()

            result = await asyncio.to_thread(_fetch)
            return result.data or []

        except Exception as e:
            print(f"❌ Error getting politics news: {e}")
            return []

    async def get_breaking_news(
        self,
        categories: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get breaking economic news.

        Args:
            categories: Optional category filter
            limit: Maximum number of articles

        Returns:
            List of breaking news articles
        """
        return await self.get_economic_news(
            categories=categories,
            breaking_only=True,
            limit=limit
        )

    async def insert_economic_news(self, news_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Insert new economic news article.

        Args:
            news_data: News article data

        Returns:
            Created article or None on error
        """
        try:
            def _insert():
                return self.client.table('economic_news').insert(news_data).execute()

            result = await asyncio.to_thread(_insert)

            if result.data:
                return result.data[0]
            return None

        except Exception as e:
            print(f"❌ Error inserting economic news: {e}")
            return None

    async def get_news_by_symbols(
        self,
        symbols: List[str],
        limit: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get economic news related to specific stock symbols.

        Args:
            symbols: List of stock ticker symbols
            limit: Maximum articles per symbol

        Returns:
            Dictionary mapping symbol to news articles
        """
        try:
            def _fetch():
                # Note: This uses contains operator for array column
                query = self.client.table('economic_news').select('*, news_sources(*)')

                # Filter for news that mentions any of the symbols
                # Would need to use @> or && operator for array overlap
                return query.order('published_at', desc=True).limit(limit * len(symbols)).execute()

            result = await asyncio.to_thread(_fetch)

            # Group by related symbols
            news_by_symbol = {symbol: [] for symbol in symbols}

            if result.data:
                for article in result.data:
                    related = article.get('related_symbols', [])
                    for symbol in symbols:
                        if symbol.upper() in [s.upper() for s in related]:
                            if len(news_by_symbol[symbol]) < limit:
                                news_by_symbol[symbol].append(article)

            return news_by_symbol

        except Exception as e:
            print(f"❌ Error getting news by symbols: {e}")
            return {symbol: [] for symbol in symbols}

    async def search_economic_news(
        self,
        query_text: str,
        categories: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search economic news by text query.

        Args:
            query_text: Search query
            categories: Optional category filter
            limit: Maximum number of results

        Returns:
            List of matching articles
        """
        try:
            def _search():
                # Note: Would need full-text search capability
                # For now, we'll use basic text search on title
                query = (
                    self.client
                    .table('economic_news')
                    .select('*, news_sources(*)')
                    .text_search('title', query_text)
                )

                if categories:
                    query = query.in_('category', categories)

                return query.order('published_at', desc=True).limit(limit).execute()

            result = await asyncio.to_thread(_search)
            return result.data or []

        except Exception as e:
            print(f"❌ Error searching economic news: {e}")
            return []

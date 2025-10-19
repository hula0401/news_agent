"""Background scheduler for stock and news updates."""
import asyncio
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from ..config import get_settings

settings = get_settings()


class SchedulerManager:
    """Manages background scheduled tasks."""

    def __init__(self):
        """Initialize scheduler manager."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._running = False

    def start(self):
        """Start the scheduler with all jobs."""
        if self._running:
            logger.warning("⚠️ Scheduler already running")
            return

        if not settings.enable_scheduler:
            logger.info("ℹ️ Scheduler disabled via configuration")
            return

        # Create scheduler
        self.scheduler = AsyncIOScheduler()

        # Add stock price update job
        self.scheduler.add_job(
            self._update_popular_stocks,
            trigger=IntervalTrigger(minutes=settings.stock_update_interval_minutes),
            id='update_popular_stocks',
            name='Update Popular Stock Prices',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )
        logger.info(
            f"✅ Scheduled stock price updates every {settings.stock_update_interval_minutes} minutes"
        )

        # Add news update job
        self.scheduler.add_job(
            self._update_latest_news,
            trigger=IntervalTrigger(minutes=settings.news_update_interval_minutes),
            id='update_latest_news',
            name='Update Latest News',
            replace_existing=True,
            max_instances=1
        )
        logger.info(
            f"✅ Scheduled news updates every {settings.news_update_interval_minutes} minutes"
        )

        # Start scheduler
        self.scheduler.start()
        self._running = True
        logger.info("🚀 Background scheduler started successfully")

    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        if not self._running or not self.scheduler:
            return

        logger.info("🛑 Shutting down background scheduler...")
        self.scheduler.shutdown(wait=True)
        self._running = False
        logger.info("✅ Background scheduler stopped")

    async def _update_popular_stocks(self):
        """
        Update popular stock prices from yfinance.

        This job runs every N minutes to:
        1. Fetch latest prices from Yahoo Finance
        2. Calculate daily price changes based on yesterday's close
        3. Update database
        4. Update Redis cache with 2-minute TTL
        """
        try:
            logger.info("🔄 Starting popular stocks update job...")

            # Import here to avoid circular dependencies
            from ..external.yfinance_client import get_yfinance_client
            from ..db.stock_prices import StockPriceDB
            from ..cache import cache_manager
            from ..database import db_manager

            # Get popular stocks list
            symbols = [s.strip() for s in settings.popular_stocks.split(',') if s.strip()]
            if not symbols:
                logger.warning("⚠️ No popular stocks configured")
                return

            logger.info(f"📊 Updating {len(symbols)} popular stocks: {', '.join(symbols)}")

            # Initialize clients
            yf_client = await get_yfinance_client()

            # Ensure cache is initialized
            if not cache_manager._initialized:
                await cache_manager.initialize()

            # Fetch batch quotes from Yahoo Finance
            quotes = await yf_client.get_batch_quotes(symbols)

            # Update database and cache for each stock
            success_count = 0
            for symbol, quote_data in quotes.items():
                if not quote_data:
                    continue

                try:
                    # Update database
                    from datetime import datetime, timezone
                    stock_db = StockPriceDB(db_manager.client)
                    await stock_db.insert_price({
                        'symbol': symbol,
                        'price': quote_data['price'],
                        'change': quote_data['change'],
                        'change_percent': quote_data['change_percent'],
                        'volume': quote_data.get('volume'),
                        'market_cap': quote_data.get('market_cap'),
                        'high_52_week': quote_data.get('high_52_week'),
                        'low_52_week': quote_data.get('low_52_week'),
                        'pe_ratio': quote_data.get('pe_ratio'),
                        'dividend_yield': quote_data.get('dividend_yield'),
                        'last_updated': datetime.now(timezone.utc).isoformat(),  # Use UTC timestamp
                        'data_source': 'yfinance'
                    })

                    # Update Redis cache with 2-minute TTL (120 seconds)
                    cache_key = f"stock:price:{symbol}"
                    await cache_manager.set(cache_key, quote_data, ttl=120)

                    success_count += 1
                    logger.debug(
                        f"✅ Updated {symbol}: ${quote_data['price']:.2f} "
                        f"({quote_data['change_percent']:+.2f}%)"
                    )

                except Exception as e:
                    logger.error(f"❌ Error updating {symbol}: {e}")

            logger.info(
                f"✅ Popular stocks update completed: {success_count}/{len(symbols)} successful"
            )

        except Exception as e:
            logger.error(f"❌ Error in popular stocks update job: {e}")

    async def _update_latest_news(self):
        """
        Update latest news for popular stocks.

        This job runs every N minutes to:
        1. Fetch latest news from multiple sources
        2. Deduplicate articles
        3. Push to LIFO stack (position 1)
        4. Update Redis cache with 2-minute TTL
        """
        try:
            logger.info("🔄 Starting latest news update job...")

            # Import here to avoid circular dependencies
            from ..services.news_aggregator import NewsAggregator
            from ..db.stock_news import StockNewsDB
            from ..cache import cache_manager
            from ..database import db_manager

            # Get popular stocks list
            symbols = [s.strip() for s in settings.popular_stocks.split(',') if s.strip()]
            if not symbols:
                logger.warning("⚠️ No popular stocks configured")
                return

            logger.info(f"📰 Updating news for {len(symbols)} popular stocks")

            # Initialize services
            news_aggregator = NewsAggregator()
            await news_aggregator.initialize()

            # Ensure cache is initialized
            if not cache_manager._initialized:
                await cache_manager.initialize()

            # Update news for each stock
            success_count = 0
            total_articles = 0

            for symbol in symbols:
                try:
                    # Aggregate news from multiple sources
                    articles = await news_aggregator.aggregate_stock_news(symbol, limit=5)

                    if not articles:
                        logger.debug(f"ℹ️ No new articles for {symbol}")
                        continue

                    # Push articles to LIFO stack (newest first)
                    stock_news_db = StockNewsDB(db_manager.client)

                    for article in articles[:5]:  # Top 5 only
                        # Prepare news data
                        news_data = {
                            'symbol': symbol,
                            'title': article.get('title'),
                            'summary': article.get('summary') or article.get('description'),
                            'url': article.get('url'),
                            'source_name': article.get('source', {}).get('name', 'Unknown'),
                            'published_at': article.get('published_at'),
                            'sentiment_score': article.get('sentiment_score')
                        }

                        # Push to LIFO stack
                        await stock_news_db.push_news_to_stack(symbol, news_data)
                        total_articles += 1

                    # Update Redis cache with news
                    cache_key = f"stock:news:{symbol}"
                    await cache_manager.set(cache_key, articles[:5], ttl=120)

                    success_count += 1
                    logger.debug(f"✅ Updated {len(articles)} articles for {symbol}")

                except Exception as e:
                    logger.error(f"❌ Error updating news for {symbol}: {e}")

            logger.info(
                f"✅ News update completed: {success_count}/{len(symbols)} stocks, "
                f"{total_articles} total articles"
            )

        except Exception as e:
            logger.error(f"❌ Error in news update job: {e}")


# Global scheduler instance
_scheduler_manager: Optional[SchedulerManager] = None


def get_scheduler_manager() -> SchedulerManager:
    """Get or create scheduler manager instance."""
    global _scheduler_manager

    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
        logger.info("✅ Scheduler manager initialized")

    return _scheduler_manager

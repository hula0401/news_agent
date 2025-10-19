"""LFU Cache Manager for Stock & News API with time-decay scoring."""
import time
import math
import json
from typing import Optional, Any, Dict, List, Tuple
from datetime import datetime
import httpx
from ..config import get_settings
from ..database import get_database

settings = get_settings()


class LFUCacheManager:
    """
    LFU (Least Frequently Used) Cache Manager with time decay.

    Implements frequency scoring algorithm:
    score = (access_count / time_span_hours) * recency_factor * 100

    Features:
    - Access frequency tracking
    - Time-based decay (24hr half-life)
    - Per-type LFU tracking (stock_price, stock_news, etc.)
    - Automatic eviction of least frequently used entries
    """

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.base_url = settings.upstash_redis_rest_url
        self.token = settings.upstash_redis_rest_token
        self._initialized = False
        self.db = None

    async def initialize(self):
        """Initialize Redis client and database connection."""
        if self._initialized:
            return

        try:
            self.client = httpx.AsyncClient(
                timeout=10.0,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
            )
            # Get database instance
            from ..database import db_manager
            self.db = db_manager
            if not self.db._initialized:
                await self.db.initialize()

            self._initialized = True
            print("✅ LFU Cache Manager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize LFU Cache Manager: {e}")
            raise

    def calculate_frequency_score(
        self,
        access_count: int,
        first_access_time: float,
        last_access_time: float,
        current_time: Optional[float] = None
    ) -> float:
        """
        Calculate LFU frequency score with time decay.

        Formula:
        score = (access_count / time_span_hours) * recency_factor * 100

        Args:
            access_count: Total number of accesses
            first_access_time: Unix timestamp of first access
            last_access_time: Unix timestamp of last access
            current_time: Current unix timestamp (defaults to now)

        Returns:
            Frequency score (higher = more frequently accessed = less likely to be evicted)
        """
        if current_time is None:
            current_time = time.time()

        # Time span since first access (in hours), minimum 1 hour
        time_span_hours = max((current_time - first_access_time) / 3600, 1.0)

        # Recency factor (exponential decay with 24-hour half-life)
        recency_hours = (current_time - last_access_time) / 3600
        recency_factor = math.exp(-recency_hours / 24)  # Decay over 24 hours

        # Frequency rate (accesses per hour)
        frequency_rate = access_count / time_span_hours

        # Combined score
        score = frequency_rate * recency_factor * 100

        return round(score, 4)

    async def track_access(self, cache_key: str, cache_type: str):
        """
        Track cache access and update LFU score.

        Args:
            cache_key: Redis cache key
            cache_type: Type of cache (stock_price, stock_news, economic_news, etc.)
        """
        if not self._initialized:
            await self.initialize()

        current_time = time.time()

        try:
            # Update access statistics in database
            query = """
                INSERT INTO cache_access_stats (cache_key, cache_type, access_count, last_access_at, first_access_at)
                VALUES ($1, $2, 1, NOW(), NOW())
                ON CONFLICT (cache_key)
                DO UPDATE SET
                    access_count = cache_access_stats.access_count + 1,
                    last_access_at = NOW(),
                    updated_at = NOW()
                RETURNING access_count,
                          EXTRACT(EPOCH FROM first_access_at) as first_access,
                          EXTRACT(EPOCH FROM last_access_at) as last_access
            """

            result = self.db.client.rpc('exec_sql', {
                'query': query,
                'params': [cache_key, cache_type]
            }).execute()

            if result.data:
                row = result.data[0]
                access_count = row['access_count']
                first_access = row['first_access']
                last_access = row['last_access']

                # Calculate new frequency score
                frequency_score = self.calculate_frequency_score(
                    access_count, first_access, last_access, current_time
                )

                # Update frequency score in database
                update_query = """
                    UPDATE cache_access_stats
                    SET frequency_score = $1, updated_at = NOW()
                    WHERE cache_key = $2
                """
                self.db.client.rpc('exec_sql', {
                    'query': update_query,
                    'params': [frequency_score, cache_key]
                }).execute()

                # Update Redis LFU sorted set
                await self._redis_zadd(f"{cache_type}:lfu", frequency_score, cache_key)

        except Exception as e:
            # Gracefully handle missing cache_access_stats table or other errors
            # Don't fail the cache operation just because tracking failed
            print(f"⚠️ Warning: Could not track cache access for {cache_key}: {str(e)}")

    async def get_lfu_candidates_for_eviction(
        self,
        cache_type: str,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get cache keys with lowest frequency scores for eviction.

        Args:
            cache_type: Type of cache (stock_price, stock_news, etc.)
            limit: Maximum number of candidates to return

        Returns:
            List of (cache_key, score) tuples, sorted by score (ascending)
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get keys with lowest LFU scores from Redis
            response = await self.client.post(
                f"{self.base_url}/zrange/{cache_type}:lfu/0/{limit - 1}/WITHSCORES"
            )

            if response.status_code == 200:
                result = response.json().get("result", [])
                # Result is [key1, score1, key2, score2, ...]
                candidates = []
                for i in range(0, len(result), 2):
                    if i + 1 < len(result):
                        cache_key = result[i]
                        score = float(result[i + 1])
                        candidates.append((cache_key, score))
                return candidates

            return []

        except Exception as e:
            print(f"❌ Error getting LFU candidates: {e}")
            return []

    async def evict_lfu_entries(self, cache_type: str, count: int):
        """
        Evict least frequently used entries.

        Args:
            cache_type: Type of cache (stock_price, stock_news, etc.)
            count: Number of entries to evict
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get candidates for eviction
            candidates = await self.get_lfu_candidates_for_eviction(cache_type, count)

            for cache_key, score in candidates:
                # Remove from cache
                await self._redis_delete(cache_key)

                # Remove from LFU tracking
                await self._redis_zrem(f"{cache_type}:lfu", cache_key)

                print(f"🗑️  Evicted LFU entry: {cache_key} (score: {score:.4f})")

        except Exception as e:
            print(f"❌ Error evicting LFU entries: {e}")

    async def get_hot_keys(self, cache_type: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Get most frequently accessed cache keys.

        Args:
            cache_type: Type of cache (stock_price, stock_news, etc.)
            limit: Maximum number of keys to return

        Returns:
            List of (cache_key, score) tuples, sorted by score (descending)
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get keys with highest LFU scores from Redis
            response = await self.client.post(
                f"{self.base_url}/zrevrange/{cache_type}:lfu/0/{limit - 1}/WITHSCORES"
            )

            if response.status_code == 200:
                result = response.json().get("result", [])
                hot_keys = []
                for i in range(0, len(result), 2):
                    if i + 1 < len(result):
                        cache_key = result[i]
                        score = float(result[i + 1])
                        hot_keys.append((cache_key, score))
                return hot_keys

            return []

        except Exception as e:
            print(f"❌ Error getting hot keys: {e}")
            return []

    async def get_cache_statistics(self, cache_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Args:
            cache_type: Optional cache type filter

        Returns:
            Dictionary with cache statistics
        """
        if not self._initialized:
            await self.initialize()

        try:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "cache_types": {}
            }

            # Get stats for specific type or all types
            cache_types = [cache_type] if cache_type else [
                "stock_price", "stock_news", "economic_news", "user_watchlist"
            ]

            for ct in cache_types:
                # Get top 10 hot keys
                hot_keys = await self.get_hot_keys(ct, 10)

                # Get total keys count
                response = await self.client.get(f"{self.base_url}/zcard/{ct}:lfu")
                total_keys = 0
                if response.status_code == 200:
                    total_keys = response.json().get("result", 0)

                # Get database stats
                db_stats_query = """
                    SELECT
                        COUNT(*) as total_accesses,
                        AVG(frequency_score) as avg_score,
                        MAX(frequency_score) as max_score,
                        MIN(frequency_score) as min_score
                    FROM cache_access_stats
                    WHERE cache_type = $1
                """
                db_result = self.db.client.rpc('exec_sql', {
                    'query': db_stats_query,
                    'params': [ct]
                }).execute()

                db_stats = db_result.data[0] if db_result.data else {}

                stats["cache_types"][ct] = {
                    "total_keys": total_keys,
                    "hot_keys": [{"key": k, "score": s} for k, s in hot_keys],
                    "total_accesses": db_stats.get("total_accesses", 0),
                    "avg_frequency_score": float(db_stats.get("avg_score", 0)) if db_stats.get("avg_score") else 0,
                    "max_frequency_score": float(db_stats.get("max_score", 0)) if db_stats.get("max_score") else 0,
                    "min_frequency_score": float(db_stats.get("min_score", 0)) if db_stats.get("min_score") else 0
                }

            return stats

        except Exception as e:
            print(f"❌ Error getting cache statistics: {e}")
            return {"error": str(e)}

    # ==================== Redis Helper Methods ====================

    async def _redis_zadd(self, key: str, score: float, member: str) -> bool:
        """Add member to sorted set with score."""
        try:
            response = await self.client.post(
                f"{self.base_url}/zadd/{key}",
                json=[score, member]
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Redis ZADD error: {e}")
            return False

    async def _redis_zrem(self, key: str, member: str) -> bool:
        """Remove member from sorted set."""
        try:
            response = await self.client.post(
                f"{self.base_url}/zrem/{key}",
                json=[member]
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Redis ZREM error: {e}")
            return False

    async def _redis_delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            response = await self.client.post(f"{self.base_url}/del/{key}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Redis DELETE error: {e}")
            return False

    async def _redis_zincrby(self, key: str, increment: float, member: str) -> bool:
        """Increment score of member in sorted set."""
        try:
            response = await self.client.post(
                f"{self.base_url}/zincrby/{key}/{increment}/{member}"
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Redis ZINCRBY error: {e}")
            return False


# Global LFU cache manager instance
lfu_cache_manager = LFUCacheManager()


async def get_lfu_cache() -> LFUCacheManager:
    """Get LFU cache manager instance."""
    if not lfu_cache_manager._initialized:
        await lfu_cache_manager.initialize()
    return lfu_cache_manager

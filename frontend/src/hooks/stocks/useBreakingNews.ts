/**
 * useBreakingNews Hook
 * Fetches and manages breaking news with auto-refresh
 */

import { useState, useEffect, useCallback } from 'react';
import { newsService } from '../../services/news-service';
import type { EconomicNewsItem } from '../../mocks/news-data';
import { logger } from '../../utils/logger';

interface UseBreakingNewsResult {
  news: EconomicNewsItem[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  lastUpdated: Date | null;
}

/**
 * Custom hook to fetch breaking news
 * Auto-refreshes every 30 seconds (market hours) or 2 minutes (off-hours)
 *
 * @param limit - Maximum number of breaking news items to fetch (default: 5)
 * @param enableAutoRefresh - Enable automatic refresh (default: true)
 * @returns Breaking news state and controls
 *
 * @example
 * ```tsx
 * function BreakingNewsWidget() {
 *   const { news, loading, error, refetch } = useBreakingNews(5);
 *
 *   return (
 *     <NewsFeed
 *       news={news}
 *       loading={loading}
 *       error={error}
 *       title="Breaking News"
 *       titleOnly={true}
 *       onRefresh={refetch}
 *     />
 *   );
 * }
 * ```
 */
export function useBreakingNews(
  limit: number = 5,
  enableAutoRefresh: boolean = true
): UseBreakingNewsResult {
  const [news, setNews] = useState<EconomicNewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchBreakingNews = useCallback(async () => {
    try {
      logger.info('useBreakingNews', `Fetching breaking news (limit: ${limit})`);
      setLoading(true);
      setError(null);

      const fetchedNews = await newsService.getBreakingNews(limit);
      setNews(fetchedNews);
      setLastUpdated(new Date());

      logger.info('useBreakingNews', `Fetched ${fetchedNews.length} breaking news items`);
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error('Failed to fetch breaking news');
      logger.error('useBreakingNews', 'Error fetching breaking news', errorObj);
      setError(errorObj);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  // Initial fetch
  useEffect(() => {
    fetchBreakingNews();
  }, [fetchBreakingNews]);

  // Auto-refresh based on market hours
  useEffect(() => {
    if (!enableAutoRefresh) return;

    const isMarketHours = () => {
      const now = new Date();
      const day = now.getDay();
      const hours = now.getHours();
      const minutes = now.getMinutes();

      // Weekend
      if (day === 0 || day === 6) return false;

      const currentMinutes = hours * 60 + minutes;
      const marketOpen = 9 * 60 + 30; // 9:30 AM
      const marketClose = 16 * 60; // 4:00 PM

      return currentMinutes >= marketOpen && currentMinutes <= marketClose;
    };

    // Refresh every 30s during market hours, 2min off-hours
    const refreshInterval = isMarketHours() ? 30000 : 120000;

    logger.info('useBreakingNews', `Setting up auto-refresh (interval: ${refreshInterval}ms)`);

    const intervalId = setInterval(() => {
      logger.info('useBreakingNews', 'Auto-refreshing breaking news');
      fetchBreakingNews();
    }, refreshInterval);

    return () => {
      logger.info('useBreakingNews', 'Clearing auto-refresh interval');
      clearInterval(intervalId);
    };
  }, [enableAutoRefresh, fetchBreakingNews]);

  return {
    news,
    loading,
    error,
    refetch: fetchBreakingNews,
    lastUpdated,
  };
}

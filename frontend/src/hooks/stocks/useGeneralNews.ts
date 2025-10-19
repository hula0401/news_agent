/**
 * useGeneralNews Hook
 * Fetches and manages general economic/market news
 */

import { useState, useEffect, useCallback } from 'react';
import { newsService } from '../../services/news-service';
import type { EconomicNewsItem } from '../../mocks/news-data';
import { logger } from '../../utils/logger';

interface UseGeneralNewsResult {
  news: EconomicNewsItem[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch and manage general economic news
 */
export function useGeneralNews(limit: number = 3): UseGeneralNewsResult {
  const [news, setNews] = useState<EconomicNewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchNews = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      logger.info('useGeneralNews', `Fetching ${limit} general news articles`);

      const articles = await newsService.getGeneralNews(limit);
      setNews(articles);

      logger.info('useGeneralNews', `Fetched ${articles.length} general news articles`);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch general news');
      setError(error);
      logger.error('useGeneralNews', 'Error fetching general news', error);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  // Initial fetch
  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  // Auto-refresh every 10 minutes
  useEffect(() => {
    const intervalId = setInterval(() => {
      logger.info('useGeneralNews', 'Auto-refreshing general news');
      fetchNews();
    }, 600000); // 10 minutes

    return () => clearInterval(intervalId);
  }, [fetchNews]);

  return {
    news,
    loading,
    error,
    refetch: fetchNews,
  };
}

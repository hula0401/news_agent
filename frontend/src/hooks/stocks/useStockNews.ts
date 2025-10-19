/**
 * useStockNews Hook
 * Fetches and manages news for a specific stock
 */

import { useState, useEffect, useCallback } from 'react';
import { newsService } from '../../services/news-service';
import type { StockNewsItem } from '../../mocks/news-data';
import { logger } from '../../utils/logger';

interface UseStockNewsResult {
  news: StockNewsItem[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * Hook to fetch and manage news for a specific stock
 */
export function useStockNews(symbol: string, limit: number = 5): UseStockNewsResult {
  const [news, setNews] = useState<StockNewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchNews = useCallback(async () => {
    if (!symbol) {
      setNews([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      logger.info('useStockNews', `Fetching ${limit} news articles for ${symbol}`);

      const articles = await newsService.getStockNews(symbol, limit);
      setNews(articles);

      logger.info('useStockNews', `Fetched ${articles.length} news articles for ${symbol}`);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch news');
      setError(error);
      logger.error('useStockNews', `Error fetching news for ${symbol}`, error);
    } finally {
      setLoading(false);
    }
  }, [symbol, limit]);

  // Initial fetch
  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  // Auto-refresh every 15 minutes (news cache TTL)
  useEffect(() => {
    const intervalId = setInterval(() => {
      logger.info('useStockNews', `Auto-refreshing news for ${symbol}`);
      fetchNews();
    }, 900000); // 15 minutes

    return () => clearInterval(intervalId);
  }, [symbol, fetchNews]);

  return {
    news,
    loading,
    error,
    refetch: fetchNews,
  };
}

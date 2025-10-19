/**
 * useWatchlistPrices Hook
 * Fetches and manages stock prices for user's watchlist
 */

import { useState, useEffect, useCallback } from 'react';
import { stockPriceService } from '../../services/stock-price-service';
import type { StockPrice } from '../../mocks/stock-data';
import { logger } from '../../utils/logger';

export interface WatchlistPriceItem extends StockPrice {
  symbol: string;
  name?: string;
}

interface UseWatchlistPricesResult {
  prices: WatchlistPriceItem[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
  isMarketOpen: boolean;
}

/**
 * Hook to fetch and manage watchlist stock prices
 */
export function useWatchlistPrices(symbols: string[]): UseWatchlistPricesResult {
  const [prices, setPrices] = useState<WatchlistPriceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isMarketOpen, setIsMarketOpen] = useState(false);

  const fetchPrices = useCallback(async () => {
    if (symbols.length === 0) {
      setPrices([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      logger.info('useWatchlistPrices', `Fetching prices for ${symbols.length} symbols`);

      // Fetch batch prices
      const response = await stockPriceService.getBatchPrices(symbols);

      setPrices(response.prices);
      setIsMarketOpen(stockPriceService.isMarketOpen());

      logger.info('useWatchlistPrices', `Fetched ${response.prices.length} prices`, {
        cache_hits: response.cache_hits,
        cache_misses: response.cache_misses,
      });
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch prices');
      setError(error);
      logger.error('useWatchlistPrices', 'Error fetching prices', error);
    } finally {
      setLoading(false);
    }
  }, [symbols]);

  // Initial fetch
  useEffect(() => {
    fetchPrices();
  }, [fetchPrices]);

  // Auto-refresh every 60 seconds if market is open, 5 minutes otherwise
  useEffect(() => {
    const intervalMs = isMarketOpen ? 60000 : 300000; // 1 min or 5 min

    const intervalId = setInterval(() => {
      logger.info('useWatchlistPrices', `Auto-refreshing prices (market ${isMarketOpen ? 'open' : 'closed'})`);
      fetchPrices();
    }, intervalMs);

    return () => clearInterval(intervalId);
  }, [isMarketOpen, fetchPrices]);

  return {
    prices,
    loading,
    error,
    refetch: fetchPrices,
    isMarketOpen,
  };
}

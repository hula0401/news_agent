/**
 * Stock Price Service
 * Handles fetching stock prices from backend API
 * NO MOCK DATA - All prices must come from real backend
 */

import { api } from '../utils/api-client';
import type { StockPrice, BatchPriceResponse } from '../mocks/stock-data';
import { logger } from '../utils/logger';

export class StockPriceService {
  /**
   * Get price for a single stock
   * Throws error if backend is unavailable - no mock fallback
   */
  async getPrice(symbol: string, refresh: boolean = false): Promise<StockPrice> {
    logger.info('stock-service', `Fetching price for ${symbol} from API`);
    const params: Record<string, string> = {};
    if (refresh) params.refresh = 'true';

    const response = await api.get<StockPrice>(`/api/v1/stocks/${symbol}/price`, params);
    return response;
  }

  /**
   * Get prices for multiple stocks in a batch request
   * Throws error if backend is unavailable - no mock fallback
   */
  async getBatchPrices(symbols: string[], refresh: boolean = false): Promise<BatchPriceResponse> {
    logger.info('stock-service', `Fetching batch prices for ${symbols.length} symbols from API`);
    const response = await api.post<BatchPriceResponse>('/api/v1/stocks/prices/batch', {
      symbols,
      refresh,
    });
    return response;
  }

  /**
   * Subscribe to real-time price updates (WebSocket)
   * Returns unsubscribe function
   */
  subscribeToPrice(
    symbol: string,
    callback: (price: StockPrice) => void,
    intervalMs: number = 5000
  ): () => void {
    logger.info('stock-service', `Subscribing to price updates for ${symbol}`);

    // Use polling for mock data
    const intervalId = setInterval(async () => {
      try {
        const price = await this.getPrice(symbol);
        callback(price);
      } catch (error) {
        logger.error('stock-service', `Error in price subscription for ${symbol}`, error);
      }
    }, intervalMs);

    // Return unsubscribe function
    return () => {
      logger.info('stock-service', `Unsubscribing from price updates for ${symbol}`);
      clearInterval(intervalId);
    };
  }

  /**
   * Check if market is currently open (US market hours)
   */
  isMarketOpen(): boolean {
    const now = new Date();
    const day = now.getDay();
    const hours = now.getHours();
    const minutes = now.getMinutes();

    // Weekend
    if (day === 0 || day === 6) return false;

    // Convert to minutes since midnight
    const currentMinutes = hours * 60 + minutes;

    // US market hours: 9:30 AM - 4:00 PM ET (in user's local time, this is simplified)
    const marketOpen = 9 * 60 + 30; // 9:30 AM
    const marketClose = 16 * 60; // 4:00 PM

    return currentMinutes >= marketOpen && currentMinutes <= marketClose;
  }
}

// Singleton instance
export const stockPriceService = new StockPriceService();

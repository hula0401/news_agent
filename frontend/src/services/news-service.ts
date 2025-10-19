/**
 * News Service
 * Handles fetching news from backend API
 * Falls back to mock data when backend is unavailable
 */

import { api } from '../utils/api-client';
import {
  generateStockNews,
  generateGeneralNews,
  type StockNewsItem,
  type EconomicNewsItem,
} from '../mocks/news-data';
import { logger } from '../utils/logger';

const USE_MOCK_DATA = false; // Use real backend API

export class NewsService {
  /**
   * Get latest news for a specific stock
   * Endpoint: GET /api/v1/stock-news/{symbol}/news?limit=5
   */
  async getStockNews(symbol: string, limit: number = 5): Promise<StockNewsItem[]> {
    if (USE_MOCK_DATA) {
      logger.info('news-service', `Getting mock news for ${symbol}`);
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, Math.random() * 300 + 150));
      return generateStockNews(symbol, limit);
    }

    try {
      logger.info('news-service', `Fetching news for ${symbol} from API`);
      const response = await api.get<{ symbol: string; news: StockNewsItem[]; total_count: number; cache_hit: boolean }>(
        `/api/v1/stock-news/${symbol}/news`,
        { limit: limit.toString(), refresh: 'false' }
      );
      return response.news;
    } catch (error) {
      logger.error('news-service', `Failed to fetch news for ${symbol}, using mock data`, error);
      return generateStockNews(symbol, limit);
    }
  }

  /**
   * Get general/latest economic news
   * Endpoint: GET /api/news/latest?topics=finance,economy&limit=10
   */
  async getGeneralNews(limit: number = 3): Promise<EconomicNewsItem[]> {
    if (USE_MOCK_DATA) {
      logger.info('news-service', `Getting mock general news (${limit} articles)`);
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, Math.random() * 250 + 100));
      return generateGeneralNews(limit);
    }

    try {
      logger.info('news-service', `Fetching general economic news from API`);
      const response = await api.get<{ articles: EconomicNewsItem[]; total_count: number }>(
        '/api/news/latest',
        { topics: 'finance,economy,markets', limit: limit.toString() }
      );
      return response.articles || [];
    } catch (error) {
      logger.error('news-service', `Failed to fetch general news, using mock data`, error);
      return generateGeneralNews(limit);
    }
  }

  /**
   * Get news for multiple stocks
   */
  async getBatchStockNews(
    symbols: string[],
    limitPerStock: number = 5
  ): Promise<Record<string, StockNewsItem[]>> {
    if (USE_MOCK_DATA) {
      logger.info('news-service', `Getting mock batch news for ${symbols.length} symbols`);
      await new Promise(resolve => setTimeout(resolve, Math.random() * 400 + 200));

      const result: Record<string, StockNewsItem[]> = {};
      symbols.forEach(symbol => {
        result[symbol] = generateStockNews(symbol, limitPerStock);
      });
      return result;
    }

    try {
      logger.info('news-service', `Fetching batch news for ${symbols.length} symbols`);
      const promises = symbols.map(async symbol => ({
        symbol,
        news: await this.getStockNews(symbol, limitPerStock),
      }));

      const results = await Promise.all(promises);
      const newsMap: Record<string, StockNewsItem[]> = {};

      results.forEach(({ symbol, news }) => {
        newsMap[symbol] = news;
      });

      return newsMap;
    } catch (error) {
      logger.error('news-service', `Failed to fetch batch news, using mock data`, error);
      const result: Record<string, StockNewsItem[]> = {};
      symbols.forEach(symbol => {
        result[symbol] = generateStockNews(symbol, limitPerStock);
      });
      return result;
    }
  }

  /**
   * Get breaking news (high urgency)
   * Endpoint: GET /api/news/breaking
   */
  async getBreakingNews(limit: number = 5): Promise<EconomicNewsItem[]> {
    if (USE_MOCK_DATA) {
      logger.info('news-service', `Getting mock breaking news`);
      await new Promise(resolve => setTimeout(resolve, 150));
      const allNews = generateGeneralNews(limit * 2);
      return allNews.filter(n => n.is_breaking).slice(0, limit);
    }

    try {
      logger.info('news-service', `Fetching breaking news from API`);
      const response = await api.get<{ articles: EconomicNewsItem[]; total_count: number }>(
        '/api/news/breaking'
      );
      return response.articles || [];
    } catch (error) {
      logger.error('news-service', `Failed to fetch breaking news, using mock data`, error);
      const allNews = generateGeneralNews(limit * 2);
      return allNews.filter(n => n.is_breaking).slice(0, limit);
    }
  }
}

// Singleton instance
export const newsService = new NewsService();

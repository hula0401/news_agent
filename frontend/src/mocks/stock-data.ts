/**
 * Mock Stock Price Data Generator
 * Based on API design from STOCK_NEWS_API_DESIGN.md
 */

export interface StockPrice {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  market_cap: number;
  high_52_week: number;
  low_52_week: number;
  last_updated: string;
  cache_hit: boolean;
}

export interface BatchPriceResponse {
  prices: StockPrice[];
  total_count: number;
  cache_hits: number;
  cache_misses: number;
  processing_time_ms: number;
}

// Base prices for realistic simulation
const BASE_PRICES: Record<string, { price: number; name: string }> = {
  AAPL: { price: 175.43, name: 'Apple Inc.' },
  GOOGL: { price: 140.25, name: 'Alphabet Inc.' },
  MSFT: { price: 378.91, name: 'Microsoft Corporation' },
  TSLA: { price: 242.84, name: 'Tesla, Inc.' },
  AMZN: { price: 145.32, name: 'Amazon.com Inc.' },
  NVDA: { price: 495.22, name: 'NVIDIA Corporation' },
  META: { price: 326.48, name: 'Meta Platforms Inc.' },
  NFLX: { price: 485.73, name: 'Netflix Inc.' },
  AMD: { price: 118.47, name: 'Advanced Micro Devices' },
  INTC: { price: 43.61, name: 'Intel Corporation' },
};

/**
 * Generate realistic stock price with small random fluctuation
 */
export function generateStockPrice(symbol: string): StockPrice {
  const baseInfo = BASE_PRICES[symbol] || { price: 100, name: 'Unknown' };
  const basePrice = baseInfo.price;

  // Random price fluctuation (-3% to +3%)
  const fluctuation = (Math.random() - 0.5) * 0.06;
  const currentPrice = basePrice * (1 + fluctuation);
  const change = currentPrice - basePrice;
  const changePercent = (change / basePrice) * 100;

  return {
    symbol,
    price: parseFloat(currentPrice.toFixed(2)),
    change: parseFloat(change.toFixed(2)),
    change_percent: parseFloat(changePercent.toFixed(2)),
    volume: Math.floor(Math.random() * 50000000) + 10000000,
    market_cap: Math.floor(basePrice * 1000000000 * (Math.random() * 5 + 8)),
    high_52_week: parseFloat((basePrice * 1.25).toFixed(2)),
    low_52_week: parseFloat((basePrice * 0.75).toFixed(2)),
    last_updated: new Date().toISOString(),
    cache_hit: Math.random() > 0.3, // 70% cache hit rate
  };
}

/**
 * Generate batch stock prices
 */
export function generateBatchPrices(symbols: string[]): BatchPriceResponse {
  const prices = symbols.map(symbol => generateStockPrice(symbol));
  const cacheHits = prices.filter(p => p.cache_hit).length;

  return {
    prices,
    total_count: prices.length,
    cache_hits: cacheHits,
    cache_misses: prices.length - cacheHits,
    processing_time_ms: Math.floor(Math.random() * 200) + 50,
  };
}

/**
 * Get stock name from symbol
 */
export function getStockName(symbol: string): string {
  return BASE_PRICES[symbol]?.name || symbol;
}

/**
 * Simulate real-time price updates
 */
export function* priceUpdateGenerator(symbol: string) {
  while (true) {
    yield generateStockPrice(symbol);
  }
}
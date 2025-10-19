/**
 * Mock News Data Generator
 * Based on API design from STOCK_NEWS_API_DESIGN.md
 */

export interface NewsSource {
  id: string;
  name: string;
  reliability_score: number;
}

export interface StockNewsItem {
  id: string;
  title: string;
  summary: string;
  url: string;
  published_at: string;
  source: NewsSource;
  sentiment_score: number;
  topics: string[];
  is_breaking: boolean;
  position_in_stack?: number;
}

export interface EconomicNewsItem {
  id: string;
  title: string;
  summary: string;
  url: string;
  published_at: string;
  source: NewsSource;
  category: 'federal_reserve' | 'politics' | 'economics' | 'inflation' | 'employment';
  sentiment_score: number;
  topics: string[];
  is_breaking: boolean;
  impact_level: 'low' | 'medium' | 'high';
  related_symbols?: string[];
}

const NEWS_SOURCES: NewsSource[] = [
  { id: 'reuters', name: 'Reuters', reliability_score: 0.95 },
  { id: 'bloomberg', name: 'Bloomberg', reliability_score: 0.98 },
  { id: 'wsj', name: 'Wall Street Journal', reliability_score: 0.94 },
  { id: 'cnbc', name: 'CNBC', reliability_score: 0.85 },
  { id: 'techcrunch', name: 'TechCrunch', reliability_score: 0.87 },
  { id: 'marketwatch', name: 'MarketWatch', reliability_score: 0.82 },
  { id: 'fed', name: 'Federal Reserve', reliability_score: 1.0 },
];

// Template news for different stocks
const STOCK_NEWS_TEMPLATES: Record<string, { topics: string[]; templates: string[] }> = {
  AAPL: {
    topics: ['technology', 'ai', 'mobile', 'earnings'],
    templates: [
      'Apple Announces New AI Features in iOS Update',
      'Apple Reports Strong Quarterly Earnings, Beats Expectations',
      'Apple Expands Services Revenue with New Subscription Offerings',
      'Apple Vision Pro Gains Traction in Enterprise Market',
      'Apple Invests Heavily in AI Research and Development',
    ],
  },
  GOOGL: {
    topics: ['technology', 'ai', 'cloud', 'advertising'],
    templates: [
      'Google Cloud Revenue Surges on AI Demand',
      'Alphabet Announces Breakthrough in Quantum Computing',
      'Google Faces Regulatory Challenges in EU Markets',
      'Alphabet\'s AI Investments Show Strong Returns',
      'Google Expands Gemini AI to More Products',
    ],
  },
  MSFT: {
    topics: ['technology', 'cloud', 'ai', 'enterprise'],
    templates: [
      'Microsoft Azure Gains Market Share in Cloud Computing',
      'Microsoft Reports Record Revenue from AI Services',
      'Microsoft Expands Copilot AI Across Enterprise Suite',
      'Microsoft Partners with Major Enterprises for Cloud Migration',
      'Microsoft\'s Gaming Division Shows Strong Growth',
    ],
  },
  TSLA: {
    topics: ['automotive', 'ev', 'energy', 'technology'],
    templates: [
      'Tesla Deliveries Exceed Analyst Expectations',
      'Tesla Expands Charging Network Across North America',
      'Tesla Full Self-Driving Beta Reaches New Milestone',
      'Tesla Energy Storage Business Shows Rapid Growth',
      'Tesla Announces New Gigafactory Location',
    ],
  },
  NVDA: {
    topics: ['technology', 'ai', 'semiconductors', 'gaming'],
    templates: [
      'NVIDIA AI Chip Demand Remains Strong Amid Supply Constraints',
      'NVIDIA Announces Next-Generation GPU Architecture',
      'NVIDIA Partners with Cloud Providers for AI Infrastructure',
      'NVIDIA Gaming Revenue Stabilizes After Crypto Decline',
      'NVIDIA Data Center Revenue Reaches New Heights',
    ],
  },
};

const GENERAL_NEWS_TEMPLATES = [
  {
    title: 'Fed Holds Interest Rates Steady, Signals Cautious Approach',
    category: 'federal_reserve' as const,
    impact_level: 'high' as const,
    topics: ['monetary_policy', 'interest_rates'],
    related_symbols: ['SPY', 'DIA', 'QQQ'],
    is_breaking: true,
  },
  {
    title: 'U.S. Job Market Remains Resilient with Strong Hiring Numbers',
    category: 'employment' as const,
    impact_level: 'high' as const,
    topics: ['employment', 'economy'],
    related_symbols: ['SPY', 'XLF'],
    is_breaking: false,
  },
  {
    title: 'Inflation Moderates as Core CPI Comes in Below Expectations',
    category: 'inflation' as const,
    impact_level: 'high' as const,
    topics: ['inflation', 'economy'],
    related_symbols: ['TLT', 'GLD'],
    is_breaking: false,
  },
  {
    title: 'Congress Passes Bipartisan Infrastructure Funding Bill',
    category: 'politics' as const,
    impact_level: 'medium' as const,
    topics: ['politics', 'infrastructure'],
    related_symbols: ['CAT', 'DE', 'XLI'],
    is_breaking: false,
  },
  {
    title: 'Tech Sector Leads Market Rally on AI Optimism',
    category: 'economics' as const,
    impact_level: 'medium' as const,
    topics: ['technology', 'markets'],
    related_symbols: ['QQQ', 'XLK'],
    is_breaking: false,
  },
  {
    title: 'Global Supply Chains Show Signs of Improvement',
    category: 'economics' as const,
    impact_level: 'low' as const,
    topics: ['trade', 'economy'],
    related_symbols: ['FDX', 'UPS'],
    is_breaking: false,
  },
];

/**
 * Generate random news ID
 */
function generateNewsId(): string {
  return `news_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Generate random date in the past 24 hours
 */
function generateRecentDate(hoursAgo: number = 24): string {
  const now = new Date();
  const randomHours = Math.random() * hoursAgo;
  const date = new Date(now.getTime() - randomHours * 60 * 60 * 1000);
  return date.toISOString();
}

/**
 * Generate stock-specific news
 */
export function generateStockNews(symbol: string, count: number = 5): StockNewsItem[] {
  const config = STOCK_NEWS_TEMPLATES[symbol] || {
    topics: ['general', 'markets'],
    templates: [
      `${symbol} Reports Quarterly Earnings`,
      `${symbol} Stock Price Moves on Market News`,
      `Analysts Update Price Target for ${symbol}`,
      `${symbol} Announces Strategic Partnership`,
      `${symbol} Faces Regulatory Scrutiny`,
    ],
  };

  return Array.from({ length: count }, (_, index) => {
    const source = NEWS_SOURCES[Math.floor(Math.random() * 5)]; // Use first 5 sources
    const template = config.templates[index % config.templates.length];

    return {
      id: generateNewsId(),
      title: template,
      summary: `${template.substring(0, 50)}... This article discusses the latest developments regarding ${symbol} and its impact on the market. ${
        Math.random() > 0.5 ? 'Analysts remain optimistic about future prospects.' : 'Market reactions have been mixed.'
      }`,
      url: `https://example.com/news/${symbol.toLowerCase()}-${index + 1}`,
      published_at: generateRecentDate(index * 3), // Spread over time
      source,
      sentiment_score: parseFloat((Math.random() * 1.5 - 0.5).toFixed(2)), // -0.5 to 1.0
      topics: config.topics,
      is_breaking: index === 0 && Math.random() > 0.7, // First news has 30% chance of being breaking
      position_in_stack: index + 1,
    };
  });
}

/**
 * Generate general economic news
 */
export function generateGeneralNews(count: number = 3): EconomicNewsItem[] {
  return Array.from({ length: count }, (_, index) => {
    const template = GENERAL_NEWS_TEMPLATES[index % GENERAL_NEWS_TEMPLATES.length];
    const source = template.category === 'federal_reserve'
      ? NEWS_SOURCES.find(s => s.id === 'fed')!
      : NEWS_SOURCES[Math.floor(Math.random() * 6)];

    return {
      id: generateNewsId(),
      title: template.title,
      summary: `${template.title}. Economists and market analysts weigh in on the implications for investors and the broader economy. ${
        template.impact_level === 'high'
          ? 'This development is expected to have significant market impact.'
          : 'Market impact is expected to be moderate.'
      }`,
      url: `https://example.com/news/economic-${index + 1}`,
      published_at: generateRecentDate(index * 2),
      source,
      category: template.category,
      sentiment_score: parseFloat((Math.random() * 0.6 - 0.3).toFixed(2)), // -0.3 to 0.3 (neutral)
      topics: template.topics,
      is_breaking: template.is_breaking && index === 0,
      impact_level: template.impact_level,
      related_symbols: template.related_symbols,
    };
  });
}

/**
 * Generate news for multiple watchlist stocks
 */
export function generateWatchlistNews(symbols: string[], newsPerStock: number = 5): Record<string, StockNewsItem[]> {
  const result: Record<string, StockNewsItem[]> = {};

  symbols.forEach(symbol => {
    result[symbol] = generateStockNews(symbol, newsPerStock);
  });

  return result;
}

/**
 * Format time ago (e.g., "2 hours ago")
 */
export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
}
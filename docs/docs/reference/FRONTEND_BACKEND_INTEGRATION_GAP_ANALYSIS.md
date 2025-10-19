# Frontend-Backend Integration Gap Analysis

**Date:** 2025-10-17
**Status:** Analysis Complete
**Project:** News Agent - Stock & News API Integration

---

## Executive Summary

This document analyzes the **current frontend UI structure** against the **Stock & News API backend** (as defined in [STOCK_NEWS_FINAL_SUMMARY.md](STOCK_NEWS_FINAL_SUMMARY.md)) to identify integration gaps and required implementation work.

### Current Status
- ✅ **Backend Foundation**: 40% complete (models, cache, database layers ready)
- ⚠️ **Backend API Endpoints**: Missing (Stock & News API v1 endpoints not implemented)
- ⚠️ **Frontend API Integration**: Partial (basic news/user endpoints exist, stock APIs missing)
- ❌ **Frontend UI Components**: Need enhancement (market/stocks/news displays incomplete)

---

## 1. Current Frontend Architecture

### 1.1 Existing Structure

```
frontend/src/
├── components/
│   ├── WatchlistCard.tsx           ✅ Connected to /api/user/watchlist
│   ├── StockWatchlistItem.tsx      ✅ UI component (needs price data)
│   ├── QuickCommands.tsx           ✅ Working
│   └── StatusIndicators.tsx        ✅ Working
├── pages/
│   ├── DashboardPage.tsx           ⚠️ Needs stock/news integration
│   ├── ProfilePage.tsx             ⚠️ Needs user preferences API
│   └── HistoryPage.tsx             ✅ Working
├── lib/
│   ├── auth-context.tsx            ✅ Working
│   └── profile-context.tsx         ⚠️ Needs update for stock watchlist
└── utils/
    └── api-client.ts               ✅ Generic API client ready
```

### 1.2 Existing API Endpoints (Backend)

**Currently Implemented:**
```
✅ GET  /api/user/preferences      - Get user preferences
✅ PUT  /api/user/preferences      - Update preferences
✅ GET  /api/user/watchlist        - Get watchlist symbols
✅ POST /api/user/watchlist/add    - Add stock to watchlist
✅ DEL  /api/user/watchlist/{symbol} - Remove from watchlist
✅ GET  /api/news/latest           - Get latest news (agent-based)
✅ GET  /api/news/search           - Search news
✅ GET  /api/news/breaking         - Get breaking news
```

### 1.3 Frontend Components Using APIs

**[WatchlistCard.tsx](../frontend/src/components/WatchlistCard.tsx:21)**
```typescript
// Currently fetches watchlist symbols only
const res = await fetch(`${API_BASE}/api/user/watchlist?user_id=${userId}`);
// Returns: { watchlist_stocks: ["AAPL", "GOOGL", ...] }
```

**Gap**: No stock price data, no change data, no market cap info

**[DashboardPage.tsx](../frontend/src/pages/DashboardPage.tsx:139)**
```typescript
// Static mock data for "Today's Summary"
<div className="space-y-3">
  <div>Conversations: 12</div>
  <div>Duration: 45 min</div>
  <div>News Briefings: 8</div>  // No real data source
</div>
```

**Gap**: No connection to actual conversation stats or news briefing data

---

## 2. Required Backend API Endpoints (Not Yet Implemented)

Based on [STOCK_NEWS_API_DESIGN.md](docs/reference/STOCK_NEWS_API_DESIGN.md), these endpoints are **designed but not implemented**:

### 2.1 Stock Price APIs ❌

```http
❌ GET  /api/v1/stocks/{symbol}/price
   Response: { symbol, price, change, change_percent, volume, market_cap, ... }

❌ POST /api/v1/stocks/prices/batch
   Request: { symbols: ["AAPL", "GOOGL", ...] }
   Response: { prices: [...], cache_hits, cache_misses, ... }
```

**Backend Status**:
- ✅ Models ready: [backend/app/models/stock.py](../backend/app/models/stock.py)
- ✅ Database layer ready: [backend/app/db/stock_prices.py](../backend/app/db/stock_prices.py)
- ❌ Service layer: Not implemented
- ❌ API endpoints: Not implemented
- ❌ External API clients (Finnhub, Polygon): Not implemented

### 2.2 Stock News APIs ❌

```http
❌ GET  /api/v1/stocks/{symbol}/news
   Response: { news: [5 latest articles with stack positions] }

❌ POST /api/v1/stocks/{symbol}/news
   Request: { title, summary, url, source_id, ... }
   Response: { id, position_in_stack, archived_article_id }
```

**Backend Status**:
- ✅ Models ready: [backend/app/models/stock.py](../backend/app/models/stock.py)
- ✅ Database layer ready: [backend/app/db/stock_news.py](../backend/app/db/stock_news.py)
- ❌ Service layer: Not implemented
- ❌ API endpoints: Not implemented
- ❌ News aggregator: Not implemented

### 2.3 Economic News APIs ❌

```http
❌ GET /api/v1/news/economic
   Query: ?limit=10&categories=federal_reserve,politics&breaking_only=true

❌ GET /api/v1/news/federal-reserve
   Response: { announcements: [FOMC statements, speeches, ...] }

❌ GET /api/v1/news/politics
   Response: { articles: [political news affecting markets] }
```

**Backend Status**:
- ✅ Models ready: [backend/app/models/news.py](../backend/app/models/news.py)
- ✅ Database layer ready: [backend/app/db/economic_news.py](../backend/app/db/economic_news.py)
- ❌ Service layer: Not implemented
- ❌ API endpoints: Not implemented
- ❌ RSS feed clients: Not implemented

### 2.4 Dashboard/Market Overview API ❌

```http
❌ GET /api/v1/dashboard
   Response: {
     market_overview: { major_indices, ... },
     trending_stocks: [...],
     breaking_news: [...],
     user_watchlist: [...],
     economic_calendar: [...]
   }
```

**Backend Status**: Not designed or implemented

---

## 3. Frontend Component Gaps

### 3.1 WatchlistCard Component

**Current Implementation:**
- ✅ Fetches watchlist symbols from `/api/user/watchlist`
- ✅ Displays symbols as plain text list

**Missing Features:**
```typescript
// Need to fetch stock prices for each symbol
❌ Real-time price data
❌ Price change (+/-) indicators
❌ Percentage change
❌ Color coding (green/red)
❌ Refresh mechanism
❌ Loading states
❌ Error handling
```

**Required API Integration:**
```typescript
// 1. Fetch watchlist symbols (already working)
const symbols = await api.get('/api/user/watchlist', { user_id });

// 2. Fetch stock prices (NEW - requires implementation)
const prices = await api.post('/api/v1/stocks/prices/batch', {
  symbols: symbols.watchlist_stocks
});

// 3. Merge and display
const enrichedWatchlist = symbols.map(symbol => {
  const priceData = prices.prices.find(p => p.symbol === symbol);
  return { symbol, ...priceData };
});
```

### 3.2 DashboardPage Component

**Current Implementation:**
- ✅ Voice interface working
- ✅ Connection status indicators
- ✅ Static "Today's Summary" section
- ✅ Static "Recent Activity" section

**Missing Features:**

#### Market Overview Section (NEW)
```typescript
❌ Major indices (S&P 500, NASDAQ, DOW)
❌ Market sentiment indicator
❌ Top gainers/losers
❌ Volume leaders
```

#### Trending Stocks Section (NEW)
```typescript
❌ Most active stocks
❌ Biggest movers
❌ News-driven stocks
```

#### Breaking News Feed (NEW)
```typescript
❌ Real-time breaking news cards
❌ Category filtering (Fed, Politics, Economics)
❌ Impact level indicators
❌ Related symbols tags
```

#### Enhanced Watchlist (UPDATE)
```typescript
❌ Live price updates
❌ Price charts (sparklines)
❌ Alert indicators
❌ News count badges
```

### 3.3 StockWatchlistItem Component

**Current Implementation:**
- ✅ Displays symbol, name, price, change
- ✅ Color-coded change indicators
- ✅ Remove button

**Missing Features:**
```typescript
❌ Click to view stock details
❌ Quick actions menu (buy/sell/alert)
❌ Mini price chart
❌ News badge (unread count)
❌ Market hours indicator
```

### 3.4 News Components (NOT YET CREATED)

**Required New Components:**

#### NewsCard.tsx ❌
```typescript
interface NewsCardProps {
  id: string;
  title: string;
  summary: string;
  source: { name: string; reliability_score: number };
  published_at: string;
  sentiment_score: number;
  is_breaking: boolean;
  impact_level?: 'low' | 'medium' | 'high';
  related_symbols?: string[];
}
```

#### NewsFeed.tsx ❌
```typescript
// Displays list of news cards with filtering
interface NewsFeedProps {
  category?: 'all' | 'federal_reserve' | 'politics' | 'economics';
  breakingOnly?: boolean;
  limit?: number;
}
```

#### StockNewsList.tsx ❌
```typescript
// Stock-specific news with stack positions
interface StockNewsListProps {
  symbol: string;
  showArchived?: boolean;
}
```

### 3.5 Market Components (NOT YET CREATED)

#### MarketOverview.tsx ❌
```typescript
// Major indices + market sentiment
interface MarketOverviewProps {
  showExtended?: boolean;  // Show extended hours data
}
```

#### TrendingStocks.tsx ❌
```typescript
// Top movers, volume leaders
interface TrendingStocksProps {
  category: 'gainers' | 'losers' | 'active' | 'news-driven';
  limit?: number;
}
```

---

## 4. Frontend Services/Hooks Needed

### 4.1 Stock Price Service ❌

**File:** `frontend/src/services/stock-price-service.ts` (not created)

```typescript
export class StockPriceService {
  async getPrice(symbol: string): Promise<StockPrice>
  async getBatchPrices(symbols: string[]): Promise<BatchPriceResponse>
  async subscribeToPrice(symbol: string, callback: (price: StockPrice) => void)
  async unsubscribe(symbol: string)
}
```

**Features:**
- Fetch single/batch stock prices
- WebSocket subscription for real-time updates
- Local caching with TTL
- Auto-refresh during market hours

### 4.2 Stock News Service ❌

**File:** `frontend/src/services/stock-news-service.ts` (not created)

```typescript
export class StockNewsService {
  async getStockNews(symbol: string, limit?: number): Promise<StockNewsResponse>
  async getArchivedNews(symbol: string): Promise<ArchivedNewsResponse>
  async subscribeToNews(symbol: string, callback: (news: StockNewsItem) => void)
}
```

### 4.3 Economic News Service ❌

**File:** `frontend/src/services/economic-news-service.ts` (not created)

```typescript
export class EconomicNewsService {
  async getEconomicNews(filters: EconomicNewsFilters): Promise<EconomicNewsResponse>
  async getFederalReserveNews(): Promise<FederalReserveNewsResponse>
  async getPoliticsNews(): Promise<PoliticsNewsResponse>
  async getBreakingNews(): Promise<BreakingNewsResponse>
}
```

### 4.4 Custom React Hooks ❌

#### useStockPrice.ts
```typescript
function useStockPrice(symbol: string, realtime?: boolean) {
  const [price, setPrice] = useState<StockPrice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Auto-fetch and subscribe if realtime=true
  useEffect(() => { /* ... */ }, [symbol, realtime]);

  return { price, loading, error, refetch };
}
```

#### useWatchlistPrices.ts
```typescript
function useWatchlistPrices(userId: string) {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);

  // Fetch symbols + batch prices
  useEffect(() => { /* ... */ }, [userId]);

  return { watchlist, loading, error, refetch };
}
```

#### useStockNews.ts
```typescript
function useStockNews(symbol: string, limit?: number) {
  const [news, setNews] = useState<StockNewsItem[]>([]);

  // Fetch news stack
  useEffect(() => { /* ... */ }, [symbol, limit]);

  return { news, loading, error, refetch };
}
```

#### useEconomicNews.ts
```typescript
function useEconomicNews(filters: EconomicNewsFilters) {
  const [news, setNews] = useState<EconomicNewsItem[]>([]);

  // Fetch filtered economic news
  useEffect(() => { /* ... */ }, [filters]);

  return { news, loading, error, refetch };
}
```

---

## 5. Implementation Gaps Summary

### 5.1 Backend Gaps

| Component | Status | Progress | Blocker |
|-----------|--------|----------|---------|
| Stock Price API Endpoints | ❌ Not Started | 0% | Service layer missing |
| Stock News API Endpoints | ❌ Not Started | 0% | Service layer missing |
| Economic News API Endpoints | ❌ Not Started | 0% | Service layer missing |
| Dashboard API Endpoint | ❌ Not Designed | 0% | Design spec needed |
| External API Clients | ❌ Not Started | 0% | API keys needed |
| Service Layer | ❌ Not Started | 0% | Critical blocker |

**Critical Path for Backend:**
1. Implement Service Layer (Week 2 - see [STOCK_NEWS_IMPLEMENTATION_CHECKLIST.md](STOCK_NEWS_IMPLEMENTATION_CHECKLIST.md))
2. Implement External API Clients (Finnhub, Polygon, NewsAPI)
3. Implement API Endpoints (v1 routes)
4. Write tests

**Estimated Timeline:** 2-3 weeks (based on 4-week plan at 40% complete)

### 5.2 Frontend Gaps

| Component | Status | Progress | Blocker |
|-----------|--------|----------|---------|
| Stock Price Services | ❌ Not Created | 0% | Backend APIs missing |
| Stock News Services | ❌ Not Created | 0% | Backend APIs missing |
| Economic News Services | ❌ Not Created | 0% | Backend APIs missing |
| Custom Hooks | ❌ Not Created | 0% | Services missing |
| NewsCard Component | ❌ Not Created | 0% | Services missing |
| NewsFeed Component | ❌ Not Created | 0% | Services missing |
| MarketOverview Component | ❌ Not Created | 0% | Backend APIs missing |
| TrendingStocks Component | ❌ Not Created | 0% | Backend APIs missing |
| Enhanced WatchlistCard | ⚠️ Partial | 30% | Price data missing |
| Enhanced DashboardPage | ⚠️ Partial | 40% | All above missing |

**Critical Path for Frontend:**
1. Wait for backend Service Layer + API Endpoints
2. Create API client services (stock, news)
3. Create custom React hooks
4. Create new UI components (NewsCard, MarketOverview, etc.)
5. Update existing components (WatchlistCard, DashboardPage)

**Estimated Timeline:** 1-2 weeks after backend is ready

---

## 6. Can We Implement Now? (Gap Analysis)

### 6.1 What Can Be Done Now ✅

**Without Backend APIs:**
1. **Create UI Component Skeletons**
   - Build `NewsCard.tsx` with mock data
   - Build `NewsFeed.tsx` with mock data
   - Build `MarketOverview.tsx` with mock data
   - Build `TrendingStocks.tsx` with mock data

2. **Create Service Layer Interfaces**
   - Define TypeScript interfaces for all services
   - Create service classes with mock implementations
   - Set up error handling patterns

3. **Create Custom Hooks**
   - Build hooks that return mock data
   - Implement loading/error states
   - Add refresh/retry logic

4. **Update Existing Components**
   - Add loading states to WatchlistCard
   - Add error boundaries
   - Improve UI/UX with skeletons

5. **Set Up Frontend Infrastructure**
   - Configure API base URL
   - Set up request/response interceptors
   - Add error toast notifications
   - Implement caching strategy

**Benefits:**
- Frontend development can proceed in parallel
- UI/UX can be refined early
- Integration will be faster once backend is ready
- Easy to swap mock data with real APIs

### 6.2 What Cannot Be Done ❌

**Hard Blockers (Backend Required):**
1. **Real Stock Price Data**
   - Requires `/api/v1/stocks/{symbol}/price` endpoint
   - Requires external API integrations (Finnhub/Polygon)
   - Requires LFU cache implementation

2. **Real Stock News**
   - Requires `/api/v1/stocks/{symbol}/news` endpoint
   - Requires news aggregator service
   - Requires LIFO stack implementation

3. **Real Economic News**
   - Requires `/api/v1/news/economic` endpoints
   - Requires RSS feed parsing
   - Requires category classification

4. **Real-Time Updates**
   - Requires WebSocket implementation
   - Requires Redis pub/sub
   - Requires connection management

5. **Cache Optimization**
   - Requires LFU cache statistics
   - Requires hot key tracking
   - Requires eviction policy

### 6.3 Workarounds for Development 🛠️

**Option 1: Mock API Server**
```typescript
// frontend/src/mocks/stock-api-mock.ts
export const mockStockPriceAPI = {
  async getPrice(symbol: string) {
    return {
      symbol,
      price: Math.random() * 500 + 100,
      change: Math.random() * 10 - 5,
      change_percent: Math.random() * 4 - 2,
      last_updated: new Date().toISOString(),
      cache_hit: false
    };
  }
};
```

**Option 2: Use Existing `/api/news/latest` Endpoint**
```typescript
// Current backend has basic news API
// Can use this for general news display
const news = await api.get('/api/news/latest', {
  limit: 10,
  breaking_only: true
});
```

**Option 3: Direct External API Calls (Client-Side)**
```typescript
// Temporary: Call Finnhub directly from frontend
// WARNING: Exposes API keys! Only for development!
const response = await fetch(
  `https://finnhub.io/api/v1/quote?symbol=${symbol}&token=${DEMO_KEY}`
);
```

**Recommendation:** Use **Option 1 (Mock API)** for now to avoid API key exposure and rate limits.

---

## 7. Recommended Implementation Plan

### Phase 1: Frontend Preparation (Can Start Now)
**Duration:** 1 week
**Dependencies:** None

**Tasks:**
1. Create service interfaces and mock implementations
2. Build custom React hooks with mock data
3. Create new UI components (NewsCard, MarketOverview, etc.)
4. Update existing components with loading/error states
5. Set up API client infrastructure
6. Write component tests with mock data

**Deliverables:**
- ✅ All UI components ready
- ✅ All hooks ready
- ✅ Integration points clearly defined
- ✅ Mock data flows working end-to-end

### Phase 2: Backend Implementation (Critical Path)
**Duration:** 2-3 weeks
**Dependencies:** Database schema applied, API keys obtained

**Tasks:**
1. **Week 1: Service Layer**
   - Stock price service with external APIs
   - Stock news service with LIFO stack
   - Economic news service with RSS parsing
   - News aggregator with deduplication

2. **Week 2: API Endpoints**
   - `/api/v1/stocks/*` routes
   - `/api/v1/news/*` routes
   - `/api/v1/dashboard` route
   - Request validation & error handling

3. **Week 3: Testing & Optimization**
   - Unit tests for services
   - Integration tests for APIs
   - Cache optimization
   - Performance tuning

**Deliverables:**
- ✅ All API endpoints working
- ✅ External APIs integrated
- ✅ Caching optimized
- ✅ Tests passing

### Phase 3: Frontend-Backend Integration
**Duration:** 1 week
**Dependencies:** Phase 2 complete

**Tasks:**
1. Replace mock services with real API calls
2. Test all data flows end-to-end
3. Add error handling for API failures
4. Implement retry logic
5. Add loading skeletons
6. Optimize API call patterns (batching, caching)

**Deliverables:**
- ✅ All components connected to backend
- ✅ Error handling working
- ✅ Performance optimized
- ✅ User experience polished

### Phase 4: Real-Time Features (Optional)
**Duration:** 1 week
**Dependencies:** Phase 3 complete

**Tasks:**
1. WebSocket connection for price updates
2. Redis pub/sub for news notifications
3. Real-time market data streaming
4. Connection management & reconnection logic

**Deliverables:**
- ✅ Real-time price updates
- ✅ Push notifications for breaking news
- ✅ Live market data

---

## 8. Immediate Next Steps

### For Backend Team:
1. **Register for API Keys** (can do now)
   - Finnhub: https://finnhub.io/register
   - Polygon.io: https://polygon.io/
   - NewsAPI: https://newsapi.org/

2. **Apply Database Schema** (can do now)
   ```bash
   psql $DATABASE_URL < database/stock_news_schema.sql
   ```

3. **Configure Redis** (can do now)
   ```
   MAXMEMORY_POLICY=allkeys-lfu
   MAXMEMORY=100mb
   ```

4. **Start Service Layer Implementation** (Week 2)
   - Create `backend/app/services/stock_price_service.py`
   - Create `backend/app/services/stock_news_service.py`
   - Create `backend/app/services/economic_news_service.py`

### For Frontend Team:
1. **Create Service Interfaces** (can do now)
   ```bash
   mkdir -p frontend/src/services
   touch frontend/src/services/stock-price-service.ts
   touch frontend/src/services/stock-news-service.ts
   touch frontend/src/services/economic-news-service.ts
   ```

2. **Create Custom Hooks** (can do now)
   ```bash
   mkdir -p frontend/src/hooks/stocks
   touch frontend/src/hooks/stocks/useStockPrice.ts
   touch frontend/src/hooks/stocks/useWatchlistPrices.ts
   touch frontend/src/hooks/stocks/useStockNews.ts
   ```

3. **Create UI Components** (can do now)
   ```bash
   mkdir -p frontend/src/components/stocks
   mkdir -p frontend/src/components/news
   touch frontend/src/components/news/NewsCard.tsx
   touch frontend/src/components/news/NewsFeed.tsx
   touch frontend/src/components/stocks/MarketOverview.tsx
   ```

4. **Set Up Mock Data** (can do now)
   ```bash
   mkdir -p frontend/src/mocks
   touch frontend/src/mocks/stock-data.ts
   touch frontend/src/mocks/news-data.ts
   ```

---

## 9. Success Criteria

### Backend Success Criteria:
- ✅ All API endpoints return correct data format
- ✅ LFU cache hit rate > 70%
- ✅ API response time < 500ms (p95)
- ✅ External API fallbacks working
- ✅ Rate limiting implemented
- ✅ All tests passing

### Frontend Success Criteria:
- ✅ All components render without errors
- ✅ Loading states smooth and responsive
- ✅ Error handling graceful
- ✅ Data updates in real-time (or near real-time)
- ✅ UI responsive on mobile/desktop
- ✅ Accessibility (WCAG 2.1 AA)

### Integration Success Criteria:
- ✅ Watchlist shows live prices
- ✅ News feeds auto-update
- ✅ Dashboard shows market overview
- ✅ No CORS errors
- ✅ No authentication errors
- ✅ Performance: First Contentful Paint < 1.5s

---

## 10. Risk Assessment

### High Risk 🔴
1. **External API Rate Limits**
   - Finnhub: 60 calls/min (free tier)
   - Polygon: 5 calls/min (free tier)
   - **Mitigation**: Aggressive caching, batching, upgrade to paid tiers

2. **Data Staleness**
   - Stock prices need to be "fresh enough"
   - **Mitigation**: Smart TTL based on market hours, fallback to multiple sources

### Medium Risk 🟡
1. **News Deduplication**
   - 85% title similarity threshold may be too aggressive/lenient
   - **Mitigation**: Make threshold configurable, A/B test

2. **LIFO Stack Management**
   - Archive logic needs to be reliable
   - **Mitigation**: Database triggers, comprehensive testing

### Low Risk 🟢
1. **Frontend Performance**
   - React re-renders with real-time data
   - **Mitigation**: React.memo, useMemo, virtualization for long lists

---

## 11. Conclusion

### Can We Implement Now?

**Short Answer:** **Partially, yes.**

**What CAN be done:**
- ✅ Frontend UI components with mock data
- ✅ Service layer interfaces
- ✅ Custom React hooks
- ✅ API client setup
- ✅ Infrastructure preparation

**What CANNOT be done without backend:**
- ❌ Real stock prices
- ❌ Real news data
- ❌ Cache optimization
- ❌ Real-time updates
- ❌ End-to-end testing

### Recommendation:

**Parallel Development Approach:**
1. **Frontend team** creates UI components with mock data immediately
2. **Backend team** completes service layer (2-3 weeks)
3. **Integration** happens once backend APIs are ready (1 week)

**Total Timeline:** 4-5 weeks to full integration

**Critical Path Blocker:** Backend service layer and API endpoints

---

## 12. Appendix

### A. Related Documents
- [STOCK_NEWS_FINAL_SUMMARY.md](STOCK_NEWS_FINAL_SUMMARY.md) - Backend implementation status
- [STOCK_NEWS_API_DESIGN.md](docs/reference/STOCK_NEWS_API_DESIGN.md) - API specification
- [STOCK_NEWS_IMPLEMENTATION_CHECKLIST.md](STOCK_NEWS_IMPLEMENTATION_CHECKLIST.md) - Implementation tasks
- [STOCK_NEWS_QUICK_START.md](STOCK_NEWS_QUICK_START.md) - Quick reference guide

### B. Key Files Reference

**Backend:**
- Models: [backend/app/models/stock.py](../backend/app/models/stock.py), [backend/app/models/news.py](../backend/app/models/news.py)
- Database: [backend/app/db/stock_prices.py](../backend/app/db/stock_prices.py), [backend/app/db/stock_news.py](../backend/app/db/stock_news.py)
- Cache: [backend/app/cache/lfu_manager.py](../backend/app/cache/lfu_manager.py)
- Schema: [database/stock_news_schema.sql](../database/stock_news_schema.sql)

**Frontend:**
- API Client: [frontend/src/utils/api-client.ts](../frontend/src/utils/api-client.ts)
- Watchlist: [frontend/src/components/WatchlistCard.tsx](../frontend/src/components/WatchlistCard.tsx)
- Dashboard: [frontend/src/pages/DashboardPage.tsx](../frontend/src/pages/DashboardPage.tsx)
- Profile Context: [frontend/src/lib/profile-context.tsx](../frontend/src/lib/profile-context.tsx)

### C. API Keys Needed (Free Tiers)
- **Finnhub**: 60 calls/min - https://finnhub.io/register
- **Polygon.io**: 5 calls/min - https://polygon.io/
- **NewsAPI**: 100 req/day - https://newsapi.org/

---

**Document Version:** 1.0
**Last Updated:** 2025-10-17
**Author:** Claude Code Agent
**Status:** Analysis Complete - Ready for Implementation Planning
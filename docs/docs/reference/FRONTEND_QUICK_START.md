# Frontend Quick Start Guide

**For:** Stock & News Integration
**Status:** Mock Data Implementation (Ready for Backend)

---

## 🚀 Quick Start (5 Minutes)

### 1. Start the Frontend

```bash
cd frontend
npm install  # If first time
npm run dev
```

Navigate to: `http://localhost:5173`

### 2. What You'll See

**Dashboard with:**
- ✅ **Connection Status** (top-left)
- ✅ **Top 3 General News** (left column - Fed, Politics, Economics)
- ✅ **Voice Interface** (center)
- ✅ **Watchlist with Live Prices** (right column - AAPL, GOOGL, MSFT, TSLA)
- ✅ **Watchlist Stock News** (bottom - 5 news per stock, tabbed)

### 3. Auto-Refresh Behavior

- **Stock Prices**: Every 60 seconds (market open), 5 minutes (closed)
- **General News**: Every 10 minutes
- **Stock News**: Every 15 minutes

---

## 📂 File Organization

### Mock Data
```
frontend/src/mocks/
├── stock-data.ts          # Stock price generators
└── news-data.ts           # News generators
```

### Services
```
frontend/src/services/
├── stock-price-service.ts # Stock price API client
└── news-service.ts        # News API client
```

### Hooks
```
frontend/src/hooks/stocks/
├── useWatchlistPrices.ts  # Batch stock prices
├── useGeneralNews.ts      # Top 3 economic news
└── useStockNews.ts        # Stock-specific news
```

### Components
```
frontend/src/components/
├── news/
│   ├── NewsCard.tsx       # Single news article card
│   └── NewsFeed.tsx       # List of news cards
├── stocks/
│   └── WatchlistNews.tsx  # Tabbed stock news
└── WatchlistCard.tsx      # Enhanced with prices
```

---

## 🔧 Configuration

### Switch to Real Backend APIs

**File:** `frontend/src/services/stock-price-service.ts`
```typescript
const USE_MOCK_DATA = false; // Change from true
```

**File:** `frontend/src/services/news-service.ts`
```typescript
const USE_MOCK_DATA = false; // Change from true
```

### Set API URL

**File:** `.env` (create if not exists)
```bash
VITE_API_URL=http://localhost:8000
```

Or for production:
```bash
VITE_API_URL=https://your-backend.com
```

---

## 🎨 Component Usage Examples

### 1. Watchlist Prices Hook

```tsx
import { useWatchlistPrices } from '../hooks/stocks/useWatchlistPrices';

function MyComponent() {
  const { prices, loading, error, refetch, isMarketOpen } = useWatchlistPrices([
    'AAPL',
    'GOOGL',
    'MSFT'
  ]);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {isMarketOpen && <span>Market is Open</span>}
      {prices.map(stock => (
        <div key={stock.symbol}>
          {stock.symbol}: ${stock.price} ({stock.change_percent}%)
        </div>
      ))}
      <button onClick={refetch}>Refresh</button>
    </div>
  );
}
```

### 2. General News Hook

```tsx
import { useGeneralNews } from '../hooks/stocks/useGeneralNews';
import { NewsFeed } from '../components/news/NewsFeed';

function NewsSection() {
  const { news, loading, error, refetch } = useGeneralNews(3);

  return (
    <NewsFeed
      news={news}
      loading={loading}
      error={error}
      title="Top Economic News"
      onRefresh={refetch}
      showImpact={true}
    />
  );
}
```

### 3. Stock News Hook

```tsx
import { useStockNews } from '../hooks/stocks/useStockNews';
import { NewsCard } from '../components/news/NewsCard';

function StockNewsPanel({ symbol }: { symbol: string }) {
  const { news, loading, error, refetch } = useStockNews(symbol, 5);

  if (loading) return <div>Loading news...</div>;

  return (
    <div>
      <h3>Latest News for {symbol}</h3>
      {news.map(article => (
        <NewsCard
          key={article.id}
          news={article}
          onClick={() => window.open(article.url, '_blank')}
        />
      ))}
    </div>
  );
}
```

### 4. Watchlist News Component

```tsx
import { WatchlistNews } from '../components/stocks/WatchlistNews';

function Dashboard() {
  const symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA'];

  return (
    <WatchlistNews
      symbols={symbols}
      newsPerStock={5}
    />
  );
}
```

---

## 🧪 Testing Mock Data

### Test Different Scenarios

**1. Empty Watchlist:**
```tsx
<WatchlistNews symbols={[]} newsPerStock={5} />
// Shows: "Add stocks to your watchlist to see their latest news"
```

**2. Loading State:**
```tsx
const { news, loading } = useGeneralNews(3);
// loading=true → Shows 3 skeleton loaders
```

**3. Error State:**
```tsx
// Simulate by stopping backend while USE_MOCK_DATA=false
// Falls back to mock data automatically
```

**4. Breaking News:**
```tsx
// Mock data includes breaking news with ~30% chance
// Look for red "BREAKING" badge
```

**5. Different Impact Levels:**
```tsx
// Economic news has impact levels: low, medium, high
// See colored badges on NewsCard
```

---

## 📊 Mock Data Characteristics

### Stock Prices:
- **Base Prices**: Realistic values (AAPL: $175, GOOGL: $140, etc.)
- **Fluctuation**: ±3% random change
- **Cache Hit Rate**: 70% simulated
- **Volume**: 10M - 60M shares
- **Market Cap**: Realistic values based on price

### News Articles:
- **Stock News**: 5 templates per symbol (AAPL, GOOGL, MSFT, TSLA, NVDA)
- **General News**: Fed, Politics, Employment, Inflation
- **Sentiment**: Ranges from -0.5 to 1.0
- **Publishing**: Staggered timestamps over past 24 hours
- **Breaking**: 30% chance for first article

---

## 🐛 Troubleshooting

### Issue: "Cannot find module '@/components/ui/...'"

**Solution:** Check if shadcn/ui components are installed:
```bash
cd frontend
npx shadcn-ui@latest add card badge skeleton tabs
```

### Issue: "Hook returns empty data"

**Solution:** Check browser console logs:
```javascript
// Should see:
[stock-service] Getting mock price for AAPL
[news-service] Getting mock general news (3 articles)
```

### Issue: "Auto-refresh not working"

**Solution:** Check component mounting:
- Hooks only start auto-refresh after initial mount
- Unmounting stops intervals
- Check browser console for interval logs

### Issue: "Real API not working"

**Checklist:**
1. Backend running? `curl http://localhost:8000/health`
2. `USE_MOCK_DATA = false` in both services?
3. `VITE_API_URL` set correctly?
4. CORS enabled on backend?
5. Check Network tab in DevTools

---

## 🔗 API Endpoints (for Backend Integration)

### Stock Prices:
```
POST /api/v1/stocks/prices/batch
Body: { "symbols": ["AAPL", "GOOGL"], "refresh": false }
Response: { "prices": [...], "cache_hits": 2, ... }
```

### Stock News:
```
GET /api/v1/stocks/{symbol}/news?limit=5
Response: { "symbol": "AAPL", "news": [...], "total_count": 5 }
```

### General News:
```
GET /api/v1/news/economic?limit=3
Response: { "news": [...], "total_count": 3 }
```

See [STOCK_NEWS_API_DESIGN.md](docs/reference/STOCK_NEWS_API_DESIGN.md) for complete API spec.

---

## 📝 Key Features Summary

| Feature | Status | Auto-Refresh | Data Source |
|---------|--------|--------------|-------------|
| Watchlist Prices | ✅ | 60s / 5min | Mock (ready for API) |
| General News | ✅ | 10 min | Mock (ready for API) |
| Stock News | ✅ | 15 min | Mock (ready for API) |
| Breaking News | ✅ | 10 min | Mock |
| Sentiment Analysis | ✅ | - | Mock |
| Impact Levels | ✅ | - | Mock |
| Market Status | ✅ | Real-time | Client-side |
| Loading States | ✅ | - | Built-in |
| Error Handling | ✅ | - | Graceful fallback |

---

## 🎯 Next Steps

1. **Test with Mock Data** (Now)
   - Verify all components render correctly
   - Check auto-refresh behavior
   - Test error states

2. **Integrate with Backend** (When Ready)
   - Set `USE_MOCK_DATA = false`
   - Configure `VITE_API_URL`
   - Test with real APIs

3. **Deploy to Production**
   - Build: `npm run build`
   - Deploy `dist/` folder
   - Set production env vars

---

## 📚 Additional Documentation

- [Complete Implementation Guide](FRONTEND_IMPLEMENTATION_COMPLETE.md)
- [Gap Analysis](FRONTEND_BACKEND_INTEGRATION_GAP_ANALYSIS.md)
- [Backend API Design](docs/reference/STOCK_NEWS_API_DESIGN.md)

---

**Last Updated:** 2025-10-17
**Status:** Production-Ready (Mock Data)

# Stock & News API - Quick Start Guide

**Version:** 1.0
**Status:** Design Complete - Ready for Implementation

---

## 📚 Complete Documentation

- **Full API Design**: [docs/reference/STOCK_NEWS_API_DESIGN.md](docs/reference/STOCK_NEWS_API_DESIGN.md)
- **SQL Schema**: [database/stock_news_schema.sql](../database/stock_news_schema.sql)
- **Documentation Index**: [docs/reference/DOCUMENTATION_INDEX.md](docs/reference/DOCUMENTATION_INDEX.md)

---

## 🎯 What's Included

### 1. API Endpoints (RESTful)

**Stock Prices** (with LFU caching):
- `GET /api/v1/stocks/{symbol}/price` - Single stock price
- `POST /api/v1/stocks/prices/batch` - Batch retrieval

**Stock News** (LIFO Stack - Latest 5 on Top):
- `GET /api/v1/stocks/{symbol}/news` - Latest 5 news per stock
- `POST /api/v1/stocks/{symbol}/news` - Push new news (internal)

**Economic News**:
- `GET /api/v1/news/economic` - General economic news
- `GET /api/v1/news/federal-reserve` - Fed announcements
- `GET /api/v1/news/politics` - Political news with economic impact

**Dashboard**:
- `GET /api/v1/dashboard` - Combined user dashboard

### 2. Database Schema (PostgreSQL/Supabase)

**5 New Tables**:
1. `stock_prices` - Real-time & historical prices
2. `stock_news` - Stock-specific news with stack management
3. `economic_news` - Economic news (Fed, politics, indicators)
4. `news_sources` - Multi-source configuration
5. `cache_access_stats` - LFU tracking

**Helper Functions**:
- `get_latest_stock_price()` - Get most recent price
- `get_stock_news_stack()` - Get top 5 news
- `archive_old_stock_news()` - Auto-archive (trigger)

### 3. Redis Caching (Upstash)

**LFU Implementation**:
```python
score = (access_count / time_span_hours) * recency_factor * 100
```

**Cache Layers**:
- Stock prices: 60s TTL (market hours)
- Stock news stack: 15min TTL
- Economic news: 10-30min TTL
- User watchlists: 1hr TTL

### 4. News Sources (11 recommended)

**Phase 1** (Free - Immediate):
- Finnhub API (60 calls/min)
- Polygon.io API (5 calls/min)
- Federal Reserve RSS (unlimited)

**Phase 2** (Free - Week 2):
- BLS API (employment/inflation)
- BEA API (GDP/indicators)
- NewsAPI (100 req/day)

**Phase 3** (Free RSS - Week 3):
- Reuters, CNBC, MarketWatch

---

## 🚀 Quick Setup

### 1. Database Setup

```bash
# Apply SQL schema to Supabase
psql $DATABASE_URL < database/stock_news_schema.sql
```

### 2. Configure Redis

```bash
# Set LFU eviction policy in Upstash dashboard
MAXMEMORY_POLICY=allkeys-lfu
MAXMEMORY=100mb
```

### 3. Register for API Keys

- [Finnhub](https://finnhub.io/) - Free tier
- [Polygon.io](https://polygon.io/) - Free tier
- [NewsAPI](https://newsapi.org/) - Free tier

### 4. Environment Variables

```bash
# Add to env_files/.env
FINNHUB_API_KEY=your_key
POLYGON_API_KEY=your_key
NEWSAPI_API_KEY=your_key
```

---

## 📊 Key Features

### LIFO News Stack

```
Position 1: Latest news (just published)
Position 2: 2nd most recent
Position 3: 3rd most recent
Position 4: 4th most recent
Position 5: 5th most recent
Position 6+: Archived to database
```

**How it works**:
1. New article arrives → Push to position 1
2. Previous articles shift down (2, 3, 4, 5)
3. Article at position 6 → Archived (removed from stack)
4. Cache TTL: 15 minutes

### LFU Cache Intelligence

**Frequency Scoring**:
```python
time_span_hours = (current_time - first_access_time) / 3600
frequency_rate = access_count / time_span_hours
recency_factor = exp(-recency_hours / 24)  # 24hr decay
score = frequency_rate * recency_factor * 100
```

**Benefits**:
- Hot stocks stay cached (AAPL, TSLA, NVDA)
- Rarely accessed symbols evicted first
- Time-based decay prevents stale data
- Per-type LFU tracking (stocks, news, watchlists)

### Multi-Source Aggregation

```python
# Fetch from multiple sources concurrently
sources = [finnhub, polygon, alphavantage]
results = await asyncio.gather(*sources)

# Deduplicate by title similarity (85% threshold)
unique_articles = deduplicate(all_articles)

# Sort by published date (most recent first)
return sorted(unique_articles, key=lambda x: x['published_at'], reverse=True)
```

---

## 📈 Performance Targets

| Metric | Target |
|--------|--------|
| API Response (cached) | < 200ms |
| API Response (uncached) | < 2s |
| Cache Hit Rate (prices) | > 80% |
| Cache Hit Rate (news) | > 70% |
| News Update Latency | < 5 min |
| Database Query | < 50ms |
| API Uptime | > 99.5% |

---

## 🗓️ Implementation Timeline

### Week 1: Infrastructure
- Database tables & indexes
- Redis LFU cache manager
- API route structure
- Pydantic models

### Week 2: Stock APIs
- Stock price endpoints
- LFU caching layer
- News stack implementation
- Finnhub integration

### Week 3: Economic News
- Economic news endpoints
- Federal Reserve RSS feeds
- NewsAPI integration
- Breaking news detection

### Week 4: Polish & Deploy
- Additional sources (Polygon, BLS, BEA)
- Performance optimization
- Comprehensive testing
- Production deployment

---

## 📖 Usage Examples

### Get Stock Price

```bash
curl -X GET "http://localhost:8000/api/v1/stocks/AAPL/price" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Latest News for Stock

```bash
curl -X GET "http://localhost:8000/api/v1/stocks/AAPL/news?limit=5" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Economic News

```bash
curl -X GET "http://localhost:8000/api/v1/news/economic?categories=federal_reserve,inflation" \
  -H "Authorization: Bearer $API_KEY"
```

### Get Dashboard

```bash
curl -X GET "http://localhost:8000/api/v1/dashboard?user_id=user_123" \
  -H "Authorization: Bearer $API_KEY"
```

---

## 🔗 Related Documentation

- **Complete API Design**: [docs/reference/STOCK_NEWS_API_DESIGN.md](docs/reference/STOCK_NEWS_API_DESIGN.md)
- **SQL Schema**: [database/stock_news_schema.sql](../database/stock_news_schema.sql)
- **Current API**: [docs/reference/API_DESIGN.md](docs/reference/API_DESIGN.md)
- **Database Setup**: [docs/reference/DATABASE_SETUP.md](docs/reference/DATABASE_SETUP.md)
- **Documentation Index**: [docs/reference/DOCUMENTATION_INDEX.md](docs/reference/DOCUMENTATION_INDEX.md)

---

## ✅ Next Steps

1. Review full design: [STOCK_NEWS_API_DESIGN.md](docs/reference/STOCK_NEWS_API_DESIGN.md)
2. Apply SQL schema: `psql $DATABASE_URL < database/stock_news_schema.sql`
3. Configure Upstash Redis with LFU policy
4. Register for API keys (Finnhub, Polygon, NewsAPI)
5. Begin Week 1 implementation

---

**Document Version**: 1.0
**Last Updated**: 2025-10-17
**Status**: Ready for Implementation

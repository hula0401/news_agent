# Stock & News API Design

**Version:** 1.1
**Date:** 2025-10-19
**Status:** Implemented (with updates)

## Recent Updates

### 2025-10-19 - P0 Bug Fix & Implementation Updates
**Summary**: Fixed critical StockNewsService initialization bug and updated endpoint paths.

**Changes**:
1. **Stock News Endpoint Path Updated**:
   - Old (Design): `/api/v1/stocks/{symbol}/news`
   - **New (Implemented)**: `/api/v1/stock-news/{symbol}/news`
   - Reason: Separate router for stock news to better organize API structure

2. **P0 Bug Fix** - StockNewsDB Initialization Order:
   - **Problem**: `StockNewsDB` initialized with `None` client before `db_manager.initialize()` ran
   - **Solution**: Moved initialization to async `initialize()` method (lazy initialization pattern)
   - **Impact**: All stock news endpoints now functional (previously 100% error rate)
   - **Details**: See [backend/app/services/stock_news_service.py:24-40](../../../backend/app/services/stock_news_service.py#L24-L40)

3. **Testing Added**:
   - Manual test: `curl /api/v1/stock-news/AAPL/news` → HTTP 200 OK ✅
   - Automated test: `TestStockNewsServiceInitialization::test_stock_news_db_initialized_correctly` ✅
   - Test file: [tests/backend/test_stock_news_api_v1.py:97-124](../../../tests/backend/test_stock_news_api_v1.py#L97-L124)

**Status**: ✅ Fully implemented and tested

---

## Table of Contents

1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Database Schema](#database-schema)
4. [Redis Caching Strategy](#redis-caching-strategy)
5. [News Sources](#news-sources)
6. [Implementation Plan](#implementation-plan)

---

## Overview

This document outlines the API design for a comprehensive stock and news service with intelligent caching, multi-source news aggregation, and economic data integration.

### Key Features

1. **Real-time Stock Prices** with LFU (Least Frequently Used) caching
2. **Latest 5 News per Stock** with stack-based storage (LIFO - Latest on Top)
3. **General Economic News** including politics, Federal Reserve announcements, economic indicators
4. **Multi-Source News Aggregation** from reliable financial and economic sources

### Technology Stack

- **Backend**: FastAPI (Python 3.9+)
- **Database**: Supabase (PostgreSQL)
- **Cache**: Upstash Redis with LFU eviction policy
- **News APIs**: AlphaVantage, Finnhub, NewsAPI, Polygon.io, Federal Reserve RSS

---

## API Endpoints

### 1. Stock Prices API

#### 1.1 Get Latest Stock Price

```http
GET /api/v1/stocks/{symbol}/price
```

**Description**: Retrieve the latest price for a specific stock with LFU caching.

**Path Parameters**:
- `symbol` (string, required): Stock ticker symbol (e.g., AAPL, TSLA)

**Query Parameters**:
- `refresh` (boolean, optional, default: false): Force cache refresh

**Response** (200 OK):
```json
{
  "symbol": "AAPL",
  "price": 229.35,
  "change": 2.45,
  "change_percent": 1.08,
  "volume": 45235678,
  "market_cap": 3562000000000,
  "high_52_week": 237.49,
  "low_52_week": 164.08,
  "last_updated": "2025-10-17T14:32:15Z",
  "source": "cache",
  "cache_hit": true
}
```

**Cache Behavior**:
- TTL: 60 seconds (market hours), 300 seconds (after hours)
- LFU tracking for access frequency
- Auto-refresh if price is stale

---

#### 1.2 Get Multiple Stock Prices

```http
POST /api/v1/stocks/prices/batch
```

**Description**: Retrieve prices for multiple stocks in a single request.

**Request Body**:
```json
{
  "symbols": ["AAPL", "GOOGL", "MSFT", "TSLA"],
  "refresh": false
}
```

**Response** (200 OK):
```json
{
  "prices": [
    {
      "symbol": "AAPL",
      "price": 229.35,
      "change": 2.45,
      "change_percent": 1.08,
      "last_updated": "2025-10-17T14:32:15Z",
      "cache_hit": true
    },
    // ... more stocks
  ],
  "total_count": 4,
  "cache_hits": 3,
  "cache_misses": 1,
  "processing_time_ms": 145
}
```

---

### 2. Stock News API

#### 2.1 Get Latest News for Stock

```http
GET /api/v1/stock-news/{symbol}/news
```

**Description**: Retrieve the latest 5 news articles for a specific stock. News is stored in a stack (LIFO - Latest on Top).

**⚠️ NOTE**: Endpoint path changed from design spec `/api/v1/stocks/{symbol}/news` to implemented `/api/v1/stock-news/{symbol}/news`

**Path Parameters**:
- `symbol` (string, required): Stock ticker symbol

**Query Parameters**:
- `limit` (integer, optional, default: 5, max: 20): Number of news articles
- `since` (datetime, optional): Only return news published after this timestamp

**Response** (200 OK):
```json
{
  "symbol": "AAPL",
  "news": [
    {
      "id": "news_123",
      "title": "Apple Announces New AI Features",
      "summary": "Apple unveiled new AI capabilities in iOS 19...",
      "url": "https://example.com/news/apple-ai",
      "published_at": "2025-10-17T14:00:00Z",
      "source": {
        "id": "source_abc",
        "name": "TechCrunch",
        "reliability_score": 0.92
      },
      "sentiment_score": 0.75,
      "topics": ["technology", "ai", "mobile"],
      "is_breaking": false,
      "position_in_stack": 1
    },
    // ... 4 more recent articles (positions 2-5)
  ],
  "total_count": 5,
  "last_updated": "2025-10-17T14:30:00Z",
  "cache_hit": true
}
```

**Stack Behavior**:
- New articles push to position 1
- Older articles shift down (positions 2, 3, 4, 5)
- Articles beyond position 5 are archived to database
- Cache TTL: 15 minutes

---

#### 2.2 Push New News to Stock Stack

```http
POST /api/v1/stock-news/{symbol}/news
```

**Description**: Add new news article to the top of the stack (internal/admin endpoint).

**⚠️ NOTE**: Endpoint path changed from design spec `/api/v1/stocks/{symbol}/news` to implemented `/api/v1/stock-news/{symbol}/news`

**Request Body**:
```json
{
  "title": "Apple Reports Record Earnings",
  "summary": "Apple exceeded analyst expectations...",
  "url": "https://example.com/news/apple-earnings",
  "published_at": "2025-10-17T14:45:00Z",
  "source_id": "source_abc",
  "sentiment_score": 0.85,
  "topics": ["finance", "earnings"],
  "is_breaking": false
}
```

**Response** (201 Created):
```json
{
  "id": "news_456",
  "symbol": "AAPL",
  "position_in_stack": 1,
  "archived_article_id": "news_789",
  "created_at": "2025-10-17T14:45:05Z"
}
```

---

### 3. General Economic News API

#### 3.1 Get Latest Economic News

```http
GET /api/v1/news/economic
```

**Description**: Retrieve latest general economic news including politics, Federal Reserve announcements, economic indicators.

**Query Parameters**:
- `limit` (integer, optional, default: 10, max: 50): Number of articles
- `categories` (array, optional): Filter by categories
  - `federal_reserve`, `politics`, `economics`, `inflation`, `employment`, `gdp`, `trade`, `monetary_policy`
- `since` (datetime, optional): Only return news after this timestamp
- `breaking_only` (boolean, optional): Only breaking news

**Response** (200 OK):
```json
{
  "news": [
    {
      "id": "econ_news_123",
      "title": "Fed Holds Interest Rates Steady",
      "summary": "The Federal Reserve kept rates unchanged...",
      "url": "https://example.com/fed-rates",
      "published_at": "2025-10-17T13:00:00Z",
      "source": {
        "id": "source_fed",
        "name": "Federal Reserve",
        "reliability_score": 1.0
      },
      "category": "federal_reserve",
      "sentiment_score": 0.0,
      "topics": ["monetary_policy", "interest_rates"],
      "is_breaking": true,
      "impact_level": "high",
      "related_symbols": ["SPY", "DIA", "QQQ"]
    },
    // ... more articles
  ],
  "total_count": 10,
  "categories": ["federal_reserve", "politics", "economics"],
  "last_updated": "2025-10-17T14:30:00Z",
  "cache_hit": true
}
```

**Cache Behavior**:
- TTL: 10 minutes for breaking news, 30 minutes for regular news
- Separate cache keys per category combination

---

#### 3.2 Get Federal Reserve Announcements

```http
GET /api/v1/news/federal-reserve
```

**Description**: Retrieve latest Federal Reserve announcements, FOMC minutes, and policy statements.

**Query Parameters**:
- `limit` (integer, optional, default: 5, max: 20): Number of announcements
- `type` (string, optional): Filter by type
  - `fomc_statement`, `speech`, `minutes`, `report`, `press_release`

**Response** (200 OK):
```json
{
  "announcements": [
    {
      "id": "fed_123",
      "type": "fomc_statement",
      "title": "FOMC Statement - October 17, 2025",
      "summary": "Federal funds rate remains at 5.25-5.50%...",
      "url": "https://federalreserve.gov/statement",
      "published_at": "2025-10-17T13:00:00Z",
      "key_points": [
        "Interest rates unchanged",
        "Inflation moderating",
        "Employment remains strong"
      ],
      "market_impact": "high",
      "related_indicators": ["interest_rates", "inflation", "employment"]
    }
  ],
  "total_count": 5,
  "last_updated": "2025-10-17T14:30:00Z"
}
```

---

#### 3.3 Get Political & Economic News

```http
GET /api/v1/news/politics
```

**Description**: Retrieve latest political news with economic impact.

**Query Parameters**:
- `limit` (integer, optional, default: 10): Number of articles
- `regions` (array, optional): Filter by region (e.g., `us`, `eu`, `china`)
- `impact_level` (string, optional): Filter by market impact (`high`, `medium`, `low`)

**Response** (200 OK):
```json
{
  "news": [
    {
      "id": "pol_news_123",
      "title": "Congress Passes Infrastructure Bill",
      "summary": "Bipartisan infrastructure legislation approved...",
      "url": "https://example.com/congress-bill",
      "published_at": "2025-10-17T12:00:00Z",
      "region": "us",
      "impact_level": "medium",
      "affected_sectors": ["construction", "technology", "energy"],
      "related_symbols": ["CAT", "DE", "XLI"],
      "sentiment_score": 0.65
    }
  ],
  "total_count": 10,
  "regions": ["us", "eu"],
  "last_updated": "2025-10-17T14:30:00Z"
}
```

---

### 4. Combined Dashboard API

#### 4.1 Get User Dashboard

```http
GET /api/v1/dashboard
```

**Description**: Retrieve comprehensive dashboard with stocks, news, and economic updates.

**Query Parameters**:
- `user_id` (string, required): User ID for watchlist
- `include_economic` (boolean, optional, default: true): Include economic news

**Response** (200 OK):
```json
{
  "user_id": "user_123",
  "timestamp": "2025-10-17T14:35:00Z",
  "watchlist": {
    "stocks": [
      {
        "symbol": "AAPL",
        "price": 229.35,
        "change_percent": 1.08,
        "latest_news": [/* top 3 news articles */]
      }
      // ... more stocks
    ],
    "total_value": 125000.00,
    "daily_change": 2450.00,
    "daily_change_percent": 2.00
  },
  "economic_news": {
    "breaking": [/* breaking economic news */],
    "federal_reserve": [/* latest Fed announcements */],
    "politics": [/* political news with economic impact */]
  },
  "market_summary": {
    "indices": {
      "SPY": {"price": 575.34, "change_percent": 0.75},
      "DIA": {"price": 422.15, "change_percent": 0.62},
      "QQQ": {"price": 492.08, "change_percent": 1.12}
    },
    "market_status": "open",
    "next_fed_meeting": "2025-11-01T14:00:00Z"
  },
  "cache_stats": {
    "total_hits": 12,
    "total_misses": 3,
    "cache_hit_rate": 0.80
  }
}
```

---

## Database Schema

### 1. Stock Prices Table

```sql
-- Table: stock_prices
CREATE TABLE stock_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(12, 4) NOT NULL,
    change DECIMAL(12, 4),
    change_percent DECIMAL(8, 4),
    volume BIGINT,
    market_cap BIGINT,
    high_52_week DECIMAL(12, 4),
    low_52_week DECIMAL(12, 4),
    pe_ratio DECIMAL(8, 2),
    dividend_yield DECIMAL(6, 4),
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_source VARCHAR(50) NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Indexes
    CONSTRAINT unique_symbol_timestamp UNIQUE (symbol, last_updated)
);

CREATE INDEX idx_stock_prices_symbol ON stock_prices(symbol);
CREATE INDEX idx_stock_prices_last_updated ON stock_prices(last_updated DESC);
CREATE INDEX idx_stock_prices_symbol_updated ON stock_prices(symbol, last_updated DESC);

COMMENT ON TABLE stock_prices IS 'Historical and current stock price data with metadata';
COMMENT ON COLUMN stock_prices.symbol IS 'Stock ticker symbol (e.g., AAPL, TSLA)';
COMMENT ON COLUMN stock_prices.price IS 'Current stock price in USD';
COMMENT ON COLUMN stock_prices.change IS 'Price change from previous close';
COMMENT ON COLUMN stock_prices.change_percent IS 'Percentage change from previous close';
COMMENT ON COLUMN stock_prices.volume IS 'Trading volume';
COMMENT ON COLUMN stock_prices.market_cap IS 'Market capitalization in USD';
COMMENT ON COLUMN stock_prices.last_updated IS 'Timestamp when price was last updated from external source';
COMMENT ON COLUMN stock_prices.data_source IS 'Source of the price data (e.g., alphavantage, polygon, finnhub)';
```

---

### 2. Stock News Table

```sql
-- Table: stock_news
CREATE TABLE stock_news (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    source_id UUID NOT NULL REFERENCES news_sources(id) ON DELETE CASCADE,
    external_id VARCHAR(255),

    -- Content
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    url TEXT,

    -- Metadata
    published_at TIMESTAMPTZ NOT NULL,
    sentiment_score DECIMAL(4, 3) CHECK (sentiment_score BETWEEN -1 AND 1),
    topics TEXT[] DEFAULT '{}',
    is_breaking BOOLEAN DEFAULT FALSE,

    -- Stack management
    position_in_stack INTEGER,
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_stock_news UNIQUE (symbol, external_id),
    CONSTRAINT valid_position CHECK (position_in_stack IS NULL OR (position_in_stack >= 1 AND position_in_stack <= 5))
);

CREATE INDEX idx_stock_news_symbol ON stock_news(symbol);
CREATE INDEX idx_stock_news_published ON stock_news(published_at DESC);
CREATE INDEX idx_stock_news_stack ON stock_news(symbol, position_in_stack) WHERE NOT is_archived;
CREATE INDEX idx_stock_news_breaking ON stock_news(symbol, is_breaking, published_at DESC) WHERE is_breaking;
CREATE INDEX idx_stock_news_archived ON stock_news(symbol, archived_at DESC) WHERE is_archived;

COMMENT ON TABLE stock_news IS 'News articles related to specific stocks with stack-based storage (LIFO)';
COMMENT ON COLUMN stock_news.symbol IS 'Stock ticker symbol this news is related to';
COMMENT ON COLUMN stock_news.external_id IS 'Unique identifier from the external news source';
COMMENT ON COLUMN stock_news.sentiment_score IS 'Sentiment score: -1 (negative) to 1 (positive)';
COMMENT ON COLUMN stock_news.position_in_stack IS 'Position in the 5-item stack (1 = most recent, 5 = oldest)';
COMMENT ON COLUMN stock_news.is_archived IS 'Whether the article has been pushed out of the top 5 stack';
COMMENT ON COLUMN stock_news.archived_at IS 'Timestamp when article was archived (pushed out of stack)';
```

---

### 3. Economic News Table

```sql
-- Table: economic_news
CREATE TABLE economic_news (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES news_sources(id) ON DELETE CASCADE,
    external_id VARCHAR(255),

    -- Content
    title TEXT NOT NULL,
    summary TEXT,
    content TEXT,
    url TEXT,

    -- Classification
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'federal_reserve', 'politics', 'economics', 'inflation',
        'employment', 'gdp', 'trade', 'monetary_policy', 'fiscal_policy'
    )),
    region VARCHAR(10) NOT NULL DEFAULT 'us',
    impact_level VARCHAR(20) CHECK (impact_level IN ('low', 'medium', 'high')),

    -- Metadata
    published_at TIMESTAMPTZ NOT NULL,
    sentiment_score DECIMAL(4, 3) CHECK (sentiment_score BETWEEN -1 AND 1),
    topics TEXT[] DEFAULT '{}',
    is_breaking BOOLEAN DEFAULT FALSE,

    -- Related data
    related_symbols TEXT[] DEFAULT '{}',
    affected_sectors TEXT[] DEFAULT '{}',
    key_points TEXT[] DEFAULT '{}',
    market_impact TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_economic_news UNIQUE (source_id, external_id)
);

CREATE INDEX idx_economic_news_category ON economic_news(category, published_at DESC);
CREATE INDEX idx_economic_news_published ON economic_news(published_at DESC);
CREATE INDEX idx_economic_news_breaking ON economic_news(is_breaking, published_at DESC) WHERE is_breaking;
CREATE INDEX idx_economic_news_impact ON economic_news(impact_level, published_at DESC);
CREATE INDEX idx_economic_news_region ON economic_news(region, category, published_at DESC);
CREATE INDEX idx_economic_news_symbols ON economic_news USING GIN (related_symbols);

COMMENT ON TABLE economic_news IS 'General economic news including Fed announcements, politics, economic indicators';
COMMENT ON COLUMN economic_news.category IS 'News category (federal_reserve, politics, economics, etc.)';
COMMENT ON COLUMN economic_news.region IS 'Geographic region (us, eu, china, global)';
COMMENT ON COLUMN economic_news.impact_level IS 'Expected market impact level';
COMMENT ON COLUMN economic_news.related_symbols IS 'Stock symbols potentially affected by this news';
COMMENT ON COLUMN economic_news.affected_sectors IS 'Economic sectors affected (technology, energy, healthcare, etc.)';
COMMENT ON COLUMN economic_news.key_points IS 'Bullet points of key information';
COMMENT ON COLUMN economic_news.market_impact IS 'Analysis of potential market impact';
```

---

### 4. News Sources Table

```sql
-- Table: news_sources (enhanced)
CREATE TABLE news_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    url TEXT,

    -- Classification
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN (
        'api', 'rss', 'scraper', 'official', 'aggregator'
    )),
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'stock_market', 'economics', 'federal_reserve', 'politics', 'general'
    )),

    -- Quality metrics
    reliability_score DECIMAL(4, 3) NOT NULL DEFAULT 0.5 CHECK (reliability_score BETWEEN 0 AND 1),
    api_name VARCHAR(100),
    api_endpoint TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_fetch_at TIMESTAMPTZ,
    fetch_frequency_minutes INTEGER DEFAULT 15,

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_news_sources_active ON news_sources(is_active, category);
CREATE INDEX idx_news_sources_category ON news_sources(category);

COMMENT ON TABLE news_sources IS 'Configuration and metadata for news sources (APIs, RSS feeds, official sources)';
COMMENT ON COLUMN news_sources.source_type IS 'Type of data source (api, rss, scraper, official, aggregator)';
COMMENT ON COLUMN news_sources.category IS 'Primary category of news from this source';
COMMENT ON COLUMN news_sources.reliability_score IS 'Reliability score from 0 to 1 (1 = most reliable)';
COMMENT ON COLUMN news_sources.api_name IS 'Name of the API service (alphavantage, finnhub, newsapi, etc.)';
COMMENT ON COLUMN news_sources.fetch_frequency_minutes IS 'How often to fetch news from this source';
```

---

### 5. Cache Access Statistics Table

```sql
-- Table: cache_access_stats
CREATE TABLE cache_access_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(255) NOT NULL,
    cache_type VARCHAR(50) NOT NULL CHECK (cache_type IN (
        'stock_price', 'stock_news', 'economic_news', 'user_watchlist', 'ai_response'
    )),

    -- Access tracking
    access_count INTEGER DEFAULT 1,
    last_access_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_access_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- LFU scoring
    frequency_score DECIMAL(10, 4) DEFAULT 1.0,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_cache_key UNIQUE (cache_key)
);

CREATE INDEX idx_cache_stats_type ON cache_access_stats(cache_type);
CREATE INDEX idx_cache_stats_frequency ON cache_access_stats(frequency_score DESC);
CREATE INDEX idx_cache_stats_last_access ON cache_access_stats(last_access_at DESC);

COMMENT ON TABLE cache_access_stats IS 'Statistics for LFU cache eviction policy';
COMMENT ON COLUMN cache_access_stats.frequency_score IS 'LFU score calculated from access patterns (higher = more frequently accessed)';
COMMENT ON COLUMN cache_access_stats.access_count IS 'Total number of cache accesses';
```

---

### 6. Updated Users Table (Add Stock Watchlist)

```sql
-- Add columns to existing users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS watchlist_stocks TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS preferred_economic_categories TEXT[] DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_users_watchlist ON users USING GIN (watchlist_stocks);

COMMENT ON COLUMN users.watchlist_stocks IS 'Array of stock symbols user is watching';
COMMENT ON COLUMN users.preferred_economic_categories IS 'User preferred economic news categories';
```

---

## Redis Caching Strategy

### Cache Architecture

**Upstash Redis Configuration:**
```bash
# Redis configuration for LFU eviction
MAXMEMORY_POLICY=allkeys-lfu
MAXMEMORY=100mb
```

---

### Cache Key Patterns

#### 1. Stock Price Cache

```redis
# Key pattern: stock:price:{SYMBOL}
# TTL: 60 seconds (market hours), 300 seconds (after hours)
# Data structure: Hash

HSET stock:price:AAPL symbol "AAPL" price 229.35 change 2.45 change_percent 1.08 last_updated "2025-10-17T14:32:15Z"
EXPIRE stock:price:AAPL 60
```

**LFU Tracking:**
```redis
# Increment access count for LFU
ZINCRBY stock:price:lfu 1 "AAPL"

# Get most frequently accessed stocks
ZREVRANGE stock:price:lfu 0 9 WITHSCORES
```

---

#### 2. Stock News Stack Cache

```redis
# Key pattern: stock:news:{SYMBOL}:stack
# TTL: 900 seconds (15 minutes)
# Data structure: List (LIFO)

# Push new news to front (position 1)
LPUSH stock:news:AAPL:stack '{"id":"news_123","title":"Apple AI Features",...}'

# Keep only top 5
LTRIM stock:news:AAPL:stack 0 4

# Get top 5 news
LRANGE stock:news:AAPL:stack 0 4
```

**Stack Operations:**
```python
# Push new article
await redis.lpush(f"stock:news:{symbol}:stack", json.dumps(article))
await redis.ltrim(f"stock:news:{symbol}:stack", 0, 4)
await redis.expire(f"stock:news:{symbol}:stack", 900)

# Get stack
articles = await redis.lrange(f"stock:news:{symbol}:stack", 0, 4)
```

---

#### 3. Economic News Cache

```redis
# Key pattern: economic:news:{CATEGORY}
# TTL: 600 seconds (10 minutes) for breaking, 1800 seconds (30 minutes) for regular
# Data structure: Sorted Set (by timestamp)

# Add economic news
ZADD economic:news:federal_reserve 1729177200 '{"id":"fed_123","title":"FOMC Statement",...}'

# Get latest 10 news (sorted by timestamp desc)
ZREVRANGE economic:news:federal_reserve 0 9

# Get news after specific timestamp
ZRANGEBYSCORE economic:news:federal_reserve 1729170000 +inf
```

---

#### 4. User Watchlist Cache

```redis
# Key pattern: user:watchlist:{USER_ID}
# TTL: 3600 seconds (1 hour)
# Data structure: Hash

# Store user watchlist with aggregated data
HSET user:watchlist:user_123 stocks '["AAPL","GOOGL","MSFT"]' last_updated "2025-10-17T14:30:00Z"
HSET user:watchlist:user_123:AAPL price 229.35 change_percent 1.08
```

---

### LFU Implementation

#### Frequency Scoring Algorithm

```python
import time
from typing import Dict, Any

class LFUCacheManager:
    """LFU Cache Manager with time-decay scoring."""

    async def calculate_frequency_score(
        self,
        access_count: int,
        first_access_time: float,
        last_access_time: float,
        current_time: float
    ) -> float:
        """
        Calculate LFU frequency score with time decay.

        Score = (access_count / time_span) * recency_factor

        Args:
            access_count: Total number of accesses
            first_access_time: Unix timestamp of first access
            last_access_time: Unix timestamp of last access
            current_time: Current unix timestamp

        Returns:
            Frequency score (higher = more frequently accessed)
        """
        # Time span since first access (in hours)
        time_span_hours = max((current_time - first_access_time) / 3600, 1.0)

        # Recency factor (exponential decay)
        recency_hours = (current_time - last_access_time) / 3600
        recency_factor = math.exp(-recency_hours / 24)  # Decay over 24 hours

        # Frequency rate (accesses per hour)
        frequency_rate = access_count / time_span_hours

        # Combined score
        score = frequency_rate * recency_factor * 100

        return score

    async def track_access(self, cache_key: str, cache_type: str):
        """Track cache access and update LFU score."""
        current_time = time.time()

        # Update access statistics in database
        await self.db.execute("""
            INSERT INTO cache_access_stats (cache_key, cache_type, access_count, last_access_at, first_access_at)
            VALUES ($1, $2, 1, NOW(), NOW())
            ON CONFLICT (cache_key)
            DO UPDATE SET
                access_count = cache_access_stats.access_count + 1,
                last_access_at = NOW(),
                updated_at = NOW()
        """, cache_key, cache_type)

        # Update Redis LFU score
        await self.redis.zincrby(f"{cache_type}:lfu", 1, cache_key)

    async def get_lfu_candidates_for_eviction(self, cache_type: str, limit: int = 10) -> List[str]:
        """Get cache keys with lowest frequency scores for eviction."""
        # Get keys with lowest LFU scores
        return await self.redis.zrange(f"{cache_type}:lfu", 0, limit - 1)

    async def evict_lfu_entries(self, cache_type: str, count: int):
        """Evict least frequently used entries."""
        candidates = await self.get_lfu_candidates_for_eviction(cache_type, count)

        for cache_key in candidates:
            # Remove from cache
            await self.redis.delete(cache_key)

            # Remove from LFU tracking
            await self.redis.zrem(f"{cache_type}:lfu", cache_key)

            print(f"Evicted LFU entry: {cache_key}")
```

---

#### Cache Access Pattern

```python
async def get_stock_price_with_lfu(symbol: str) -> Dict[str, Any]:
    """
    Get stock price with LFU tracking.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Stock price data
    """
    cache_key = f"stock:price:{symbol}"

    # Try to get from cache
    cached_data = await cache.get(cache_key)

    if cached_data:
        # Track cache access for LFU
        await lfu_manager.track_access(cache_key, "stock_price")
        return cached_data

    # Cache miss - fetch from external API
    price_data = await fetch_stock_price_from_api(symbol)

    # Store in cache with TTL
    ttl = 60 if is_market_hours() else 300
    await cache.set(cache_key, price_data, ttl)

    # Initialize LFU tracking
    await lfu_manager.track_access(cache_key, "stock_price")

    return price_data
```

---

### Cache Invalidation Strategies

#### 1. Time-Based Invalidation (TTL)

```python
# Stock prices - short TTL
await redis.setex(f"stock:price:{symbol}", 60, price_data)

# Stock news stack - medium TTL
await redis.setex(f"stock:news:{symbol}:stack", 900, news_stack)

# Economic news - longer TTL (unless breaking)
ttl = 600 if is_breaking else 1800
await redis.setex(f"economic:news:{category}", ttl, news_data)
```

---

#### 2. Event-Based Invalidation

```python
async def invalidate_stock_cache_on_news(symbol: str):
    """Invalidate stock cache when major news breaks."""
    # Remove stock price cache
    await redis.delete(f"stock:price:{symbol}")

    # Clear news stack cache
    await redis.delete(f"stock:news:{symbol}:stack")

    # Invalidate related user watchlists
    users_watching = await get_users_watching_symbol(symbol)
    for user_id in users_watching:
        await redis.delete(f"user:watchlist:{user_id}")
```

---

#### 3. Pattern-Based Invalidation

```python
async def invalidate_economic_news_cache():
    """Invalidate all economic news caches."""
    # Get all economic news cache keys
    keys = await redis.keys("economic:news:*")

    if keys:
        await redis.delete(*keys)
```

---

### Cache Statistics & Monitoring

```python
class CacheMonitor:
    """Monitor cache performance and LFU effectiveness."""

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        # Overall stats
        info = await redis.info("stats")

        # LFU stats per type
        lfu_stats = {}
        for cache_type in ["stock_price", "stock_news", "economic_news"]:
            top_keys = await redis.zrevrange(
                f"{cache_type}:lfu", 0, 9, withscores=True
            )
            lfu_stats[cache_type] = {
                "top_keys": top_keys,
                "total_keys": await redis.zcard(f"{cache_type}:lfu")
            }

        # Memory usage
        memory_info = await redis.info("memory")

        return {
            "redis_info": info,
            "lfu_stats": lfu_stats,
            "memory_usage": memory_info,
            "cache_hit_rate": self.calculate_hit_rate(),
            "eviction_count": info.get("evicted_keys", 0)
        }

    async def get_hot_stocks(self, limit: int = 10) -> List[str]:
        """Get most frequently accessed stocks."""
        return await redis.zrevrange("stock_price:lfu", 0, limit - 1)
```

---

## News Sources

### Recommended News Sources for Integration

#### 1. Financial Market Data APIs

##### AlphaVantage (Currently Integrated)
- **Type**: API
- **Coverage**: Stock-specific news, market data
- **Cost**: Free tier (25 requests/day), Premium ($49.99/month)
- **Reliability**: 0.85
- **Use Case**: Stock prices, company news
- **API Endpoint**: `https://www.alphavantage.co/query?function=NEWS_SENTIMENT`

##### Finnhub
- **Type**: API
- **Coverage**: Real-time stock news, earnings, market data
- **Cost**: Free tier (60 calls/minute), Premium ($59/month)
- **Reliability**: 0.90
- **Use Case**: Real-time stock news, earnings reports
- **API Endpoint**: `https://finnhub.io/api/v1/news`
- **Integration**:
  ```python
  # Stock-specific news
  GET /api/v1/company-news?symbol={symbol}&from={date}&to={date}
  ```

##### Polygon.io
- **Type**: API
- **Coverage**: Stock market data, news, real-time quotes
- **Cost**: Free tier (5 calls/minute), Starter ($29/month)
- **Reliability**: 0.92
- **Use Case**: Stock news, market data, real-time updates
- **API Endpoint**: `https://api.polygon.io/v2/reference/news`
- **Integration**:
  ```python
  # Ticker news
  GET /v2/reference/news?ticker={symbol}&limit=5
  ```

##### NewsAPI
- **Type**: API
- **Coverage**: General news, business news, international coverage
- **Cost**: Free tier (100 requests/day), Premium ($449/month)
- **Reliability**: 0.80
- **Use Case**: General financial news, international markets
- **API Endpoint**: `https://newsapi.org/v2/everything`
- **Integration**:
  ```python
  # Business news
  GET /v2/top-headlines?category=business&country=us

  # Stock-specific
  GET /v2/everything?q={company_name} OR {symbol}&sortBy=publishedAt
  ```

---

#### 2. Official Economic Sources

##### Federal Reserve System
- **Type**: RSS Feed + Official Website
- **Coverage**: FOMC statements, speeches, economic reports
- **Cost**: Free
- **Reliability**: 1.0 (Official source)
- **Use Case**: Monetary policy, interest rates, Fed announcements
- **RSS Feeds**:
  - Press Releases: `https://www.federalreserve.gov/feeds/press_all.xml`
  - Speeches: `https://www.federalreserve.gov/feeds/speeches.xml`
  - FOMC Calendar: `https://www.federalreserve.gov/feeds/calendar.xml`
- **Integration**:
  ```python
  # Parse RSS feeds
  import feedparser

  feed = feedparser.parse("https://www.federalreserve.gov/feeds/press_all.xml")
  for entry in feed.entries:
      # Process Fed announcement
      process_federal_reserve_news(entry)
  ```

##### U.S. Bureau of Economic Analysis (BEA)
- **Type**: RSS Feed + API
- **Coverage**: GDP, economic indicators, trade data
- **Cost**: Free
- **Reliability**: 1.0 (Official source)
- **Use Case**: Economic indicators (GDP, PCE, trade balance)
- **RSS Feed**: `https://www.bea.gov/rss/rss.xml`
- **API**: `https://apps.bea.gov/api/signup/`

##### U.S. Bureau of Labor Statistics (BLS)
- **Type**: API + RSS
- **Coverage**: Employment, inflation (CPI), wages
- **Cost**: Free
- **Reliability**: 1.0 (Official source)
- **Use Case**: Employment reports, inflation data
- **API**: `https://api.bls.gov/publicAPI/v2/timeseries/data/`
- **RSS**: `https://www.bls.gov/feed/news_release_rss.xml`

---

#### 3. Financial News Publishers (RSS)

##### Reuters Business
- **Type**: RSS Feed
- **Coverage**: Global business news, markets, economics
- **Cost**: Free (RSS)
- **Reliability**: 0.95
- **RSS Feed**: `http://feeds.reuters.com/reuters/businessNews`
- **Use Case**: Breaking business news, market analysis

##### Bloomberg (via APIs)
- **Type**: API (Terminal required)
- **Coverage**: Comprehensive financial news, real-time data
- **Cost**: Expensive (Terminal subscription)
- **Reliability**: 0.98
- **Use Case**: Institutional-grade financial data
- **Note**: Requires Bloomberg Terminal subscription

##### Financial Times
- **Type**: RSS Feed (limited)
- **Coverage**: Global finance, economics, politics
- **Cost**: Free RSS (limited), Subscription for full content
- **Reliability**: 0.93
- **RSS Feed**: `https://www.ft.com/rss/home/us`

##### The Wall Street Journal
- **Type**: RSS Feed (headlines only)
- **Coverage**: U.S. markets, business, economics
- **Cost**: Free RSS (headlines), Subscription for content
- **Reliability**: 0.94
- **RSS Feed**: `https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml`

##### CNBC
- **Type**: RSS Feed
- **Coverage**: Real-time market news, analysis
- **Cost**: Free
- **Reliability**: 0.85
- **RSS Feeds**:
  - Top News: `https://www.cnbc.com/id/100003114/device/rss/rss.html`
  - Economy: `https://www.cnbc.com/id/20910258/device/rss/rss.html`
  - Markets: `https://www.cnbc.com/id/10000664/device/rss/rss.html`

##### MarketWatch
- **Type**: RSS Feed
- **Coverage**: Stock market news, personal finance
- **Cost**: Free
- **Reliability**: 0.82
- **RSS Feeds**:
  - Top Stories: `http://feeds.marketwatch.com/marketwatch/topstories/`
  - Real-time: `http://feeds.marketwatch.com/marketwatch/realtimeheadlines/`

---

#### 4. Specialized Sources

##### Seeking Alpha
- **Type**: API / RSS
- **Coverage**: Stock analysis, earnings, market commentary
- **Cost**: Free tier (limited), Premium
- **Reliability**: 0.75
- **Use Case**: Detailed stock analysis, earnings coverage
- **RSS**: `https://seekingalpha.com/feed.xml`

##### TradingView News
- **Type**: API
- **Coverage**: Stock news, crypto, market analysis
- **Cost**: API available
- **Reliability**: 0.80
- **Use Case**: Real-time stock news, technical analysis

##### Yahoo Finance
- **Type**: Unofficial API / Web scraping
- **Coverage**: Stock news, quotes, financial data
- **Cost**: Free
- **Reliability**: 0.78
- **Use Case**: Stock news, historical data
- **Integration**: Use `yfinance` Python library

---

### Recommended Integration Priority

#### Phase 1: Core APIs (Immediate)
1. **Finnhub** - Real-time stock news (free tier: 60 calls/min)
2. **Polygon.io** - Additional stock news (free tier: 5 calls/min)
3. **Federal Reserve RSS** - Official economic announcements (free, unlimited)

#### Phase 2: Economic Data (Week 2)
4. **BLS API** - Employment and inflation data (free)
5. **BEA API** - GDP and economic indicators (free)
6. **NewsAPI** - General business news (free tier: 100 req/day)

#### Phase 3: Enhanced Coverage (Week 3)
7. **Reuters RSS** - Breaking business news (free)
8. **CNBC RSS** - Real-time market news (free)
9. **MarketWatch RSS** - Additional market coverage (free)

#### Phase 4: Premium (Optional)
10. **Bloomberg API** - Institutional-grade data (requires subscription)
11. **Seeking Alpha Premium** - Detailed analysis (paid)

---

### Source Configuration Table

```sql
-- Insert news sources
INSERT INTO news_sources (name, url, source_type, category, reliability_score, api_name, fetch_frequency_minutes) VALUES
-- APIs
('AlphaVantage', 'https://www.alphavantage.co/', 'api', 'stock_market', 0.85, 'alphavantage', 60),
('Finnhub', 'https://finnhub.io/', 'api', 'stock_market', 0.90, 'finnhub', 15),
('Polygon.io', 'https://polygon.io/', 'api', 'stock_market', 0.92, 'polygon', 15),
('NewsAPI', 'https://newsapi.org/', 'api', 'general', 0.80, 'newsapi', 30),

-- Official Sources
('Federal Reserve', 'https://www.federalreserve.gov/', 'official', 'federal_reserve', 1.0, 'fed_rss', 30),
('Bureau of Labor Statistics', 'https://www.bls.gov/', 'official', 'economics', 1.0, 'bls_api', 1440),
('Bureau of Economic Analysis', 'https://www.bea.gov/', 'official', 'economics', 1.0, 'bea_api', 1440),

-- RSS Feeds
('Reuters Business', 'http://feeds.reuters.com/reuters/businessNews', 'rss', 'general', 0.95, NULL, 15),
('CNBC', 'https://www.cnbc.com/', 'rss', 'stock_market', 0.85, NULL, 15),
('MarketWatch', 'http://feeds.marketwatch.com/', 'rss', 'stock_market', 0.82, NULL, 15),
('Wall Street Journal', 'https://feeds.a.dj.com/', 'rss', 'general', 0.94, NULL, 30),
('Financial Times', 'https://www.ft.com/rss/', 'rss', 'general', 0.93, NULL, 30);
```

---

### Multi-Source Aggregation Strategy

```python
class NewsAggregator:
    """Aggregate news from multiple sources with deduplication."""

    async def fetch_stock_news(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        Fetch stock news from multiple sources.

        Args:
            symbol: Stock ticker symbol
            limit: Number of articles to return

        Returns:
            Aggregated and deduplicated news articles
        """
        sources = [
            self.fetch_from_finnhub(symbol),
            self.fetch_from_polygon(symbol),
            self.fetch_from_alphavantage(symbol),
        ]

        # Fetch from all sources concurrently
        results = await asyncio.gather(*sources, return_exceptions=True)

        # Merge and deduplicate
        all_articles = []
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)

        # Deduplicate by title similarity
        deduplicated = self.deduplicate_articles(all_articles)

        # Sort by published date (most recent first)
        deduplicated.sort(key=lambda x: x['published_at'], reverse=True)

        return deduplicated[:limit]

    def deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles using title similarity."""
        from difflib import SequenceMatcher

        unique_articles = []
        seen_titles = []

        for article in articles:
            title = article['title'].lower()

            # Check similarity with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = SequenceMatcher(None, title, seen_title).ratio()
                if similarity > 0.85:  # 85% similarity threshold
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.append(title)

        return unique_articles
```

---

### News Source Reliability Scoring

```python
def calculate_source_reliability(
    source_accuracy: float,  # 0-1
    update_frequency: int,    # Minutes
    api_uptime: float,        # 0-1
    content_depth: float      # 0-1
) -> float:
    """
    Calculate reliability score for news source.

    Returns:
        Reliability score 0-1
    """
    # Weight factors
    accuracy_weight = 0.40
    frequency_weight = 0.20
    uptime_weight = 0.25
    depth_weight = 0.15

    # Frequency score (lower is better, up to 15 min)
    frequency_score = max(0, 1 - (update_frequency / 60))

    # Calculate weighted score
    reliability_score = (
        source_accuracy * accuracy_weight +
        frequency_score * frequency_weight +
        api_uptime * uptime_weight +
        content_depth * depth_weight
    )

    return round(reliability_score, 3)
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)

#### Day 1-2: Database Setup
- [ ] Create Supabase tables (stock_prices, stock_news, economic_news, news_sources)
- [ ] Set up indexes and constraints
- [ ] Insert initial news sources configuration
- [ ] Test database queries and relationships

#### Day 3-4: Redis LFU Cache
- [ ] Implement LFU cache manager
- [ ] Set up Redis with LFU eviction policy
- [ ] Implement cache access tracking
- [ ] Test LFU eviction logic

#### Day 5: API Foundation
- [ ] Create API route structure
- [ ] Implement authentication middleware
- [ ] Set up error handling
- [ ] Create Pydantic models

---

### Phase 2: Stock APIs (Week 2)

#### Day 6-7: Stock Prices
- [ ] Implement `/api/v1/stocks/{symbol}/price` endpoint
- [ ] Implement `/api/v1/stocks/prices/batch` endpoint
- [ ] Integrate with AlphaVantage/yfinance
- [ ] Add LFU caching layer
- [ ] Test cache hit rates

#### Day 8-9: Stock News Stack
- [ ] Implement news stack data structure
- [ ] Create `/api/v1/stocks/{symbol}/news` endpoint
- [ ] Implement stack push/pop logic
- [ ] Add news archival mechanism
- [ ] Integrate Finnhub API

#### Day 10: Testing & Optimization
- [ ] Write unit tests for stock APIs
- [ ] Performance testing
- [ ] Cache optimization
- [ ] Documentation

---

### Phase 3: Economic News APIs (Week 3)

#### Day 11-12: Economic News
- [ ] Implement `/api/v1/news/economic` endpoint
- [ ] Integrate Federal Reserve RSS feeds
- [ ] Create news categorization logic
- [ ] Add sentiment analysis

#### Day 13-14: Specialized Endpoints
- [ ] Implement `/api/v1/news/federal-reserve` endpoint
- [ ] Implement `/api/v1/news/politics` endpoint
- [ ] Integrate NewsAPI
- [ ] Add breaking news detection

#### Day 15: Integration
- [ ] Create `/api/v1/dashboard` endpoint
- [ ] Implement multi-source aggregation
- [ ] Add deduplication logic
- [ ] Test end-to-end flows

---

### Phase 4: Additional Sources (Week 4)

#### Day 16-18: API Integrations
- [ ] Integrate Polygon.io
- [ ] Integrate BLS API (employment/inflation)
- [ ] Integrate BEA API (GDP)
- [ ] Add RSS feed parsers (Reuters, CNBC, MarketWatch)

#### Day 19-20: Polish & Deploy
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Deploy to production

---

### Success Metrics

#### Performance Targets
- **API Response Time**: < 200ms (with cache), < 2s (without cache)
- **Cache Hit Rate**: > 80% for stock prices, > 70% for news
- **Database Query Time**: < 50ms for most queries
- **News Update Latency**: < 5 minutes for breaking news

#### Quality Metrics
- **News Deduplication Rate**: > 90% duplicates removed
- **Source Reliability**: Average reliability score > 0.85
- **API Uptime**: > 99.5%
- **Data Freshness**: Stock prices < 1 min old during market hours

---

## Appendix

### A. Example API Responses

See [API Endpoints](#api-endpoints) section for detailed response examples.

### B. Error Handling

All API endpoints return standardized error responses:

```json
{
  "error": {
    "code": "STOCK_NOT_FOUND",
    "message": "Stock symbol 'XYZ' not found",
    "status": 404,
    "timestamp": "2025-10-17T14:35:00Z",
    "request_id": "req_abc123"
  }
}
```

### C. Rate Limiting

All API endpoints are rate-limited:
- **Free tier**: 100 requests/minute
- **Premium tier**: 1000 requests/minute
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### D. Authentication

All endpoints require API key authentication:
```http
Authorization: Bearer {API_KEY}
```

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Supabase Documentation](https://supabase.com/docs)
- [Upstash Redis Documentation](https://docs.upstash.com/redis)
- [AlphaVantage API Docs](https://www.alphavantage.co/documentation/)
- [Finnhub API Docs](https://finnhub.io/docs/api)
- [Polygon.io API Docs](https://polygon.io/docs/stocks/getting-started)
- [Federal Reserve Data](https://www.federalreserve.gov/feeds/)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-17
**Author**: AI Agent
**Status**: Ready for Implementation

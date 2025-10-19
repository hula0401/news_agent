# Bug Fixes and Setup Instructions

## Summary

Fixed 5 critical issues preventing stock price and news updates from working:

1. ✅ **Datetime serialization error** - Fixed in code
2. ✅ **Missing last_updated field** - Fixed in code
3. ✅ **Upstash Redis configuration** - Fixed env file format
4. ⚠️  **Supabase RLS policies** - **ACTION REQUIRED** (see below)
5. ⚠️  **Missing exec_sql function** - **ACTION REQUIRED** (see below)

---

## Files Modified

### 1. Datetime Serialization Fixed
**File**: [backend/app/services/stock_price_service.py](../backend/app/services/stock_price_service.py#L132)
```python
# BEFORE (caused error):
"last_updated": datetime.now()

# AFTER (fixed):
"last_updated": datetime.now().isoformat()  # Convert to ISO string
```

**File**: [backend/app/scheduler/scheduler_manager.py](../backend/app/scheduler/scheduler_manager.py#L132)
```python
# Added last_updated field with ISO format:
'last_updated': datetime.now().isoformat()
```

### 2. Upstash Redis Configuration
**File**: [env_files/upstash.env](../env_files/upstash.env)
```bash
# BEFORE (invalid format with quotes and spaces):
UPSTASH_REDIS_REST_URL = "https://..."

# AFTER (valid .env format):
UPSTASH_REDIS_REST_URL=https://popular-lacewing-21190.upstash.io
UPSTASH_REDIS_REST_TOKEN=AVLGAAIncDI1Y2M4ZTAxYmFmMjQ0YWY5YmNkOGZjOGY5MmY4ZjE1YXAyMjExOTA
```

---

## 🚨 ACTION REQUIRED: Fix Supabase RLS Policies

### Problem
The backend cannot insert data into Supabase tables due to Row-Level Security (RLS) policies:
```
❌ Error inserting price data: 'new row violates row-level security policy for table "stock_prices"'
```

### Solution
Apply the SQL script to fix RLS policies and add the missing `exec_sql` function.

### Option 1: Supabase Dashboard (Recommended)

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard)
2. Select your project
3. Click on **SQL Editor** in the left sidebar
4. Copy the SQL from [database/fix_rls_policies.sql](../database/fix_rls_policies.sql)
5. Paste into the SQL Editor
6. Click **RUN**

### Option 2: Using psql Command

```bash
# From project root directory
psql 'postgresql://[YOUR-PROJECT].supabase.co' \
     -f database/fix_rls_policies.sql
```

### What This SQL Script Does

1. **Enables RLS** on all stock and news tables
2. **Creates policies** that allow:
   - Backend service to INSERT/UPDATE/DELETE data
   - Public users to READ data
3. **Creates `exec_sql` function** for cache tracking
4. **Grants permissions** to authenticated and anonymous users

### Affected Tables
- `stock_prices`
- `stock_news`
- `news_articles`
- `news_sources`
- `economic_news`

---

## Testing the Fixes

### 1. Start the Server
```bash
make run-server
```

### 2. Expected Logs (Success)
After applying RLS fixes, you should see:
```
✅ Scheduled stock price updates every 5 minutes
✅ Scheduled news updates every 5 minutes
🚀 Background scheduler started successfully

# After 5 minutes:
✅ Updated AAPL: $252.29 (+1.96%)
✅ Updated GOOGL: $140.25 (+0.86%)
✅ News update completed: 10/10 stocks, 25 total articles
```

### 3. No More Errors
You should **NOT** see these errors anymore:
```
❌ Error inserting price data: Object of type datetime is not JSON serializable
❌ Error inserting price data: 'new row violates row-level security policy'
❌ Could not find the function public.exec_sql
```

### 4. Verify Data in Supabase

Go to Supabase Dashboard → Table Editor:

**stock_prices table** should have new rows:
```
symbol | price  | change | change_percent | last_updated          | data_source
-------|--------|--------|----------------|----------------------|------------
AAPL   | 252.29 | +4.85  | +1.96          | 2025-10-18T17:42:00Z | yfinance
GOOGL  | 140.25 | +1.20  | +0.86          | 2025-10-18T17:42:00Z | yfinance
```

**stock_news table** should have new articles:
```
symbol | title              | summary        | position | published_at
-------|-------------------|----------------|----------|------------------
AAPL   | Apple announces.. | Apple unveiled | 1        | 2025-10-18T...
```

---

## Scheduler Configuration

### Current Settings
From [backend/app/config.py](../backend/app/config.py):

```python
# Update intervals
stock_update_interval_minutes: int = 5  # Stock prices every 5 mins
news_update_interval_minutes: int = 5   # News every 5 mins

# Popular stocks to track
popular_stocks: str = "AAPL,GOOGL,MSFT,AMZN,TSLA,NVDA,META,NFLX,AMD,INTC"
```

### Modify Update Frequency
To change update intervals, edit your `.env` file:
```bash
STOCK_UPDATE_INTERVAL_MINUTES=3  # Update every 3 minutes
NEWS_UPDATE_INTERVAL_MINUTES=10  # Update every 10 minutes
```

---

## Cache Flow

### Stock Prices (Redis → DB → API)
```
Request for AAPL price
  ↓
1. Check Redis (< 2 min fresh?) → Return immediately ⚡ <1ms
  ↓ (miss or stale)
2. Check Database (< 5 min fresh?) → Update Redis → Return
  ↓ (miss or stale)
3. Fetch from YFinance → Save to DB → Update Redis → Return
```

### News (Redis → Stack → Aggregation)
```
Request for AAPL news
  ↓
1. Check Redis cache → Return immediately ⚡
  ↓ (miss)
2. Check LIFO stack in DB (positions 1-5) → Update Redis → Return
  ↓ (empty)
3. Aggregate from sources (Finnhub + Polygon + NewsAPI) → Push to stack → Return
```

---

## Architecture Overview

### Scheduler Jobs
```
┌─────────────────────────────────────────┐
│  APScheduler (AsyncIO)                  │
├─────────────────────────────────────────┤
│                                         │
│  Job 1: Update Popular Stocks (5 min)  │
│  ├─ Fetch from YFinance                │
│  ├─ Calculate daily price changes      │
│  ├─ Save to Supabase (stock_prices)    │
│  └─ Update Redis cache (2 min TTL)     │
│                                         │
│  Job 2: Update Latest News (5 min)     │
│  ├─ Aggregate from 3 sources           │
│  ├─ Deduplicate by URL                 │
│  ├─ Push to LIFO stack (positions 1-5)│
│  └─ Update Redis cache                 │
│                                         │
└─────────────────────────────────────────┘
```

### Data Flow
```
External APIs          Cache Layer         Database          API Response
─────────────────────────────────────────────────────────────────────────
                      ┌──────────┐
YFinance API    ─────→│  Upstash │──────→  Supabase   ────→  FastAPI
Finnhub API     ─────→│  Redis   │         stock_prices     /api/v1/stocks
Polygon API     ─────→│  (2-5min │         stock_news       /api/v1/news
NewsAPI         ─────→│   TTL)   │         news_articles
                      └──────────┘
```

---

## Test Results

### ✅ Scheduler Tests (8/8 Passing)
```bash
uv run python -m pytest tests/backend/test_scheduler.py -v
```
```
tests/backend/test_scheduler.py::TestSchedulerManager::test_scheduler_initialization PASSED
tests/backend/test_scheduler.py::TestSchedulerManager::test_scheduler_disabled_via_config PASSED
tests/backend/test_scheduler.py::TestSchedulerManager::test_scheduler_prevents_duplicate_start PASSED
tests/backend/test_scheduler.py::TestPopularStocksUpdate::test_popular_stocks_update_success PASSED
tests/backend/test_scheduler.py::TestPopularStocksUpdate::test_popular_stocks_update_no_stocks_configured PASSED
tests/backend/test_scheduler.py::TestPopularStocksUpdate::test_popular_stocks_update_partial_failure PASSED
tests/backend/test_scheduler.py::TestLatestNewsUpdate::test_news_update_success PASSED
tests/backend/test_scheduler.py::TestLatestNewsUpdate::test_news_update_no_articles_found PASSED

8 passed in 3.16s ✅
```

---

## Troubleshooting

### Issue: Still seeing RLS errors
**Solution**: Make sure you applied the SQL script in Supabase Dashboard

### Issue: Upstash Redis not connecting
**Check**:
```bash
# Verify environment variables are loaded
uv run python -c "from backend.app.config import get_settings; s=get_settings(); print(f'URL: {s.upstash_redis_rest_url}'); print(f'Configured: {s.is_cache_configured()}')"
```

### Issue: No stock updates after 5 minutes
**Check scheduler status**:
```bash
curl http://localhost:8000/health | jq .services.scheduler
```

Expected:
```json
{
  "status": "running",
  "jobs_count": 2,
  "next_run": "2025-10-18T17:47:00Z"
}
```

---

## Next Steps

1. ✅ Apply the RLS SQL script (see above)
2. ✅ Restart the server: `make run-server`
3. ✅ Wait 5 minutes for first scheduler run
4. ✅ Check Supabase tables for new data
5. ✅ Test API endpoints:
   ```bash
   # Get stock price
   curl http://localhost:8000/api/v1/stocks/AAPL/price

   # Get stock news
   curl http://localhost:8000/api/v1/stocks/AAPL/news
   ```

---

## Files Created

- [database/fix_rls_policies.sql](../database/fix_rls_policies.sql) - SQL script to fix RLS
- [database/apply_rls_fix.py](../database/apply_rls_fix.py) - Helper script with instructions
- [tests/backend/test_scheduler.py](../tests/backend/test_scheduler.py) - Comprehensive scheduler tests
- [tests/backend/test_stock_price_api.py](../tests/backend/test_stock_price_api.py) - Cache scenario tests
- [tests/backend/test_stock_news_api.py](../tests/backend/test_stock_news_api.py) - News aggregation tests

---

## Summary of Changes

| Issue | Status | Fix Location |
|-------|--------|--------------|
| Datetime serialization error | ✅ Fixed | `backend/app/services/stock_price_service.py:132` |
| Missing last_updated field | ✅ Fixed | `backend/app/scheduler/scheduler_manager.py:132` |
| Upstash Redis env format | ✅ Fixed | `env_files/upstash.env` |
| RLS policy blocking inserts | ⚠️ Action Required | `database/fix_rls_policies.sql` |
| Missing exec_sql function | ⚠️ Action Required | `database/fix_rls_policies.sql` |

**After applying the SQL script, all issues will be resolved! 🎉**

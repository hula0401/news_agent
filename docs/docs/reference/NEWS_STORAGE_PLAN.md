# News Storage & Categorization Plan

## Current Status

### ✅ What's Working
- Stock prices update every 5 minutes via scheduler
- Prices saved to Supabase `stock_prices` table
- Redis caching with 2-minute TTL
- YFinance integration for daily price changes

### ⚠️ What Needs Implementation

1. **News Categorization** - LLM-based categorization not yet implemented
2. **Session-based News Storage** - Save news discussed during conversation
3. **Audio URL Storage** - Missing `audio_url` column in conversation_messages

---

## Architecture Overview

### Current Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     SCHEDULER (Every 5 mins)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Stock Prices:                                                   │
│  YFinance → Supabase stock_prices → Redis (2 min TTL)          │
│  ✅ WORKING                                                      │
│                                                                  │
│  News Updates:                                                   │
│  Finnhub + Polygon + NewsAPI → ??? → Supabase                  │
│  ⚠️  NEEDS: Categorization & Storage Logic                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  CONVERSATION SESSION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User asks about stock/news                                     │
│         ↓                                                        │
│  Agent fetches relevant news                                    │
│         ↓                                                        │
│  Agent responds with news summary                               │
│         ↓                                                        │
│  Session ends → Save discussed news to DB                       │
│  ⚠️  NEEDS: Implementation                                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Proposed Solution

### Phase 1: Session-Based News Storage (Immediate)

**Goal**: Save news articles that were discussed during a conversation session

**Implementation**:

1. **Track News in Session Context**
   ```python
   # In WebSocketManager or ConversationTracker
   class SessionContext:
       session_id: str
       user_id: str
       discussed_news: List[Dict]  # News articles mentioned
       discussed_stocks: Set[str]   # Stock symbols mentioned
   ```

2. **On Session End, Save to Database**
   ```python
   async def end_session(session_id: str):
       # Get all news discussed in this session
       news_articles = session_context.discussed_news

       for article in news_articles:
           await save_news_article(article, session_id=session_id)
   ```

3. **Database Schema**
   ```sql
   -- Existing table: news_articles
   CREATE TABLE news_articles (
       id UUID PRIMARY KEY,
       title TEXT NOT NULL,
       summary TEXT,
       content TEXT,
       url TEXT UNIQUE,
       source_id UUID REFERENCES news_sources(id),
       published_at TIMESTAMPTZ,
       created_at TIMESTAMPTZ DEFAULT NOW(),

       -- NEW: Session tracking
       session_id UUID,  -- Which session discussed this
       user_id UUID,     -- Which user saw this

       -- NEW: Categorization (optional for Phase 2)
       category TEXT,    -- e.g., 'earnings', 'merger', 'product'
       sentiment TEXT,   -- 'positive', 'negative', 'neutral'
       relevance_score FLOAT
   );

   -- Link news to stocks
   CREATE TABLE stock_news (
       stock_symbol TEXT,
       news_id UUID REFERENCES news_articles(id),
       position INT,  -- LIFO stack position (1-5)
       PRIMARY KEY (stock_symbol, news_id)
   );
   ```

**Files to Modify**:
- [backend/app/core/websocket_manager.py](../backend/app/core/websocket_manager.py) - Track discussed news
- [backend/app/core/conversation_tracker.py](../backend/app/core/conversation_tracker.py) - Save on session end
- [backend/app/db/stock_news.py](../backend/app/db/stock_news.py) - Add save methods

---

### Phase 2: LLM-Based News Categorization (Future)

**Goal**: Automatically categorize news using LLM before storing

**When to Use**:
- Scheduler job: Categorize fetched news before storing
- Session end: Categorize discussed news before saving

**Implementation**:

```python
from openai import AsyncOpenAI  # or your LLM provider

class NewsCategorizer:
    """Categorize news articles using LLM."""

    async def categorize_article(self, article: Dict) -> Dict:
        """
        Categorize a news article.

        Returns:
            {
                'category': 'earnings' | 'merger' | 'product' | 'legal' | 'other',
                'sentiment': 'positive' | 'negative' | 'neutral',
                'relevance_score': 0.0 - 1.0,
                'key_topics': ['AI', 'revenue', 'guidance'],
                'summary': 'Brief 1-sentence summary'
            }
        """
        prompt = f"""
        Categorize this news article:

        Title: {article['title']}
        Summary: {article.get('summary', '')}

        Provide:
        1. Category (earnings/merger/product/legal/other)
        2. Sentiment (positive/negative/neutral)
        3. Relevance score (0-1)
        4. Key topics (list)
        5. One-sentence summary

        Output as JSON.
        """

        response = await self.llm.chat.completions.create(
            model="gpt-4o-mini",  # Fast and cheap
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)
```

**Cost Optimization**:
- Use `gpt-4o-mini` ($0.15/1M input tokens, $0.60/1M output)
- Batch categorize (10-20 articles per request)
- Cache categorizations by URL
- Only categorize new/uncategorized articles

**When to Run**:
- **Option A**: Real-time during scheduler (adds latency)
- **Option B**: Background job after fetching (recommended)
- **Option C**: Lazy categorization when first accessed

---

### Phase 3: Conversation Audio Storage (Immediate Fix)

**Problem**: Missing `audio_url` column in `conversation_messages`

**Solution**: Apply SQL migration

**SQL Script**: [database/add_audio_url_column.sql](../database/add_audio_url_column.sql)

```sql
ALTER TABLE conversation_messages
ADD COLUMN IF NOT EXISTS audio_url TEXT;
```

**Apply via Supabase Dashboard**:
1. Go to SQL Editor
2. Run the migration script
3. Restart server

---

## Recommended Implementation Order

### Sprint 1: Critical Fixes (Today)
1. ✅ Fix datetime timezone issues (DONE)
2. **Add `audio_url` column** → Run SQL migration
3. **Test TSLA API** → Should work after timezone fix
4. **Verify stock prices** → Check Supabase table

### Sprint 2: Session News Storage (Next)
1. Add `session_id` and `user_id` to `news_articles` table
2. Implement news tracking in session context
3. Save discussed news on session end
4. Test end-to-end flow

### Sprint 3: LLM Categorization (Future - Optional)
1. Create `NewsCategorizer` class
2. Integrate with scheduler (background job)
3. Add category filters to API endpoints
4. Monitor costs and performance

---

## Database Migrations Needed

### 1. Add audio_url column (NOW)
```bash
# In Supabase SQL Editor, run:
database/add_audio_url_column.sql
```

### 2. Extend news_articles table (NEXT)
```sql
ALTER TABLE news_articles
ADD COLUMN IF NOT EXISTS session_id UUID,
ADD COLUMN IF NOT EXISTS user_id UUID,
ADD COLUMN IF NOT EXISTS category TEXT,
ADD COLUMN IF NOT EXISTS sentiment TEXT,
ADD COLUMN IF NOT EXISTS relevance_score FLOAT;

CREATE INDEX idx_news_session ON news_articles(session_id);
CREATE INDEX idx_news_user ON news_articles(user_id);
CREATE INDEX idx_news_category ON news_articles(category);
```

---

## News Storage Strategy Decision Tree

```
New News Article Available
    ↓
    Is it from scheduler?
        YES → Store immediately to stock_news LIFO stack
        NO → Is it from user conversation?
                YES → Track in session context
                        ↓
                        Session ends?
                            YES → Save to news_articles + stock_news
                            NO → Keep in memory
                NO → Ignore
```

---

## API Endpoints to Implement

### Current (Partially Working)
- `GET /api/v1/stocks/{symbol}/price` - ✅ Working
- `GET /api/v1/stocks/{symbol}/news` - ⚠️ Needs fixing

### Proposed New Endpoints
```python
# Get categorized news
GET /api/v1/news?category=earnings&sentiment=positive&limit=10

# Get session news history
GET /api/v1/sessions/{session_id}/news

# Get user's discussed news
GET /api/v1/users/{user_id}/news-history?days=7
```

---

## Cost Estimate for LLM Categorization

**Assumptions**:
- 10 stocks tracked
- 5 news articles per stock per day = 50 articles/day
- Average article: ~200 tokens input + 50 tokens output
- Model: gpt-4o-mini

**Daily Cost**:
```
Input:  50 articles × 200 tokens × $0.15/1M = $0.0015
Output: 50 articles × 50 tokens × $0.60/1M  = $0.0015
Total:  ~$0.003/day = $0.09/month
```

**Conclusion**: Very affordable, can enable immediately if needed.

---

## Questions to Answer

1. **Do we need real-time categorization?**
   - If YES → Use gpt-4o-mini during scheduler
   - If NO → Store raw, categorize later

2. **Should we store ALL fetched news or only discussed?**
   - ALL → Use scheduler + background categorization
   - DISCUSSED → Use session-based approach (recommended)

3. **How long to keep news articles?**
   - Suggestion: 30 days, then archive to cheaper storage

4. **Do we need full-text search?**
   - If YES → Add `to_tsvector` index for PostgreSQL FTS
   - If NO → Simple LIKE/ILIKE queries sufficient

---

## Next Actions for User

### Immediate (5 minutes)
1. Apply SQL migration for audio_url:
   ```sql
   -- In Supabase SQL Editor
   ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS audio_url TEXT;
   ```

2. Restart server:
   ```bash
   make run-server
   ```

3. Test TSLA API:
   ```bash
   curl http://localhost:8000/api/v1/stocks/TSLA/price
   ```

### Short-term (Next Session)
1. Decide on news storage strategy (scheduler vs session-based)
2. Implement chosen approach
3. Test news flow end-to-end

### Long-term (Optional)
1. Add LLM categorization if needed
2. Implement advanced search/filters
3. Add analytics dashboard

---

## Current vs Future Architecture

### Current (After Immediate Fixes)
```
Stock Prices: ✅ Scheduler → DB → Redis → API
News Fetching: ✅ Scheduler → Aggregation
News Storage: ❌ Not implemented
Audio URL: ✅ After migration
```

### Future (After Full Implementation)
```
Stock Prices: ✅ Complete
News Pipeline: ✅ Scheduler → Aggregation → Categorization → DB → Redis → API
Session Tracking: ✅ Track discussed news → Save on end
Audio Storage: ✅ With URL in DB
```

---

## Files to Create/Modify

### Create
- [backend/app/services/news_categorizer.py](../backend/app/services/news_categorizer.py) - LLM categorization (Phase 2)
- [backend/app/models/session_news.py](../backend/app/models/session_news.py) - Session news model (Phase 1)

### Modify
- [backend/app/core/conversation_tracker.py](../backend/app/core/conversation_tracker.py) - Track discussed news
- [backend/app/db/stock_news.py](../backend/app/db/stock_news.py) - Add save methods
- [backend/app/scheduler/scheduler_manager.py](../backend/app/scheduler/scheduler_manager.py) - Add news storage

---

**Decision**: Let me know which approach you prefer for news storage:
- **A**: Session-based (only save discussed news) - Simpler, less storage
- **B**: Scheduler-based (save all fetched news) - More comprehensive, enables search
- **C**: Hybrid (scheduler saves raw, session adds metadata) - Best of both

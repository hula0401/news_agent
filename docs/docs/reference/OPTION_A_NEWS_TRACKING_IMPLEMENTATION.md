# Option A: Session-Based News Tracking - Implementation Complete

## Summary

Implemented session-based news tracking that saves only news discussed in actual conversations (Option A). When users ask about Tesla, Apple, etc., the news mentioned in the agent's response is automatically tracked and saved to the database when the session ends.

## Implementation Details

### 1. News Tracking Methods ✅ IMPLEMENTED

Added to [conversation_tracker.py](../backend/app/core/conversation_tracker.py):

```python
def track_discussed_news(
    session_id, stock_symbol, news_title,
    news_url=None, news_source=None, published_at=None
)
```
- Tracks news discussed during conversation
- Stores in session state memory
- Logged: "📰 Tracked news for TSLA in session abc12345..."

```python
async def _save_discussed_news(session_id)
```
- Called during `end_session()`
- Saves all tracked news to `session_news` table
- Links news to conversation via FK
- Logged: "✅ Saved 2 news items for session abc12345... (stocks: TSLA, AAPL)"

### 2. Automatic News Detection ✅ IMPLEMENTED

Added to [websocket_manager.py:1010](../backend/app/core/websocket_manager.py#L1010):

```python
async def _track_news_from_response(
    session_id, user_input, agent_response
)
```

**Detection Logic**:
1. Detects stock symbols: TSLA, AAPL, GOOGL, MSFT, AMZN, NVDA, META
2. Maps company names: "Tesla" → "TSLA", "Apple" → "AAPL", etc.
3. Checks for news keywords: "news", "article", "reports", "announced", "feedback"
4. Extracts title from `**Title**` markdown or first sentence
5. Automatically calls `conversation_tracker.track_discussed_news()`

**Example Flow**:
```
User: "What's the latest news about Tesla?"
Agent: "**Tesla Gets Feedback on More Affordable Models...**"
         ↓
Detected: symbol=TSLA, title="Tesla Gets Feedback on More Affordable Models"
         ↓
Tracked: conversation_tracker.track_discussed_news(TSLA, title)
         ↓
Session ends
         ↓
Saved to database: session_news table
```

### 3. Database Schema ✅ CREATED (USER ACTION REQUIRED)

**File**: [database/create_session_news_table.sql](../database/create_session_news_table.sql)

**Schema**:
```sql
CREATE TABLE session_news (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    stock_symbol VARCHAR(10) NOT NULL,
    news_title TEXT NOT NULL,
    news_url TEXT,
    news_source VARCHAR(255),
    published_at TIMESTAMPTZ,
    discussed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Indexes**:
- `idx_session_news_session_id` - Fast session lookups
- `idx_session_news_stock_symbol` - Fast stock symbol queries
- `idx_session_news_discussed_at` - Chronological ordering

**RLS Policy**: Allows service role full access

## How It Works

### Conversation Flow

1. **User asks about stock news**:
   ```
   User: "Tell me the latest news about Tesla"
   ```

2. **Agent responds with news**:
   ```
   Agent: "Based on the latest news, here's what I found about Tesla:

   **Tesla Gets Feedback on More Affordable Models. Hint: It's Not Inspiring**

   While Tesla recently unveiled its more affordable Model 3 and Model Y..."
   ```

3. **Auto-detection** ([websocket_manager.py:534](../backend/app/core/websocket_manager.py#L534)):
   - Detects "Tesla" → TSLA
   - Finds news keywords ("latest news")
   - Extracts title from `**...**`
   - Calls `track_discussed_news()`

4. **In-memory tracking** ([conversation_tracker.py:380](../backend/app/core/conversation_tracker.py#L380)):
   ```python
   session_states[session_id]["discussed_news"].append({
       "stock_symbol": "TSLA",
       "title": "Tesla Gets Feedback on More Affordable Models...",
       "discussed_at": "2025-10-18T22:10:27.000321"
   })
   ```

5. **Session ends** ([conversation_tracker.py:202](../backend/app/core/conversation_tracker.py#L202)):
   ```python
   await self._save_discussed_news(session_id)
   ```

6. **Database insert** ([conversation_tracker.py:419](../backend/app/core/conversation_tracker.py#L419)):
   ```sql
   INSERT INTO session_news (session_id, stock_symbol, news_title, ...)
   VALUES (db_id, 'TSLA', 'Tesla Gets Feedback...', ...)
   ```

### Session State Structure

```python
session_states[session_id] = {
    "user_id": "03f6b167-...",
    "db_id": "1654bac7-...",  # FK for messages and news
    "session_start": datetime,
    "is_active": True,
    "message_count": 2,
    "metadata": {},
    "discussed_news": [
        {
            "stock_symbol": "TSLA",
            "title": "Tesla Gets Feedback on More Affordable Models...",
            "url": None,
            "source": None,
            "published_at": None,
            "discussed_at": "2025-10-18T22:10:27Z"
        }
    ],
    "discussed_stocks": {"TSLA"}
}
```

## Action Required

### 1. Create Database Table ⚠️

```bash
# In Supabase Dashboard → SQL Editor
# Run: database/create_session_news_table.sql
```

This creates:
- `session_news` table
- Indexes for performance
- RLS policies for security

### 2. Restart Server

```bash
make run-server
```

### 3. Test the Flow

```bash
# Test via voice or WebSocket
# User: "What's the latest news about Tesla?"
# Expected logs:
#   📰 Tracked news: TSLA - Tesla Gets Feedback on More Affordable Models...
#   ✅ Ended session abc12345... (duration: 45.2s, messages: 4)
#   ✅ Saved 1 news items for session abc12345... (stocks: TSLA)
```

### 4. Verify in Database

```sql
-- Check saved news
SELECT * FROM session_news
WHERE stock_symbol = 'TSLA'
ORDER BY discussed_at DESC
LIMIT 5;

-- Check with session details
SELECT
    sn.stock_symbol,
    sn.news_title,
    sn.discussed_at,
    cs.user_id,
    cs.started_at,
    cs.ended_at
FROM session_news sn
JOIN conversation_sessions cs ON sn.session_id = cs.id
ORDER BY sn.discussed_at DESC;
```

## Supported Stocks

Currently detects these symbols:
- TSLA (Tesla)
- AAPL (Apple)
- GOOGL (Google)
- MSFT (Microsoft)
- AMZN (Amazon)
- NVDA (Nvidia)
- META (Facebook/Meta)

**To add more**: Edit [websocket_manager.py:1020](../backend/app/core/websocket_manager.py#L1020)

## Benefits of Option A

1. **Storage Efficient**: Only saves news users actually discussed
2. **Relevant Data**: No noise from unused news articles
3. **Session Context**: Links news to conversation for analytics
4. **User Insights**: See what topics users are interested in

## Example Queries

### Most Discussed Stocks
```sql
SELECT stock_symbol, COUNT(*) as discussion_count
FROM session_news
GROUP BY stock_symbol
ORDER BY discussion_count DESC;
```

### Recent News Discussions
```sql
SELECT
    sn.stock_symbol,
    sn.news_title,
    sn.discussed_at,
    cs.user_id
FROM session_news sn
JOIN conversation_sessions cs ON sn.session_id = cs.id
WHERE sn.discussed_at > NOW() - INTERVAL '24 hours'
ORDER BY sn.discussed_at DESC;
```

### User's News History
```sql
SELECT
    sn.stock_symbol,
    sn.news_title,
    sn.discussed_at
FROM session_news sn
JOIN conversation_sessions cs ON sn.session_id = cs.id
WHERE cs.user_id = '03f6b167-0c4d-4983-a380-54b8eb42f830'
ORDER BY sn.discussed_at DESC;
```

## Troubleshooting

### News not being tracked?

1. **Check logs**: Look for "📰 Tracked news:" messages
2. **Verify keywords**: Ensure response contains news keywords
3. **Check symbol detection**: Add debug print in `_track_news_from_response`

### DNS error on session end?

This is a known issue with Supabase client connection. The session end update might fail with "nodename nor servname provided" error. This doesn't affect news tracking (which happens in-memory first) but prevents saving to database.

**Temporary workaround**: News is tracked in memory, so if the session update works, news will be saved. Monitor logs for "✅ Saved X news items" message.

## Files Modified

1. [backend/app/core/conversation_tracker.py](../backend/app/core/conversation_tracker.py)
   - Added `track_discussed_news()` method
   - Added `_save_discussed_news()` method
   - Updated `end_session()` to save news

2. [backend/app/core/websocket_manager.py](../backend/app/core/websocket_manager.py)
   - Added `_track_news_from_response()` method
   - Auto-tracking on agent response

3. [database/create_session_news_table.sql](../database/create_session_news_table.sql)
   - New table schema
   - Indexes
   - RLS policies

## Next Steps

After table creation:
1. Test with real conversations
2. Add more stock symbols as needed
3. Improve title extraction logic
4. Add news URL/source extraction if available from agent
5. Create analytics dashboard for news trends

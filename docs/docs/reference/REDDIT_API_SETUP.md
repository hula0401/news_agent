# External API Setup: Reddit

Brief guide to configure and use the Reddit API (read-only) with this project.

Last Updated: 2025-10-17
Version: Docs v0.1

---
## Overview

- This document describes how to obtain Reddit API credentials and configure them for development.
- Focuses on read-only access for fetching posts/comments for news summarization workflows.
- Works with popular Python client libraries such as `praw` or `asyncpraw`.

---

Install (choose one):

```bash
uv add praw
# or
uv add asyncpraw
```

---

## Create a Reddit App

1. Go to `https://www.reddit.com/prefs/apps` while logged in.
2. Click “Create another app”.
3. Choose “script” type for server-to-server usage.
4. Set a name (e.g., "Voice News Agent").
5. Set redirect URI to `http://localhost:8080` (required by Reddit, not used for script flows).
6. After creation, note the `client id` (under the app name) and the `client secret`.

---

## Environment Variables

Add these to `backend/.env`:

```bash
REDDIT_CLIENT_ID=your-client-id
REDDIT_CLIENT_SECRET=your-client-secret
REDDIT_USER_AGENT=voice-news-agent/0.1 by your-reddit-username
```

## Verify variables are loaded when running the backend or scripts that access Reddit.

## Usage Examples

### Example (praw synchronous)

```python
import os
import praw

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT", "voice-news-agent/0.1"),
)

subreddit = reddit.subreddit("news")
for submission in subreddit.hot(limit=5):
    print(submission.title)
```

### Example (asyncpraw asynchronous)

```python
import os
import asyncio
import asyncpraw

async def main():
    reddit = asyncpraw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "voice-news-agent/0.1"),
    )
    subreddit = await reddit.subreddit("news")
    async for submission in subreddit.hot(limit=5):
        print(submission.title)
    await reddit.close()

asyncio.run(main())
```

---

## Troubleshooting

- Invalid credentials: Regenerate secret on the Reddit app page and update `.env`.
- 401/403 errors: Check `user_agent` format; ensure it includes an app name and your username.
- Rate limits: Respect Reddit API limits; add delays or smaller page sizes.
- Corporate networks: Proxy/VPN may be required; test on a different network.

---

## References

- Reddit Apps: `https://www.reddit.com/prefs/apps`
- PRAW Docs: `https://praw.readthedocs.io`
- asyncpraw Docs: `https://asyncpraw.readthedocs.io`
- Existing setup docs: [docs/LOCAL_SETUP.md](../LOCAL_SETUP.md)

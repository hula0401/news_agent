"""Stock news API endpoints with LIFO stack."""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from ...models.stock import (
    StockNewsResponse,
    StockNewsItem,
    StockNewsCreateRequest,
    StockNewsCreateResponse
)
from ...services import get_stock_news_service

router = APIRouter(prefix="/stock-news")


@router.get("/{symbol}/news", response_model=StockNewsResponse)
async def get_stock_news(
    symbol: str,
    limit: int = Query(5, ge=1, le=20, description="Number of news articles"),
    refresh: bool = Query(False, description="Force cache refresh")
):
    """
    Get the latest news for a stock (LIFO stack - Latest 5 on Top).

    - **symbol**: Stock ticker symbol (e.g., AAPL, TSLA)
    - **limit**: Number of articles to return (1-20, default: 5)
    - **refresh**: Force cache refresh

    Returns news from the LIFO stack (positions 1-5).
    """
    try:
        service = await get_stock_news_service()
        news_data = await service.get_stock_news(
            symbol.upper(),
            limit=min(limit, 5),  # Stack only has 5 items
            refresh=refresh
        )

        # Format news items
        news_items = [
            StockNewsItem(
                id=item.get("id", ""),
                title=item.get("title", ""),
                summary=item.get("summary"),
                url=item.get("url"),
                published_at=item.get("published_at", datetime.now()),
                source=item.get("source", {}),
                sentiment_score=item.get("sentiment_score"),
                topics=item.get("topics", []),
                is_breaking=item.get("is_breaking", False),
                position_in_stack=item.get("position_in_stack")
            )
            for item in news_data.get("news", [])
        ]

        return StockNewsResponse(
            symbol=news_data.get("symbol", symbol.upper()),
            news=news_items,
            total_count=news_data.get("total_count", 0),
            last_updated=news_data.get("last_updated", datetime.now()),
            cache_hit=news_data.get("cache_hit", False)
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stock news: {str(e)}"
        )


@router.post("/{symbol}/news", response_model=StockNewsCreateResponse)
async def push_stock_news(
    symbol: str,
    request: StockNewsCreateRequest
):
    """
    Push new news to the top of the stack (position 1).

    This is an internal/admin endpoint for adding news to the stack.
    News at position 6+ will be automatically archived.

    - **symbol**: Stock ticker symbol
    - **request**: News article data

    Returns created news with archived article ID if any.
    """
    try:
        service = await get_stock_news_service()

        # Prepare news data for database
        news_data = {
            "title": request.title,
            "summary": request.summary,
            "url": request.url,
            "published_at": request.published_at,
            "source_id": request.source_id,
            "sentiment_score": request.sentiment_score,
            "topics": request.topics,
            "is_breaking": request.is_breaking
        }

        result = await service.push_news_to_stack(symbol.upper(), news_data)

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to push news to stack"
            )

        return StockNewsCreateResponse(
            id=result.get("id", ""),
            symbol=result.get("symbol", symbol.upper()),
            position_in_stack=result.get("position_in_stack", 1),
            archived_article_id=result.get("archived_article_id"),
            created_at=result.get("created_at", datetime.now())
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error pushing news to stack: {str(e)}"
        )

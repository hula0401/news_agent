"""Stock prices API endpoints."""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
import time
from datetime import datetime

from ...models.stock import (
    StockPriceResponse,
    StockPriceBatchRequest,
    StockPriceBatchResponse
)
from ...services import get_stock_price_service

router = APIRouter(prefix="/stocks")


@router.get("/{symbol}/price", response_model=StockPriceResponse)
async def get_stock_price(
    symbol: str,
    refresh: bool = Query(False, description="Force cache refresh")
):
    """
    Get the latest stock price for a symbol.

    - **symbol**: Stock ticker symbol (e.g., AAPL, GOOGL, MSFT)
    - **refresh**: Force cache refresh (default: false)

    Returns current price with cache metadata.
    """
    try:
        service = await get_stock_price_service()
        price_data = await service.get_stock_price(symbol.upper(), refresh=refresh)

        if not price_data:
            raise HTTPException(
                status_code=404,
                detail=f"Stock price not found for symbol: {symbol}"
            )

        return StockPriceResponse(
            symbol=price_data.get("symbol", symbol.upper()),
            price=price_data.get("price", 0.0),
            change=price_data.get("change"),
            change_percent=price_data.get("change_percent"),
            volume=price_data.get("volume"),
            market_cap=price_data.get("market_cap"),
            high_52_week=price_data.get("high_52_week"),
            low_52_week=price_data.get("low_52_week"),
            last_updated=price_data.get("last_updated", datetime.now()),
            source=price_data.get("source", "unknown"),
            cache_hit=price_data.get("cache_hit", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stock price: {str(e)}"
        )


@router.post("/prices/batch", response_model=StockPriceBatchResponse)
async def get_batch_prices(request: StockPriceBatchRequest):
    """
    Get prices for multiple stocks in one request.

    - **symbols**: List of stock ticker symbols (1-50)
    - **refresh**: Force cache refresh for all symbols

    Returns batch response with cache statistics.
    """
    try:
        start_time = time.time()
        service = await get_stock_price_service()

        # Get prices for all symbols
        results = await service.get_multiple_prices(
            request.symbols,
            refresh=request.refresh
        )

        # Format responses and count cache hits
        prices = []
        cache_hits = 0
        cache_misses = 0

        for symbol, price_data in results.items():
            if price_data:
                prices.append(
                    StockPriceResponse(
                        symbol=price_data.get("symbol", symbol),
                        price=price_data.get("price", 0.0),
                        change=price_data.get("change"),
                        change_percent=price_data.get("change_percent"),
                        volume=price_data.get("volume"),
                        market_cap=price_data.get("market_cap"),
                        high_52_week=price_data.get("high_52_week"),
                        low_52_week=price_data.get("low_52_week"),
                        last_updated=price_data.get("last_updated", datetime.now()),
                        source=price_data.get("source", "unknown"),
                        cache_hit=price_data.get("cache_hit", False)
                    )
                )

                if price_data.get("cache_hit"):
                    cache_hits += 1
                else:
                    cache_misses += 1

        processing_time_ms = int((time.time() - start_time) * 1000)

        return StockPriceBatchResponse(
            prices=prices,
            total_count=len(prices),
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching batch prices: {str(e)}"
        )


@router.get("/{symbol}/history")
async def get_price_history(
    symbol: str,
    limit: int = Query(100, ge=1, le=1000, description="Number of historical records")
):
    """
    Get historical price data for a symbol.

    - **symbol**: Stock ticker symbol
    - **limit**: Number of records to return (1-1000, default: 100)

    Returns historical price data from database.
    """
    try:
        service = await get_stock_price_service()
        history = await service.get_price_history(symbol.upper(), limit=limit)

        return {
            "symbol": symbol.upper(),
            "history": history,
            "count": len(history),
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching price history: {str(e)}"
        )

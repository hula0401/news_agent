"""API v1 router for Stock & News endpoints."""
from fastapi import APIRouter
from .stocks import router as stocks_router
from .stock_news import router as stock_news_router

# Create v1 API router
api_v1_router = APIRouter()

# Include all sub-routers
api_v1_router.include_router(stocks_router, tags=["stocks"])
api_v1_router.include_router(stock_news_router, tags=["stock-news"])

__all__ = ["api_v1_router"]

#!/usr/bin/env python3
"""
FastAPI wrapper for Market Assistant LangGraph Agent.

Provides REST API endpoints for the LangGraph agent deployment on GKE.
"""

import asyncio
import logging
import os
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agent_core.graph import run_market_agent
from agent_core.state import ChatMessage, MarketState
from agent_core.long_term_memory import start_session, finalize_session

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ====== REQUEST/RESPONSE MODELS ======

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    query: str = Field(..., description="User's market query", min_length=1)
    thread_id: Optional[str] = Field(None, description="Conversation thread ID for context")
    chat_history: Optional[List[dict]] = Field(default_factory=list, description="Previous conversation messages")
    output_mode: str = Field("voice", description="Response mode: 'voice' (concise) or 'text' (detailed)")
    timeout_seconds: float = Field(10.0, description="Timeout for API calls", gt=0, le=30)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What's Tesla's current stock price?",
                "thread_id": "chat_20251106_120000",
                "chat_history": [],
                "output_mode": "voice",
                "timeout_seconds": 10.0
            }
        }


class IntentInfo(BaseModel):
    """Intent information in response."""
    intent: str
    symbols: List[str]
    timeframe: str
    reasoning: str
    keywords: List[str] = Field(default_factory=list)


class MarketDataInfo(BaseModel):
    """Market data item in response."""
    symbol: str
    price: Optional[float]
    change_percent: Optional[float]
    volume: Optional[int]
    timestamp: Optional[str]
    source: str


class NewsInfo(BaseModel):
    """News item in response."""
    title: str
    summary: str
    url: str
    source: str
    published_at: str
    sentiment: Optional[str]
    symbols: List[str]


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    summary: str = Field(..., description="Agent's response summary")
    intents: List[IntentInfo] = Field(default_factory=list, description="Detected intents")
    symbols: List[str] = Field(default_factory=list, description="Extracted stock symbols")
    selected_tools: List[str] = Field(default_factory=list, description="Tools used by agent")
    market_data: List[MarketDataInfo] = Field(default_factory=list, description="Market data collected")
    news_data: List[NewsInfo] = Field(default_factory=list, description="News articles collected")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID")
    memory_id: Optional[str] = Field(None, description="Memory persistence ID")
    timestamp: str = Field(..., description="Response timestamp")
    error: Optional[str] = Field(None, description="Error message if any")

    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Tesla's current stock price is $234.56, up 2.3% today.",
                "intents": [{"intent": "price_check", "symbols": ["TSLA"], "timeframe": "1d", "reasoning": "User asked for current price"}],
                "symbols": ["TSLA"],
                "selected_tools": ["price"],
                "market_data": [{"symbol": "TSLA", "price": 234.56, "change_percent": 2.3, "source": "alphavantage"}],
                "news_data": [],
                "thread_id": "chat_20251106_120000",
                "timestamp": "2025-11-06T12:00:00Z"
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str = "1.0.0"


# ====== LIFESPAN MANAGEMENT ======

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    logger.info("🚀 Starting Market Assistant API")
    logger.info(f"OpenAI API Key: {'✓ Set' if os.getenv('OPENAI_API_KEY') else '✗ Missing'}")
    logger.info(f"Tavily API Key: {'✓ Set' if os.getenv('TAVILY_API_KEY') else '✗ Missing'}")
    logger.info(f"Alpha Vantage API Key: {'✓ Set' if os.getenv('ALPHAVANTAGE_API_KEY') else '✗ Missing'}")

    yield

    # Shutdown
    logger.info("⬇️  Shutting down Market Assistant API")


# ====== FASTAPI APPLICATION ======

app = FastAPI(
    title="Market Assistant API",
    description="LangGraph-based financial market assistant with real-time data and news",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====== API ENDPOINTS ======

@app.get("/", response_model=dict)
async def root():
    """Root endpoint."""
    return {
        "name": "Market Assistant API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )


@app.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for interacting with the Market Assistant agent.

    Processes user queries and returns comprehensive market insights.
    """
    try:
        logger.info(f"📨 Received query: {request.query}")

        # Generate thread_id if not provided
        thread_id = request.thread_id or f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Convert chat_history dicts to ChatMessage objects
        chat_history = []
        if request.chat_history:
            chat_history = [
                ChatMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    timestamp=msg.get("timestamp", datetime.utcnow().isoformat())
                )
                for msg in request.chat_history
            ]

        # Run the market agent
        result: MarketState = await run_market_agent(
            query=request.query,
            chat_history=chat_history,
            thread_id=thread_id,
            output_mode=request.output_mode,
            timeout_seconds=request.timeout_seconds
        )

        # Check for errors
        if result.error:
            logger.error(f"❌ Agent error: {result.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent execution error: {result.error}"
            )

        # Convert intents to IntentInfo
        intents_info = [
            IntentInfo(
                intent=intent.intent,
                symbols=intent.symbols,
                timeframe=intent.timeframe,
                reasoning=intent.reasoning,
                keywords=intent.keywords
            )
            for intent in result.intents
        ]

        # Convert market_data to MarketDataInfo
        market_data_info = [
            MarketDataInfo(
                symbol=item.symbol,
                price=item.price,
                change_percent=item.change_percent,
                volume=item.volume,
                timestamp=item.timestamp,
                source=item.source
            )
            for item in result.market_data
        ]

        # Convert news_data to NewsInfo
        news_info = [
            NewsInfo(
                title=item.title,
                summary=item.summary,
                url=item.url,
                source=item.source,
                published_at=item.published_at,
                sentiment=item.sentiment,
                symbols=item.symbols
            )
            for item in result.news_data
        ]

        logger.info(f"✅ Query processed successfully: {len(market_data_info)} market items, {len(news_info)} news items")

        return ChatResponse(
            summary=result.summary,
            intents=intents_info,
            symbols=result.symbols,
            selected_tools=result.selected_tools,
            market_data=market_data_info,
            news_data=news_info,
            thread_id=thread_id,
            memory_id=result.memory_id,
            timestamp=result.timestamp,
            error=result.error
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/api/info")
async def api_info():
    """Get API configuration and available features."""
    return {
        "version": "1.0.0",
        "features": {
            "intents": ["price_check", "news_search", "market_summary", "comparison", "research", "chat", "watchlist"],
            "data_sources": ["alphavantage", "tavily", "general_market_news"],
            "output_modes": ["voice", "text"]
        },
        "limits": {
            "max_timeout_seconds": 30,
            "max_query_length": 1000
        }
    }


# ====== MAIN ENTRY POINT ======

if __name__ == "__main__":
    import uvicorn

    # Get port from environment or default to 8080 (GKE standard)
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"🚀 Starting FastAPI server on {host}:{port}")

    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

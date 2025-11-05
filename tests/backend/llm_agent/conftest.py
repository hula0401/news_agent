"""
Pytest configuration and fixtures for LangGraph agent tests.

Provides shared fixtures and configuration for all test files.
"""

import pytest
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend'))


# ====== PYTEST CONFIGURATION ======

def pytest_configure(config):
    """Configure pytest."""
    # Set test environment variables
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'

    # Mock API keys if not set
    if not os.environ.get('ZHIPUAI_API_KEY'):
        os.environ['ZHIPUAI_API_KEY'] = 'test_key_123'
    if not os.environ.get('TAVILY_API_KEY'):
        os.environ['TAVILY_API_KEY'] = 'test_tavily_key'


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add skip_ci marker for Render deployment
    skip_ci = pytest.mark.skip(reason="Skipped in CI environment")

    for item in items:
        # Skip tests requiring real APIs in CI
        if "requires_api" in item.keywords and os.environ.get('CI'):
            item.add_marker(skip_ci)

        # Skip slow tests in CI unless explicitly requested
        if "slow" in item.keywords and os.environ.get('CI') and not config.getoption("--runslow", default=False):
            item.add_marker(pytest.mark.skip(reason="Slow test skipped in CI"))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ====== DATABASE FIXTURES ======

@pytest.fixture
def mock_db():
    """Mock database manager."""
    db = AsyncMock()
    db.get_user_notes = AsyncMock(return_value={
        "stocks": "Interested in tech stocks",
        "investment": "Long-term growth strategy"
    })
    db.upsert_user_notes = AsyncMock(return_value=True)
    db.get_user_watchlist = AsyncMock(return_value=["AAPL", "GOOGL", "META"])
    db.update_user_watchlist = AsyncMock(return_value=True)
    db.get_user = AsyncMock(return_value={
        "id": "test_user_123",
        "email": "test@example.com",
        "preferred_topics": ["tech", "finance"],
        "watchlist_stocks": ["AAPL", "GOOGL"]
    })
    return db


@pytest.fixture
def mock_cache():
    """Mock cache manager."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    return cache


# ====== LOGGING FIXTURES ======

@pytest.fixture
def temp_log_dir():
    """Create temporary log directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_logger():
    """Mock agent logger."""
    from unittest.mock import Mock
    logger = Mock()
    logger.start_session = Mock()
    logger.end_session = Mock()
    logger.log_query_received = Mock()
    logger.log_response_sent = Mock()
    logger.log_intent_analysis = Mock()
    logger.log_tool_execution = Mock()
    logger.log_llm_call = Mock()
    logger.log_error = Mock()
    logger.current_session_id = "test_session"
    return logger


# ====== LLM FIXTURES ======

@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = AsyncMock()

    # Default response for intent analysis
    intent_response = Mock()
    intent_response.content = json.dumps({
        "intents": [{
            "intent": "price_check",
            "symbols": ["META"],
            "timeframe": "1d",
            "reasoning": "User wants current price"
        }]
    })

    llm.ainvoke = AsyncMock(return_value=intent_response)
    return llm


@pytest.fixture
def mock_llm_response_generator():
    """Mock LLM for response generation."""
    llm = AsyncMock()

    response = Mock()
    response.content = "META is trading at $450.23, up $5.67 (+1.28%) today."

    llm.ainvoke = AsyncMock(return_value=response)
    return llm


# ====== MEMORY FIXTURES ======

@pytest.fixture
async def mock_memory(mock_db):
    """Mock long-term memory instance."""
    from app.llm_agent.long_term_memory_supabase import LongTermMemory

    memory = LongTermMemory(user_id="test_user_123", db_manager=mock_db)
    await memory.initialize()
    return memory


# ====== AGENT FIXTURES ======

@pytest.fixture
def mock_market_state():
    """Mock MarketState for testing."""
    from app.llm_agent.state import MarketState, IntentItem

    state = MarketState(
        query="What's the price of META?",
        session_id="test_session_123"
    )
    state.intents = [
        IntentItem(
            intent="price_check",
            symbols=["META"],
            timeframe="1d"
        )
    ]
    return state


@pytest.fixture
async def mock_agent_wrapper(mock_db, mock_cache):
    """Mock agent wrapper for testing."""
    from app.core.agent_wrapper_langgraph import LangGraphAgentWrapper

    wrapper = LangGraphAgentWrapper()
    wrapper.db = mock_db
    wrapper.cache = mock_cache
    wrapper._initialized = True

    # Mock graph
    wrapper.graph = AsyncMock()
    wrapper.graph.ainvoke = AsyncMock(return_value=Mock(
        query="What's META price?",
        intent="price_check",
        symbols=["META"],
        summary="META is trading at $450.23",
        raw_data={"price": 450.23},
        intents=[Mock(intent="price_check", symbols=["META"], timeframe="1d")]
    ))

    return wrapper


# ====== TOOL FIXTURES ======

@pytest.fixture
def mock_market_data():
    """Mock market data response."""
    return {
        "symbol": "META",
        "price": 450.23,
        "change": 5.67,
        "change_percent": 1.28,
        "volume": 12345678,
        "source": "yfinance"
    }


@pytest.fixture
def mock_news_data():
    """Mock news data response."""
    return [
        {
            "title": "Meta Platforms Reports Strong Q4 Earnings",
            "summary": "Meta exceeded expectations with revenue growth...",
            "url": "https://example.com/news1",
            "published_at": "2025-01-04T10:00:00Z",
            "sentiment": 0.8,
            "source": "NewsAPI"
        },
        {
            "title": "Meta AI Innovations Drive User Engagement",
            "summary": "New AI features boost user engagement...",
            "url": "https://example.com/news2",
            "published_at": "2025-01-04T09:00:00Z",
            "sentiment": 0.6,
            "source": "Tavily"
        }
    ]


# ====== USER FIXTURES ======

@pytest.fixture
def test_user_id():
    """Test user ID."""
    return "test_user_123"


@pytest.fixture
def test_session_id():
    """Test session ID."""
    return "test_session_456"


@pytest.fixture
def test_user_data():
    """Test user data."""
    return {
        "id": "test_user_123",
        "email": "test@example.com",
        "preferred_topics": ["tech", "finance"],
        "watchlist_stocks": ["AAPL", "GOOGL", "META"],
        "subscription_tier": "free",
        "created_at": "2025-01-01T00:00:00Z"
    }


# ====== TEST DATA FIXTURES ======

@pytest.fixture
def sample_queries():
    """Sample queries for testing."""
    return [
        "What's the price of META?",
        "Show me latest news on Tesla",
        "Compare NVDA and AMD",
        "Add GOOGL to my watchlist",
        "What's Apple's P/E ratio?",
        "Show my watchlist"
    ]


@pytest.fixture
def sample_intents():
    """Sample intent objects."""
    from app.llm_agent.state import IntentItem

    return [
        IntentItem(intent="price_check", symbols=["META"], timeframe="1d"),
        IntentItem(intent="news_search", symbols=["TSLA"], timeframe="1d"),
        IntentItem(intent="comparison", symbols=["NVDA", "AMD"], timeframe="1d"),
        IntentItem(intent="watchlist", symbols=["GOOGL"], timeframe="1d", watchlist_action="add"),
        IntentItem(intent="research", symbols=["AAPL"], timeframe="1d", keywords=["P/E ratio"]),
        IntentItem(intent="watchlist", symbols=[], timeframe="1d", watchlist_action="view")
    ]


# ====== HELPER FUNCTIONS ======

def assert_valid_jsonl(file_path):
    """Assert file is valid JSONL."""
    with open(file_path) as f:
        for line in f:
            json.loads(line)  # Should not raise


def create_test_log_entry(event="test_event", **kwargs):
    """Create test log entry."""
    return {
        "session_id": "test_session",
        "timestamp": datetime.now().isoformat(),
        "event": event,
        **kwargs
    }


@pytest.fixture
def assert_jsonl():
    """Fixture providing JSONL validation function."""
    return assert_valid_jsonl


@pytest.fixture
def create_log_entry():
    """Fixture providing log entry creation function."""
    return create_test_log_entry


# ====== ENVIRONMENT FIXTURES ======

@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    env_vars = {
        'ZHIPUAI_API_KEY': 'test_key',
        'TAVILY_API_KEY': 'test_tavily',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test_supabase_key',
        'UPSTASH_REDIS_REST_URL': 'https://test.upstash.io',
        'UPSTASH_REDIS_REST_TOKEN': 'test_redis_token'
    }
    return env_vars


@pytest.fixture
def set_test_env(mock_env_vars):
    """Set test environment variables."""
    original_env = os.environ.copy()
    os.environ.update(mock_env_vars)
    yield
    os.environ.clear()
    os.environ.update(original_env)


# ====== CLEANUP FIXTURES ======

@pytest.fixture(autouse=True)
def cleanup_globals():
    """Clean up global state after each test."""
    yield

    # Clear memory instances cache
    try:
        from app.llm_agent.long_term_memory_supabase import _memory_instances
        _memory_instances.clear()
    except:
        pass

    # Clear any other global state
    # Add as needed


if __name__ == "__main__":
    print("Pytest conftest.py - Run tests with: pytest")

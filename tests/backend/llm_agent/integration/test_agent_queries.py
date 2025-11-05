"""
Integration tests for LangGraph agent with various real-world queries.

Tests the agent's ability to understand different query types and provide
appropriate responses using agent_wrapper_langgraph.py (NOT src/agent.py).
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import AsyncMock, patch

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

from app.core.agent_wrapper_langgraph import LangGraphAgentWrapper


@pytest.mark.integration
@pytest.mark.requires_api
class TestAgentPriceCheckQueries:
    """Test agent with price check queries using LangGraph agent."""

    @pytest.fixture
    async def agent_wrapper(self):
        """Create LangGraph agent wrapper with mocked DB."""
        mock_db = AsyncMock()
        mock_db.get_user_notes = AsyncMock(return_value={})
        mock_db.upsert_user_notes = AsyncMock(return_value=True)
        mock_db.get_user_watchlist = AsyncMock(return_value=[])
        mock_db.update_user_watchlist = AsyncMock(return_value=True)

        wrapper = LangGraphAgentWrapper()
        wrapper.db = mock_db
        wrapper.cache = AsyncMock()
        await wrapper.initialize()

        return wrapper

    @pytest.mark.asyncio
    async def test_single_stock_price(self, agent_wrapper):
        """Test: What's the price of META?"""
        query = "What's the price of META?"
        user_id = "test_user_123"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        # Verify intent detection
        assert result["intent"] == "price_check", f"Expected price_check, got {result['intent']}"
        assert "META" in result["symbols"], f"Expected META in symbols, got {result['symbols']}"

        # Verify response
        assert result["response"] is not None, "Expected non-empty response"
        assert len(result["response"]) > 0, "Expected response text"

        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Symbols: {result['symbols']}")
        print(f"   Response: {result['response'][:200]}...")

    @pytest.mark.asyncio
    async def test_company_name_to_ticker(self, agent_wrapper):
        """Test: What's Apple's stock price?"""
        query = "What's Apple's stock price?"
        user_id = "test_user_123"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        assert result["intent"] == "price_check"
        # Should convert "Apple" to "AAPL"
        assert "AAPL" in result["symbols"], f"Expected AAPL in symbols, got {result['symbols']}"

        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Symbols: {result['symbols']}")
        print(f"   Response: {result['response'][:200]}...")

    @pytest.mark.asyncio
    async def test_multiple_stocks_price(self, agent_wrapper):
        """Test: What are the prices of META and GOOGL?"""
        query = "What are the prices of META and GOOGL?"
        user_id = "test_user_123"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        assert result["intent"] in ["price_check", "comparison"]
        assert "META" in result["symbols"]
        assert "GOOGL" in result["symbols"] or "GOOG" in result["symbols"]

        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Symbols: {result['symbols']}")
        print(f"   Response: {result['response'][:200]}...")


@pytest.mark.integration
@pytest.mark.requires_api
class TestAgentNewsQueries:
    """Test agent with news search queries."""

    @pytest.fixture
    async def agent_wrapper(self):
        """Create LangGraph agent wrapper."""
        mock_db = AsyncMock()
        mock_db.get_user_notes = AsyncMock(return_value={})
        mock_db.upsert_user_notes = AsyncMock(return_value=True)
        mock_db.get_user_watchlist = AsyncMock(return_value=[])
        mock_db.update_user_watchlist = AsyncMock(return_value=True)

        wrapper = LangGraphAgentWrapper()
        wrapper.db = mock_db
        wrapper.cache = AsyncMock()
        await wrapper.initialize()

        return wrapper

    @pytest.mark.asyncio
    async def test_stock_news(self, agent_wrapper):
        """Test: Show me latest news on Tesla"""
        query = "Show me latest news on Tesla"
        user_id = "test_user_123"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        assert result["intent"] == "news_search", f"Expected news_search, got {result['intent']}"
        assert "TSLA" in result["symbols"], f"Expected TSLA in symbols, got {result['symbols']}"
        assert result["response"] is not None

        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Symbols: {result['symbols']}")
        print(f"   Response: {result['response'][:200]}...")

    @pytest.mark.asyncio
    async def test_general_market_news(self, agent_wrapper):
        """Test: What's happening in the stock market today?"""
        query = "What's happening in the stock market today?"
        user_id = "test_user_123"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        # Should detect as news search or market summary
        assert result["intent"] in ["news_search", "market_summary"], \
            f"Expected news_search or market_summary, got {result['intent']}"

        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Response: {result['response'][:200]}...")


@pytest.mark.integration
@pytest.mark.requires_api
class TestAgentResearchQueries:
    """Test agent with research/analytical queries."""

    @pytest.fixture
    async def agent_wrapper(self):
        """Create LangGraph agent wrapper."""
        mock_db = AsyncMock()
        mock_db.get_user_notes = AsyncMock(return_value={})
        mock_db.upsert_user_notes = AsyncMock(return_value=True)
        mock_db.get_user_watchlist = AsyncMock(return_value=[])
        mock_db.update_user_watchlist = AsyncMock(return_value=True)

        wrapper = LangGraphAgentWrapper()
        wrapper.db = mock_db
        wrapper.cache = AsyncMock()
        await wrapper.initialize()

        return wrapper

    @pytest.mark.asyncio
    async def test_pe_ratio_query(self, agent_wrapper):
        """Test: What's META's P/E ratio?"""
        query = "What's META's P/E ratio?"
        user_id = "test_user_123"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        assert result["intent"] == "research", f"Expected research, got {result['intent']}"
        assert "META" in result["symbols"]

        # Should mention P/E in response
        summary_lower = result["response"].lower()
        assert "p/e" in summary_lower or "pe" in summary_lower or "ratio" in summary_lower, \
            f"Response should mention P/E ratio: {result['response']}"

        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Symbols: {result['symbols']}")
        print(f"   Response: {result['response'][:200]}...")


@pytest.mark.integration
@pytest.mark.requires_api
class TestAgentWatchlistQueries:
    """Test agent with watchlist management queries."""

    @pytest.fixture
    async def agent_wrapper(self):
        """Create LangGraph agent wrapper with watchlist tracking."""
        watchlist_state = []

        async def get_watchlist(user_id):
            return watchlist_state.copy()

        async def update_watchlist(user_id, watchlist):
            watchlist_state.clear()
            watchlist_state.extend(watchlist)
            return True

        mock_db = AsyncMock()
        mock_db.get_user_notes = AsyncMock(return_value={})
        mock_db.upsert_user_notes = AsyncMock(return_value=True)
        mock_db.get_user_watchlist = AsyncMock(side_effect=get_watchlist)
        mock_db.update_user_watchlist = AsyncMock(side_effect=update_watchlist)

        wrapper = LangGraphAgentWrapper()
        wrapper.db = mock_db
        wrapper.cache = AsyncMock()
        await wrapper.initialize()

        return wrapper

    @pytest.mark.asyncio
    async def test_add_to_watchlist(self, agent_wrapper):
        """Test: Add META to my watchlist"""
        query = "Add META to my watchlist"
        user_id = "test_user_watchlist"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        assert result["intent"] == "watchlist", f"Expected watchlist, got {result['intent']}"

        # Check intents for watchlist action
        if "intents" in result and len(result["intents"]) > 0:
            watchlist_intent = result["intents"][0]
            # Verify add action was detected
            print(f"✅ Query: {query}")
            print(f"   Intent: {result['intent']}")
            print(f"   Response: {result['response'][:200]}...")

    @pytest.mark.asyncio
    async def test_view_watchlist(self, agent_wrapper):
        """Test: Show my watchlist"""
        query = "Show my watchlist"
        user_id = "test_user_watchlist"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        assert result["intent"] == "watchlist"
        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Response: {result['response'][:200]}...")


@pytest.mark.integration
@pytest.mark.requires_api
class TestAgentMultiIntentQueries:
    """Test agent with multi-intent queries."""

    @pytest.fixture
    async def agent_wrapper(self):
        """Create LangGraph agent wrapper."""
        mock_db = AsyncMock()
        mock_db.get_user_notes = AsyncMock(return_value={})
        mock_db.upsert_user_notes = AsyncMock(return_value=True)
        mock_db.get_user_watchlist = AsyncMock(return_value=[])
        mock_db.update_user_watchlist = AsyncMock(return_value=True)

        wrapper = LangGraphAgentWrapper()
        wrapper.db = mock_db
        wrapper.cache = AsyncMock()
        await wrapper.initialize()

        return wrapper

    @pytest.mark.asyncio
    async def test_price_and_news(self, agent_wrapper):
        """Test: What's META's price and latest news?"""
        query = "What's META's price and latest news?"
        user_id = "test_user_multi"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        # Should detect multiple intents
        assert "intents" in result
        assert len(result["intents"]) >= 2, f"Expected 2+ intents, got {len(result['intents'])}"

        intent_types = [i["intent"] for i in result["intents"]]
        print(f"✅ Query: {query}")
        print(f"   Intents: {intent_types}")
        print(f"   Response: {result['response'][:300]}...")


@pytest.mark.integration
@pytest.mark.requires_api
class TestAgentChatQueries:
    """Test agent with casual conversation queries."""

    @pytest.fixture
    async def agent_wrapper(self):
        """Create LangGraph agent wrapper."""
        mock_db = AsyncMock()
        mock_db.get_user_notes = AsyncMock(return_value={})
        mock_db.upsert_user_notes = AsyncMock(return_value=True)
        mock_db.get_user_watchlist = AsyncMock(return_value=[])
        mock_db.update_user_watchlist = AsyncMock(return_value=True)

        wrapper = LangGraphAgentWrapper()
        wrapper.db = mock_db
        wrapper.cache = AsyncMock()
        await wrapper.initialize()

        return wrapper

    @pytest.mark.asyncio
    async def test_greeting(self, agent_wrapper):
        """Test: Hello, how are you?"""
        query = "Hello, how are you?"
        user_id = "test_user_chat"

        result = await agent_wrapper.process_text_command(
            user_id=user_id,
            query=query
        )

        assert result["intent"] == "chat", f"Expected chat, got {result['intent']}"
        assert result["response"] is not None

        print(f"✅ Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Response: {result['response'][:200]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])

"""
Unit tests for Supabase-integrated long-term memory.

Tests memory functionality with mocked database.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

from app.llm_agent.long_term_memory_supabase import LongTermMemory, get_memory_for_user


class TestLongTermMemory:
    """Test suite for LongTermMemory class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database manager."""
        db = AsyncMock()
        db.get_user_notes = AsyncMock(return_value={
            "stocks": "Interested in tech stocks",
            "investment": "Long-term growth strategy"
        })
        db.upsert_user_notes = AsyncMock(return_value=True)
        return db

    @pytest.fixture
    async def memory(self, mock_db):
        """Create LongTermMemory instance with mock DB."""
        mem = LongTermMemory(user_id="test_user_123", db_manager=mock_db)
        await mem.initialize()
        return mem

    @pytest.mark.asyncio
    async def test_initialization(self, memory, mock_db):
        """Test memory initializes and loads from database."""
        assert memory.user_id == "test_user_123"
        assert memory.db == mock_db
        assert "stocks" in memory.key_notes
        assert memory.key_notes["stocks"] == "Interested in tech stocks"
        mock_db.get_user_notes.assert_called_once_with("test_user_123")

    @pytest.mark.asyncio
    async def test_start_session(self, memory):
        """Test starting a session."""
        memory.start_session("session_123")

        assert memory.current_session_id == "session_123"
        assert len(memory.session_queries) == 0
        assert len(memory.session_symbols) == 0
        assert len(memory.session_intents) == 0

    @pytest.mark.asyncio
    async def test_track_conversation(self, memory):
        """Test tracking conversation."""
        memory.start_session("session_123")

        memory.track_conversation(
            query="What's META's P/E ratio?",
            intent="research",
            symbols=["META"],
            summary="META's P/E ratio is 30.03"
        )

        assert len(memory.session_queries) == 1
        assert memory.session_queries[0] == "What's META's P/E ratio?"
        assert "META" in memory.session_symbols
        assert "research" in memory.session_intents

    @pytest.mark.asyncio
    async def test_track_multiple_conversations(self, memory):
        """Test tracking multiple conversations in session."""
        memory.start_session("session_123")

        memory.track_conversation("Query 1", "intent1", ["SYM1"], "Summary 1")
        memory.track_conversation("Query 2", "intent2", ["SYM2"], "Summary 2")
        memory.track_conversation("Query 3", "intent3", ["SYM3"], "Summary 3")

        assert len(memory.session_queries) == 3
        assert len(memory.session_symbols) == 3
        assert len(memory.session_intents) == 3

    @pytest.mark.asyncio
    async def test_track_without_session(self, memory, caplog):
        """Test tracking conversation without starting session."""
        memory.track_conversation("Query", "intent", ["SYM"], "Summary")

        # Should log warning
        assert "No active session" in caplog.text

    @pytest.mark.asyncio
    async def test_finalize_session_empty(self, memory, mock_db):
        """Test finalizing empty session."""
        memory.start_session("session_123")
        await memory.finalize_session()

        # Should not call LLM or update database for empty session
        assert memory.current_session_id is None
        mock_db.upsert_user_notes.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalize_session_with_data(self, memory, mock_db):
        """Test finalizing session with conversation data."""
        memory.start_session("session_123")
        memory.track_conversation(
            "What's META price?",
            "price_check",
            ["META"],
            "META is trading at $450"
        )

        # Mock LLM summarization
        with patch.object(memory, '_summarize_session_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"stocks": "Updated interest in META"}

            await memory.finalize_session()

            # Verify LLM was called
            mock_llm.assert_called_once()

            # Verify database was updated
            mock_db.upsert_user_notes.assert_called_once()
            call_args = mock_db.upsert_user_notes.call_args
            assert call_args[0][0] == "test_user_123"  # user_id
            assert "stocks" in call_args[0][1]  # key_notes

            # Verify session was cleared
            assert memory.current_session_id is None
            assert len(memory.session_queries) == 0

    @pytest.mark.asyncio
    async def test_finalize_session_llm_error(self, memory, mock_db, caplog):
        """Test finalizing session when LLM fails."""
        memory.start_session("session_123")
        memory.track_conversation("Query", "intent", ["SYM"], "Summary")

        # Mock LLM to raise error
        with patch.object(memory, '_summarize_session_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API error")

            await memory.finalize_session()

            # Should handle error gracefully
            assert "Error finalizing session" in caplog.text
            assert memory.current_session_id is None

    @pytest.mark.asyncio
    async def test_summarize_session_with_llm(self, memory):
        """Test LLM summarization of session."""
        memory.start_session("session_123")
        memory.session_queries = ["What's META price?", "Show TSLA news"]
        memory.session_symbols = ["META", "TSLA"]
        memory.session_intents = ["price_check", "news_search"]

        # Mock LLM response
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.content = '{"stocks": "Tracking META and TSLA", "news": "Following tech news"}'
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch('app.llm_agent.long_term_memory_supabase.get_llm_for_summarizer', return_value=mock_llm):
            result = await memory._summarize_session_with_llm()

            assert "stocks" in result
            assert "Tracking META and TSLA" in result["stocks"]
            assert "news" in result
            mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_session_with_llm_invalid_json(self, memory, caplog):
        """Test LLM returns invalid JSON."""
        memory.start_session("session_123")
        memory.session_queries = ["Query"]
        memory.session_symbols = ["SYM"]
        memory.session_intents = ["intent"]

        # Mock LLM response with invalid JSON
        mock_llm = AsyncMock()
        mock_response = Mock()
        mock_response.content = 'This is not JSON'
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch('app.llm_agent.long_term_memory_supabase.get_llm_for_summarizer', return_value=mock_llm):
            result = await memory._summarize_session_with_llm()

            # Should return empty dict on error
            assert result == {}
            assert "Error in LLM summarization" in caplog.text

    @pytest.mark.asyncio
    async def test_get_user_context_empty(self, mock_db):
        """Test getting user context with no memory."""
        mock_db.get_user_notes = AsyncMock(return_value={})
        memory = LongTermMemory(user_id="test_user", db_manager=mock_db)
        await memory.initialize()

        context = memory.get_user_context()
        assert context == ""

    @pytest.mark.asyncio
    async def test_get_user_context_with_data(self, memory):
        """Test getting formatted user context."""
        context = memory.get_user_context()

        assert "User's Long-Term Interests:" in context
        assert "Stocks: Interested in tech stocks" in context
        assert "Investment: Long-term growth strategy" in context

    @pytest.mark.asyncio
    async def test_memory_update_merges_notes(self, memory, mock_db):
        """Test that new notes merge with existing notes."""
        memory.start_session("session_123")
        memory.track_conversation("Query", "research", ["META"], "Summary")

        # Mock LLM to return new category
        with patch.object(memory, '_summarize_session_with_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"research": "Interested in P/E ratios"}

            await memory.finalize_session()

            # Verify merged notes
            call_args = mock_db.upsert_user_notes.call_args[0][1]
            assert "stocks" in call_args  # Existing note
            assert "research" in call_args  # New note


class TestMemoryGlobalFunctions:
    """Test global convenience functions."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database manager."""
        db = AsyncMock()
        db.get_user_notes = AsyncMock(return_value={})
        db.upsert_user_notes = AsyncMock(return_value=True)
        return db

    @pytest.mark.asyncio
    async def test_get_memory_for_user_creates_instance(self, mock_db):
        """Test get_memory_for_user creates new instance."""
        with patch('app.llm_agent.long_term_memory_supabase.get_database', return_value=mock_db):
            memory = await get_memory_for_user("user_123")

            assert memory is not None
            assert memory.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_get_memory_for_user_returns_cached(self, mock_db):
        """Test get_memory_for_user returns cached instance."""
        with patch('app.llm_agent.long_term_memory_supabase.get_database', return_value=mock_db):
            memory1 = await get_memory_for_user("user_123")
            memory2 = await get_memory_for_user("user_123")

            assert memory1 is memory2  # Same instance

    @pytest.mark.asyncio
    async def test_convenience_functions(self, mock_db):
        """Test convenience functions."""
        from app.llm_agent.long_term_memory_supabase import (
            start_session,
            track_conversation,
            finalize_session,
            get_user_context
        )

        with patch('app.llm_agent.long_term_memory_supabase.get_database', return_value=mock_db):
            # Start session
            await start_session("user_123", "session_456")

            # Track conversation
            await track_conversation(
                "user_123",
                "Query",
                "intent",
                ["SYM"],
                "Summary"
            )

            # Get context
            context = await get_user_context("user_123")
            assert isinstance(context, str)

            # Finalize (mock LLM)
            with patch('app.llm_agent.long_term_memory_supabase.LongTermMemory._summarize_session_with_llm', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = {}
                await finalize_session("user_123")


class TestMemoryWithDatabase:
    """Test memory with actual database methods (mocked Supabase)."""

    @pytest.fixture
    def mock_supabase_client(self):
        """Mock Supabase client."""
        client = Mock()
        # Mock table() chain
        table_mock = Mock()
        select_mock = Mock()
        eq_mock = Mock()

        table_mock.select = Mock(return_value=select_mock)
        select_mock.eq = Mock(return_value=eq_mock)
        eq_mock.execute = Mock(return_value=Mock(data=[{"key_notes": {"test": "data"}}]))

        client.table = Mock(return_value=table_mock)
        return client

    @pytest.mark.asyncio
    async def test_database_integration(self, mock_supabase_client):
        """Test memory integrates with database manager."""
        # This would need actual DatabaseManager mock
        # Placeholder for integration test
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

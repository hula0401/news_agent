"""
Unit tests for offline logging system.

Tests the agent logger functionality without external dependencies.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'backend'))

from app.llm_agent.logger import AgentLogger, agent_logger


class TestAgentLogger:
    """Test suite for AgentLogger class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create AgentLogger instance with temp directory."""
        return AgentLogger(log_dir=temp_log_dir)

    def test_logger_initialization(self, logger, temp_log_dir):
        """Test logger initializes correctly."""
        assert logger.log_dir == Path(temp_log_dir)
        assert logger.session_logger is not None
        assert logger.intent_logger is not None
        assert logger.tool_logger is not None
        assert logger.llm_logger is not None
        assert logger.error_logger is not None

    def test_log_directory_creation(self, logger, temp_log_dir):
        """Test log directories are created."""
        expected_dirs = [
            'agent/sessions',
            'agent/intents',
            'agent/tools',
            'agent/llm',
            'agent/errors'
        ]

        for subdir in expected_dirs:
            dir_path = Path(temp_log_dir) / subdir
            assert dir_path.exists(), f"Directory {subdir} should exist"
            assert dir_path.is_dir(), f"{subdir} should be a directory"

    def test_start_session(self, logger, temp_log_dir):
        """Test session start logging."""
        logger.start_session(
            session_id="test_session_123",
            user_id="user_456",
            metadata={"source": "test"}
        )

        assert logger.current_session_id == "test_session_123"
        assert logger.session_start_time is not None

        # Check log file was created
        log_file = Path(temp_log_dir) / 'agent/sessions' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        assert log_file.exists()

        # Verify log entry
        with open(log_file) as f:
            line = f.readline()
            entry = json.loads(line)
            assert entry['session_id'] == "test_session_123"
            assert entry['user_id'] == "user_456"
            assert entry['event'] == "session_start"
            assert entry['metadata']['source'] == "test"

    def test_end_session(self, logger, temp_log_dir):
        """Test session end logging."""
        logger.start_session("test_session", "user_id")
        logger.end_session(summary={"queries": 5})

        assert logger.current_session_id is None
        assert logger.session_start_time is None

        # Verify log entry
        log_file = Path(temp_log_dir) / 'agent/sessions' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            lines = f.readlines()
            end_entry = json.loads(lines[-1])
            assert end_entry['event'] == "session_end"
            assert 'duration_ms' in end_entry
            assert end_entry['summary']['queries'] == 5

    def test_log_query_received(self, logger, temp_log_dir):
        """Test query logging."""
        logger.start_session("test_session", "user_id")
        logger.log_query_received("What's the price of META?", source="api")

        log_file = Path(temp_log_dir) / 'agent/sessions' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            lines = f.readlines()
            query_entry = json.loads(lines[-1])
            assert query_entry['event'] == "query_received"
            assert query_entry['data']['query'] == "What's the price of META?"
            assert query_entry['data']['source'] == "api"
            assert query_entry['data']['query_length'] == len("What's the price of META?")

    def test_log_response_sent(self, logger, temp_log_dir):
        """Test response logging."""
        logger.start_session("test_session", "user_id")
        logger.log_response_sent(
            response="META is trading at $450.23",
            processing_time_ms=2500,
            metadata={"intent": "price_check", "symbols": ["META"]}
        )

        log_file = Path(temp_log_dir) / 'agent/sessions' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            lines = f.readlines()
            response_entry = json.loads(lines[-1])
            assert response_entry['event'] == "response_sent"
            assert response_entry['data']['response'] == "META is trading at $450.23"
            assert response_entry['data']['processing_time_ms'] == 2500
            assert response_entry['data']['metadata']['intent'] == "price_check"

    def test_log_intent_analysis(self, logger, temp_log_dir):
        """Test intent analysis logging."""
        logger.start_session("test_session", "user_id")
        intents = [
            {"intent": "price_check", "symbols": ["META"], "timeframe": "1d"}
        ]
        logger.log_intent_analysis(
            query="What's META price?",
            intents=intents,
            processing_time_ms=800
        )

        log_file = Path(temp_log_dir) / 'agent/intents' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            entry = json.loads(f.readline())
            assert entry['query'] == "What's META price?"
            assert entry['num_intents'] == 1
            assert entry['intents'][0]['intent'] == "price_check"
            assert entry['processing_time_ms'] == 800

    def test_log_tool_execution_success(self, logger, temp_log_dir):
        """Test successful tool execution logging."""
        logger.start_session("test_session", "user_id")
        logger.log_tool_execution(
            tool_name="get_stock_price",
            tool_input={"symbol": "META"},
            tool_output={"price": 450.23, "change": 5.67},
            execution_time_ms=450,
            success=True
        )

        log_file = Path(temp_log_dir) / 'agent/tools' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            entry = json.loads(f.readline())
            assert entry['tool_name'] == "get_stock_price"
            assert entry['tool_input']['symbol'] == "META"
            assert entry['execution_time_ms'] == 450
            assert entry['success'] is True
            assert entry['error'] is None

    def test_log_tool_execution_failure(self, logger, temp_log_dir):
        """Test failed tool execution logging."""
        logger.start_session("test_session", "user_id")
        logger.log_tool_execution(
            tool_name="get_stock_price",
            tool_input={"symbol": "INVALID"},
            tool_output=None,
            execution_time_ms=100,
            success=False,
            error="Symbol not found"
        )

        log_file = Path(temp_log_dir) / 'agent/tools' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            entry = json.loads(f.readline())
            assert entry['success'] is False
            assert entry['error'] == "Symbol not found"

    def test_log_llm_call(self, logger, temp_log_dir):
        """Test LLM call logging."""
        logger.start_session("test_session", "user_id")
        logger.log_llm_call(
            stage="intent_analysis",
            prompt="Analyze this query...",
            response='{"intent": "price_check"}',
            model="glm-4.5-flash",
            tokens={"prompt": 100, "completion": 50},
            latency_ms=800
        )

        log_file = Path(temp_log_dir) / 'agent/llm' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            entry = json.loads(f.readline())
            assert entry['stage'] == "intent_analysis"
            assert entry['model'] == "glm-4.5-flash"
            assert entry['tokens']['prompt'] == 100
            assert entry['tokens']['completion'] == 50
            assert entry['latency_ms'] == 800

    def test_log_llm_call_truncates_long_content(self, logger, temp_log_dir):
        """Test that long prompts/responses are truncated."""
        logger.start_session("test_session", "user_id")
        long_prompt = "A" * 1000
        long_response = "B" * 1000

        logger.log_llm_call(
            stage="test",
            prompt=long_prompt,
            response=long_response,
            model="glm-4.5-flash",
            latency_ms=100
        )

        log_file = Path(temp_log_dir) / 'agent/llm' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            entry = json.loads(f.readline())
            assert len(entry['prompt']) <= 503  # 500 + "..."
            assert len(entry['response']) <= 503

    def test_log_error(self, logger, temp_log_dir):
        """Test error logging."""
        logger.start_session("test_session", "user_id")
        logger.log_error(
            error_type="tool_error",
            error_message="Failed to fetch data",
            traceback="Traceback...",
            context={"tool": "get_stock_price", "symbol": "META"}
        )

        log_file = Path(temp_log_dir) / 'agent/errors' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            entry = json.loads(f.readline())
            assert entry['error_type'] == "tool_error"
            assert entry['error_message'] == "Failed to fetch data"
            assert entry['context']['tool'] == "get_stock_price"

    def test_log_without_session(self, logger, temp_log_dir):
        """Test logging without active session."""
        # Should not crash, just skip logging
        logger.log_query_received("test query")
        logger.log_response_sent("test response", 100)

        # Verify no crash occurred
        assert logger.current_session_id is None

    def test_get_session_stats(self, logger):
        """Test session statistics."""
        logger.start_session("test_session", "user_id")
        stats = logger.get_session_stats()

        assert stats['session_id'] == "test_session"
        assert stats['active'] is True
        assert stats['duration_ms'] >= 0

    def test_get_session_stats_no_session(self, logger):
        """Test session stats without active session."""
        stats = logger.get_session_stats()
        assert stats == {}

    def test_multiple_sessions(self, logger, temp_log_dir):
        """Test logging for multiple sessions."""
        # Session 1
        logger.start_session("session_1", "user_1")
        logger.log_query_received("Query 1")
        logger.end_session()

        # Session 2
        logger.start_session("session_2", "user_2")
        logger.log_query_received("Query 2")
        logger.end_session()

        # Verify both sessions logged
        log_file = Path(temp_log_dir) / 'agent/sessions' / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file) as f:
            lines = f.readlines()
            assert len(lines) >= 4  # 2 start + 2 end + queries

    def test_jsonl_format(self, logger, temp_log_dir):
        """Test all logs are valid JSONL."""
        logger.start_session("test_session", "user_id")
        logger.log_query_received("test query")
        logger.log_intent_analysis("test", [{"intent": "test"}], 100)
        logger.log_tool_execution("test_tool", {}, {}, 100, True)
        logger.log_llm_call("test", "prompt", "response", "model", latency_ms=100)
        logger.log_error("test_error", "message")
        logger.end_session()

        # Check all log files are valid JSONL
        for subdir in ['sessions', 'intents', 'tools', 'llm', 'errors']:
            log_file = Path(temp_log_dir) / 'agent' / subdir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
            if log_file.exists():
                with open(log_file) as f:
                    for line in f:
                        entry = json.loads(line)  # Should not raise
                        assert isinstance(entry, dict)
                        assert 'timestamp' in entry


class TestGlobalLoggerInstance:
    """Test global logger instance."""

    def test_global_logger_exists(self):
        """Test global agent_logger instance exists."""
        from app.llm_agent.logger import agent_logger
        assert agent_logger is not None
        assert isinstance(agent_logger, AgentLogger)

    def test_convenience_functions(self, tmp_path):
        """Test convenience functions."""
        from app.llm_agent import logger as logger_module

        # Patch the global logger to use temp dir
        with patch.object(logger_module, 'agent_logger') as mock_logger:
            logger_module.start_session("test_session", "user_id")
            mock_logger.start_session.assert_called_once_with("test_session", "user_id", None)

            logger_module.end_session({"test": "data"})
            mock_logger.end_session.assert_called_once_with({"test": "data"})

            logger_module.log_query("test query", "api")
            mock_logger.log_query_received.assert_called_once_with("test query", "api")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

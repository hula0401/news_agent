"""Comprehensive offline logging system for LangGraph agent.

This logger tracks the complete lifecycle:
ASR → Intent Analysis → Tool Calling → Response Generation → TTS

All logs are stored locally in JSONL format for easy parsing and analysis.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import time
from contextlib import contextmanager


class AgentLogger:
    """Comprehensive logging for LangGraph agent with structured JSONL output."""

    def __init__(self, log_dir: str = "backend/logs"):
        """Initialize logger with separate files for different log types.

        Args:
            log_dir: Base directory for all logs
        """
        self.log_dir = Path(log_dir)
        self.setup_loggers()

        # Session context for tracking
        self.current_session_id: Optional[str] = None
        self.session_start_time: Optional[float] = None

    def setup_loggers(self):
        """Create separate loggers for different log types."""
        self.session_logger = self._create_logger("agent.session", "agent/sessions")
        self.intent_logger = self._create_logger("agent.intent", "agent/intents")
        self.tool_logger = self._create_logger("agent.tool", "agent/tools")
        self.llm_logger = self._create_logger("agent.llm", "agent/llm")
        self.error_logger = self._create_logger("agent.error", "agent/errors")

    def _create_logger(self, name: str, subdir: str) -> logging.Logger:
        """Create logger with JSONL file handler.

        Args:
            name: Logger name
            subdir: Subdirectory under log_dir

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        logger.handlers = []  # Clear existing handlers

        # Create log directory
        log_path = self.log_dir / subdir
        log_path.mkdir(parents=True, exist_ok=True)

        # Create file handler with date-based filename
        log_file = log_path / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(handler)

        return logger

    def start_session(self, session_id: str, user_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Start a new session and log the event.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
            metadata: Additional session metadata
        """
        self.current_session_id = session_id
        self.session_start_time = time.time()

        entry = {
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "event": "session_start",
            "metadata": metadata or {}
        }
        self.session_logger.info(json.dumps(entry))

    def end_session(self, summary: Optional[Dict[str, Any]] = None):
        """End current session and log the event.

        Args:
            summary: Session summary statistics
        """
        if not self.current_session_id:
            return

        duration_ms = int((time.time() - self.session_start_time) * 1000) if self.session_start_time else 0

        entry = {
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat(),
            "event": "session_end",
            "duration_ms": duration_ms,
            "summary": summary or {}
        }
        self.session_logger.info(json.dumps(entry))

        # Reset session context
        self.current_session_id = None
        self.session_start_time = None

    def log_query_received(self, query: str, source: str = "websocket"):
        """Log when a user query is received.

        Args:
            query: User query text
            source: Source of query (websocket, api, etc.)
        """
        if not self.current_session_id:
            return

        entry = {
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat(),
            "event": "query_received",
            "data": {
                "query": query,
                "source": source,
                "query_length": len(query)
            }
        }
        self.session_logger.info(json.dumps(entry))

    def log_response_sent(self, response: str, processing_time_ms: int, metadata: Optional[Dict[str, Any]] = None):
        """Log when a response is sent to user.

        Args:
            response: Response text
            processing_time_ms: Total processing time
            metadata: Additional metadata (intent, symbols, etc.)
        """
        if not self.current_session_id:
            return

        entry = {
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat(),
            "event": "response_sent",
            "data": {
                "response": response[:500],  # Truncate long responses
                "response_length": len(response),
                "processing_time_ms": processing_time_ms,
                "metadata": metadata or {}
            }
        }
        self.session_logger.info(json.dumps(entry))

    def log_intent_analysis(
        self,
        query: str,
        intents: List[Dict[str, Any]],
        processing_time_ms: int,
        model: str = "glm-4.5-flash"
    ):
        """Log intent analysis results.

        Args:
            query: User query
            intents: List of detected intents with metadata
            processing_time_ms: Time taken for intent analysis
            model: LLM model used
        """
        if not self.current_session_id:
            return

        entry = {
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "intents": intents,
            "num_intents": len(intents),
            "processing_time_ms": processing_time_ms,
            "model": model
        }
        self.intent_logger.info(json.dumps(entry))

    def log_tool_execution(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        execution_time_ms: int,
        success: bool,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log tool execution with timing and results.

        Args:
            tool_name: Name of tool executed
            tool_input: Tool input parameters
            tool_output: Tool output (will be truncated if too long)
            execution_time_ms: Execution time in milliseconds
            success: Whether tool execution succeeded
            error: Error message if failed
            metadata: Additional metadata
        """
        if not self.current_session_id:
            return

        # Truncate large outputs
        output_str = str(tool_output)
        if len(output_str) > 1000:
            output_str = output_str[:1000] + "... (truncated)"

        entry = {
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": output_str,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "error": error,
            "metadata": metadata or {}
        }
        self.tool_logger.info(json.dumps(entry))

    def log_llm_call(
        self,
        stage: str,
        prompt: str,
        response: str,
        model: str,
        tokens: Optional[Dict[str, int]] = None,
        latency_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log LLM API call with timing and token usage.

        Args:
            stage: Stage of processing (intent_analysis, response_generation, memory_summary)
            prompt: Prompt sent to LLM (will be truncated)
            response: LLM response (will be truncated)
            model: Model name
            tokens: Token usage dict with 'prompt' and 'completion' keys
            latency_ms: API latency in milliseconds
            metadata: Additional metadata
        """
        if not self.current_session_id:
            return

        entry = {
            "session_id": self.current_session_id,
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "prompt": prompt[:500] + "..." if len(prompt) > 500 else prompt,
            "response": response[:500] + "..." if len(response) > 500 else response,
            "model": model,
            "tokens": tokens or {"prompt": 0, "completion": 0},
            "latency_ms": latency_ms,
            "metadata": metadata or {}
        }
        self.llm_logger.info(json.dumps(entry))

    def log_error(
        self,
        error_type: str,
        error_message: str,
        traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log error with context.

        Args:
            error_type: Type of error (intent_analysis_error, tool_error, etc.)
            error_message: Error message
            traceback: Stack trace if available
            context: Additional context
        """
        entry = {
            "session_id": self.current_session_id or "unknown",
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "traceback": traceback,
            "context": context or {}
        }
        self.error_logger.info(json.dumps(entry))

    @contextmanager
    def log_tool_timing(self, tool_name: str, tool_input: Dict[str, Any]):
        """Context manager for timing tool execution.

        Usage:
            with agent_logger.log_tool_timing("get_stock_price", {"symbol": "AAPL"}):
                result = get_stock_price("AAPL")

        Args:
            tool_name: Name of tool
            tool_input: Tool input parameters
        """
        start_time = time.time()
        error = None
        result = None
        success = True

        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.log_tool_execution(
                tool_name=tool_name,
                tool_input=tool_input,
                tool_output=result,
                execution_time_ms=execution_time_ms,
                success=success,
                error=error
            )

    @contextmanager
    def log_llm_timing(self, stage: str, model: str = "glm-4.5-flash"):
        """Context manager for timing LLM calls.

        Usage:
            with agent_logger.log_llm_timing("intent_analysis") as log_ctx:
                response = await llm.ainvoke(prompt)
                log_ctx['prompt'] = prompt
                log_ctx['response'] = response

        Args:
            stage: Processing stage
            model: Model name
        """
        start_time = time.time()
        log_ctx = {"prompt": "", "response": "", "tokens": None}

        try:
            yield log_ctx
        finally:
            latency_ms = int((time.time() - start_time) * 1000)
            self.log_llm_call(
                stage=stage,
                prompt=log_ctx.get("prompt", ""),
                response=log_ctx.get("response", ""),
                model=model,
                tokens=log_ctx.get("tokens"),
                latency_ms=latency_ms
            )

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for current session.

        Returns:
            Session statistics
        """
        if not self.current_session_id or not self.session_start_time:
            return {}

        return {
            "session_id": self.current_session_id,
            "duration_ms": int((time.time() - self.session_start_time) * 1000),
            "active": True
        }


# Global logger instance
agent_logger = AgentLogger()


# Convenience functions for direct usage
def start_session(session_id: str, user_id: str, metadata: Optional[Dict[str, Any]] = None):
    """Start a new session."""
    agent_logger.start_session(session_id, user_id, metadata)


def end_session(summary: Optional[Dict[str, Any]] = None):
    """End current session."""
    agent_logger.end_session(summary)


def log_query(query: str, source: str = "websocket"):
    """Log query received."""
    agent_logger.log_query_received(query, source)


def log_response(response: str, processing_time_ms: int, metadata: Optional[Dict[str, Any]] = None):
    """Log response sent."""
    agent_logger.log_response_sent(response, processing_time_ms, metadata)


def log_intent(query: str, intents: List[Dict[str, Any]], processing_time_ms: int):
    """Log intent analysis."""
    agent_logger.log_intent_analysis(query, intents, processing_time_ms)


def log_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Any,
    execution_time_ms: int,
    success: bool = True,
    error: Optional[str] = None
):
    """Log tool execution."""
    agent_logger.log_tool_execution(
        tool_name, tool_input, tool_output, execution_time_ms, success, error
    )


def log_llm(
    stage: str,
    prompt: str,
    response: str,
    model: str = "glm-4.5-flash",
    tokens: Optional[Dict[str, int]] = None,
    latency_ms: int = 0
):
    """Log LLM call."""
    agent_logger.log_llm_call(stage, prompt, response, model, tokens, latency_ms)


def log_error(error_type: str, error_message: str, traceback: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
    """Log error."""
    agent_logger.log_error(error_type, error_message, traceback, context)

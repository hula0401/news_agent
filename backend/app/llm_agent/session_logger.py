"""
Session-Based Detailed Logging for Agent Conversations

Creates comprehensive log files for each session in logs/agent/session/
with complete details of LLM queries, tool calls, and agent responses.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import logging


class SessionLogger:
    """Logger that creates detailed session-specific log files."""

    def __init__(self, base_dir: Path = None):
        """
        Initialize session logger.

        Args:
            base_dir: Base directory for logs (default: backend/logs/agent)
        """
        if base_dir is None:
            # backend/app/llm_agent/session_logger.py -> backend/logs/agent
            base_dir = Path(__file__).parent.parent.parent / "logs" / "agent"

        self.session_dir = base_dir / "session"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Track active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        self.logger = logging.getLogger(__name__)

    def start_session(
        self,
        session_id: str,
        user_id: str,
        initial_query: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Start a new session log.

        Args:
            session_id: Unique session identifier
            user_id: User ID
            initial_query: Optional first query from user
            metadata: Additional session metadata

        Returns:
            Path to session log file
        """
        session_file = self.session_dir / f"{session_id}.log"
        start_time = datetime.now()

        # Track session
        self.active_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "start_time": start_time,
            "log_file": session_file,
            "metadata": metadata or {}
        }

        # Write header
        header = f"""{'='*80}
Chat Session: chat_{start_time.strftime('%Y%m%d_%H%M%S')}
Started: {start_time.isoformat()}
Session ID: {session_id}
User ID: {user_id}
"""
        if initial_query:
            header += f"Initial Query: {initial_query}\n"

        if metadata:
            header += f"Metadata: {json.dumps(metadata, indent=2)}\n"

        header += "="*80 + "\n\n"

        with open(session_file, "w", encoding="utf-8") as f:
            f.write(header)

        self.logger.info(f"✅ Started session log: {session_id} -> {session_file}")
        return session_file

    def _write_to_session(self, session_id: str, content: str):
        """Append content to session log file."""
        if session_id not in self.active_sessions:
            self.logger.warning(f"⚠️ Session {session_id} not found in active sessions")
            return

        session_file = self.active_sessions[session_id]["log_file"]
        try:
            with open(session_file, "a", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            self.logger.error(f"❌ Failed to write to session log {session_id}: {e}", exc_info=True)

    def log_llm_query(
        self,
        session_id: str,
        model: str,
        prompt: str,
        response: str,
        duration_ms: float,
        stage: str = "unknown",
        tokens: Optional[Dict[str, int]] = None,
        status: str = "SUCCESS",
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log detailed LLM query with full prompt and response.

        Args:
            session_id: Session identifier
            model: Model name (e.g., 'glm-4.5-flash')
            prompt: Full prompt sent to LLM
            response: Full response from LLM
            duration_ms: Query duration in milliseconds
            stage: Stage name (e.g., 'intent_analysis', 'summary_generator')
            tokens: Token usage dict with 'prompt', 'completion' keys
            status: SUCCESS or ERROR
            error: Error message if failed
            metadata: Additional metadata
        """
        timestamp = datetime.now().isoformat()

        # Build log entry (match reference format exactly)
        stage_display = f" ({stage})" if stage and stage != "unknown" else ""
        log_entry = f"""
{'='*80}
LLM QUERY: {model}{stage_display}
{'='*80}
Timestamp: {timestamp}
Status: {status}
Duration: {duration_ms:.2f}ms

"""

        if tokens:
            log_entry += f"Tokens: {tokens.get('prompt', 0)} prompt + {tokens.get('completion', 0)} completion = {tokens.get('prompt', 0) + tokens.get('completion', 0)} total\n\n"

        log_entry += f"""INPUT:
'''
{prompt}
'''

OUTPUT:
'''
{response}
'''
"""

        if error:
            log_entry += f"\nERROR:\n{error}\n"

        if metadata:
            log_entry += f"\nMETADATA:\n{json.dumps(metadata, indent=2)}\n"

        log_entry += "="*80 + "\n\n"

        self._write_to_session(session_id, log_entry)

    def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        input_data: Any,
        output_data: Any,
        duration_ms: Optional[float] = None,
        status: str = "SUCCESS",
        error: Optional[str] = None
    ):
        """
        Log detailed tool call with full input and output.

        Args:
            session_id: Session identifier
            tool_name: Name of the tool
            input_data: Full input parameters
            output_data: Full output/result
            duration_ms: Execution time
            status: SUCCESS or ERROR
            error: Error message if failed
        """
        timestamp = datetime.now().isoformat()
        duration_str = f"{duration_ms:.2f}ms" if duration_ms is not None else "N/A"

        # Format input/output
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data, indent=2, default=str)
        else:
            input_str = str(input_data)

        if isinstance(output_data, (dict, list)):
            output_str = json.dumps(output_data, indent=2, default=str)
        else:
            output_str = str(output_data)

        log_entry = f"""
{'='*80}
TOOL CALL: {tool_name}
{'='*80}
Timestamp: {timestamp}
Status: {status}
Duration: {duration_str}

INPUT:
'''
{input_str}
'''

OUTPUT:
'''
{output_str}
'''
"""

        if error:
            log_entry += f"\nERROR:\n{error}\n"

        log_entry += "="*80 + "\n\n"

        self._write_to_session(session_id, log_entry)

    def log_user_query(
        self,
        session_id: str,
        query: str,
        source: str = "voice",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log user query.

        Args:
            session_id: Session identifier
            query: User's query text
            source: Source of query (voice/text/api)
            metadata: Additional metadata
        """
        timestamp = datetime.now().isoformat()

        log_entry = f"""
{'='*80}
USER QUERY
{'='*80}
Timestamp: {timestamp}
Source: {source}
Query: {query}
"""

        if metadata:
            log_entry += f"Metadata: {json.dumps(metadata, indent=2)}\n"

        log_entry += "="*80 + "\n\n"

        self._write_to_session(session_id, log_entry)

    def log_agent_response(
        self,
        session_id: str,
        response: str,
        sentiment: Optional[str] = None,
        key_insights: Optional[list] = None,
        processing_time_ms: Optional[float] = None
    ):
        """
        Log final agent response.

        Args:
            session_id: Session identifier
            response: Agent's response text
            sentiment: Sentiment (positive/negative/neutral/mixed)
            key_insights: List of key insights
            processing_time_ms: Total processing time
        """
        timestamp = datetime.now().isoformat()

        log_entry = f"""
{'='*80}
AGENT RESPONSE
{'='*80}
Timestamp: {timestamp}
"""

        if processing_time_ms:
            log_entry += f"Total Processing Time: {processing_time_ms:.2f}ms\n"

        if sentiment:
            log_entry += f"Sentiment: {sentiment}\n"

        if key_insights:
            log_entry += f"Key Insights:\n"
            for insight in key_insights:
                log_entry += f"  - {insight}\n"

        log_entry += f"\nResponse:\n{response}\n"
        log_entry += "="*80 + "\n\n"

        self._write_to_session(session_id, log_entry)

    def end_session(
        self,
        session_id: str,
        summary: Optional[str] = None
    ):
        """
        End a session and write footer.

        Args:
            session_id: Session identifier
            summary: Optional session summary
        """
        if session_id not in self.active_sessions:
            self.logger.warning(f"⚠️ Session {session_id} not in active sessions")
            return

        session_info = self.active_sessions[session_id]
        end_time = datetime.now()
        duration = end_time - session_info["start_time"]

        footer = f"""
{'='*80}
SESSION END
{'='*80}
Ended: {end_time.isoformat()}
Duration: {duration.total_seconds():.2f}s
"""

        if summary:
            footer += f"\nSummary:\n{summary}\n"

        footer += "="*80 + "\n"

        self._write_to_session(session_id, footer)

        # Remove from active sessions
        del self.active_sessions[session_id]
        self.logger.info(f"✅ Ended session log: {session_id}")

    def get_session_log_path(self, session_id: str) -> Optional[Path]:
        """Get path to session log file."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]["log_file"]
        return self.session_dir / f"{session_id}.log"


# Global instance
_session_logger: Optional[SessionLogger] = None


def get_session_logger() -> SessionLogger:
    """Get or create global session logger instance."""
    global _session_logger
    if _session_logger is None:
        _session_logger = SessionLogger()
    return _session_logger


# Example usage
if __name__ == "__main__":
    # Example: Create session log
    logger = get_session_logger()

    session_id = "test_session_123"
    logger.start_session(
        session_id=session_id,
        user_id="user_456",
        initial_query="What's TSLA price?",
        metadata={"source": "websocket_v2"}
    )

    # Log LLM query
    logger.log_llm_query(
        session_id=session_id,
        model="glm-4.5-flash",
        prompt="System: You are a market analyst...\n\nUser: What's TSLA price?",
        response='{"intent":"price_check","symbols":["TSLA"]}',
        duration_ms=1500.0,
        stage="intent_analysis",
        tokens={"prompt": 500, "completion": 50}
    )

    # Log tool call
    logger.log_tool_call(
        session_id=session_id,
        tool_name="yfinance_price",
        input_data={"symbols": ["TSLA"], "timeframe": "1d"},
        output_data={"TSLA": {"price": 433.72, "change": -2.93}},
        duration_ms=250.5
    )

    # Log agent response
    logger.log_agent_response(
        session_id=session_id,
        response="Tesla is trading at $433.72, down 2.93% today.",
        sentiment="negative",
        key_insights=["Price down 2.93%", "High volume activity"],
        processing_time_ms=2000.0
    )

    # End session
    logger.end_session(session_id)

    print(f"Log written to: {logger.get_session_log_path(session_id)}")

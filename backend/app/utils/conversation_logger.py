"""
Conversation Logger for Voice News Agent

This module provides comprehensive logging for voice conversations including:
- Full conversation details (transcription, agent response, etc.)
- Model loading information
- Performance metrics
- Error tracking
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import logging


@dataclass
class ConversationTurn:
    """Represents a single conversation turn."""
    session_id: str
    user_id: str
    timestamp: str
    transcription: str
    agent_response: str
    processing_time_ms: float
    audio_format: str
    audio_size_bytes: int
    tts_chunks_sent: int
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SessionInfo:
    """Represents a conversation session."""
    session_id: str
    user_id: str
    session_start: str
    session_end: Optional[str] = None
    turns: List[ConversationTurn] = None
    total_turns: int = 0
    total_interruptions: int = 0

    def __post_init__(self):
        if self.turns is None:
            self.turns = []


class ConversationLogger:
    """Comprehensive conversation logger for voice interactions."""

    def __init__(self, log_dir: str = "logs/conversations"):
        """
        Initialize conversation logger.

        Args:
            log_dir: Directory to store conversation logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # In-memory session storage
        self.active_sessions: Dict[str, SessionInfo] = {}

        # Model info storage
        self.model_info: Dict[str, Any] = {
            "sensevoice_loaded": False,
            "sensevoice_model_path": None,
            "tts_engine": "edge-tts",
            "agent_type": None,
            "loading_time_ms": {}
        }

        # Logger
        self.logger = logging.getLogger("conversation_logger")
        self.logger.setLevel(logging.INFO)

    def log_model_info(self, model_name: str, loaded: bool,
                      model_path: Optional[str] = None,
                      loading_time_ms: Optional[float] = None,
                      error: Optional[str] = None):
        """
        Log model loading information.

        Args:
            model_name: Name of the model (e.g., 'sensevoice', 'agent')
            loaded: Whether model loaded successfully
            model_path: Path to model
            loading_time_ms: Time taken to load model
            error: Error message if loading failed
        """
        info = {
            "loaded": loaded,
            "path": model_path,
            "loading_time_ms": loading_time_ms,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

        self.model_info[f"{model_name}_loaded"] = loaded
        self.model_info[f"{model_name}_path"] = model_path

        if loading_time_ms:
            self.model_info["loading_time_ms"][model_name] = loading_time_ms

        # Log to file
        log_file = self.log_dir / "model_info.json"
        try:
            with open(log_file, 'a') as f:
                log_entry = {
                    "model": model_name,
                    **info
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log model info: {e}")

    def start_session(self, session_id: str, user_id: str):
        """
        Start a new conversation session.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
        """
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user_id,
            session_start=datetime.now().isoformat()
        )

        self.active_sessions[session_id] = session_info
        self.logger.info(f"Started session: {session_id[:8]}... for user {user_id[:8]}...")

    def log_conversation_turn(
        self,
        session_id: str,
        user_id: str,
        transcription: str,
        agent_response: str,
        processing_time_ms: float,
        audio_format: str,
        audio_size_bytes: int,
        tts_chunks_sent: int,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a complete conversation turn.

        Args:
            session_id: Session identifier
            user_id: User identifier
            transcription: User's transcribed speech
            agent_response: Agent's response text
            processing_time_ms: Total processing time
            audio_format: Audio format (opus, wav, etc.)
            audio_size_bytes: Size of audio input
            tts_chunks_sent: Number of TTS chunks sent
            error: Error message if any
            metadata: Additional metadata (stock data, news items, etc.)
        """
        turn = ConversationTurn(
            session_id=session_id,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            transcription=transcription,
            agent_response=agent_response,
            processing_time_ms=processing_time_ms,
            audio_format=audio_format,
            audio_size_bytes=audio_size_bytes,
            tts_chunks_sent=tts_chunks_sent,
            error=error,
            metadata=metadata
        )

        # Add to session
        if session_id in self.active_sessions:
            self.active_sessions[session_id].turns.append(turn)
            self.active_sessions[session_id].total_turns += 1

        # Log to file immediately
        self._write_turn_to_file(turn)

        # Log to console with rich details
        self.logger.info(f"📝 Conversation Turn | session={session_id[:8]}...")
        self.logger.info(f"   🎤 User: \"{transcription}\"")
        self.logger.info(f"   🤖 Agent: \"{agent_response}\"")
        self.logger.info(f"   ⏱️ Processing: {processing_time_ms:.0f}ms")
        self.logger.info(f"   🎵 Audio: {audio_format} ({audio_size_bytes:,} bytes)")
        self.logger.info(f"   🔊 TTS: {tts_chunks_sent} chunks")

        if metadata:
            self.logger.info(f"   📊 Metadata: {json.dumps(metadata, indent=6)}")

        if error:
            self.logger.error(f"   ❌ Error: {error}")

    def log_interruption(self, session_id: str):
        """
        Log a voice interruption event.

        Args:
            session_id: Session identifier
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id].total_interruptions += 1
            self.logger.info(f"🛑 Interruption | session={session_id[:8]}... | total={self.active_sessions[session_id].total_interruptions}")

    def end_session(self, session_id: str) -> Optional[SessionInfo]:
        """
        End a conversation session and write full session log.

        Args:
            session_id: Session identifier

        Returns:
            SessionInfo if session exists, None otherwise
        """
        if session_id not in self.active_sessions:
            return None

        session_info = self.active_sessions[session_id]
        session_info.session_end = datetime.now().isoformat()

        # Write full session to file
        self._write_session_to_file(session_info)

        # Remove from active sessions
        del self.active_sessions[session_id]

        self.logger.info(f"🏁 Session ended | session={session_id[:8]}... | turns={session_info.total_turns} | interruptions={session_info.total_interruptions}")

        return session_info

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get information about an active or completed session.

        Args:
            session_id: Session identifier

        Returns:
            SessionInfo if found, None otherwise
        """
        # Check active sessions
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        # Try to load from file
        return self._load_session_from_file(session_id)

    def _write_turn_to_file(self, turn: ConversationTurn):
        """Write a conversation turn to file."""
        try:
            # Create daily log file
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = self.log_dir / f"turns_{date_str}.jsonl"

            with open(log_file, 'a') as f:
                f.write(json.dumps(asdict(turn)) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write turn to file: {e}")

    def _write_session_to_file(self, session_info: SessionInfo):
        """Write complete session to file."""
        try:
            # Create session file
            session_file = self.log_dir / f"session_{session_info.session_id}.json"

            with open(session_file, 'w') as f:
                session_dict = asdict(session_info)
                json.dump(session_dict, f, indent=2)

            self.logger.info(f"📁 Session saved to {session_file.name}")
        except Exception as e:
            self.logger.error(f"Failed to write session to file: {e}")

    def _load_session_from_file(self, session_id: str) -> Optional[SessionInfo]:
        """Load session from file."""
        try:
            session_file = self.log_dir / f"session_{session_id}.json"

            if not session_file.exists():
                return None

            with open(session_file, 'r') as f:
                session_dict = json.load(f)

            # Reconstruct SessionInfo from dict
            turns = [ConversationTurn(**turn) for turn in session_dict.get('turns', [])]
            session_info = SessionInfo(
                session_id=session_dict['session_id'],
                user_id=session_dict['user_id'],
                session_start=session_dict['session_start'],
                session_end=session_dict.get('session_end'),
                turns=turns,
                total_turns=session_dict.get('total_turns', 0),
                total_interruptions=session_dict.get('total_interruptions', 0)
            )

            return session_info
        except Exception as e:
            self.logger.error(f"Failed to load session from file: {e}")
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information."""
        return self.model_info.copy()

    def log_llm_call(
        self,
        session_id: str,
        node_name: str,
        model: str,
        prompt: str,
        response: str,
        duration_ms: float,
        status: str = "SUCCESS",
        tokens: Optional[Dict[str, int]] = None
    ):
        """
        Log detailed LLM call with full input/output.

        Args:
            session_id: Session identifier
            node_name: Node name (e.g., "intent_analyzer", "response_generator")
            model: Model name (e.g., "glm-4.5-flash")
            prompt: Full input prompt
            response: Full LLM response
            duration_ms: Processing duration in milliseconds
            status: SUCCESS or FAILED
            tokens: Optional token usage dict
        """
        if session_id not in self.active_sessions:
            return

        separator = "=" * 80
        log_entry = f"\n{separator}\n"
        log_entry += f"LLM QUERY: {node_name} ({model})\n"
        log_entry += f"{separator}\n"
        log_entry += f"Timestamp: {datetime.now().isoformat()}\n"
        log_entry += f"Status: {status}\n"
        log_entry += f"Duration: {duration_ms:.2f}ms\n"

        if tokens:
            log_entry += f"Tokens: {tokens.get('prompt', 0)} prompt + {tokens.get('completion', 0)} completion = {tokens.get('total', 0)} total\n"

        log_entry += f"\nINPUT:\n'''\n{prompt}\n'''\n"
        log_entry += f"\nOUTPUT:\n'''\n{response}\n'''\n"

        self.logger.info(log_entry)

        # Also write to session log file immediately for real-time viewing
        self._append_to_session_log(session_id, log_entry)

    def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: Any,
        duration_ms: float,
        status: str = "SUCCESS",
        error: Optional[str] = None
    ):
        """
        Log detailed tool execution with full input/output.

        Args:
            session_id: Session identifier
            tool_name: Tool/function name
            tool_input: Tool input parameters as dict
            tool_output: Tool output (will be converted to string)
            duration_ms: Execution duration in milliseconds
            status: SUCCESS or FAILED
            error: Error message if failed
        """
        if session_id not in self.active_sessions:
            return

        separator = "=" * 80
        log_entry = f"\n{separator}\n"
        log_entry += f"TOOL EXECUTION: {tool_name}\n"
        log_entry += f"{separator}\n"
        log_entry += f"Timestamp: {datetime.now().isoformat()}\n"
        log_entry += f"Status: {status}\n"
        log_entry += f"Duration: {duration_ms:.2f}ms\n"

        # Format input
        log_entry += f"\nINPUT:\n"
        log_entry += json.dumps(tool_input, indent=2, default=str) + "\n"

        # Format output
        log_entry += f"\nOUTPUT:\n"
        if error:
            log_entry += f"ERROR: {error}\n"
        else:
            if isinstance(tool_output, (dict, list)):
                log_entry += json.dumps(tool_output, indent=2, default=str) + "\n"
            else:
                log_entry += str(tool_output) + "\n"

        self.logger.info(log_entry)

        # Also write to session log file immediately
        self._append_to_session_log(session_id, log_entry)

    def _append_to_session_log(self, session_id: str, log_entry: str):
        """Append log entry to session's human-readable log file."""
        try:
            # Use chat_YYYYMMDD_HHMMSS.log format
            if session_id in self.active_sessions:
                session_info = self.active_sessions[session_id]
                session_start = datetime.fromisoformat(session_info.session_start)
                log_filename = f"chat_{session_start.strftime('%Y%m%d_%H%M%S')}.log"
                log_file = self.log_dir / log_filename

                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
        except Exception as e:
            self.logger.error(f"Failed to append to session log: {e}")


# Global conversation logger instance
conversation_logger = ConversationLogger()


def get_conversation_logger() -> ConversationLogger:
    """Get conversation logger instance."""
    return conversation_logger

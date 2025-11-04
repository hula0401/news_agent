"""
Comprehensive Logging Configuration for Market Agent

Features:
1. Per-chat log files with unique IDs
2. Detailed tool call logging (input/output)
3. Detailed LLM query logging (prompt/response)
4. Multiple log levels and formats
5. Structured logging for analysis
"""
import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import inspect


# ====== CONFIGURATION ======
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log format
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
SIMPLE_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Global chat session ID (updated per chat)
_current_chat_id: Optional[str] = None


# ====== LOGGER SETUP ======
def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logging.Logger:
    """
    Create a logger with file and console handlers.

    Args:
        name: Logger name (typically __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_to_file: Enable file logging
        log_to_console: Enable console logging

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(SIMPLE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler (main debug log)
    if log_to_file:
        debug_log = LOG_DIR / "agent_debug.log"
        file_handler = logging.FileHandler(debug_log, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(DETAILED_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


# ====== CHAT SESSION MANAGEMENT ======
def start_new_chat_session(user_query: str = "") -> str:
    """
    Start a new chat session with unique ID and log file.

    Args:
        user_query: Optional initial query for context

    Returns:
        Chat session ID
    """
    global _current_chat_id, _structured_logger

    # Generate unique chat ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _current_chat_id = f"chat_{timestamp}"

    # Create chat-specific log file
    chat_log_file = LOG_DIR / f"{_current_chat_id}.log"

    # Log session start
    with open(chat_log_file, "w", encoding="utf-8") as f:
        f.write("="*80 + "\n")
        f.write(f"Chat Session: {_current_chat_id}\n")
        f.write(f"Started: {datetime.now().isoformat()}\n")
        if user_query:
            f.write(f"Initial Query: {user_query}\n")
        f.write("="*80 + "\n\n")

    # Reinitialize structured logger with new chat session
    _structured_logger = StructuredLogger(_main_logger)

    logging.getLogger(__name__).info(f"🆕 Started new chat session: {_current_chat_id}")
    return _current_chat_id


def get_current_chat_id() -> Optional[str]:
    """Get current chat session ID"""
    return _current_chat_id


def get_chat_log_path() -> Optional[Path]:
    """Get path to current chat log file"""
    if _current_chat_id:
        return LOG_DIR / f"{_current_chat_id}.log"
    return None


# ====== STRUCTURED LOGGING ======
class StructuredLogger:
    """Logger for structured data (JSON-serializable)"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.chat_log_path = get_chat_log_path()

    def _write_to_chat_log(self, content: str):
        """Write to current chat session log"""
        if self.chat_log_path:
            with open(self.chat_log_path, "a", encoding="utf-8") as f:
                f.write(content + "\n")

    def _format_data(self, data: Any, max_length: int = 1000) -> str:
        """Format data for logging (truncate if too long)"""
        try:
            if isinstance(data, (dict, list)):
                json_str = json.dumps(data, indent=2, default=str)
                if len(json_str) > max_length:
                    return json_str[:max_length] + f"\n... (truncated, total {len(json_str)} chars)"
                return json_str
            else:
                str_data = str(data)
                if len(str_data) > max_length:
                    return str_data[:max_length] + f"... (truncated, total {len(str_data)} chars)"
                return str_data
        except Exception as e:
            return f"<Error formatting data: {e}>"

    def log_tool_call(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        output_data: Any,
        duration_ms: Optional[float] = None,
        error: Optional[Exception] = None,
    ):
        """
        Log detailed tool call information.

        IMPORTANT: Logs COMPLETE input and output without any truncation.

        Args:
            tool_name: Name of the tool/function called
            input_data: Input parameters
            output_data: Output/result
            duration_ms: Execution time in milliseconds
            error: Exception if tool call failed
        """
        # Create structured log entry
        timestamp = datetime.now().isoformat()
        status = "ERROR" if error else "SUCCESS"

        # Log to main logger
        if error:
            self.logger.error(f"🔧 Tool Call FAILED: {tool_name}")
            self.logger.error(f"   Error: {error}")
        else:
            self.logger.info(f"🔧 Tool Call: {tool_name} ({status})")

        # Format complete input/output (no truncation)
        duration_str = f"{duration_ms:.2f}ms" if duration_ms else "N/A"

        # Convert to JSON if dict/list, otherwise string
        if isinstance(input_data, (dict, list)):
            input_str = json.dumps(input_data, indent=2, default=str)
        else:
            input_str = str(input_data)

        if isinstance(output_data, (dict, list)):
            output_str = json.dumps(output_data, indent=2, default=str)
        else:
            output_str = str(output_data)

        # Detailed log to chat session file with triple quotes format
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
            log_entry += f"\nERROR:\n{str(error)}\n"

        log_entry += "="*80 + "\n"

        self._write_to_chat_log(log_entry)

        # Also log summary to main log (preview only for console)
        self.logger.debug(f"Tool {tool_name} - Input: {self._format_data(input_data, max_length=200)}")
        self.logger.debug(f"Tool {tool_name} - Output: {self._format_data(output_data, max_length=500)}")

    def log_llm_query(
        self,
        model: str,
        prompt: str,
        response: str,
        duration_ms: Optional[float] = None,
        tokens_used: Optional[Dict[str, int]] = None,
        error: Optional[Exception] = None,
    ):
        """
        Log detailed LLM query information.

        IMPORTANT: Logs COMPLETE input and output without any truncation.

        Args:
            model: Model name/ID
            prompt: Full prompt sent to LLM
            response: Full response from LLM
            duration_ms: Query duration in milliseconds
            tokens_used: Token usage stats (prompt_tokens, completion_tokens, total_tokens)
            error: Exception if query failed
        """
        timestamp = datetime.now().isoformat()
        status = "ERROR" if error else "SUCCESS"

        # Log to main logger
        if error:
            self.logger.error(f"🤖 LLM Query FAILED: {model}")
            self.logger.error(f"   Error: {error}")
        else:
            self.logger.info(f"🤖 LLM Query: {model} ({status})")

        # Build complete log entry with NO truncation
        duration_str = f"{duration_ms:.2f}ms" if duration_ms else "N/A"

        log_entry = f"""
{'='*80}
LLM QUERY: {model}
{'='*80}
Timestamp: {timestamp}
Status: {status}
Duration: {duration_str}
"""

        if tokens_used:
            log_entry += f"Tokens: {tokens_used.get('prompt_tokens', 0)} prompt + {tokens_used.get('completion_tokens', 0)} completion = {tokens_used.get('total_tokens', 0)} total\n"

        # Use triple quotes format as requested, with COMPLETE content (no truncation)
        log_entry += f"""
INPUT:
'''
{prompt}
'''

OUTPUT:
'''
{response}
'''
"""

        if error:
            log_entry += f"\nERROR:\n{str(error)}\n"

        log_entry += "="*80 + "\n"

        self._write_to_chat_log(log_entry)

        # Also log summary to main log (preview only for console)
        prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
        response_preview = response[:200] + "..." if len(response) > 200 else response
        self.logger.debug(f"LLM Prompt ({len(prompt)} chars): {prompt_preview}")
        self.logger.debug(f"LLM Response ({len(response)} chars): {response_preview}")

    def log_node_execution(
        self,
        node_name: str,
        input_state: Dict[str, Any],
        output_state: Dict[str, Any],
        duration_ms: Optional[float] = None,
    ):
        """
        Log node execution details.

        Args:
            node_name: Name of the LangGraph node
            input_state: State before node execution
            output_state: State after node execution
            duration_ms: Execution time in milliseconds
        """
        timestamp = datetime.now().isoformat()

        self.logger.info(f"📦 Node Execution: {node_name}")

        log_entry = f"""
{'='*80}
NODE EXECUTION: {node_name}
{'='*80}
Timestamp: {timestamp}
Duration: {duration_ms:.2f}ms if duration_ms else 'N/A'

INPUT STATE (key fields):
{self._format_data({k: v for k, v in input_state.items() if k in ['query', 'intent', 'symbols', 'timeframe']}, max_length=1000)}

OUTPUT STATE (key fields):
{self._format_data({k: v for k, v in output_state.items() if k in ['intent', 'symbols', 'summary', 'error']}, max_length=1000)}

{'='*80}
"""

        self._write_to_chat_log(log_entry)


# ====== GLOBAL INSTANCE ======
_main_logger = setup_logger(__name__)
_structured_logger = StructuredLogger(_main_logger)


def get_structured_logger() -> StructuredLogger:
    """Get global structured logger instance"""
    return _structured_logger


# ====== UTILITY FUNCTIONS ======
def log_function_call(func):
    """Decorator to automatically log function calls with input/output"""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger = logging.getLogger(func.__module__)

        # Log input
        logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")

        try:
            # Execute function
            import time
            start_time = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            # Log output
            logger.debug(f"{func_name} completed in {duration_ms:.2f}ms")
            logger.debug(f"{func_name} returned: {str(result)[:200]}")

            return result
        except Exception as e:
            logger.error(f"{func_name} raised exception: {e}", exc_info=True)
            raise

    return wrapper


# ====== EXAMPLE USAGE ======
if __name__ == "__main__":
    # Example: Start a chat session
    chat_id = start_new_chat_session("What's the price of TSLA?")

    # Example: Log a tool call
    structured_logger = get_structured_logger()
    structured_logger.log_tool_call(
        tool_name="fetch_market_news",
        input_data={"symbols": ["TSLA"], "limit": 10},
        output_data=[{"title": "Tesla stock rises", "url": "http://example.com"}],
        duration_ms=250.5,
    )

    # Example: Log an LLM query
    structured_logger.log_llm_query(
        model="gpt-4",
        prompt="What's the market sentiment for TSLA?",
        response="The market sentiment for TSLA is positive...",
        duration_ms=1500.0,
        tokens_used={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
    )

    print(f"Logs written to: {get_chat_log_path()}")

"""
LLM Concurrency Limiter

Global semaphore to limit concurrent LLM API calls and prevent rate limiting.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Global semaphore - allows only 1 concurrent LLM call at a time
_llm_semaphore = asyncio.Semaphore(1)


@asynccontextmanager
async def llm_call_limiter(model_name: str = "unknown"):
    """
    Context manager to limit concurrent LLM calls.

    Usage:
        async with llm_call_limiter("glm-4.5-flash"):
            response = await llm.ainvoke(messages)

    Args:
        model_name: Name of the LLM model for logging
    """
    logger.debug(f"🔒 Acquiring LLM semaphore for {model_name}...")

    async with _llm_semaphore:
        logger.debug(f"✅ LLM semaphore acquired for {model_name}")
        try:
            yield
        finally:
            logger.debug(f"🔓 LLM semaphore released for {model_name}")


def get_active_llm_calls() -> int:
    """Get the number of currently active LLM calls."""
    return _llm_semaphore._value == 0  # True if semaphore is acquired

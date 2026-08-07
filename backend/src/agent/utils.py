"""
Bharat Voice AI — Utility Functions

Provides shared utilities: timing decorators, environment helpers,
and retry logic for resilient service calls.
"""

import asyncio
import functools
import os
import time
from typing import Any, Callable, TypeVar

from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)

T = TypeVar("T")


def get_env_or_raise(key: str) -> str:
    """
    Get a required environment variable or raise with a clear message.

    Args:
        key: The environment variable name.

    Returns:
        The environment variable value.

    Raises:
        EnvironmentError: If the variable is not set or is empty.
    """
    value = os.environ.get(key, "").strip()
    if not value:
        raise OSError(
            f"Required environment variable '{key}' is not set. "
            f"Please add it to your .env.local file."
        )
    return value


def get_env_optional(key: str, default: str = "") -> str:
    """
    Get an optional environment variable with a default.

    Args:
        key: The environment variable name.
        default: The default value if not set.

    Returns:
        The environment variable value or the default.
    """
    return os.environ.get(key, default).strip()


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that measures and logs the execution time of a sync function.

    Args:
        func: The function to wrap.

    Returns:
        The wrapped function with timing.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug("%s completed in %.1fms", func.__name__, elapsed_ms)
            return result
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "%s failed after %.1fms: %s",
                func.__name__,
                elapsed_ms,
                str(exc),
            )
            raise

    return wrapper


def measure_time_async(
    func: Callable[..., Any],
) -> Callable[..., Any]:
    """
    Decorator that measures and logs the execution time of an async function.

    Args:
        func: The async function to wrap.

    Returns:
        The wrapped async function with timing.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.debug("%s completed in %.1fms", func.__name__, elapsed_ms)
            return result
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "%s failed after %.1fms: %s",
                func.__name__,
                elapsed_ms,
                str(exc),
            )
            raise

    return wrapper


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs: Any,
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        func: The async function to call.
        *args: Positional arguments for the function.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds between retries.
        max_delay: Maximum delay in seconds between retries.
        **kwargs: Keyword arguments for the function.

    Returns:
        The result of the function call.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exception = exc

            if attempt == max_retries:
                logger.error(
                    "All %d retries exhausted for %s: %s",
                    max_retries,
                    func.__name__,
                    str(exc),
                )
                raise

            delay = min(base_delay * (2**attempt), max_delay)
            logger.warning(
                "Retry %d/%d for %s after %.1fs: %s",
                attempt + 1,
                max_retries,
                func.__name__,
                delay,
                str(exc),
            )
            await asyncio.sleep(delay)

    # This should never be reached, but satisfies type checker
    raise last_exception  # type: ignore[misc]

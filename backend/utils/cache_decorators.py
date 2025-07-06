"""Cache decorators for automatic method result caching."""

import functools
import inspect
# import logging # Removed
from typing import Any, Callable, Optional, TypeVar

from .cache_utils import generate_cache_key, serialize_for_cache
from services.cache_service import cache_service
from backend.utils.logging import logger as structured_logger # Use StructuredLogger

# logger = logging.getLogger(__name__) # Removed

F = TypeVar("F", bound=Callable[..., Any])


def cache_result(ttl: Optional[int] = 300) -> Callable[[F], F]:
    """Decorator to cache function results with automatic key generation.

    Args:
        ttl: Time-to-live in seconds for cached results. Defaults to 300 (5 minutes).

    Returns:
        Decorated function with caching capabilities

    Example:
        @cache_result(ttl=600)
        async def get_dao_proposals(dao_id: str, limit: int = 10) -> List[Proposal]:
            # Expensive operation
            return await fetch_proposals_from_api(dao_id, limit)
    """

    def decorator(func: F) -> F:
        # Preserve function metadata
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Synchronous wrapper for sync functions."""
            try:
                # Try to get from cache (Note: this won't work in sync context with async cache)
                # For now, just call the function directly for sync functions
                structured_logger.warning(
                    f"Sync function {func.__name__} using cache decorator - cache disabled",
                    func_name=func.__name__
                )
                return func(*args, **kwargs)
            except Exception as e:
                structured_logger.error(
                    f"Cache error for sync function {func.__name__}",
                    func_name=func.__name__,
                    exc_info=e
                )
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Asynchronous wrapper for async functions."""
            # Generate cache key from function name and parameters
            cache_key = generate_cache_key(func.__name__, args, kwargs)

            try:
                # Check if cache service is available
                if not cache_service.is_available:
                    structured_logger.warning(
                        f"Cache service unavailable for {func.__name__}, calling function directly",
                        func_name=func.__name__,
                        cache_key=cache_key
                    )
                    return await func(*args, **kwargs)

                # Try to get from cache
                cached_result = await cache_service.get(cache_key)
                if cached_result is not None:
                    structured_logger.debug(f"Cache hit for {func.__name__}", func_name=func.__name__, cache_key=cache_key)
                    return cached_result

                # Cache miss - call the function
                structured_logger.debug(f"Cache miss for {func.__name__}", func_name=func.__name__, cache_key=cache_key)
                result = await func(*args, **kwargs)

                # Store result in cache
                try:
                    serialized_result = serialize_for_cache(result)
                    await cache_service.set(cache_key, serialized_result, ttl)
                    structured_logger.debug(
                        f"Cached result for {func.__name__}", func_name=func.__name__, cache_key=cache_key, ttl=ttl
                    )
                except Exception as cache_error:
                    structured_logger.warning(
                        f"Failed to cache result for {func.__name__}",
                        func_name=func.__name__,
                        cache_key=cache_key,
                        exc_info=cache_error # Use exc_info for the exception
                    )

                return result

            except Exception as e:
                structured_logger.error(
                    f"Cache error for async function {func.__name__}",
                    func_name=func.__name__,
                    cache_key=cache_key,
                    exc_info=e
                )
                # Fallback to calling the function directly
                return await func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator

"""Redis cache service for efficient data caching."""

import json
import time # For timing spans
from typing import Any, List, Optional

import logfire # For spans
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from backend.utils.logging import logger, log_function_call # Use StructuredLogger instance and decorator
from config import settings


class CacheService:
    """Service for managing Redis cache operations with connection pooling."""

    def __init__(self):
        """Initialize the cache service with connection pool."""
        self._pool: Optional[ConnectionPool] = None
        self._redis_client: Optional[Redis] = None
        self._is_available = False

    @log_function_call(log_args=False, log_result=False, log_timing=True, log_level="info") # log_args=False as it takes no args other than self
    async def initialize(self) -> None:
        """Initialize Redis connection pool and client."""
        try:
            self._pool = ConnectionPool.from_url(
                settings.redis_connection_url,
                max_connections=settings.redis_max_connections,
                decode_responses=settings.redis_decode_responses,
                socket_connect_timeout=settings.redis_socket_connect_timeout,
                socket_keepalive=settings.redis_socket_keepalive,
                health_check_interval=settings.redis_health_check_interval,
            )
            self._redis_client = Redis(connection_pool=self._pool)

            # Test connection
            await self._redis_client.ping()
            self._is_available = True
            logger.info("Redis cache service initialized successfully", redis_url=settings.redis_connection_url)
        except (ConnectionError, TimeoutError) as e:
            logger.warning("Redis service unavailable on initialization", detail=str(e), exc_info=e, redis_url=settings.redis_connection_url)
            self._is_available = False
        except Exception as e:
            logger.error("Failed to initialize Redis", detail=str(e), exc_info=e, redis_url=settings.redis_connection_url)
            self._is_available = False

    @log_function_call(log_args=False, log_result=False, log_timing=True, log_level="info")
    async def close(self) -> None:
        """Close Redis connection pool."""
        if self._pool:
            await self._pool.disconnect()
            logger.info("Redis cache service closed")

    def _ensure_available(self) -> bool:
        """Check if service is available and ready for operations."""
        return self._is_available and self._redis_client is not None

    def _deserialize_value(self, value: str) -> Any:
        """Deserialize value from Redis storage."""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    def _serialize_value(self, value: Any) -> str:
        """Serialize value to string for Redis storage."""
        if isinstance(value, str):
            return value
        return json.dumps(value)

    def _handle_redis_error(self, operation: str, key: str, error: Exception) -> None:
        """Handle Redis errors with consistent logging and availability updates."""
        log_params = {
            "cache_operation": operation,
            "cache_key": key,
            "error_type": type(error).__name__,
            "detail": str(error),
            "exc_info": error
        }
        if isinstance(error, (ConnectionError, TimeoutError, ResponseError)):
            logger.warning(f"Cache {operation} connection/response error for key '{key}'", **log_params)
            self._is_available = False # Potentially mark as unavailable on these
        else:
            logger.error(f"Unexpected cache {operation} error for key '{key}'", **log_params)

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing already in span
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache by key.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or Redis unavailable
        """
        if not self._ensure_available():
            logger.debug("Cache get: Redis unavailable", cache_key=key)
            return None

        logger.debug("Cache get: Attempting to get key", cache_key=key)
        start_time = time.time()
        try:
            with logfire.span("cache.get", key=key):
                value = await self._redis_client.get(key)
                duration_ms = (time.time() - start_time) * 1000
                if value is not None:
                    logger.debug("Cache get: Hit", cache_key=key, duration_ms=duration_ms)
                    return self._deserialize_value(value)
                else:
                    logger.debug("Cache get: Miss", cache_key=key, duration_ms=duration_ms)
                    return None
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._handle_redis_error("get", key, e)
            logger.debug("Cache get: Error", cache_key=key, duration_ms=duration_ms, error=str(e))
            return None

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing already in span
    async def set(
        self, key: str, value: Any, expire_seconds: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional expiration.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized if not string)
            expire_seconds: Optional expiration time in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._ensure_available():
            logger.debug("Cache set: Redis unavailable", cache_key=key)
            return False

        logger.debug("Cache set: Attempting to set key", cache_key=key, expire_seconds=expire_seconds)
        start_time = time.time()
        try:
            with logfire.span("cache.set", key=key, expire_seconds=expire_seconds):
                serialized_value = self._serialize_value(value)
                if expire_seconds:
                    await self._redis_client.setex(key, expire_seconds, serialized_value)
                else:
                    await self._redis_client.set(key, serialized_value)
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("Cache set: Success", cache_key=key, expire_seconds=expire_seconds, duration_ms=duration_ms)
                return True
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._handle_redis_error("set", key, e)
            logger.debug("Cache set: Error", cache_key=key, duration_ms=duration_ms, error=str(e))
            return False

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing already in span
    async def delete(self, *keys: str) -> int:
        """Delete value(s) from cache by key(s).

        Args:
            keys: Cache key(s) to delete

        Returns:
            Number of keys deleted
        """
        if not self._ensure_available():
            logger.debug("Cache delete: Redis unavailable", cache_keys=keys)
            return 0

        if not keys:
            logger.debug("Cache delete: No keys provided")
            return 0

        logger.debug("Cache delete: Attempting to delete keys", cache_keys=keys)
        start_time = time.time()
        try:
            with logfire.span("cache.delete", num_keys=len(keys)):
                result = await self._redis_client.delete(*keys)
                deleted_count = int(result) if result else 0
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("Cache delete: Success", cache_keys=keys, deleted_count=deleted_count, duration_ms=duration_ms)
                return deleted_count
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            key_str = ", ".join(keys[:3]) + ("..." if len(keys) > 3 else "") # For error reporting
            self._handle_redis_error("delete", key_str, e)
            logger.debug("Cache delete: Error", cache_keys=keys, duration_ms=duration_ms, error=str(e))
            return 0

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing already in span
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        if not self._ensure_available():
            logger.debug("Cache exists: Redis unavailable", cache_key=key)
            return False

        logger.debug("Cache exists: Attempting to check key", cache_key=key)
        start_time = time.time()
        try:
            with logfire.span("cache.exists", key=key):
                exists = bool(await self._redis_client.exists(key))
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("Cache exists: Result", cache_key=key, exists=exists, duration_ms=duration_ms)
                return exists
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._handle_redis_error("exists", key, e)
            logger.debug("Cache exists: Error", cache_key=key, duration_ms=duration_ms, error=str(e))
            return False

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing already in span
    async def keys(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "cache:*")

        Returns:
            List of matching keys
        """
        if not self._ensure_available():
            logger.debug("Cache keys: Redis unavailable", cache_pattern=pattern)
            return []

        logger.debug("Cache keys: Attempting to get keys for pattern", cache_pattern=pattern)
        start_time = time.time()
        try:
            with logfire.span("cache.keys", pattern=pattern):
                keys_found = await self._redis_client.keys(pattern)
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("Cache keys: Found keys", cache_pattern=pattern, count=len(keys_found), duration_ms=duration_ms)
                return keys_found if keys_found else []
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._handle_redis_error("keys", pattern, e)
            logger.debug("Cache keys: Error", cache_pattern=pattern, duration_ms=duration_ms, error=str(e))
            return []

    @property
    def is_available(self) -> bool:
        """Check if Redis service is available."""
        return self._is_available

    @log_function_call(log_args=False, log_result=True, log_timing=False, log_level="info") # timing in span
    async def health_check(self) -> bool:
        """Perform health check on Redis connection.

        Returns:
            True if healthy, False otherwise
        """
        if not self._redis_client:
            logger.warning("Redis health check: Client not initialized")
            return False

        start_time = time.time()
        try:
            with logfire.span("cache.health_check"):
                await self._redis_client.ping()
                self._is_available = True
                duration_ms = (time.time() - start_time) * 1000
                logger.info("Redis health check: Success", duration_ms=duration_ms)
                return True
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning("Redis health check: Failed", detail=str(e), exc_info=e, duration_ms=duration_ms)
            self._is_available = False
            return False

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing in span
    async def acquire_lock(self, lock_key: str, timeout_seconds: int = 30) -> bool:
        """Acquire a distributed lock.

        Args:
            lock_key: The lock key
            timeout_seconds: Lock timeout in seconds

        Returns:
            True if lock acquired, False otherwise
        """
        if not self._ensure_available():
            logger.debug("Cache acquire_lock: Redis unavailable", lock_key=lock_key)
            return False

        logger.debug("Cache acquire_lock: Attempting to acquire lock", lock_key=lock_key, timeout_seconds=timeout_seconds)
        start_time = time.time()
        try:
            with logfire.span("cache.acquire_lock", lock_key=lock_key, timeout_seconds=timeout_seconds):
                # Use Redis SET with NX (only if not exists) and EX (expiration)
                result = await self._redis_client.set(
                    f"lock:{lock_key}", "locked", nx=True, ex=timeout_seconds
                )
                acquired = bool(result)
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("Cache acquire_lock: Result", lock_key=lock_key, acquired=acquired, duration_ms=duration_ms)
                return acquired
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._handle_redis_error("acquire_lock", lock_key, e)
            logger.debug("Cache acquire_lock: Error", lock_key=lock_key, duration_ms=duration_ms, error=str(e))
            return False

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing in span
    async def release_lock(self, lock_key: str) -> bool:
        """Release a distributed lock.

        Args:
            lock_key: The lock key

        Returns:
            True if lock released, False otherwise
        """
        if not self._ensure_available():
            logger.debug("Cache release_lock: Redis unavailable", lock_key=lock_key)
            return False

        logger.debug("Cache release_lock: Attempting to release lock", lock_key=lock_key)
        start_time = time.time()
        try:
            with logfire.span("cache.release_lock", lock_key=lock_key):
                result = await self._redis_client.delete(f"lock:{lock_key}")
                released = bool(result)
                duration_ms = (time.time() - start_time) * 1000
                logger.debug("Cache release_lock: Result", lock_key=lock_key, released=released, duration_ms=duration_ms)
                return released
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._handle_redis_error("release_lock", lock_key, e)
            logger.debug("Cache release_lock: Error", lock_key=lock_key, duration_ms=duration_ms, error=str(e))
            return False

    @log_function_call(log_args=True, log_result=True, log_timing=False, log_level="debug") # timing in span
    async def wait_for_lock(self, lock_key: str, max_wait_seconds: int = 10) -> bool:
        """Wait for a lock to be released.

        Args:
            lock_key: The lock key
            max_wait_seconds: Maximum time to wait in seconds

        Returns:
            True if lock was released (and we can proceed), False if timeout
        """
        if not self._ensure_available():
            logger.debug("Cache wait_for_lock: Redis unavailable", lock_key=lock_key)
            return False

        import asyncio

        logger.debug("Cache wait_for_lock: Starting to wait for lock", lock_key=lock_key, max_wait_seconds=max_wait_seconds)
        start_time = time.time()
        wait_interval = 0.1  # 100ms
        total_waited = 0

        try:
            with logfire.span("cache.wait_for_lock", lock_key=lock_key, max_wait_seconds=max_wait_seconds):
                while total_waited < max_wait_seconds:
                    exists = await self._redis_client.exists(f"lock:{lock_key}")
                    if not exists:
                        duration_ms = (time.time() - start_time) * 1000
                        logger.debug("Cache wait_for_lock: Lock released", lock_key=lock_key, total_waited_ms=round(total_waited * 1000), duration_ms=duration_ms)
                        return True  # Lock is gone, we can proceed

                    await asyncio.sleep(wait_interval)
                    total_waited += wait_interval

                duration_ms = (time.time() - start_time) * 1000
                logger.debug("Cache wait_for_lock: Timed out", lock_key=lock_key, total_waited_ms=round(total_waited * 1000), duration_ms=duration_ms)
                return False  # Timeout
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self._handle_redis_error("wait_for_lock", lock_key, e)
            logger.debug("Cache wait_for_lock: Error", lock_key=lock_key, duration_ms=duration_ms, error=str(e))
            return False


# Global cache service instance
cache_service = CacheService()

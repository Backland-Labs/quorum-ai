"""Redis cache service for efficient data caching."""

import json
import logging
from typing import Any, Optional

from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing Redis cache operations with connection pooling."""
    
    def __init__(self):
        """Initialize the cache service with connection pool."""
        self._pool: Optional[ConnectionPool] = None
        self._redis_client: Optional[Redis] = None
        self._is_available = False
        
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
            logger.info("Redis cache service initialized successfully")
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Redis service unavailable: {e}")
            self._is_available = False
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            self._is_available = False
    
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
        if isinstance(error, (ConnectionError, TimeoutError, ResponseError)):
            logger.warning(f"Cache {operation} error for key '{key}': {error}")
            self._is_available = False
        else:
            logger.error(f"Unexpected cache {operation} error for key '{key}': {error}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or Redis unavailable
        """
        if not self._ensure_available():
            return None
            
        try:
            value = await self._redis_client.get(key)
            return self._deserialize_value(value) if value else None
        except Exception as e:
            self._handle_redis_error("get", key, e)
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire_seconds: Optional[int] = None
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
            return False
            
        try:
            serialized_value = self._serialize_value(value)
            if expire_seconds:
                await self._redis_client.setex(key, expire_seconds, serialized_value)
            else:
                await self._redis_client.set(key, serialized_value)
            return True
        except Exception as e:
            self._handle_redis_error("set", key, e)
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if not self._ensure_available():
            return False
            
        try:
            result = await self._redis_client.delete(key)
            return bool(result)
        except Exception as e:
            self._handle_redis_error("delete", key, e)
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        if not self._ensure_available():
            return False
            
        try:
            return bool(await self._redis_client.exists(key))
        except Exception as e:
            self._handle_redis_error("exists", key, e)
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if Redis service is available."""
        return self._is_available
    
    async def health_check(self) -> bool:
        """Perform health check on Redis connection.
        
        Returns:
            True if healthy, False otherwise
        """
        if not self._redis_client:
            return False
            
        try:
            await self._redis_client.ping()
            self._is_available = True
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._is_available = False
            return False
    
    async def acquire_lock(self, lock_key: str, timeout_seconds: int = 30) -> bool:
        """Acquire a distributed lock.
        
        Args:
            lock_key: The lock key
            timeout_seconds: Lock timeout in seconds
            
        Returns:
            True if lock acquired, False otherwise
        """
        if not self._ensure_available():
            return False
            
        try:
            # Use Redis SET with NX (only if not exists) and EX (expiration)
            result = await self._redis_client.set(
                f"lock:{lock_key}", 
                "locked", 
                nx=True, 
                ex=timeout_seconds
            )
            return bool(result)
        except Exception as e:
            self._handle_redis_error("acquire_lock", lock_key, e)
            return False
    
    async def release_lock(self, lock_key: str) -> bool:
        """Release a distributed lock.
        
        Args:
            lock_key: The lock key
            
        Returns:
            True if lock released, False otherwise
        """
        if not self._ensure_available():
            return False
            
        try:
            result = await self._redis_client.delete(f"lock:{lock_key}")
            return bool(result)
        except Exception as e:
            self._handle_redis_error("release_lock", lock_key, e)
            return False
    
    async def wait_for_lock(self, lock_key: str, max_wait_seconds: int = 10) -> bool:
        """Wait for a lock to be released.
        
        Args:
            lock_key: The lock key
            max_wait_seconds: Maximum time to wait in seconds
            
        Returns:
            True if lock was released (and we can proceed), False if timeout
        """
        if not self._ensure_available():
            return False
            
        import asyncio
        
        wait_interval = 0.1  # 100ms
        total_waited = 0
        
        while total_waited < max_wait_seconds:
            try:
                exists = await self._redis_client.exists(f"lock:{lock_key}")
                if not exists:
                    return True  # Lock is gone, we can proceed
                    
                await asyncio.sleep(wait_interval)
                total_waited += wait_interval
            except Exception as e:
                self._handle_redis_error("wait_for_lock", lock_key, e)
                return False
                
        return False  # Timeout


# Global cache service instance
cache_service = CacheService()
"""Redis cache service for efficient data caching."""

import json
import logging
from typing import Any, Optional

import redis
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
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or Redis unavailable
        """
        if not self._is_available or not self._redis_client:
            return None
            
        try:
            value = await self._redis_client.get(key)
            if value:
                try:
                    # Try to deserialize JSON
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Return as string if not JSON
                    return value
            return None
        except (ConnectionError, TimeoutError, ResponseError) as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            self._is_available = False
            return None
        except Exception as e:
            logger.error(f"Unexpected cache get error for key '{key}': {e}")
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
        if not self._is_available or not self._redis_client:
            return False
            
        try:
            # Serialize to JSON if not string
            if not isinstance(value, str):
                value = json.dumps(value)
                
            if expire_seconds:
                await self._redis_client.setex(key, expire_seconds, value)
            else:
                await self._redis_client.set(key, value)
            return True
        except (ConnectionError, TimeoutError, ResponseError) as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            self._is_available = False
            return False
        except Exception as e:
            logger.error(f"Unexpected cache set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache by key.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if not self._is_available or not self._redis_client:
            return False
            
        try:
            result = await self._redis_client.delete(key)
            return bool(result)
        except (ConnectionError, TimeoutError, ResponseError) as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")
            self._is_available = False
            return False
        except Exception as e:
            logger.error(f"Unexpected cache delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        if not self._is_available or not self._redis_client:
            return False
            
        try:
            return bool(await self._redis_client.exists(key))
        except (ConnectionError, TimeoutError, ResponseError) as e:
            logger.warning(f"Cache exists error for key '{key}': {e}")
            self._is_available = False
            return False
        except Exception as e:
            logger.error(f"Unexpected cache exists error for key '{key}': {e}")
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


# Global cache service instance
cache_service = CacheService()
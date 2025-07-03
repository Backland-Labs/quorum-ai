"""Tests for Redis cache service."""

import json
import pytest
from unittest.mock import AsyncMock, patch

from redis.exceptions import ConnectionError, ResponseError, TimeoutError

from services.cache_service import CacheService


@pytest.fixture
async def cache_service():
    """Create a fresh cache service instance for each test."""
    service = CacheService()
    yield service
    # Ensure cleanup
    if service._pool and hasattr(service._pool, "disconnect"):
        try:
            await service._pool.disconnect()
        except TypeError:
            # Handle mock objects
            pass


@pytest.fixture
async def mock_redis():
    """Create a mock Redis client."""
    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=1)
    return mock


class TestCacheServiceInitialization:
    """Test cache service initialization and connection handling."""

    @pytest.mark.asyncio
    async def test_successful_initialization(self, cache_service, mock_redis):
        """Test successful Redis connection initialization."""
        mock_pool = AsyncMock()
        with patch(
            "services.cache_service.ConnectionPool.from_url", return_value=mock_pool
        ):
            with patch("services.cache_service.Redis", return_value=mock_redis):
                await cache_service.initialize()

                assert cache_service._pool is not None
                assert cache_service._redis_client is not None
                assert cache_service.is_available is True
                mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_connection_error(self, cache_service):
        """Test graceful handling of connection errors during initialization."""
        mock_pool = AsyncMock()
        with patch(
            "services.cache_service.ConnectionPool.from_url", return_value=mock_pool
        ):
            mock_redis_failing = AsyncMock()
            mock_redis_failing.ping = AsyncMock(
                side_effect=ConnectionError("Connection failed")
            )

            with patch("services.cache_service.Redis", return_value=mock_redis_failing):
                await cache_service.initialize()

                assert cache_service.is_available is False

    @pytest.mark.asyncio
    async def test_close_connection(self, cache_service):
        """Test closing Redis connection pool."""
        mock_pool = AsyncMock()
        cache_service._pool = mock_pool

        await cache_service.close()

        mock_pool.disconnect.assert_called_once()


class TestCacheOperations:
    """Test cache CRUD operations."""

    @pytest.mark.asyncio
    async def test_get_string_value(self, cache_service, mock_redis):
        """Test getting a string value from cache."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.get.return_value = "test_value"

        result = await cache_service.get("test_key")

        assert result == "test_value"
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_json_value(self, cache_service, mock_redis):
        """Test getting a JSON value from cache."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        test_dict = {"key": "value", "number": 42}
        mock_redis.get.return_value = json.dumps(test_dict)

        result = await cache_service.get("test_key")

        assert result == test_dict
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_service, mock_redis):
        """Test getting a nonexistent key returns None."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.get.return_value = None

        result = await cache_service.get("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_when_unavailable(self, cache_service):
        """Test get returns None when Redis is unavailable."""
        cache_service._is_available = False

        result = await cache_service.get("test_key")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_string_value(self, cache_service, mock_redis):
        """Test setting a string value in cache."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True

        result = await cache_service.set("test_key", "test_value")

        assert result is True
        mock_redis.set.assert_called_once_with("test_key", "test_value")

    @pytest.mark.asyncio
    async def test_set_json_value(self, cache_service, mock_redis):
        """Test setting a JSON value in cache."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        test_dict = {"key": "value", "number": 42}

        result = await cache_service.set("test_key", test_dict)

        assert result is True
        mock_redis.set.assert_called_once_with("test_key", json.dumps(test_dict))

    @pytest.mark.asyncio
    async def test_set_with_expiration(self, cache_service, mock_redis):
        """Test setting a value with expiration time."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True

        result = await cache_service.set("test_key", "test_value", expire_seconds=300)

        assert result is True
        mock_redis.setex.assert_called_once_with("test_key", 300, "test_value")

    @pytest.mark.asyncio
    async def test_set_when_unavailable(self, cache_service):
        """Test set returns False when Redis is unavailable."""
        cache_service._is_available = False

        result = await cache_service.set("test_key", "test_value")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_existing_key(self, cache_service, mock_redis):
        """Test deleting an existing key."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.delete.return_value = 1

        result = await cache_service.delete("test_key")

        assert result == 1
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache_service, mock_redis):
        """Test deleting a nonexistent key."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.delete.return_value = 0

        result = await cache_service.delete("nonexistent")

        assert result == 0

    @pytest.mark.asyncio
    async def test_exists_for_existing_key(self, cache_service, mock_redis):
        """Test checking existence of an existing key."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.exists.return_value = 1

        result = await cache_service.exists("test_key")

        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_exists_for_nonexistent_key(self, cache_service, mock_redis):
        """Test checking existence of a nonexistent key."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.exists.return_value = 0

        result = await cache_service.exists("nonexistent")

        assert result is False


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_get_connection_error(self, cache_service, mock_redis):
        """Test get handles connection errors gracefully."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.get.side_effect = ConnectionError("Connection lost")

        result = await cache_service.get("test_key")

        assert result is None
        assert cache_service.is_available is False

    @pytest.mark.asyncio
    async def test_set_timeout_error(self, cache_service, mock_redis):
        """Test set handles timeout errors gracefully."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.set.side_effect = TimeoutError("Operation timed out")

        result = await cache_service.set("test_key", "value")

        assert result is False
        assert cache_service.is_available is False

    @pytest.mark.asyncio
    async def test_delete_response_error(self, cache_service, mock_redis):
        """Test delete handles response errors gracefully."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.delete.side_effect = ResponseError("Invalid command")

        result = await cache_service.delete("test_key")

        assert result == 0
        assert cache_service.is_available is False

    @pytest.mark.asyncio
    async def test_exists_generic_error(self, cache_service, mock_redis):
        """Test exists handles generic errors gracefully."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True
        mock_redis.exists.side_effect = Exception("Unexpected error")

        result = await cache_service.exists("test_key")

        assert result is False
        # Generic errors don't mark service as unavailable
        assert cache_service.is_available is True


class TestHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_service, mock_redis):
        """Test successful health check."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = False  # Start as unavailable

        result = await cache_service.health_check()

        assert result is True
        assert cache_service.is_available is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, cache_service, mock_redis):
        """Test failed health check."""
        cache_service._redis_client = mock_redis
        cache_service._is_available = True  # Start as available
        mock_redis.ping.side_effect = ConnectionError("Connection failed")

        result = await cache_service.health_check()

        assert result is False
        assert cache_service.is_available is False

    @pytest.mark.asyncio
    async def test_health_check_no_client(self, cache_service):
        """Test health check when client is not initialized."""
        cache_service._redis_client = None

        result = await cache_service.health_check()

        assert result is False


class TestPrivateHelperMethods:
    """Test private helper methods for completeness."""

    def test_ensure_available_when_available(self, cache_service):
        """Test _ensure_available returns True when service is ready."""
        cache_service._is_available = True
        cache_service._redis_client = AsyncMock()

        result = cache_service._ensure_available()

        assert result is True
        assert cache_service._is_available is True

    def test_ensure_available_when_unavailable(self, cache_service):
        """Test _ensure_available returns False when service not ready."""
        cache_service._is_available = False
        cache_service._redis_client = None

        result = cache_service._ensure_available()

        assert result is False
        assert cache_service._redis_client is None

    def test_serialize_value_string(self, cache_service):
        """Test _serialize_value with string input."""
        test_string = "test_value"

        result = cache_service._serialize_value(test_string)

        assert result == test_string
        assert isinstance(result, str)

    def test_serialize_value_dict(self, cache_service):
        """Test _serialize_value with dictionary input."""
        test_dict = {"key": "value", "number": 42}

        result = cache_service._serialize_value(test_dict)

        assert result == json.dumps(test_dict)
        assert isinstance(result, str)

    def test_deserialize_value_json(self, cache_service):
        """Test _deserialize_value with valid JSON."""
        test_dict = {"key": "value", "number": 42}
        json_string = json.dumps(test_dict)

        result = cache_service._deserialize_value(json_string)

        assert result == test_dict
        assert isinstance(result, dict)

    def test_deserialize_value_string(self, cache_service):
        """Test _deserialize_value with non-JSON string."""
        test_string = "not_json_string"

        result = cache_service._deserialize_value(test_string)

        assert result == test_string
        assert isinstance(result, str)

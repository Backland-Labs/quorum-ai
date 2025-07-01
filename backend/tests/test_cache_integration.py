"""Integration tests for Redis cache service with real Redis instance."""

import asyncio
import os
import pytest
from datetime import datetime

from services.cache_service import CacheService
from config import settings


# Skip integration tests if SKIP_INTEGRATION_TESTS is set
pytestmark = pytest.mark.skipif(
    os.getenv("SKIP_INTEGRATION_TESTS", "false").lower() == "true",
    reason="Integration tests disabled"
)


@pytest.fixture(scope="module")
async def redis_cache_service():
    """Create a cache service instance for integration tests."""
    service = CacheService()
    await service.initialize()
    yield service
    # Cleanup
    await service.close()


class TestCacheServiceIntegration:
    """Integration tests with real Redis instance."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_redis_connectivity(self, redis_cache_service):
        """Test basic Redis connectivity and availability."""
        # Check health
        is_healthy = await redis_cache_service.health_check()
        
        if not is_healthy:
            pytest.skip("Redis is not available for integration testing")
        
        assert redis_cache_service.is_available is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_cache_lifecycle(self, redis_cache_service):
        """Test complete cache lifecycle with real Redis."""
        if not redis_cache_service.is_available:
            pytest.skip("Redis is not available for integration testing")
        
        test_key = f"test_integration_{datetime.utcnow().timestamp()}"
        test_value = {"message": "Hello Redis", "timestamp": datetime.utcnow().isoformat()}
        
        # Ensure key doesn't exist
        assert await redis_cache_service.exists(test_key) is False
        
        # Set value
        set_result = await redis_cache_service.set(test_key, test_value)
        assert set_result is True
        
        # Check existence
        assert await redis_cache_service.exists(test_key) is True
        
        # Get value
        retrieved_value = await redis_cache_service.get(test_key)
        assert retrieved_value == test_value
        
        # Delete value
        delete_result = await redis_cache_service.delete(test_key)
        assert delete_result is True
        
        # Verify deletion
        assert await redis_cache_service.exists(test_key) is False
        assert await redis_cache_service.get(test_key) is None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_expiration(self, redis_cache_service):
        """Test key expiration functionality."""
        if not redis_cache_service.is_available:
            pytest.skip("Redis is not available for integration testing")
        
        test_key = f"test_expiry_{datetime.utcnow().timestamp()}"
        test_value = "This will expire"
        
        # Set with 1 second expiration
        await redis_cache_service.set(test_key, test_value, expire_seconds=1)
        
        # Verify it exists
        assert await redis_cache_service.exists(test_key) is True
        assert await redis_cache_service.get(test_key) == test_value
        
        # Wait for expiration
        await asyncio.sleep(1.5)
        
        # Verify it's gone
        assert await redis_cache_service.exists(test_key) is False
        assert await redis_cache_service.get(test_key) is None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_operations(self, redis_cache_service):
        """Test concurrent cache operations."""
        if not redis_cache_service.is_available:
            pytest.skip("Redis is not available for integration testing")
        
        base_key = f"test_concurrent_{datetime.utcnow().timestamp()}"
        
        async def set_value(index: int):
            key = f"{base_key}_{index}"
            value = f"value_{index}"
            return await redis_cache_service.set(key, value)
        
        async def get_value(index: int):
            key = f"{base_key}_{index}"
            return await redis_cache_service.get(key)
        
        # Set values concurrently
        set_tasks = [set_value(i) for i in range(10)]
        set_results = await asyncio.gather(*set_tasks)
        assert all(result is True for result in set_results)
        
        # Get values concurrently
        get_tasks = [get_value(i) for i in range(10)]
        get_results = await asyncio.gather(*get_tasks)
        
        for i, result in enumerate(get_results):
            assert result == f"value_{i}"
        
        # Cleanup
        delete_tasks = [
            redis_cache_service.delete(f"{base_key}_{i}") for i in range(10)
        ]
        await asyncio.gather(*delete_tasks)
    
    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_large_value_handling(self, redis_cache_service):
        """Test handling of large values."""
        if not redis_cache_service.is_available:
            pytest.skip("Redis is not available for integration testing")
        
        test_key = f"test_large_{datetime.utcnow().timestamp()}"
        # Create a large value (1MB of data)
        large_value = {
            "data": "x" * (1024 * 1024),  # 1MB string
            "metadata": {
                "size": "1MB",
                "type": "test"
            }
        }
        
        # Set large value
        set_result = await redis_cache_service.set(test_key, large_value)
        assert set_result is True
        
        # Retrieve large value
        retrieved = await redis_cache_service.get(test_key)
        assert retrieved == large_value
        
        # Cleanup
        await redis_cache_service.delete(test_key)
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_special_characters_in_keys(self, redis_cache_service):
        """Test handling of special characters in cache keys."""
        if not redis_cache_service.is_available:
            pytest.skip("Redis is not available for integration testing")
        
        special_keys = [
            f"test:colon:{datetime.utcnow().timestamp()}",
            f"test.dot.{datetime.utcnow().timestamp()}",
            f"test-dash-{datetime.utcnow().timestamp()}",
            f"test_underscore_{datetime.utcnow().timestamp()}",
            f"test/slash/{datetime.utcnow().timestamp()}",
        ]
        
        for key in special_keys:
            value = f"value_for_{key}"
            
            # Set and verify
            assert await redis_cache_service.set(key, value) is True
            assert await redis_cache_service.get(key) == value
            
            # Cleanup
            assert await redis_cache_service.delete(key) is True
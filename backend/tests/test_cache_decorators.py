"""Tests for cache decorator functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from typing import List

from models import Proposal, ProposalState
from utils.cache_decorators import cache_result
from services.cache_service import cache_service


class TestCacheResultDecorator:
    """Test @cache_result decorator functionality."""

    @pytest.fixture(autouse=True)
    async def setup_cache_service(self):
        """Set up cache service for testing."""
        # Mock the cache service methods directly
        with patch.object(cache_service, "_is_available", True), patch.object(
            cache_service, "get", new_callable=AsyncMock
        ) as mock_get, patch.object(
            cache_service, "set", new_callable=AsyncMock
        ) as mock_set:
            mock_get.return_value = None
            mock_set.return_value = True
            yield {"get": mock_get, "set": mock_set}

    def test_cache_result_decorator_basic_functionality(self):
        """Test that @cache_result decorator can be applied to functions."""

        @cache_result(ttl=300)
        def simple_function(x: int) -> int:
            return x * 2

        # The function should still be callable
        result = simple_function(5)
        assert result == 10

    def test_cache_result_decorator_with_ttl_parameter(self):
        """Test that @cache_result decorator accepts TTL parameter."""

        @cache_result(ttl=600)
        def function_with_ttl(x: str) -> str:
            return f"processed_{x}"

        result = function_with_ttl("test")
        assert result == "processed_test"

    async def test_cache_result_decorator_with_async_function(
        self, setup_cache_service
    ):
        """Test that @cache_result decorator works with async functions."""

        @cache_result(ttl=300)
        async def async_function(x: int) -> int:
            return x * 3

        result = await async_function(4)
        assert result == 12

    async def test_cache_hit_returns_cached_value(self, setup_cache_service):
        """Test that cache hit returns cached value without calling function."""
        mocks = setup_cache_service
        # Mock a cache hit - return JSON string as Redis would
        mocks["get"].return_value = '{"cached": true, "value": 42}'

        call_count = 0

        @cache_result(ttl=300)
        async def expensive_function(x: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"cached": False, "value": x * 10}

        result = await expensive_function(5)

        # Should return cached value
        assert result == {"cached": True, "value": 42}
        # Function should not be called
        assert call_count == 0
        # get should be called to check cache
        mocks["get"].assert_called_once()

    async def test_cache_miss_calls_function_and_stores_result(
        self, setup_cache_service
    ):
        """Test that cache miss calls function and stores result in cache."""
        mocks = setup_cache_service
        # Mock a cache miss
        mocks["get"].return_value = None

        call_count = 0

        @cache_result(ttl=300)
        async def expensive_function(x: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"computed": True, "value": x * 10}

        result = await expensive_function(5)

        # Should return computed value
        assert result == {"computed": True, "value": 50}
        # Function should be called once
        assert call_count == 1
        # Both get and set should be called
        mocks["get"].assert_called_once()
        mocks["set"].assert_called_once()

    async def test_cache_key_generation_includes_function_name_and_args(
        self, setup_cache_service
    ):
        """Test that cache keys are generated correctly from function name and arguments."""
        mocks = setup_cache_service

        @cache_result(ttl=300)
        async def test_function(dao_id: str, limit: int = 10) -> List[str]:
            return [f"item_{i}" for i in range(limit)]

        await test_function("dao_123", limit=5)

        # Check that get was called with a key containing function name and parameters
        call_args = mocks["get"].call_args[0][0]
        assert "test_function" in call_args
        assert "dao_123" in call_args
        assert "5" in call_args

    def test_cache_result_with_pydantic_model_arguments(self):
        """Test that @cache_result works with Pydantic model arguments."""

        @cache_result(ttl=300)
        def process_proposal(proposal: Proposal) -> str:
            return f"Processed: {proposal.title}"

        proposal = Proposal(
            id="prop-123",
            title="Test Proposal",
            description="Test description",
            state=ProposalState.ACTIVE,
            created_at=datetime(2024, 1, 1),
            start_block=1000,
            end_block=2000,
            votes_for="1000",
            votes_against="100",
            votes_abstain="10",
            dao_id="dao-123",
            dao_name="Test DAO",
        )

        result = process_proposal(proposal)
        assert result == "Processed: Test Proposal"

    async def test_different_arguments_produce_different_cache_keys(
        self, setup_cache_service
    ):
        """Test that different function arguments produce different cache keys."""
        mocks = setup_cache_service

        @cache_result(ttl=300)
        async def parameterized_function(x: int, y: str) -> str:
            return f"{x}_{y}"

        # Call with different arguments
        await parameterized_function(1, "a")
        await parameterized_function(2, "b")

        # Should have been called twice with different keys
        assert mocks["get"].call_count == 2

        call_args_1 = mocks["get"].call_args_list[0][0][0]
        call_args_2 = mocks["get"].call_args_list[1][0][0]

        # Keys should be different
        assert call_args_1 != call_args_2

    async def test_cache_result_preserves_function_metadata(self):
        """Test that @cache_result preserves original function metadata."""

        @cache_result(ttl=300)
        async def documented_function(x: int) -> int:
            """This function does something important."""
            return x + 1

        # Function metadata should be preserved
        assert documented_function.__name__ == "documented_function"
        assert "important" in documented_function.__doc__

    def test_cache_result_without_ttl_uses_default(self):
        """Test that @cache_result can be used without explicit TTL."""

        # This should work and use a default TTL
        @cache_result()
        def function_default_ttl(x: int) -> int:
            return x

        result = function_default_ttl(42)
        assert result == 42


class TestCacheResultDecoratorFailureHandling:
    """Test @cache_result decorator failure handling and graceful fallback."""

    async def test_cache_service_unavailable_calls_function_directly(self):
        """Test that when cache service is unavailable, function is called directly."""
        with patch.object(cache_service, "_is_available", False):
            call_count = 0

            @cache_result(ttl=300)
            async def function_with_unavailable_cache(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x * 2

            result = await function_with_unavailable_cache(5)

            # Should return function result
            assert result == 10
            # Function should be called directly
            assert call_count == 1

    async def test_cache_get_exception_calls_function_directly(self):
        """Test that cache.get() exceptions result in direct function call."""
        with patch.object(cache_service, "_is_available", True), patch.object(
            cache_service, "get", new_callable=AsyncMock
        ) as mock_get:
            # Mock cache.get to raise an exception
            mock_get.side_effect = Exception("Redis connection failed")

            call_count = 0

            @cache_result(ttl=300)
            async def function_with_cache_error(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x * 3

            result = await function_with_cache_error(4)

            # Should return function result despite cache error
            assert result == 12
            # Function should be called directly
            assert call_count == 1

    async def test_cache_set_failure_does_not_affect_result(self):
        """Test that cache.set() failures don't affect function result."""
        with patch.object(cache_service, "_is_available", True), patch.object(
            cache_service, "get", new_callable=AsyncMock
        ) as mock_get, patch.object(
            cache_service, "set", new_callable=AsyncMock
        ) as mock_set:
            # Cache miss
            mock_get.return_value = None
            # Cache set fails
            mock_set.side_effect = Exception("Redis write failed")

            call_count = 0

            @cache_result(ttl=300)
            async def function_with_cache_write_error(x: int) -> dict:
                nonlocal call_count
                call_count += 1
                return {"value": x * 4}

            result = await function_with_cache_write_error(3)

            # Should return function result
            assert result == {"value": 12}
            # Function should be called
            assert call_count == 1
            # get should be called
            mock_get.assert_called_once()
            # set should be attempted but fail
            mock_set.assert_called_once()

    async def test_serialization_error_falls_back_to_function(self):
        """Test that serialization errors result in fallback to function."""
        with patch.object(cache_service, "_is_available", True), patch.object(
            cache_service, "get", new_callable=AsyncMock
        ) as mock_get, patch.object(
            cache_service, "set", new_callable=AsyncMock
        ) as mock_set, patch(
            "utils.cache_decorators.serialize_for_cache"
        ) as mock_serialize:
            # Cache miss
            mock_get.return_value = None
            # Serialization fails
            mock_serialize.side_effect = TypeError("Cannot serialize")

            call_count = 0

            @cache_result(ttl=300)
            async def function_with_serialization_error(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x * 5

            result = await function_with_serialization_error(2)

            # Should return function result
            assert result == 10
            # Function should be called
            assert call_count == 1
            # get should be called
            mock_get.assert_called_once()
            # set should not be called due to serialization error
            mock_set.assert_not_called()

    async def test_deserialization_error_falls_back_to_function(self):
        """Test that deserialization errors result in fallback to function."""
        with patch.object(cache_service, "_is_available", True), patch.object(
            cache_service, "get", new_callable=AsyncMock
        ) as mock_get, patch(
            "utils.cache_decorators.deserialize_from_cache"
        ) as mock_deserialize:
            # Cache hit with corrupt data
            mock_get.return_value = "corrupted cache data"
            # Deserialization fails
            mock_deserialize.side_effect = ValueError("Invalid JSON")

            call_count = 0

            @cache_result(ttl=300)
            async def function_with_deserialization_error(x: int) -> int:
                nonlocal call_count
                call_count += 1
                return x * 6

            result = await function_with_deserialization_error(1)

            # Should return function result
            assert result == 6
            # Function should be called
            assert call_count == 1
            # get should be called
            mock_get.assert_called_once()

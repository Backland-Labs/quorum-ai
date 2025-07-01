"""Tests for cache utility functions."""

import pytest
import unittest.mock
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

from models import Proposal, ProposalState, DAO
from utils.cache_utils import generate_cache_key, serialize_for_cache, deserialize_from_cache
from services.cache_service import cache_service


class TestCacheKeyGeneration:
    """Test cache key generation functionality."""
    
    def test_generate_cache_key_with_method_name_and_args(self):
        """Test that cache key includes method name and arguments."""
        method_name = "get_proposal"
        args = ("prop_123",)
        kwargs = {}
        
        key = generate_cache_key(method_name, args, kwargs)
        
        assert "get_proposal" in key
        assert "prop_123" in key
        
    def test_generate_cache_key_with_kwargs(self):
        """Test that cache key includes keyword arguments."""
        method_name = "get_proposals"
        args = ()
        kwargs = {"dao_id": "dao_123", "limit": 10}
        
        key = generate_cache_key(method_name, args, kwargs)
        
        assert "get_proposals" in key
        assert "dao_123" in key
        assert "10" in key
        
    def test_generate_cache_key_deterministic(self):
        """Test that identical inputs produce identical cache keys."""
        method_name = "get_dao"
        args = ("dao_123",)
        kwargs = {"include_stats": True}
        
        key1 = generate_cache_key(method_name, args, kwargs)
        key2 = generate_cache_key(method_name, args, kwargs)
        
        assert key1 == key2
        
    def test_generate_cache_key_different_for_different_inputs(self):
        """Test that different inputs produce different cache keys."""
        method_name = "get_dao"
        
        key1 = generate_cache_key(method_name, ("dao_123",), {})
        key2 = generate_cache_key(method_name, ("dao_456",), {})
        
        assert key1 != key2
        
    def test_generate_cache_key_with_complex_objects(self):
        """Test cache key generation with complex objects like Pydantic models."""
        method_name = "process_proposal"
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
            dao_name="Test DAO"
        )
        args = (proposal,)
        kwargs = {}
        
        key = generate_cache_key(method_name, args, kwargs)
        
        assert "process_proposal" in key
        assert "prop-123" in key
        
    def test_generate_cache_key_handles_none_values(self):
        """Test that cache key generation handles None values gracefully."""
        method_name = "get_data"
        args = (None, "value")
        kwargs = {"optional_param": None}
        
        key = generate_cache_key(method_name, args, kwargs)
        
        assert "get_data" in key
        assert key is not None
        
    def test_generate_cache_key_different_kwargs_order_same_result(self):
        """Test that kwargs order doesn't affect cache key generation."""
        method_name = "get_data"
        args = ()
        kwargs1 = {"a": 1, "b": 2}
        kwargs2 = {"b": 2, "a": 1}
        
        key1 = generate_cache_key(method_name, args, kwargs1)
        key2 = generate_cache_key(method_name, args, kwargs2)
        
        assert key1 == key2


class TestCacheSerialization:
    """Test cache serialization and deserialization functionality."""
    
    def test_serialize_simple_types(self):
        """Test serialization of simple Python types."""
        test_data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"key": "value"}
        }
        
        serialized = serialize_for_cache(test_data)
        
        assert isinstance(serialized, str)
        assert "hello" in serialized
        assert "42" in serialized
        
    def test_serialize_pydantic_models(self):
        """Test serialization of Pydantic models."""
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
            dao_name="Test DAO"
        )
        
        serialized = serialize_for_cache(proposal)
        
        assert isinstance(serialized, str)
        assert "prop-123" in serialized
        assert "Test Proposal" in serialized
        
    def test_deserialize_simple_types(self):
        """Test deserialization of simple Python types."""
        original_data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "dict": {"key": "value"}
        }
        
        serialized = serialize_for_cache(original_data)
        deserialized = deserialize_from_cache(serialized)
        
        assert deserialized == original_data
        
    def test_deserialize_pydantic_models_to_dict(self):
        """Test that Pydantic models are deserialized as dictionaries."""
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
            dao_name="Test DAO"
        )
        
        serialized = serialize_for_cache(proposal)
        deserialized = deserialize_from_cache(serialized)
        
        assert isinstance(deserialized, dict)
        assert deserialized["id"] == "prop-123"
        assert deserialized["title"] == "Test Proposal"
        
    def test_serialize_list_of_pydantic_models(self):
        """Test serialization of lists containing Pydantic models."""
        proposals = [
            Proposal(
                id="prop-1",
                title="Proposal 1",
                description="Description 1",
                state=ProposalState.ACTIVE,
                created_at=datetime(2024, 1, 1),
                start_block=1000,
                end_block=2000,
                votes_for="1000",
                votes_against="100",
                votes_abstain="10",
                dao_id="dao-123",
                dao_name="Test DAO"
            ),
            Proposal(
                id="prop-2",
                title="Proposal 2",
                description="Description 2",
                state=ProposalState.SUCCEEDED,
                created_at=datetime(2024, 1, 2),
                start_block=2000,
                end_block=3000,
                votes_for="2000",
                votes_against="200",
                votes_abstain="20",
                dao_id="dao-123",
                dao_name="Test DAO"
            )
        ]
        
        serialized = serialize_for_cache(proposals)
        deserialized = deserialize_from_cache(serialized)
        
        assert isinstance(deserialized, list)
        assert len(deserialized) == 2
        assert deserialized[0]["id"] == "prop-1"
        assert deserialized[1]["id"] == "prop-2"
        
    def test_serialize_invalid_data_raises_error(self):
        """Test that serializing invalid data raises appropriate error."""
        # Create a non-serializable object
        class NonSerializable:
            def __init__(self):
                self.func = lambda x: x
        
        non_serializable = NonSerializable()
        
        with pytest.raises(TypeError):
            serialize_for_cache(non_serializable)
            
    def test_deserialize_invalid_json_raises_error(self):
        """Test that deserializing invalid JSON raises appropriate error."""
        invalid_json = "invalid json string {"
        
        with pytest.raises(ValueError):
            deserialize_from_cache(invalid_json)
            
    def test_round_trip_serialization(self):
        """Test that data survives round-trip serialization."""
        complex_data = {
            "proposals": [
                Proposal(
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
                    dao_name="Test DAO"
                )
            ],
            "metadata": {
                "count": 1,
                "cached_at": "2024-01-01T00:00:00Z"
            }
        }
        
        serialized = serialize_for_cache(complex_data)
        deserialized = deserialize_from_cache(serialized)
        
        assert isinstance(deserialized, dict)
        assert "proposals" in deserialized
        assert "metadata" in deserialized
        assert len(deserialized["proposals"]) == 1
        assert deserialized["proposals"][0]["id"] == "prop-123"
        assert deserialized["metadata"]["count"] == 1


class TestCacheInvalidationUtilities:
    """Test cache invalidation utility functions."""
    
    @pytest.fixture(autouse=True)
    async def setup_cache_invalidation_service(self):
        """Set up cache service for invalidation testing."""
        with patch.object(cache_service, '_is_available', True), \
             patch.object(cache_service, '_redis_client') as mock_redis:
            mock_redis.delete = AsyncMock(return_value=3)  # Should match number of keys
            mock_redis.keys = AsyncMock(return_value=['key1', 'key2', 'key3'])
            yield mock_redis
    
    async def test_invalidate_cache_by_pattern_basic(self, setup_cache_invalidation_service):
        """Test cache invalidation by key pattern."""
        from utils.cache_utils import invalidate_cache_pattern
        
        mock_redis = setup_cache_invalidation_service
        
        # Should find and delete keys matching pattern
        deleted_count = await invalidate_cache_pattern("cache:get_dao:*")
        
        assert deleted_count == 3
        mock_redis.keys.assert_called_once_with("cache:get_dao:*")
        mock_redis.delete.assert_called_once_with('key1', 'key2', 'key3')
    
    async def test_invalidate_cache_by_pattern_no_matches(self, setup_cache_invalidation_service):
        """Test cache invalidation when no keys match pattern."""
        from utils.cache_utils import invalidate_cache_pattern
        
        mock_redis = setup_cache_invalidation_service
        mock_redis.keys.return_value = []
        
        deleted_count = await invalidate_cache_pattern("cache:nonexistent:*")
        
        assert deleted_count == 0
        mock_redis.keys.assert_called_once_with("cache:nonexistent:*")
        mock_redis.delete.assert_not_called()
    
    async def test_invalidate_dao_cache(self, setup_cache_invalidation_service):
        """Test cache invalidation for all DAO-related keys."""
        from utils.cache_utils import invalidate_dao_cache
        
        mock_redis = setup_cache_invalidation_service
        
        # Should invalidate all cache keys related to a specific DAO
        deleted_count = await invalidate_dao_cache("dao_123")
        
        # Should call keys with patterns for DAO-related cache entries
        expected_calls = [
            unittest.mock.call("cache:*dao_123*"),
            unittest.mock.call("cache:get_dao_proposals:dao_123:*"),
            unittest.mock.call("cache:get_proposals:*dao_id:dao_123*")
        ]
        
        assert mock_redis.keys.call_count >= 1
        assert deleted_count >= 0
    
    async def test_invalidate_proposal_cache(self, setup_cache_invalidation_service):
        """Test cache invalidation for proposal-related keys."""
        from utils.cache_utils import invalidate_proposal_cache
        
        mock_redis = setup_cache_invalidation_service
        
        # Should invalidate all cache keys related to a specific proposal
        deleted_count = await invalidate_proposal_cache("prop_123")
        
        # Should look for proposal-specific cache keys
        assert mock_redis.keys.call_count >= 1
        assert deleted_count >= 0
    
    async def test_bulk_cache_invalidation(self, setup_cache_invalidation_service):
        """Test bulk cache invalidation by multiple patterns."""
        from utils.cache_utils import bulk_invalidate_cache
        
        mock_redis = setup_cache_invalidation_service
        
        patterns = [
            "cache:get_dao:*",
            "cache:get_proposals:*", 
            "cache:process_proposal:*"
        ]
        
        total_deleted = await bulk_invalidate_cache(patterns)
        
        # Should call keys for each pattern
        assert mock_redis.keys.call_count == len(patterns)
        assert total_deleted >= 0
    
    async def test_invalidate_pattern_handles_redis_errors(self, setup_cache_invalidation_service):
        """Test that cache invalidation handles Redis errors gracefully."""
        from utils.cache_utils import invalidate_cache_pattern
        
        mock_redis = setup_cache_invalidation_service
        mock_redis.keys.side_effect = Exception("Redis connection failed")
        
        # Should return 0 and not raise exception
        deleted_count = await invalidate_cache_pattern("cache:test:*")
        
        assert deleted_count == 0
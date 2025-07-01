"""Tests for cache utility functions."""

import pytest
from datetime import datetime
from typing import Dict, Any

from models import Proposal, ProposalState, DAO
from utils.cache_utils import generate_cache_key


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
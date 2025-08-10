"""
Test suite for Pearl-compliant health functions.

This module tests the individual health functions that support the /healthcheck endpoint.
These functions provide the core health monitoring capabilities required by Pearl platform.

Key functions being tested:
1. get_tm_health_status() - Transaction manager health
2. is_making_on_chain_transactions() - On-chain activity check
3. is_staking_kpi_met() - Staking KPI validation
4. has_required_funds() - Fund availability check
5. get_agent_health() - Comprehensive health metrics
6. get_recent_rounds() - Recent rounds information
7. get_rounds_info() - Rounds metadata
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

import main
from models import AgentHealthMetrics, RoundInfo, RoundsInfo


class TestHealthFunctionsBehavior:
    """Test suite for health function behavior and integration."""

    def test_get_tm_health_status_returns_boolean(self):
        """
        Test that get_tm_health_status returns a boolean value.
        
        The function should always return True or False, never None or other types.
        """
        # Clear cache to ensure fresh test
        main.get_tm_health_status.cache_clear()
        
        result = main.get_tm_health_status()
        
        assert isinstance(result, bool), "Should return boolean value"

    def test_is_making_on_chain_transactions_returns_boolean(self):
        """
        Test that is_making_on_chain_transactions returns a boolean value.
        
        The function should always return True or False, never None or other types.
        """
        # Clear cache to ensure fresh test
        main.is_making_on_chain_transactions.cache_clear()
        
        result = main.is_making_on_chain_transactions()
        
        assert isinstance(result, bool), "Should return boolean value"

    def test_is_staking_kpi_met_returns_boolean(self):
        """
        Test that is_staking_kpi_met returns a boolean value.
        
        The function should always return True or False, never None or other types.
        """
        # Clear cache to ensure fresh test
        main.is_staking_kpi_met.cache_clear()
        
        result = main.is_staking_kpi_met()
        
        assert isinstance(result, bool), "Should return boolean value"

    def test_has_required_funds_returns_boolean(self):
        """
        Test that has_required_funds returns a boolean value.
        
        The function should always return True or False, never None or other types.
        """
        # Clear cache to ensure fresh test
        main.has_required_funds.cache_clear()
        
        result = main.has_required_funds()
        
        assert isinstance(result, bool), "Should return boolean value"


class TestAgentHealth:
    """Test suite for comprehensive agent health metrics."""

    @patch('main.has_required_funds')
    @patch('main.is_staking_kpi_met')
    @patch('main.is_making_on_chain_transactions')
    def test_get_agent_health_all_healthy(
        self, mock_transactions, mock_kpi, mock_funds
    ):
        """
        Test agent health when all sub-checks are healthy.
        
        Should return AgentHealthMetrics with all boolean fields set to True.
        """
        # Mock all health checks as healthy
        mock_transactions.return_value = True
        mock_kpi.return_value = True
        mock_funds.return_value = True
        
        result = main.get_agent_health()
        
        assert isinstance(result, AgentHealthMetrics)
        assert result.is_making_on_chain_transactions is True
        assert result.is_staking_kpi_met is True
        assert result.has_required_funds is True

    @patch('main.has_required_funds')
    @patch('main.is_staking_kpi_met')
    @patch('main.is_making_on_chain_transactions')
    def test_get_agent_health_mixed_status(
        self, mock_transactions, mock_kpi, mock_funds
    ):
        """
        Test agent health with mixed health status.
        
        Should accurately reflect the status of each individual check.
        """
        # Mock mixed health status
        mock_transactions.return_value = True
        mock_kpi.return_value = False
        mock_funds.return_value = True
        
        result = main.get_agent_health()
        
        assert isinstance(result, AgentHealthMetrics)
        assert result.is_making_on_chain_transactions is True
        assert result.is_staking_kpi_met is False
        assert result.has_required_funds is True

    @patch('main.has_required_funds')
    @patch('main.is_staking_kpi_met')
    @patch('main.is_making_on_chain_transactions')
    def test_get_agent_health_exception_handling(
        self, mock_transactions, mock_kpi, mock_funds
    ):
        """
        Test agent health handles exceptions gracefully.
        
        When any sub-check raises an exception, should return safe fallback values.
        """
        # Mock exception in one of the checks
        mock_transactions.side_effect = Exception("Service error")
        mock_kpi.return_value = True
        mock_funds.return_value = True
        
        result = main.get_agent_health()
        
        assert isinstance(result, AgentHealthMetrics)
        # Should return safe fallback values
        assert result.is_making_on_chain_transactions is False
        assert result.is_staking_kpi_met is False
        assert result.has_required_funds is False


class TestRoundsTracking:
    """Test suite for rounds tracking functionality."""

    def test_get_recent_rounds_structure(self):
        """
        Test that get_recent_rounds returns properly structured round objects.
        
        Each round should have id, timestamp, and status fields with correct types.
        """
        # Clear cache to ensure fresh test
        main.get_recent_rounds.cache_clear()
        
        result = main.get_recent_rounds()
        
        assert isinstance(result, list), "Should return a list"
        assert len(result) > 0, "Should return some rounds for MVP"
        
        # Check structure of first round
        round_obj = result[0]
        assert isinstance(round_obj, RoundInfo)
        assert isinstance(round_obj.id, str)
        assert isinstance(round_obj.timestamp, datetime)
        assert isinstance(round_obj.status, str)

    def test_get_recent_rounds_caching(self):
        """
        Test that recent rounds information is cached properly.
        
        The function should use @lru_cache to avoid repeated expensive operations.
        """
        # Clear cache first
        main.get_recent_rounds.cache_clear()
        
        # First call
        result1 = main.get_recent_rounds()
        # Second call should use cache
        result2 = main.get_recent_rounds()
        
        assert result1 == result2, "Cached results should be identical"
        
        # Verify cache info shows hits
        cache_info = main.get_recent_rounds.cache_info()
        assert cache_info.hits >= 1, "Should have cache hits"

    def test_get_recent_rounds_exception_handling(self):
        """
        Test that get_recent_rounds handles exceptions gracefully.
        
        When an error occurs, should return empty list as safe fallback.
        """
        # Clear cache first
        main.get_recent_rounds.cache_clear()
        
        with patch('main.datetime') as mock_datetime:
            # Mock datetime to raise exception
            mock_datetime.now.side_effect = Exception("Time error")
            
            result = main.get_recent_rounds()
            
            assert result == [], "Should return empty list on exception"

    def test_get_rounds_info_structure(self):
        """
        Test that get_rounds_info returns properly structured metadata.
        
        Should return RoundsInfo with total_rounds and last_round_timestamp.
        """
        # Clear cache to ensure fresh test
        main.get_rounds_info.cache_clear()
        
        result = main.get_rounds_info()
        
        assert isinstance(result, RoundsInfo)
        assert isinstance(result.total_rounds, int)
        assert result.total_rounds >= 0
        
        if result.last_round_timestamp is not None:
            assert isinstance(result.last_round_timestamp, datetime)

    @patch('main.get_recent_rounds')
    def test_get_rounds_info_integration(self, mock_recent_rounds):
        """
        Test that get_rounds_info properly integrates with get_recent_rounds.
        
        Should use the recent rounds data to calculate metadata.
        """
        # Clear cache first
        main.get_rounds_info.cache_clear()
        
        # Mock recent rounds
        mock_rounds = [
            RoundInfo(id="1", timestamp=datetime.now(timezone.utc), status="completed"),
            RoundInfo(id="2", timestamp=datetime.now(timezone.utc), status="completed")
        ]
        mock_recent_rounds.return_value = mock_rounds
        
        result = main.get_rounds_info()
        
        assert result.total_rounds == 2
        assert result.last_round_timestamp == mock_rounds[0].timestamp

    @patch('main.get_recent_rounds')
    def test_get_rounds_info_empty_rounds(self, mock_recent_rounds):
        """
        Test get_rounds_info when no recent rounds are available.
        
        Should handle empty rounds list gracefully.
        """
        # Clear cache first
        main.get_rounds_info.cache_clear()
        
        # Mock empty rounds
        mock_recent_rounds.return_value = []
        
        result = main.get_rounds_info()
        
        assert result.total_rounds == 0
        assert result.last_round_timestamp is None


class TestCachingBehavior:
    """Test suite for caching behavior across all health functions."""

    def test_all_functions_have_lru_cache(self):
        """
        Test that all health functions use @lru_cache decorator.
        
        This is required for performance to meet <100ms response time.
        """
        cached_functions = [
            main.get_tm_health_status,
            main.is_making_on_chain_transactions,
            main.is_staking_kpi_met,
            main.has_required_funds,
            main.get_recent_rounds,
            main.get_rounds_info,
        ]
        
        for func in cached_functions:
            assert hasattr(func, 'cache_info'), f"{func.__name__} should have cache_info"
            assert hasattr(func, 'cache_clear'), f"{func.__name__} should have cache_clear"

    def test_cache_clearing_behavior(self):
        """
        Test that cache clearing works properly for TTL simulation.
        
        The healthcheck endpoint clears caches to simulate TTL behavior.
        """
        # Call functions to populate cache
        main.get_tm_health_status()
        main.is_making_on_chain_transactions()
        main.is_staking_kpi_met()
        main.has_required_funds()
        main.get_recent_rounds()
        main.get_rounds_info()
        
        # Clear all caches
        main.get_tm_health_status.cache_clear()
        main.is_making_on_chain_transactions.cache_clear()
        main.is_staking_kpi_met.cache_clear()
        main.has_required_funds.cache_clear()
        main.get_recent_rounds.cache_clear()
        main.get_rounds_info.cache_clear()
        
        # Verify caches are cleared
        assert main.get_tm_health_status.cache_info().currsize == 0
        assert main.is_making_on_chain_transactions.cache_info().currsize == 0
        assert main.is_staking_kpi_met.cache_info().currsize == 0
        assert main.has_required_funds.cache_info().currsize == 0
        assert main.get_recent_rounds.cache_info().currsize == 0
        assert main.get_rounds_info.cache_info().currsize == 0
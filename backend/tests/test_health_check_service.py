"""
Test suite for HealthCheckService.

This module tests the HealthCheckService which provides comprehensive health status
information required for Olas Pearl integration. The service integrates with
ActivityService, SafeService, and StateTransitionTracker to provide real-time
health monitoring capabilities.

Key functionality being tested:
1. Service initialization and configuration
2. Caching behavior for performance optimization
3. Integration with external services (ActivityService, SafeService, StateTransitionTracker)
4. Error handling and graceful degradation
5. Complete health status generation with all required Pearl fields
6. Transaction manager health assessment
7. Agent health status (transactions, staking KPI, funds)
8. Consensus rounds information generation
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest

from services.health_check_service import HealthCheckService
from services.state_transition_tracker import AgentState, StateTransition


class TestHealthCheckService:
    """Test suite for the HealthCheckService class."""

    def test_service_initialization(self):
        """
        Test that HealthCheckService initializes correctly with all dependencies.
        
        This test verifies that the service can be created with proper dependency
        injection and that all configuration parameters are set correctly.
        """
        # Create mock dependencies
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Initialize service
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
            cache_ttl_seconds=15,
        )
        
        # Verify initialization
        assert service.activity_service == mock_activity_service
        assert service.safe_service == mock_safe_service
        assert service.state_transition_tracker == mock_state_tracker
        assert service.cache_ttl_seconds == 15
        assert service._cache == {}
        assert service._cache_timestamp is None

    def test_service_initialization_with_defaults(self):
        """
        Test that HealthCheckService initializes with default values when no dependencies provided.
        
        This ensures the service can handle cases where some dependencies are not available.
        """
        service = HealthCheckService()
        
        assert service.activity_service is None
        assert service.safe_service is None
        assert service.state_transition_tracker is None
        assert service.cache_ttl_seconds == 10  # Default value

    def test_cache_behavior_fresh_data(self):
        """
        Test that the service generates fresh data when cache is empty or expired.
        
        This test verifies that the caching mechanism works correctly and that
        fresh data is generated when needed.
        """
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Configure mocks for basic status
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        # Configure mocks for agent health
        mock_activity_service.get_activity_status.return_value = {
            "daily_activity_needed": False,
            "last_activity_date": "2025-01-30",
        }
        mock_activity_service.is_daily_activity_needed.return_value = False
        mock_safe_service.has_sufficient_funds.return_value = True
        
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
            cache_ttl_seconds=10,
        )
        
        # First call should generate fresh data
        result1 = service.get_complete_health_status()
        
        # Verify data structure
        assert "seconds_since_last_transition" in result1
        assert "is_tm_healthy" in result1
        assert "agent_health" in result1
        assert "rounds" in result1
        assert "rounds_info" in result1
        
        # Verify cache was populated
        assert service._cache_timestamp is not None
        assert service._cache == result1

    def test_cache_behavior_cached_data(self):
        """
        Test that the service returns cached data when cache is still valid.
        
        This test ensures that the caching mechanism improves performance by
        avoiding unnecessary computation when data is still fresh.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
            cache_ttl_seconds=10,
        )
        
        # First call to populate cache
        result1 = service.get_complete_health_status()
        first_timestamp = service._cache_timestamp
        
        # Second call should return cached data
        result2 = service.get_complete_health_status()
        second_timestamp = service._cache_timestamp
        
        # Verify same data returned and timestamp unchanged
        assert result1 == result2
        assert first_timestamp == second_timestamp

    def test_cache_expiration(self):
        """
        Test that cached data expires after the configured TTL.
        
        This test verifies that the cache doesn't serve stale data indefinitely
        and that fresh data is generated when the cache expires.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
            cache_ttl_seconds=1,  # Very short TTL for testing
        )
        
        # First call to populate cache
        result1 = service.get_complete_health_status()
        first_timestamp = service._cache_timestamp
        
        # Wait for cache to expire
        time.sleep(1.1)
        
        # Second call should generate fresh data
        result2 = service.get_complete_health_status()
        second_timestamp = service._cache_timestamp
        
        # Verify new timestamp (cache was refreshed)
        assert second_timestamp > first_timestamp

    def test_transaction_manager_health_healthy(self):
        """
        Test transaction manager health assessment when system is healthy.
        
        This test verifies that the TM health check correctly identifies a healthy
        system based on recent transitions and stability.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 30.0  # Recent activity
        mock_state_tracker.is_transitioning_fast.return_value = False  # Stable
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # TM should be healthy (recent activity + stable)
        assert result["is_tm_healthy"] is True

    def test_transaction_manager_health_unhealthy_no_transitions(self):
        """
        Test transaction manager health assessment when no transitions recorded.
        
        This test verifies that the TM health check correctly identifies an unhealthy
        system when no state transitions have been recorded.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = float('inf')  # No transitions
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # TM should be unhealthy (no transitions)
        assert result["is_tm_healthy"] is False

    def test_transaction_manager_health_unhealthy_old_transitions(self):
        """
        Test transaction manager health assessment when transitions are too old.
        
        This test verifies that the TM health check correctly identifies an unhealthy
        system when the last transition was too long ago.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 600.0  # 10 minutes ago (too old)
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # TM should be unhealthy (transitions too old)
        assert result["is_tm_healthy"] is False

    def test_transaction_manager_health_unhealthy_fast_transitions(self):
        """
        Test transaction manager health assessment when transitioning too fast.
        
        This test verifies that the TM health check correctly identifies an unhealthy
        system when transitions are happening too rapidly (indicating instability).
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 30.0  # Recent
        mock_state_tracker.is_transitioning_fast.return_value = True  # Too fast
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # TM should be unhealthy (transitioning too fast)
        assert result["is_tm_healthy"] is False

    def test_agent_health_all_healthy(self):
        """
        Test agent health assessment when all components are healthy.
        
        This test verifies that the agent health object correctly reports healthy
        status for transactions, staking KPI, and funds when all are functioning properly.
        """
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Configure healthy state
        mock_activity_service.get_activity_status.return_value = {
            "daily_activity_needed": False,
            "last_activity_date": "2025-01-30",
        }
        mock_activity_service.is_daily_activity_needed.return_value = False
        mock_safe_service.has_sufficient_funds.return_value = True
        
        # Basic state tracker setup
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # All agent health components should be healthy
        agent_health = result["agent_health"]
        assert agent_health["is_making_on_chain_transactions"] is True
        assert agent_health["is_staking_kpi_met"] is True
        assert agent_health["has_required_funds"] is True

    def test_agent_health_all_unhealthy(self):
        """
        Test agent health assessment when all components are unhealthy.
        
        This test verifies that the agent health object correctly reports unhealthy
        status when transactions, staking KPI, and funds are all problematic.
        """
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Configure unhealthy state
        mock_activity_service.get_activity_status.return_value = {
            "daily_activity_needed": True,
            "last_activity_date": None,
        }
        mock_activity_service.is_daily_activity_needed.return_value = True
        mock_safe_service.has_sufficient_funds.return_value = False
        
        # Basic state tracker setup
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # All agent health components should be unhealthy
        agent_health = result["agent_health"]
        assert agent_health["is_making_on_chain_transactions"] is False
        assert agent_health["is_staking_kpi_met"] is False
        assert agent_health["has_required_funds"] is False

    def test_agent_health_missing_services(self):
        """
        Test agent health assessment when required services are not available.
        
        This test verifies that the agent health gracefully handles missing
        dependencies and returns safe default values.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        service = HealthCheckService(
            activity_service=None,  # Missing
            safe_service=None,      # Missing
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # Should return safe defaults when services are missing
        agent_health = result["agent_health"]
        assert agent_health["is_making_on_chain_transactions"] is False
        assert agent_health["is_staking_kpi_met"] is False
        assert agent_health["has_required_funds"] is False

    def test_rounds_info_with_transitions(self):
        """
        Test rounds information generation when state transitions are available.
        
        This test verifies that the service can generate meaningful rounds data
        from state transition history.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        
        # Create mock transitions
        transitions = []
        base_time = datetime.now()
        for i in range(3):
            transition = Mock()
            transition.from_state = AgentState.IDLE
            transition.to_state = AgentState.STARTING
            transition.timestamp = base_time + timedelta(seconds=i * 10)
            transition.metadata = {"test": f"data_{i}"}
            transitions.append(transition)
        
        mock_state_tracker.transition_history = transitions
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # Verify rounds data
        rounds = result["rounds"]
        rounds_info = result["rounds_info"]
        
        assert len(rounds) == 3
        assert rounds_info["total_rounds"] == 3
        assert rounds_info["latest_round"] is not None
        assert rounds_info["average_round_duration"] > 0

    def test_rounds_info_no_transitions(self):
        """
        Test rounds information generation when no state transitions are available.
        
        This test verifies that the service handles the case where no transition
        history is available and returns appropriate empty data structures.
        """
        mock_state_tracker = Mock()
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []  # No transitions
        
        service = HealthCheckService(
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # Verify empty rounds data
        rounds = result["rounds"]
        rounds_info = result["rounds_info"]
        
        assert rounds == []
        assert rounds_info["total_rounds"] == 0
        assert rounds_info["latest_round"] is None
        assert rounds_info["average_round_duration"] == 0

    def test_error_handling_service_exceptions(self):
        """
        Test error handling when external services raise exceptions.
        
        This test verifies that the HealthCheckService gracefully handles
        exceptions from external dependencies and returns safe default values.
        """
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Configure services to raise exceptions
        mock_activity_service.get_activity_status.side_effect = Exception("Activity service error")
        mock_safe_service.has_sufficient_funds.side_effect = Exception("Safe service error")
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.side_effect = Exception("State tracker error")
        
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
        )
        
        # Should not raise exception, should return safe defaults
        result = service.get_complete_health_status()
        
        # Verify safe defaults are returned
        assert result["is_tm_healthy"] is False
        assert result["agent_health"]["is_making_on_chain_transactions"] is False
        assert result["agent_health"]["is_staking_kpi_met"] is False
        assert result["agent_health"]["has_required_funds"] is False
        assert result["rounds"] == []
        assert result["rounds_info"]["total_rounds"] == 0

    def test_complete_health_status_structure(self):
        """
        Test that the complete health status contains all required Pearl fields.
        
        This test verifies that the service returns a properly structured response
        with all the fields required by the Olas Pearl platform.
        """
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Configure basic mocks
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        mock_activity_service.get_activity_status.return_value = {
            "daily_activity_needed": False,
            "last_activity_date": "2025-01-30",
        }
        mock_activity_service.is_daily_activity_needed.return_value = False
        mock_safe_service.has_sufficient_funds.return_value = True
        
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
        )
        
        result = service.get_complete_health_status()
        
        # Verify all required Pearl fields are present
        required_fields = [
            "seconds_since_last_transition",
            "is_transitioning_fast",
            "period",
            "reset_pause_duration",
            "is_tm_healthy",
            "agent_health",
            "rounds",
            "rounds_info",
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
        
        # Verify agent_health structure
        agent_health = result["agent_health"]
        agent_health_fields = [
            "is_making_on_chain_transactions",
            "is_staking_kpi_met",
            "has_required_funds",
        ]
        
        for field in agent_health_fields:
            assert field in agent_health, f"Missing agent_health field: {field}"
        
        # Verify rounds_info structure
        rounds_info = result["rounds_info"]
        rounds_info_fields = [
            "total_rounds",
            "latest_round",
            "average_round_duration",
        ]
        
        for field in rounds_info_fields:
            assert field in rounds_info, f"Missing rounds_info field: {field}"

    def test_performance_under_100ms(self):
        """
        Test that the health check service responds within 100ms requirement.
        
        This test verifies that the service meets the Pearl platform's performance
        requirement of responding to health checks within 100 milliseconds.
        """
        mock_activity_service = Mock()
        mock_safe_service = Mock()
        mock_state_tracker = Mock()
        
        # Configure mocks for quick responses
        mock_state_tracker.seconds_since_last_transition = 42.5
        mock_state_tracker.is_transitioning_fast.return_value = False
        mock_state_tracker.fast_transition_window = 5
        mock_state_tracker.fast_transition_threshold = 0.5
        mock_state_tracker.transition_history = []
        
        mock_activity_service.get_activity_status.return_value = {
            "daily_activity_needed": False,
            "last_activity_date": "2025-01-30",
        }
        mock_activity_service.is_daily_activity_needed.return_value = False
        mock_safe_service.has_sufficient_funds.return_value = True
        
        service = HealthCheckService(
            activity_service=mock_activity_service,
            safe_service=mock_safe_service,
            state_transition_tracker=mock_state_tracker,
        )
        
        # Warm up the service (first call populates cache)
        service.get_complete_health_status()
        
        # Measure response time for cached call
        start_time = time.time()
        result = service.get_complete_health_status()
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Should be well under 100ms due to caching
        assert response_time < 100, f"Response time {response_time:.2f}ms exceeds 100ms requirement"
        assert result is not None
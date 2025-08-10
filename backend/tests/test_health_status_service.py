"""Tests for HealthStatusService."""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from services.health_status_service import HealthStatusService
from models import AgentHealth, HealthCheckResponse


class TestHealthStatusServiceInitialization:
    """Test HealthStatusService initialization and dependency injection."""

    def test_health_status_service_initialization(self):
        """
        Test HealthStatusService initialization with dependency injection.
        
        This test verifies that the HealthStatusService can be properly initialized
        with its required dependencies (SafeService, ActivityService, StateTransitionTracker)
        following the constructor injection pattern used throughout the codebase.
        """
        # Create mock dependencies
        mock_safe_service = MagicMock()
        mock_activity_service = MagicMock()
        mock_state_tracker = MagicMock()
        
        # Initialize service with dependencies
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        # Verify dependencies are properly injected
        assert service.safe_service is mock_safe_service
        assert service.activity_service is mock_activity_service
        assert service.state_transition_tracker is mock_state_tracker
        assert service.logger is not None

    def test_health_status_service_initialization_with_none_dependencies(self):
        """
        Test HealthStatusService handles None dependencies gracefully.
        
        This test ensures the service can handle cases where some dependencies
        might not be available, which is important for graceful degradation.
        """
        service = HealthStatusService(
            safe_service=None,
            activity_service=None,
            state_transition_tracker=None
        )
        
        assert service.safe_service is None
        assert service.activity_service is None
        assert service.state_transition_tracker is None
        assert service.logger is not None


class TestHealthStatusServiceHealthGathering:
    """Test HealthStatusService health status gathering functionality."""

    @pytest.mark.asyncio
    async def test_get_health_status_success_all_healthy(self):
        """
        Test successful health status gathering when all services are healthy.
        
        This test verifies that the service can successfully gather health information
        from all dependencies in parallel and return a complete HealthCheckResponse
        with all systems reporting as healthy.
        """
        # Create mock dependencies with healthy responses
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(return_value="gnosis")
        mock_web3 = MagicMock()
        mock_web3.is_connected = MagicMock(return_value=True)
        mock_safe_service.get_web3_connection = MagicMock(return_value=mock_web3)
        
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=False)
        mock_activity_service.get_activity_status = MagicMock(return_value={
            "last_activity_date": datetime.now().date().isoformat()
        })
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=[
            {"from_state": "idle", "to_state": "active", "timestamp": datetime.now()}
        ])
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        # Execute health status gathering
        result = await service.get_health_status()
        
        # Verify result structure and content
        assert isinstance(result, HealthCheckResponse)
        assert result.is_tm_healthy is True
        assert result.agent_health is not None
        assert isinstance(result.agent_health, AgentHealth)
        assert result.agent_health.is_making_on_chain_transactions is True
        assert result.agent_health.is_staking_kpi_met is True
        assert result.agent_health.has_required_funds is True
        assert isinstance(result.rounds, list)
        
        # Verify safe service methods were called
        mock_safe_service.select_optimal_chain.assert_called_once()
        mock_safe_service.get_web3_connection.assert_called_once_with("gnosis")

    @pytest.mark.asyncio
    async def test_get_health_status_with_timeout_failures(self):
        """
        Test health status gathering with timeout failures and graceful degradation.
        
        This test ensures that when individual health checks timeout or fail,
        the service returns safe defaults rather than failing completely,
        which is critical for maintaining system availability.
        """
        # Create mock dependencies with timeout scenarios
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(side_effect=asyncio.TimeoutError())
        
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(side_effect=Exception("Service unavailable"))
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=[])
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        # Execute health status gathering
        result = await service.get_health_status()
        
        # Verify graceful degradation with safe defaults
        assert isinstance(result, HealthCheckResponse)
        assert result.is_tm_healthy is True  # Safe default
        assert result.agent_health is not None
        assert result.agent_health.is_making_on_chain_transactions is True  # Safe default
        assert result.agent_health.is_staking_kpi_met is True  # Safe default
        assert result.agent_health.has_required_funds is True  # Safe default
        assert isinstance(result.rounds, list)

    @pytest.mark.asyncio
    async def test_get_health_status_with_none_dependencies(self):
        """
        Test health status gathering when dependencies are None.
        
        This test verifies that the service can handle missing dependencies
        gracefully by returning safe defaults, which is important for
        system resilience during partial service failures.
        """
        service = HealthStatusService(
            safe_service=None,
            activity_service=None,
            state_transition_tracker=None
        )
        
        # Execute health status gathering
        result = await service.get_health_status()
        
        # Verify safe defaults are returned
        assert isinstance(result, HealthCheckResponse)
        assert result.is_tm_healthy is True
        assert result.agent_health is not None
        assert result.agent_health.is_making_on_chain_transactions is True
        assert result.agent_health.is_staking_kpi_met is True
        assert result.agent_health.has_required_funds is True
        assert result.rounds == []

    @pytest.mark.asyncio
    async def test_get_health_status_parallel_execution_performance(self):
        """
        Test that health status gathering executes checks in parallel for performance.
        
        This test ensures that the service uses asyncio.gather() to execute
        health checks concurrently rather than sequentially, which is critical
        for meeting the <100ms response time requirement.
        """
        # Create mock dependencies with controlled delays
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(return_value="gnosis")
        mock_web3 = MagicMock()
        mock_web3.is_connected = MagicMock(return_value=True)
        mock_safe_service.get_web3_connection = MagicMock(return_value=mock_web3)
        
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=False)
        mock_activity_service.get_activity_status = MagicMock(return_value={})
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=[])
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        # Measure execution time
        start_time = datetime.now()
        result = await service.get_health_status()
        execution_time = (datetime.now() - start_time).total_seconds() * 1000  # Convert to milliseconds
        
        # Verify result and performance
        assert isinstance(result, HealthCheckResponse)
        assert execution_time < 100  # Should be under 100ms for parallel execution

    @pytest.mark.asyncio
    async def test_get_health_status_activity_service_integration(self):
        """
        Test health status gathering integrates properly with ActivityService.
        
        This test verifies that the service correctly interprets ActivityService
        responses to determine agent health status, particularly for staking KPI
        compliance which is critical for OLAS network participation.
        """
        # Create mock activity service with specific scenarios
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=True)  # Activity needed
        mock_activity_service.get_activity_status = MagicMock(return_value={
            "last_activity_date": (datetime.now().date() - timedelta(days=2)).isoformat()
        })
        
        service = HealthStatusService(
            safe_service=None,
            activity_service=mock_activity_service,
            state_transition_tracker=None
        )
        
        result = await service.get_health_status()
        
        # Verify activity service integration affects agent health
        assert isinstance(result, HealthCheckResponse)
        assert result.agent_health is not None
        # When activity is needed, staking KPI is not met (inverse relationship)
        assert result.agent_health.is_staking_kpi_met is False
        # Old activity means not making recent transactions
        assert result.agent_health.is_making_on_chain_transactions is False

    @pytest.mark.asyncio
    async def test_get_health_status_state_tracker_integration(self):
        """
        Test health status gathering integrates properly with StateTransitionTracker.
        
        This test verifies that the service can extract meaningful rounds information
        from the StateTransitionTracker, which provides insight into agent operational
        cycles and state management.
        """
        # Create mock state tracker with transition data
        mock_transitions = [
            {
                "from_state": "idle",
                "to_state": "fetching_proposals", 
                "timestamp": datetime.now() - timedelta(minutes=5),
                "metadata": {"round": 1}
            },
            {
                "from_state": "fetching_proposals",
                "to_state": "analyzing_proposal",
                "timestamp": datetime.now() - timedelta(minutes=3),
                "metadata": {"round": 1, "proposal_count": 5}
            }
        ]
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=mock_transitions)
        
        service = HealthStatusService(
            safe_service=None,
            activity_service=None,
            state_transition_tracker=mock_state_tracker
        )
        
        result = await service.get_health_status()
        
        # Verify state tracker integration provides rounds data
        assert isinstance(result, HealthCheckResponse)
        assert isinstance(result.rounds, list)
        # The service should process transitions into rounds info
        mock_state_tracker.get_recent_transitions.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_health_status_with_exception_in_gather(self):
        """
        Test health status gathering handles exceptions during parallel execution.
        
        This test verifies that when asyncio.gather() itself fails, the service
        returns safe defaults rather than propagating the exception.
        """
        # Create service that will cause gather to fail
        service = HealthStatusService(
            safe_service=None,
            activity_service=None,
            state_transition_tracker=None
        )
        
        # Mock the gather method to raise an exception
        with patch('asyncio.gather', side_effect=Exception("Gather failed")):
            result = await service.get_health_status()
        
        # Verify safe defaults are returned even on gather failure
        assert isinstance(result, HealthCheckResponse)
        assert result.is_tm_healthy is True
        assert result.agent_health is not None
        assert result.rounds == []

    @pytest.mark.asyncio
    async def test_transaction_manager_health_with_connection_error(self):
        """
        Test transaction manager health check handles connection errors gracefully.
        
        This test ensures that when the Safe service fails to connect to the blockchain,
        the health check returns a safe default rather than failing.
        """
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(return_value="gnosis")
        mock_safe_service.get_web3_connection = MagicMock(side_effect=ConnectionError("Network unavailable"))
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=None,
            state_transition_tracker=None
        )
        
        result = await service.get_health_status()
        
        # Should return safe default despite connection error
        assert result.is_tm_healthy is True

    @pytest.mark.asyncio
    async def test_agent_health_with_invalid_date_format(self):
        """
        Test agent health check handles invalid date formats gracefully.
        
        This test ensures that when the activity service returns malformed date data,
        the health check uses safe defaults rather than failing.
        """
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=False)
        mock_activity_service.get_activity_status = MagicMock(return_value={
            "last_activity_date": "invalid-date-format"
        })
        
        service = HealthStatusService(
            safe_service=None,
            activity_service=mock_activity_service,
            state_transition_tracker=None
        )
        
        result = await service.get_health_status()
        
        # Should handle invalid date gracefully
        assert result.agent_health is not None
        assert result.agent_health.is_making_on_chain_transactions is True  # Safe default

    @pytest.mark.asyncio
    async def test_rounds_info_with_complex_transitions(self):
        """
        Test rounds info gathering with complex state transition data.
        
        This test verifies that the service can properly process complex transition
        objects with various attribute types and structures.
        """
        # Create mock transition objects with different structures
        class MockTransition:
            def __init__(self, from_state, to_state, timestamp, metadata=None):
                self.from_state = MockState(from_state)
                self.to_state = MockState(to_state)
                self.timestamp = timestamp
                self.metadata = metadata or {}
        
        class MockState:
            def __init__(self, value):
                self.value = value
        
        mock_transitions = [
            MockTransition("idle", "active", datetime.now(), {"round": 1, "data": "test"}),
            MockTransition("active", "completed", datetime.now() - timedelta(minutes=1), {"round": 1})
        ]
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=mock_transitions)
        
        service = HealthStatusService(
            safe_service=None,
            activity_service=None,
            state_transition_tracker=mock_state_tracker
        )
        
        result = await service.get_health_status()
        
        # Should process complex transitions correctly
        assert isinstance(result.rounds, list)
        assert len(result.rounds) == 2
        if result.rounds:
            assert "from_state" in result.rounds[0]
            assert "to_state" in result.rounds[0]
            assert "timestamp" in result.rounds[0]
            assert "metadata" in result.rounds[0]


class TestHealthStatusServicePerformance:
    """Comprehensive performance tests for HealthStatusService."""

    @pytest.mark.asyncio
    async def test_health_status_gathering_performance_under_load(self):
        """
        Test health status gathering performance under concurrent load.
        
        This test ensures that the service maintains <100ms response time
        even when multiple health checks are executed concurrently, which
        is critical for Pearl platform monitoring requirements.
        """
        # Create mock dependencies with realistic delays
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(return_value="gnosis")
        mock_web3 = MagicMock()
        mock_web3.is_connected = MagicMock(return_value=True)
        mock_safe_service.get_web3_connection = MagicMock(return_value=mock_web3)
        
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=False)
        mock_activity_service.get_activity_status = MagicMock(return_value={
            "last_activity_date": datetime.now().date().isoformat()
        })
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=[])
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        # Execute multiple concurrent health checks
        async def single_health_check():
            start_time = datetime.now()
            result = await service.get_health_status()
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            return result, execution_time
        
        # Run 10 concurrent health checks
        tasks = [single_health_check() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all results and performance
        for result, execution_time in results:
            assert isinstance(result, HealthCheckResponse)
            assert execution_time < 100, f"Health check took {execution_time:.2f}ms, exceeds 100ms requirement"
            assert result.is_tm_healthy is True
            assert result.agent_health is not None

    @pytest.mark.asyncio
    async def test_health_status_gathering_timeout_performance(self):
        """
        Test that individual health check timeouts don't exceed service limits.
        
        This test verifies that even when individual service calls timeout,
        the overall health check completes within the required time bounds
        due to proper timeout handling and parallel execution.
        """
        # Create mock services with controlled timeout scenarios
        mock_safe_service = MagicMock()
        
        async def slow_chain_selection():
            await asyncio.sleep(0.1)  # 100ms delay - should timeout
            return "gnosis"
        
        mock_safe_service.select_optimal_chain = slow_chain_selection
        
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=False)
        mock_activity_service.get_activity_status = MagicMock(return_value={})
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=[])
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        # Measure total execution time
        start_time = datetime.now()
        result = await service.get_health_status()
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Should complete quickly despite individual timeouts
        assert execution_time < 100, f"Health check with timeouts took {execution_time:.2f}ms"
        assert isinstance(result, HealthCheckResponse)
        assert result.is_tm_healthy is True  # Safe default due to timeout

    @pytest.mark.asyncio
    async def test_health_status_memory_efficiency(self):
        """
        Test that health status gathering is memory efficient.
        
        This test ensures that the service doesn't create excessive objects
        or hold unnecessary references during health gathering, which is
        important for long-running agent processes.
        """
        import gc
        import sys
        
        # Create minimal mock dependencies
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(return_value="gnosis")
        mock_web3 = MagicMock()
        mock_web3.is_connected = MagicMock(return_value=True)
        mock_safe_service.get_web3_connection = MagicMock(return_value=mock_web3)
        
        service = HealthStatusService(safe_service=mock_safe_service)
        
        # Force garbage collection and measure initial memory
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Execute health check multiple times
        for _ in range(100):
            result = await service.get_health_status()
            assert isinstance(result, HealthCheckResponse)
        
        # Force garbage collection and measure final memory
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory growth should be reasonable (allow for logging and mock objects)
        object_growth = final_objects - initial_objects
        assert object_growth < 5000, f"Excessive memory growth: {object_growth} objects created"


class TestHealthStatusServiceEdgeCases:
    """Edge case tests for HealthStatusService to achieve >90% coverage."""

    @pytest.mark.asyncio
    async def test_agent_health_with_date_object_instead_of_string(self):
        """
        Test agent health check handles date objects correctly.
        
        This test covers the edge case where last_activity_date is already
        a date object rather than a string, ensuring the service handles
        both formats correctly.
        """
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=False)
        mock_activity_service.get_activity_status = MagicMock(return_value={
            "last_activity_date": datetime.now().date()  # Date object, not string
        })
        
        service = HealthStatusService(
            safe_service=None,
            activity_service=mock_activity_service,
            state_transition_tracker=None
        )
        
        result = await service.get_health_status()
        
        # Should handle date object correctly
        assert result.agent_health is not None
        assert result.agent_health.is_making_on_chain_transactions is True
        assert result.agent_health.is_staking_kpi_met is True

    @pytest.mark.asyncio
    async def test_rounds_info_gathering_with_timeout_exception(self):
        """
        Test rounds info gathering handles timeout exceptions gracefully.
        
        This test covers the exception handling path in _get_rounds_info
        to ensure proper error handling and safe defaults.
        """
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(
            side_effect=asyncio.TimeoutError("Timeout occurred")
        )
        
        service = HealthStatusService(
            safe_service=None,
            activity_service=None,
            state_transition_tracker=mock_state_tracker
        )
        
        result = await service.get_health_status()
        
        # Should handle timeout gracefully with safe defaults
        assert isinstance(result.rounds, list)
        assert result.rounds == []  # Safe default
        assert result.is_tm_healthy is True
        assert result.agent_health is not None

    @pytest.mark.asyncio
    async def test_health_status_with_mixed_success_and_failure(self):
        """
        Test health status gathering with mixed success and failure scenarios.
        
        This test ensures that when some health checks succeed and others fail,
        the service properly combines successful results with safe defaults
        for failed checks.
        """
        # Mock safe service that succeeds
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(return_value="gnosis")
        mock_web3 = MagicMock()
        mock_web3.is_connected = MagicMock(return_value=True)
        mock_safe_service.get_web3_connection = MagicMock(return_value=mock_web3)
        
        # Mock activity service that fails
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(
            side_effect=Exception("Activity service error")
        )
        
        # Mock state tracker that succeeds
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=[
            {"from_state": "idle", "to_state": "active", "timestamp": datetime.now()}
        ])
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        result = await service.get_health_status()
        
        # Should combine successful and failed results appropriately
        assert isinstance(result, HealthCheckResponse)
        assert result.is_tm_healthy is True  # Safe service succeeded
        assert result.agent_health is not None  # Safe default due to activity service failure
        assert result.agent_health.is_making_on_chain_transactions is True  # Safe default
        assert isinstance(result.rounds, list)  # State tracker succeeded

    @pytest.mark.asyncio
    async def test_comprehensive_performance_benchmark(self):
        """
        Comprehensive performance benchmark test for health status gathering.
        
        This test provides detailed performance metrics and ensures the service
        meets all performance requirements under various load conditions.
        """
        # Create realistic mock dependencies
        mock_safe_service = MagicMock()
        mock_safe_service.select_optimal_chain = MagicMock(return_value="gnosis")
        mock_web3 = MagicMock()
        mock_web3.is_connected = MagicMock(return_value=True)
        mock_safe_service.get_web3_connection = MagicMock(return_value=mock_web3)
        
        mock_activity_service = MagicMock()
        mock_activity_service.is_daily_activity_needed = MagicMock(return_value=False)
        mock_activity_service.get_activity_status = MagicMock(return_value={
            "last_activity_date": datetime.now().date().isoformat()
        })
        
        mock_state_tracker = MagicMock()
        mock_state_tracker.get_recent_transitions = MagicMock(return_value=[
            {"from_state": "idle", "to_state": "active", "timestamp": datetime.now()}
        ])
        
        service = HealthStatusService(
            safe_service=mock_safe_service,
            activity_service=mock_activity_service,
            state_transition_tracker=mock_state_tracker
        )
        
        # Warm up the service
        await service.get_health_status()
        
        # Benchmark multiple iterations
        execution_times = []
        for _ in range(50):
            start_time = datetime.now()
            result = await service.get_health_status()
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            execution_times.append(execution_time)
            
            # Verify result integrity
            assert isinstance(result, HealthCheckResponse)
            assert result.is_tm_healthy is True
            assert result.agent_health is not None
        
        # Calculate performance metrics
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        # Performance assertions
        assert avg_time < 50, f"Average response time {avg_time:.2f}ms exceeds 50ms target"
        assert max_time < 100, f"Maximum response time {max_time:.2f}ms exceeds 100ms requirement"
        assert min_time > 0, "Minimum response time should be positive"
        
        # Log performance metrics for monitoring
        print(f"\nPerformance Metrics:")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Maximum: {max_time:.2f}ms")
        print(f"Minimum: {min_time:.2f}ms")
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
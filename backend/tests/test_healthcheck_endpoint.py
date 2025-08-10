"""
Test suite for Pearl-compliant health check endpoint.

This module tests the /healthcheck endpoint which is required for Pearl platform integration.
The endpoint must provide real-time information about the agent's state transitions to help
the Pearl platform monitor agent health and responsiveness.

Key requirements being tested:
1. Endpoint exists at /healthcheck (not /health)
2. Returns JSON with required fields: seconds_since_last_transition, is_transitioning_fast
3. Optional fields: period, reset_pause_duration
4. Integration with StateTransitionTracker for accurate state monitoring
5. Response time must be < 100ms for real-time monitoring
6. Proper HTTP status codes (200 for healthy, appropriate errors otherwise)
7. Graceful handling when no transitions have been recorded yet
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

import main
from main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthcheckEndpoint:
    """Test suite for the Pearl-compliant /healthcheck endpoint."""

    def test_healthcheck_endpoint_exists(self, client):
        """
        Test that the /healthcheck endpoint exists and is accessible.
        
        This is critical because Pearl expects this exact endpoint path for monitoring.
        The endpoint must be at /healthcheck, not /health or any other variation.
        """
        response = client.get("/healthcheck")
        
        # Should not return 404
        assert response.status_code != 404, "Endpoint /healthcheck must exist"
        # Should return a successful status code
        assert response.status_code in [200, 503], f"Expected 200 or 503, got {response.status_code}"

    def test_healthcheck_returns_required_json_fields(self, client):
        """
        Test that the endpoint returns the required JSON fields.
        
        Pearl platform expects specific fields in the response:
        - seconds_since_last_transition: float indicating time since last state change
        - is_transitioning_fast: boolean indicating if transitions are happening too quickly
        
        These fields are critical for Pearl to assess agent health and stability.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "seconds_since_last_transition" in data, "Missing required field: seconds_since_last_transition"
        assert "is_transitioning_fast" in data, "Missing required field: is_transitioning_fast"
        
        # Check field types
        assert isinstance(data["seconds_since_last_transition"], (int, float)), \
            "seconds_since_last_transition must be a number"
        assert isinstance(data["is_transitioning_fast"], bool), \
            "is_transitioning_fast must be a boolean"

    def test_healthcheck_optional_fields(self, client):
        """
        Test that optional fields are properly formatted when present.
        
        Optional fields that Pearl may use for additional monitoring:
        - period: the time window for checking fast transitions
        - reset_pause_duration: threshold for considering transitions as "fast"
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check optional fields if present
        if "period" in data:
            assert isinstance(data["period"], (int, float)), "period must be a number"
            assert data["period"] > 0, "period must be positive"
            
        if "reset_pause_duration" in data:
            assert isinstance(data["reset_pause_duration"], (int, float)), \
                "reset_pause_duration must be a number"
            assert data["reset_pause_duration"] > 0, "reset_pause_duration must be positive"

    @patch('main._get_state_transition_tracker')
    def test_healthcheck_integrates_with_state_tracker(self, mock_get_tracker, client):
        """
        Test that the endpoint properly integrates with StateTransitionTracker.
        
        The health check must use the StateTransitionTracker to get accurate
        information about state transitions. This ensures consistency between
        what the agent is doing and what the health check reports.
        """
        # Mock the tracker instance
        mock_tracker = Mock()
        mock_tracker.seconds_since_last_transition = 42.5  # Property, not method
        mock_tracker.is_transitioning_fast.return_value = False
        mock_tracker.fast_transition_window = 5  # Add missing attributes
        mock_tracker.fast_transition_threshold = 0.5
        mock_get_tracker.return_value = mock_tracker
        
        response = client.get("/healthcheck")
        
        data = response.json()
        
        # Verify the endpoint used the tracker methods
        # Since seconds_since_last_transition is a property, we can't track calls
        # But we can verify the method was called
        assert mock_tracker.is_transitioning_fast.called, \
            "Endpoint must call StateTransitionTracker.is_transitioning_fast()"
        
        # Verify the values match what the tracker returned
        assert data["seconds_since_last_transition"] == 42.5
        assert data["is_transitioning_fast"] is False

    def test_healthcheck_response_time_under_100ms(self, client):
        """
        Test that the endpoint responds within 100ms.
        
        Pearl platform requires fast response times for real-time monitoring.
        The health check must respond quickly to avoid being considered unresponsive.
        100ms is the maximum acceptable response time for health checks.
        """
        # Warm up the endpoint
        client.get("/healthcheck")
        
        # Measure response time
        start_time = time.time()
        response = client.get("/healthcheck")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        assert response.status_code == 200
        assert response_time < 100, \
            f"Response time {response_time:.2f}ms exceeds 100ms requirement"

    def test_healthcheck_returns_200_when_healthy(self, client):
        """
        Test that the endpoint returns 200 OK when the agent is healthy.
        
        A healthy agent should always return 200 OK. This is the signal
        to Pearl that the agent is functioning normally.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200, "Healthy agent should return 200"
        
        # Should also return valid JSON
        data = response.json()
        assert isinstance(data, dict), "Response should be valid JSON object"

    @patch('main._get_state_transition_tracker')
    def test_healthcheck_handles_no_transitions_gracefully(self, mock_get_tracker, client):
        """
        Test that the endpoint handles the case when no transitions have occurred.
        
        When the agent first starts or hasn't recorded any transitions yet,
        the endpoint should still return valid data without crashing.
        This might happen during initialization or after a reset.
        """
        # Mock a fresh StateTransitionTracker with no transitions
        mock_tracker = Mock()
        # Simulate no transitions recorded
        mock_tracker.seconds_since_last_transition = float('inf')  # Property, not method
        mock_tracker.is_transitioning_fast.return_value = False
        mock_tracker.fast_transition_window = 5  # Add missing attributes
        mock_tracker.fast_transition_threshold = 0.5
        mock_get_tracker.return_value = mock_tracker
        
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle infinity gracefully
        assert data["seconds_since_last_transition"] in [float('inf'), None, -1], \
            "Should handle no transitions case gracefully"
        assert data["is_transitioning_fast"] is False

    def test_healthcheck_concurrent_requests(self, client):
        """
        Test that the endpoint handles concurrent requests properly.
        
        Pearl platform may make multiple concurrent health check requests.
        The endpoint must handle these without errors or data corruption.
        """
        import threading
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = client.get("/healthcheck")
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)
        
        # Launch 10 concurrent requests
        threads = []
        for _ in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Check results
        assert len(errors) == 0, f"Concurrent requests caused errors: {errors}"
        assert all(status == 200 for status in results), \
            f"Some requests failed: {results}"

    @patch('main._get_state_transition_tracker')
    def test_healthcheck_error_handling(self, mock_get_tracker, client):
        """
        Test that the endpoint handles errors gracefully.
        
        If the StateTransitionTracker encounters an error, the health check
        should still respond (possibly with a 503 Service Unavailable) rather
        than crashing. This ensures Pearl can still monitor the agent even
        when there are internal issues.
        """
        # Mock tracker that raises an exception
        mock_get_tracker.side_effect = Exception("Tracker error")
        
        response = client.get("/healthcheck")
        
        # Should handle error gracefully
        assert response.status_code in [200, 503], \
            f"Should return 200 or 503 on error, not {response.status_code}"
        
        # Should still return valid JSON
        data = response.json()
        assert isinstance(data, dict), "Should return valid JSON even on error"

    def test_healthcheck_contains_pearl_specific_fields(self, client):
        """
        Test that /healthcheck contains Pearl-specific fields.
        
        The Pearl-compliant /healthcheck endpoint must provide specific
        information about state transitions and agent health that is
        required by the Pearl platform for monitoring.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Pearl-specific fields are present
        assert "seconds_since_last_transition" in data, \
            "/healthcheck must have Pearl-specific state transition fields"
        assert "is_transitioning_fast" in data, \
            "/healthcheck must have Pearl-specific transition speed fields"
        assert "is_tm_healthy" in data, \
            "/healthcheck must have Pearl-specific transaction manager health fields"
        assert "agent_health" in data, \
            "/healthcheck must have Pearl-specific agent health fields"
        assert "rounds" in data, \
            "/healthcheck must have Pearl-specific rounds fields"


class TestHealthcheckEndpointEnhancement:
    """Test suite for enhanced healthcheck endpoint with Pearl compliance fields."""

    @patch('main.health_status_service')
    @patch('main._get_state_transition_tracker')
    def test_healthcheck_includes_pearl_compliance_fields_when_service_available(
        self, mock_get_tracker, mock_health_service, client
    ):
        """
        Test that healthcheck endpoint includes Pearl compliance fields when HealthStatusService is available.
        
        This is the core business logic test - when HEALTH_CHECK_ENABLED=True and HealthStatusService
        is initialized, the endpoint must include the additional Pearl compliance fields while
        maintaining backward compatibility with existing state transition fields.
        """
        # Mock state transition tracker (existing functionality)
        mock_tracker = Mock()
        mock_tracker.seconds_since_last_transition = 30.0
        mock_tracker.is_transitioning_fast.return_value = False
        mock_tracker.fast_transition_window = 5
        mock_tracker.fast_transition_threshold = 0.5
        mock_get_tracker.return_value = mock_tracker
        
        # Mock HealthStatusService with Pearl compliance data
        from models import AgentHealth, HealthCheckResponse
        import asyncio
        
        mock_health_response = HealthCheckResponse(
            is_tm_healthy=True,
            agent_health=AgentHealth(
                is_making_on_chain_transactions=True,
                is_staking_kpi_met=True,
                has_required_funds=True
            ),
            rounds=[{"round": 1, "status": "completed"}],
            rounds_info={"total_rounds": 1}
        )
        
        # Create a coroutine that returns the mock response
        async def mock_get_health_status():
            return mock_health_response
        
        mock_health_service.get_health_status = mock_get_health_status
        
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify existing state transition fields are preserved
        assert "seconds_since_last_transition" in data
        assert "is_transitioning_fast" in data
        assert data["seconds_since_last_transition"] == 30.0
        assert data["is_transitioning_fast"] is False
        
        # Verify new Pearl compliance fields are included
        assert "is_tm_healthy" in data
        assert "agent_health" in data
        assert "rounds" in data
        assert "rounds_info" in data
        
        # Verify field values match HealthStatusService response
        assert data["is_tm_healthy"] is True
        assert data["agent_health"]["is_making_on_chain_transactions"] is True
        assert data["agent_health"]["is_staking_kpi_met"] is True
        assert data["agent_health"]["has_required_funds"] is True
        assert data["rounds"] == [{"round": 1, "status": "completed"}]
        assert data["rounds_info"] == {"total_rounds": 1}

    @patch('main.health_status_service', None)
    @patch('main._get_state_transition_tracker')
    def test_healthcheck_graceful_degradation_when_service_unavailable(
        self, mock_get_tracker, client
    ):
        """
        Test that healthcheck endpoint gracefully degrades when HealthStatusService is not available.
        
        This tests the critical error handling path - when HealthStatusService is None or fails,
        the endpoint must still return HTTP 200 with safe defaults for Pearl compliance fields
        while preserving existing state transition functionality.
        """
        # Mock state transition tracker (existing functionality should still work)
        mock_tracker = Mock()
        mock_tracker.seconds_since_last_transition = 45.0
        mock_tracker.is_transitioning_fast.return_value = True
        mock_tracker.fast_transition_window = 5
        mock_tracker.fast_transition_threshold = 0.5
        mock_get_tracker.return_value = mock_tracker
        
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify existing functionality is preserved
        assert "seconds_since_last_transition" in data
        assert "is_transitioning_fast" in data
        assert data["seconds_since_last_transition"] == 45.0
        assert data["is_transitioning_fast"] is True
        
        # Verify safe defaults are returned for Pearl compliance fields
        assert "is_tm_healthy" in data
        assert "agent_health" in data
        assert "rounds" in data
        
        # Verify safe default values
        assert data["is_tm_healthy"] is True  # Safe default
        assert data["agent_health"]["is_making_on_chain_transactions"] is True
        assert data["agent_health"]["is_staking_kpi_met"] is True
        assert data["agent_health"]["has_required_funds"] is True
        assert data["rounds"] == []  # Empty list as safe default

    @patch('main.health_status_service')
    @patch('main._get_state_transition_tracker')
    def test_healthcheck_response_time_with_health_service(
        self, mock_get_tracker, mock_health_service, client
    ):
        """
        Test that enhanced healthcheck endpoint maintains <100ms response time requirement.
        
        This tests the critical performance requirement - even with additional Pearl compliance
        data gathering, the endpoint must respond within 100ms to meet Pearl platform requirements.
        """
        # Mock fast responses from all services
        mock_tracker = Mock()
        mock_tracker.seconds_since_last_transition = 15.0
        mock_tracker.is_transitioning_fast.return_value = False
        mock_tracker.fast_transition_window = 5
        mock_tracker.fast_transition_threshold = 0.5
        mock_get_tracker.return_value = mock_tracker
        
        from models import HealthCheckResponse
        import asyncio
        
        mock_health_response = HealthCheckResponse()  # Uses safe defaults
        
        # Create a coroutine that returns the mock response
        async def mock_get_health_status():
            return mock_health_response
        
        mock_health_service.get_health_status = mock_get_health_status
        
        # Warm up the endpoint
        client.get("/healthcheck")
        
        # Measure response time
        start_time = time.time()
        response = client.get("/healthcheck")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        assert response.status_code == 200
        assert response_time < 100, \
            f"Enhanced healthcheck response time {response_time:.2f}ms exceeds 100ms requirement"
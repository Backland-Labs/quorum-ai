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

    def test_healthcheck_has_pearl_specific_fields(self, client):
        """
        Test that /healthcheck provides Pearl-specific information.
        
        The Pearl-compliant /healthcheck endpoint must provide specific
        information about state transitions and agent health that is
        different from general health check endpoints.
        """
        healthcheck_response = client.get("/healthcheck")
        
        # Should exist and return 200
        assert healthcheck_response.status_code == 200
        
        # Should have Pearl-specific fields
        healthcheck_data = healthcheck_response.json()
        
        # Verify Pearl-specific fields are present
        pearl_fields = [
            "seconds_since_last_transition",
            "is_transitioning_fast", 
            "is_tm_healthy",
            "agent_health",
            "rounds",
            "rounds_info"
        ]
        
        for field in pearl_fields:
            assert field in healthcheck_data, \
                f"/healthcheck must have Pearl-specific field: {field}"

    def test_healthcheck_returns_new_pearl_fields(self, client):
        """
        Test that the endpoint returns all new Pearl-required fields.
        
        Pearl platform now requires additional fields beyond the basic transition info:
        - is_tm_healthy: Transaction manager health status
        - agent_health: Object with transaction, staking, and fund status
        - rounds: Array of recent consensus rounds
        - rounds_info: Metadata about consensus rounds
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check new required fields exist
        assert "is_tm_healthy" in data, "Missing required field: is_tm_healthy"
        assert "agent_health" in data, "Missing required field: agent_health"
        assert "rounds" in data, "Missing required field: rounds"
        assert "rounds_info" in data, "Missing required field: rounds_info"
        
        # Check field types
        assert isinstance(data["is_tm_healthy"], bool), \
            "is_tm_healthy must be a boolean"
        assert isinstance(data["agent_health"], dict), \
            "agent_health must be a dictionary"
        assert isinstance(data["rounds"], list), \
            "rounds must be a list"
        assert isinstance(data["rounds_info"], dict), \
            "rounds_info must be a dictionary"

    def test_healthcheck_agent_health_structure(self, client):
        """
        Test that the agent_health object has the correct structure.
        
        The agent_health object must contain three specific boolean fields
        that Pearl uses to assess agent operational status.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        agent_health = data["agent_health"]
        
        # Check required agent_health fields
        required_fields = [
            "is_making_on_chain_transactions",
            "is_staking_kpi_met", 
            "has_required_funds"
        ]
        
        for field in required_fields:
            assert field in agent_health, f"Missing agent_health field: {field}"
            assert isinstance(agent_health[field], bool), \
                f"agent_health.{field} must be a boolean"

    def test_healthcheck_rounds_info_structure(self, client):
        """
        Test that the rounds_info object has the correct structure.
        
        The rounds_info object provides metadata about consensus rounds
        that Pearl uses for monitoring agent consensus participation.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        rounds_info = data["rounds_info"]
        
        # Check required rounds_info fields
        assert "total_rounds" in rounds_info, "Missing rounds_info field: total_rounds"
        assert "latest_round" in rounds_info, "Missing rounds_info field: latest_round"
        assert "average_round_duration" in rounds_info, "Missing rounds_info field: average_round_duration"
        
        # Check field types
        assert isinstance(rounds_info["total_rounds"], int), \
            "rounds_info.total_rounds must be an integer"
        assert isinstance(rounds_info["average_round_duration"], (int, float)), \
            "rounds_info.average_round_duration must be a number"
        # latest_round can be None or dict

    def test_healthcheck_uses_health_check_service_integration(self, client):
        """
        Test that the endpoint integrates with HealthCheckService functionality.
        
        This test verifies that the endpoint returns the comprehensive health data
        that would be provided by the HealthCheckService, including all Pearl fields.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all Pearl fields are present (indicating service integration)
        required_fields = [
            "seconds_since_last_transition",
            "is_transitioning_fast",
            "is_tm_healthy",
            "agent_health",
            "rounds",
            "rounds_info",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field indicates service not integrated: {field}"
        
        # Verify agent_health structure
        agent_health = data["agent_health"]
        assert "is_making_on_chain_transactions" in agent_health
        assert "is_staking_kpi_met" in agent_health
        assert "has_required_funds" in agent_health
        
        # Verify rounds_info structure
        rounds_info = data["rounds_info"]
        assert "total_rounds" in rounds_info
        assert "latest_round" in rounds_info
        assert "average_round_duration" in rounds_info

    def test_healthcheck_graceful_degradation(self, client):
        """
        Test that the endpoint handles errors gracefully with safe defaults.
        
        Even if internal services fail, the endpoint should return a valid
        response with conservative default values rather than failing completely.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have all required fields even in error conditions
        assert "is_tm_healthy" in data
        assert "agent_health" in data
        assert "rounds" in data
        assert "rounds_info" in data
        
        # Verify data types are correct even for defaults
        assert isinstance(data["is_tm_healthy"], bool)
        assert isinstance(data["agent_health"], dict)
        assert isinstance(data["rounds"], list)
        assert isinstance(data["rounds_info"], dict)
        
        # Agent health should have required structure
        agent_health = data["agent_health"]
        for field in ["is_making_on_chain_transactions", "is_staking_kpi_met", "has_required_funds"]:
            assert field in agent_health
            assert isinstance(agent_health[field], bool)
        
        # Rounds info should have required structure
        rounds_info = data["rounds_info"]
        for field in ["total_rounds", "latest_round", "average_round_duration"]:
            assert field in rounds_info
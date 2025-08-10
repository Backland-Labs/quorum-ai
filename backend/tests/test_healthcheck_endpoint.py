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

    def test_healthcheck_different_from_health_endpoint(self, client):
        """
        Test that /healthcheck is different from the existing /health endpoint.
        
        The application already has a /health endpoint for general health checks.
        The Pearl-compliant /healthcheck endpoint must be separate and provide
        different, Pearl-specific information about state transitions.
        """
        # Get responses from both endpoints
        health_response = client.get("/health")
        healthcheck_response = client.get("/healthcheck")
        
        # Both should exist
        assert health_response.status_code == 200
        assert healthcheck_response.status_code != 404
        
        # They should return different data
        health_data = health_response.json()
        healthcheck_data = healthcheck_response.json()
        
        # /health has general info, /healthcheck has Pearl-specific fields
        assert "seconds_since_last_transition" not in health_data, \
            "/health should not have Pearl-specific fields"
        assert "seconds_since_last_transition" in healthcheck_data, \
            "/healthcheck must have Pearl-specific fields"

    def test_healthcheck_returns_new_pearl_fields(self, client):
        """
        Test that the endpoint returns all new Pearl-compliant fields.
        
        The enhanced healthcheck must include:
        - is_tm_healthy: Transaction manager health status
        - agent_health: Object with 3 boolean sub-fields
        - rounds: Array of recent rounds
        - rounds_info: Metadata about rounds
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check new Pearl-compliant fields exist
        assert "is_tm_healthy" in data, "Missing required field: is_tm_healthy"
        assert "agent_health" in data, "Missing required field: agent_health"
        assert "rounds" in data, "Missing required field: rounds"
        assert "rounds_info" in data, "Missing required field: rounds_info"
        
        # Check field types
        assert isinstance(data["is_tm_healthy"], bool), \
            "is_tm_healthy must be a boolean"
        assert isinstance(data["agent_health"], dict), \
            "agent_health must be an object"
        assert isinstance(data["rounds"], list), \
            "rounds must be an array"
        assert isinstance(data["rounds_info"], dict), \
            "rounds_info must be an object"

    def test_healthcheck_agent_health_structure(self, client):
        """
        Test that agent_health object has the correct 3 boolean sub-fields.
        
        The agent_health object must contain exactly these 3 boolean fields:
        - is_making_on_chain_transactions
        - is_staking_kpi_met
        - has_required_funds
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        agent_health = data["agent_health"]
        
        # Check required sub-fields exist
        assert "is_making_on_chain_transactions" in agent_health, \
            "Missing agent_health field: is_making_on_chain_transactions"
        assert "is_staking_kpi_met" in agent_health, \
            "Missing agent_health field: is_staking_kpi_met"
        assert "has_required_funds" in agent_health, \
            "Missing agent_health field: has_required_funds"
        
        # Check field types are boolean
        assert isinstance(agent_health["is_making_on_chain_transactions"], bool), \
            "is_making_on_chain_transactions must be boolean"
        assert isinstance(agent_health["is_staking_kpi_met"], bool), \
            "is_staking_kpi_met must be boolean"
        assert isinstance(agent_health["has_required_funds"], bool), \
            "has_required_funds must be boolean"

    def test_healthcheck_rounds_structure(self, client):
        """
        Test that rounds array contains properly structured round objects.
        
        Each round object should have:
        - id: string identifier
        - timestamp: ISO timestamp
        - status: string status
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        rounds = data["rounds"]
        
        # Rounds can be empty, but if present should be properly structured
        for round_obj in rounds:
            assert "id" in round_obj, "Round object missing id field"
            assert "timestamp" in round_obj, "Round object missing timestamp field"
            assert "status" in round_obj, "Round object missing status field"
            
            assert isinstance(round_obj["id"], str), "Round id must be string"
            assert isinstance(round_obj["timestamp"], str), "Round timestamp must be string"
            assert isinstance(round_obj["status"], str), "Round status must be string"

    def test_healthcheck_rounds_info_structure(self, client):
        """
        Test that rounds_info object has the correct metadata fields.
        
        The rounds_info object should contain:
        - total_rounds: integer count
        - last_round_timestamp: optional timestamp
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        rounds_info = data["rounds_info"]
        
        # Check required fields
        assert "total_rounds" in rounds_info, \
            "Missing rounds_info field: total_rounds"
        assert "last_round_timestamp" in rounds_info, \
            "Missing rounds_info field: last_round_timestamp"
        
        # Check field types
        assert isinstance(rounds_info["total_rounds"], int), \
            "total_rounds must be integer"
        assert rounds_info["total_rounds"] >= 0, \
            "total_rounds must be non-negative"
        
        # last_round_timestamp can be null or string
        if rounds_info["last_round_timestamp"] is not None:
            assert isinstance(rounds_info["last_round_timestamp"], str), \
                "last_round_timestamp must be string or null"

    def test_healthcheck_backward_compatibility(self, client):
        """
        Test that all existing fields are still present and unchanged.
        
        The enhanced endpoint must maintain backward compatibility by
        including all original fields with the same structure and types.
        """
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all original fields are still present
        original_fields = [
            "seconds_since_last_transition",
            "is_transitioning_fast",
            "period",
            "reset_pause_duration"
        ]
        
        for field in original_fields:
            assert field in data, f"Backward compatibility broken: missing {field}"
        
        # Check original field types are unchanged
        assert isinstance(data["seconds_since_last_transition"], (int, float)), \
            "seconds_since_last_transition type changed"
        assert isinstance(data["is_transitioning_fast"], bool), \
            "is_transitioning_fast type changed"
        
        if data["period"] is not None:
            assert isinstance(data["period"], (int, float)), \
                "period type changed"
        if data["reset_pause_duration"] is not None:
            assert isinstance(data["reset_pause_duration"], (int, float)), \
                "reset_pause_duration type changed"

    @patch('main.get_tm_health_status')
    @patch('main.get_agent_health')
    @patch('main.get_recent_rounds')
    @patch('main.get_rounds_info')
    def test_healthcheck_health_function_integration(
        self, mock_rounds_info, mock_recent_rounds, mock_agent_health, mock_tm_health, client
    ):
        """
        Test that the endpoint properly integrates with all health functions.
        
        Verifies that the endpoint calls all the new health functions and
        uses their return values in the response.
        """
        # Mock return values
        mock_tm_health.return_value = True
        mock_agent_health.return_value = {
            "is_making_on_chain_transactions": True,
            "is_staking_kpi_met": False,
            "has_required_funds": True
        }
        mock_recent_rounds.return_value = [
            {"id": "test_round", "timestamp": "2023-01-01T00:00:00Z", "status": "completed"}
        ]
        mock_rounds_info.return_value = {
            "total_rounds": 1,
            "last_round_timestamp": "2023-01-01T00:00:00Z"
        }
        
        response = client.get("/healthcheck")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify function calls
        assert mock_tm_health.called, "get_tm_health_status should be called"
        assert mock_agent_health.called, "get_agent_health should be called"
        assert mock_recent_rounds.called, "get_recent_rounds should be called"
        assert mock_rounds_info.called, "get_rounds_info should be called"
        
        # Verify response uses mocked values
        assert data["is_tm_healthy"] is True
        assert data["agent_health"]["is_making_on_chain_transactions"] is True
        assert data["agent_health"]["is_staking_kpi_met"] is False
        assert data["agent_health"]["has_required_funds"] is True
        assert len(data["rounds"]) == 1
        assert data["rounds"][0]["id"] == "test_round"
        assert data["rounds_info"]["total_rounds"] == 1

    def test_healthcheck_performance_with_new_fields(self, client):
        """
        Test that the enhanced endpoint still meets <100ms performance requirement.
        
        Even with additional health checks, the endpoint must respond quickly
        for real-time monitoring by the Pearl platform.
        """
        # Warm up the endpoint
        client.get("/healthcheck")
        
        # Measure response time for enhanced endpoint
        start_time = time.time()
        response = client.get("/healthcheck")
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        assert response.status_code == 200
        assert response_time < 100, \
            f"Enhanced endpoint response time {response_time:.2f}ms exceeds 100ms requirement"
        
        # Verify all new fields are present (ensuring we're testing the full endpoint)
        data = response.json()
        assert "is_tm_healthy" in data
        assert "agent_health" in data
        assert "rounds" in data
        assert "rounds_info" in data
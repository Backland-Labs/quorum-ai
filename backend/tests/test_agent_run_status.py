"""
Test suite for GET /agent-run/status endpoint.

This test suite validates the agent run status endpoint following TDD methodology.
Tests are written first to define the expected behavior before implementation.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from main import app


class TestAgentRunStatusEndpoint:
    """Test cases for the GET /agent-run/status endpoint."""

    @pytest.fixture
    def client(self):
        """FastAPI test client fixture."""
        # Initialize global services for testing
        import main
        from unittest.mock import Mock
        from services.agent_run_service import AgentRunService
        
        # Create mock agent run service
        main.agent_run_service = Mock(spec=AgentRunService)
        main.agent_run_service.get_latest_checkpoint = AsyncMock(return_value=None)
        main.agent_run_service.get_current_state = Mock(return_value="IDLE")
        main.agent_run_service.is_agent_active = Mock(return_value=False)
        
        return TestClient(app)

    def test_get_status_returns_correct_structure(self, client):
        """
        Verify that the status endpoint returns the expected JSON structure.
        
        Why this test is important:
        - Ensures the API contract is maintained for frontend components
        - Validates that all required fields are present in the response
        - Confirms the response structure matches what the AgentStatusWidget expects
        """
        response = client.get("/agent-run/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        assert "current_state" in data
        assert "last_run_timestamp" in data
        assert "is_active" in data
        assert "current_space_id" in data
        
        # Verify field types
        assert isinstance(data["current_state"], str)
        assert data["last_run_timestamp"] is None or isinstance(data["last_run_timestamp"], str)
        assert isinstance(data["is_active"], bool)
        assert data["current_space_id"] is None or isinstance(data["current_space_id"], str)

    def test_get_status_when_no_runs_have_occurred(self, client):
        """
        Ensure the endpoint handles gracefully when no agent runs have occurred.
        
        Why this test is important:
        - Validates error handling for fresh installations
        - Ensures the dashboard doesn't crash on first load
        - Confirms default values are sensible and don't confuse users
        """
        with patch('services.agent_run_service.AgentRunService.get_latest_checkpoint', return_value=None):
            response = client.get("/agent-run/status")
            
            assert response.status_code == 200
            data = response.json()
            
            # When no runs have occurred, expect default values
            assert data["current_state"] == "IDLE"
            assert data["last_run_timestamp"] is None
            assert data["is_active"] is False
            assert data["current_space_id"] is None

    def test_get_status_reflects_latest_checkpoint(self, client):
        """
        Ensure the timestamp is from the most recent checkpoint file.
        
        Why this test is important:
        - Validates that the service correctly identifies the latest run
        - Ensures timestamps are properly formatted for frontend display
        - Confirms the checkpoint aggregation logic works correctly
        """
        mock_checkpoint = {
            "space_id": "gitcoindao.eth",
            "timestamp": "2024-03-15T10:30:00Z",
            "proposals_analyzed": 5,
            "votes_cast": [
                {
                    "proposal_id": "0x123",
                    "vote": "FOR",
                    "timestamp": "2024-03-15T10:30:00Z"
                }
            ]
        }
        
        # Configure mocks for this test
        import main
        main.agent_run_service.get_latest_checkpoint.return_value = mock_checkpoint
        main.agent_run_service.get_current_state.return_value = "IDLE"
        main.agent_run_service.is_agent_active.return_value = False
        
        response = client.get("/agent-run/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["current_state"] == "IDLE"
        assert data["last_run_timestamp"] == "2024-03-15T10:30:00Z"
        assert data["is_active"] is False
        assert data["current_space_id"] == "gitcoindao.eth"

    def test_get_status_reflects_active_agent(self, client):
        """
        Verify the endpoint correctly reports when the agent is actively running.
        
        Why this test is important:
        - Ensures the frontend can disable action buttons during active runs
        - Validates integration with StateTransitionTracker
        - Confirms real-time status updates work correctly
        """
        mock_checkpoint = {
            "space_id": "gitcoindao.eth",
            "timestamp": "2024-03-15T10:30:00Z"
        }
        
        # Configure mocks for this test
        import main
        main.agent_run_service.get_latest_checkpoint.return_value = mock_checkpoint
        main.agent_run_service.get_current_state.return_value = "FETCHING_PROPOSALS"
        main.agent_run_service.is_agent_active.return_value = True
        
        response = client.get("/agent-run/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["current_state"] == "FETCHING_PROPOSALS"
        assert data["is_active"] is True

    def test_get_status_handles_errors_gracefully(self, client):
        """
        Ensure the endpoint handles internal errors without crashing.
        
        Why this test is important:
        - Validates error handling doesn't expose internal details
        - Ensures the dashboard remains functional even with backend issues
        - Confirms appropriate HTTP status codes are returned
        """
        # Configure mock to raise exception
        import main
        main.agent_run_service.get_latest_checkpoint.side_effect = Exception("Internal error")
        
        response = client.get("/agent-run/status")
        
        # Should return 500 with appropriate error message
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_status_endpoint_uses_state_transition_tracker(self):
        """
        Verify the endpoint correctly integrates with StateTransitionTracker.
        
        Why this test is important:
        - Ensures proper integration with existing state management
        - Validates that real-time state updates are reflected
        - Confirms the agent lifecycle is accurately reported
        """
        from services.agent_run_service import AgentRunService
        from services.state_manager import StateManager
        
        # Mock dependencies
        mock_state_manager = Mock(spec=StateManager)
        service = AgentRunService(state_manager=mock_state_manager)
        
        # Initialize service with mocked state tracker
        await service.initialize()
        
        # Verify state tracker is used
        assert hasattr(service, 'state_tracker')
        assert service.get_current_state() in [
            "idle", "starting", "loading_preferences", "fetching_proposals",
            "filtering_proposals", "analyzing_proposal", "deciding_vote",
            "submitting_vote", "casting_votes", "completing", "completed", "error"
        ]

    def test_status_endpoint_follows_api_conventions(self, client):
        """
        Ensure the endpoint follows project API conventions.
        
        Why this test is important:
        - Maintains consistency across all API endpoints
        - Ensures proper content-type headers
        - Validates response format matches OpenAPI schema
        """
        response = client.get("/agent-run/status")
        
        # Check headers
        assert response.headers["content-type"] == "application/json"
        
        # Verify response can be parsed as JSON
        data = response.json()
        assert isinstance(data, dict)
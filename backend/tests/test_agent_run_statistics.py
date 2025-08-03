"""
Tests for the GET /agent-run/statistics endpoint.

This test suite ensures the statistics endpoint correctly aggregates performance
metrics from all agent checkpoint files and handles various edge cases.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from main import app


class TestAgentRunStatisticsEndpoint:
    """Test cases for the GET /agent-run/statistics endpoint."""

    @pytest.fixture
    def client(self):
        """FastAPI test client fixture."""
        # Initialize global services for testing
        import main
        from unittest.mock import Mock
        from services.agent_run_service import AgentRunService
        
        # Create mock agent run service
        main.agent_run_service = Mock(spec=AgentRunService)
        main.agent_run_service.get_agent_run_statistics = AsyncMock()
        
        return TestClient(app)

    def test_get_statistics_returns_correct_structure(self, client):
        """
        Test that the statistics endpoint returns the expected data structure.
        
        Why: The frontend expects a specific structure to display performance metrics.
        What: Verifies all required fields are present in the response.
        """
        # Arrange
        import main
        expected_stats = {
            "total_runs": 10,
            "total_proposals_evaluated": 150,
            "total_votes_cast": 45,
            "average_confidence_score": 0.85,
            "success_rate": 0.9,
            "average_runtime_seconds": 120.5
        }
        main.agent_run_service.get_agent_run_statistics = AsyncMock(return_value=expected_stats)
        
        # Act
        response = client.get("/agent-run/statistics")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_runs"] == 10
        assert data["total_proposals_evaluated"] == 150
        assert data["total_votes_cast"] == 45
        assert data["average_confidence_score"] == 0.85
        assert data["success_rate"] == 0.9
        assert data["average_runtime_seconds"] == 120.5
        
    def test_get_statistics_handles_no_checkpoints_gracefully(self, client):
        """
        Test that the endpoint returns sensible defaults when no checkpoint files exist.
        
        Why: New installations won't have any agent runs yet.
        What: Verifies zeros and appropriate defaults are returned.
        """
        # Arrange
        import main
        expected_stats = {
            "total_runs": 0,
            "total_proposals_evaluated": 0,
            "total_votes_cast": 0,
            "average_confidence_score": 0.0,
            "success_rate": 0.0,
            "average_runtime_seconds": 0.0
        }
        main.agent_run_service.get_agent_run_statistics = AsyncMock(return_value=expected_stats)
        
        # Act
        response = client.get("/agent-run/statistics")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_runs"] == 0
        assert data["success_rate"] == 0.0
        
    def test_get_statistics_handles_service_errors_gracefully(self, client):
        """
        Test that the endpoint handles service-level errors appropriately.
        
        Why: File system errors or corrupted data shouldn't crash the API.
        What: Verifies proper error response when service fails.
        """
        # Arrange
        import main
        main.agent_run_service.get_agent_run_statistics = AsyncMock(
            side_effect=Exception("Failed to read checkpoint files")
        )
        
        # Act
        response = client.get("/agent-run/statistics")
        
        # Assert
        assert response.status_code == 500
        assert "detail" in response.json()


class TestAgentRunStatisticsService:
    """Test cases for the AgentRunService.get_agent_run_statistics method."""
    
    @pytest.fixture
    def agent_run_service(self):
        """Create a mock AgentRunService instance."""
        from services.agent_run_service import AgentRunService
        from services.state_manager import StateManager
        from unittest.mock import Mock, AsyncMock
        
        # Create a mock state manager
        mock_state_manager = Mock(spec=StateManager)
        mock_state_manager.load_state = AsyncMock()
        mock_state_manager.list_files = AsyncMock()
        
        # Create service with mocked dependencies
        with patch('services.agent_run_service.setup_pearl_logger'):
            service = AgentRunService(state_manager=mock_state_manager)
            # Mock the pearl_logger to avoid logging during tests
            service.pearl_logger = Mock()
            service.pearl_logger.warning = Mock()
            service.pearl_logger.error = Mock()
        
        return service
    
    @pytest.mark.asyncio
    async def test_statistics_aggregates_data_from_multiple_checkpoints(self, agent_run_service):
        """
        Test that statistics are correctly aggregated from multiple checkpoint files.
        
        Why: The agent creates one checkpoint per space, we need to aggregate all.
        What: Verifies correct summation and averaging across checkpoints.
        """
        # Arrange - Create multiple checkpoint files
        checkpoint1 = {
            "space_id": "space1.eth",
            "run_id": "run1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "proposals_evaluated": 50,
            "votes_cast": [
                {"proposal_id": "0x1", "vote": "FOR", "confidence": 0.9},
                {"proposal_id": "0x2", "vote": "AGAINST", "confidence": 0.8}
            ],
            "runtime_seconds": 100,
            "errors": []
        }
        
        checkpoint2 = {
            "space_id": "space2.eth",
            "run_id": "run2",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "proposals_evaluated": 30,
            "votes_cast": [
                {"proposal_id": "0x3", "vote": "FOR", "confidence": 0.7}
            ],
            "runtime_seconds": 80,
            "errors": []
        }
        
        # Mock state manager to return our test checkpoints
        agent_run_service.state_manager.list_files = AsyncMock(
            return_value=["agent_checkpoint_space1.eth.json", "agent_checkpoint_space2.eth.json"]
        )
        agent_run_service.state_manager.load_state = AsyncMock(
            side_effect=[checkpoint1, checkpoint2]
        )
        
        # Act
        stats = await agent_run_service.get_agent_run_statistics()
        
        # Assert
        assert stats["total_runs"] == 2
        assert stats["total_proposals_evaluated"] == 80  # 50 + 30
        assert stats["total_votes_cast"] == 3  # 2 + 1
        assert stats["average_confidence_score"] == 0.8  # (0.9 + 0.8 + 0.7) / 3
        assert stats["success_rate"] == 1.0  # Both runs have no errors
        assert stats["average_runtime_seconds"] == 90.0  # (100 + 80) / 2
    
    @pytest.mark.asyncio
    async def test_statistics_calculates_success_rate_correctly(self, agent_run_service):
        """
        Test that success rate is calculated as (runs_without_errors / total_runs).
        
        Why: Success rate is a key metric for agent reliability.
        What: Verifies correct calculation with mix of successful and failed runs.
        """
        # Arrange
        checkpoint_success = {
            "space_id": "space1.eth",
            "errors": [],
            "proposals_evaluated": 0,
            "votes_cast": [],
            "runtime_seconds": 0
        }
        
        checkpoint_failure = {
            "space_id": "space2.eth",
            "errors": ["Error: API rate limit exceeded"],
            "proposals_evaluated": 0,
            "votes_cast": [],
            "runtime_seconds": 0
        }
        
        agent_run_service.state_manager.list_files = AsyncMock(
            return_value=["agent_checkpoint_space1.eth.json", "agent_checkpoint_space2.eth.json"]
        )
        agent_run_service.state_manager.load_state = AsyncMock(
            side_effect=[checkpoint_success, checkpoint_failure]
        )
        
        # Act
        stats = await agent_run_service.get_agent_run_statistics()
        
        # Assert
        assert stats["success_rate"] == 0.5  # 1 success out of 2 runs
    
    @pytest.mark.asyncio
    async def test_statistics_handles_division_by_zero_when_no_runs(self, agent_run_service):
        """
        Test that statistics calculation handles division by zero gracefully.
        
        Why: When no runs exist, averages would cause division by zero.
        What: Verifies all averages return 0.0 when no data exists.
        """
        # Arrange
        agent_run_service.state_manager.list_files = AsyncMock(return_value=[])
        
        # Act
        stats = await agent_run_service.get_agent_run_statistics()
        
        # Assert
        assert stats["average_confidence_score"] == 0.0
        assert stats["success_rate"] == 0.0
        assert stats["average_runtime_seconds"] == 0.0
    
    @pytest.mark.asyncio
    async def test_statistics_handles_corrupted_checkpoint_gracefully(self, agent_run_service):
        """
        Test that corrupted checkpoint files are skipped without crashing.
        
        Why: File corruption shouldn't prevent statistics from being calculated.
        What: Verifies partial results are returned when some files are corrupted.
        """
        # Arrange
        valid_checkpoint = {
            "space_id": "valid.eth",
            "proposals_evaluated": 10,
            "votes_cast": [],
            "runtime_seconds": 60,
            "errors": []
        }
        
        agent_run_service.state_manager.list_files = AsyncMock(
            return_value=["agent_checkpoint_valid.eth.json", "agent_checkpoint_corrupted.eth.json"]
        )
        # First load succeeds, second fails
        agent_run_service.state_manager.load_state = AsyncMock(
            side_effect=[valid_checkpoint, Exception("Corrupted file")]
        )
        
        # Act
        stats = await agent_run_service.get_agent_run_statistics()
        
        # Assert - Should still return stats from valid checkpoint
        assert stats["total_runs"] == 1
        assert stats["total_proposals_evaluated"] == 10
    
    @pytest.mark.asyncio
    async def test_statistics_handles_missing_fields_in_checkpoints(self, agent_run_service):
        """
        Test that missing fields in checkpoint files are handled gracefully.
        
        Why: Checkpoint schema might evolve, old files might miss new fields.
        What: Verifies sensible defaults are used for missing fields.
        """
        # Arrange - Checkpoint missing some expected fields
        incomplete_checkpoint = {
            "space_id": "incomplete.eth",
            "votes_cast": [{"confidence": 0.9}]  # Missing other fields
        }
        
        agent_run_service.state_manager.list_files = AsyncMock(
            return_value=["agent_checkpoint_incomplete.eth.json"]
        )
        agent_run_service.state_manager.load_state = AsyncMock(
            return_value=incomplete_checkpoint
        )
        
        # Act
        stats = await agent_run_service.get_agent_run_statistics()
        
        # Assert - Should use defaults for missing fields
        assert stats["total_runs"] == 1
        assert stats["total_proposals_evaluated"] == 0  # Default when missing
        assert stats["total_votes_cast"] == 1
        assert stats["average_runtime_seconds"] == 0.0  # Default when missing
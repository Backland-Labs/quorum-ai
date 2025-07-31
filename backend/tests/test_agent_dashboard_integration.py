"""
Integration tests for the Agent Dashboard functionality.

These tests verify the end-to-end behavior of all agent dashboard endpoints
and their interaction with the underlying services.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock

import pytest
from httpx import AsyncClient, ASGITransport

from backend.config import settings
from backend.main import app
from backend.models import (
    AgentDecisionResponse,
    AgentRunRequest,
    AgentRunStatistics,
    AgentRunStatus,
    Proposal,
)
from backend.services.state_manager import StateManager
from backend.services.state_transition_tracker import StateTransitionTracker


@pytest.fixture
def mock_state_dir(tmp_path):
    """Create a temporary state directory for testing."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return state_dir


@pytest.fixture
def sample_checkpoint_data():
    """Sample checkpoint data for testing."""
    return {
        "space_id": "test-space",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "end_time": datetime.now(timezone.utc).isoformat(),
        "proposals_evaluated": 5,
        "votes_cast": [
            {
                "proposal_id": "0x123",
                "proposal_title": "Test Proposal 1",
                "vote": "FOR",
                "confidence": 0.95,
                "reasoning": "Strong alignment",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "proposal_id": "0x456",
                "proposal_title": "Test Proposal 2",
                "vote": "AGAINST",
                "confidence": 0.85,
                "reasoning": "Risk concerns",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ],
        "errors": [],
        "dry_run": False,
    }


@pytest.fixture
async def setup_test_checkpoints(mock_state_dir, sample_checkpoint_data):
    """Set up test checkpoint files."""
    # Create multiple checkpoints for different spaces
    spaces = ["test-space", "another-space", "third-space"]
    
    for i, space_id in enumerate(spaces):
        checkpoint_data = sample_checkpoint_data.copy()
        checkpoint_data["space_id"] = space_id
        checkpoint_data["proposals_evaluated"] = 3 + i * 2
        
        # Add some errors to test success rate calculation
        if i == 2:  # Third space has errors
            checkpoint_data["errors"] = ["Test error 1", "Test error 2"]
        
        checkpoint_file = mock_state_dir / f"agent_checkpoint_{space_id}.json"
        checkpoint_file.write_text(json.dumps(checkpoint_data))
    
    return mock_state_dir


@pytest.fixture
def mock_state_manager(mock_state_dir):
    """Create a mock StateManager that uses the test directory."""
    manager = MagicMock(spec=StateManager)
    manager.store_path = mock_state_dir
    return manager


class TestAgentDashboardIntegration:
    """Integration tests for the complete agent dashboard flow."""

    @pytest.mark.asyncio
    async def test_complete_dashboard_flow(self, setup_test_checkpoints, monkeypatch):
        """Test the complete flow of fetching agent dashboard data."""
        # Set environment variable for state path
        monkeypatch.setenv("STORE_PATH", str(setup_test_checkpoints))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test 1: Get agent status
            response = await client.get("/agent-run/status")
            assert response.status_code == 200
            status_data = response.json()
            
            assert status_data["current_state"] == "IDLE"
            assert status_data["is_active"] is False
            assert "last_run_timestamp" in status_data
            assert status_data["current_space_id"] == "third-space"  # Most recent
            
            # Test 2: Get agent decisions
            response = await client.get("/agent-run/decisions?limit=5")
            assert response.status_code == 200
            decisions_data = response.json()
            
            assert len(decisions_data["decisions"]) == 5  # Should get top 5
            assert decisions_data["total"] == 6  # 2 decisions per space * 3 spaces
            
            # Verify decision structure
            first_decision = decisions_data["decisions"][0]
            assert "proposal_id" in first_decision
            assert "proposal_title" in first_decision
            assert "vote" in first_decision
            assert "confidence" in first_decision
            assert "timestamp" in first_decision
            
            # Test 3: Get agent statistics
            response = await client.get("/agent-run/statistics")
            assert response.status_code == 200
            stats_data = response.json()
            
            assert stats_data["total_runs"] == 3
            assert stats_data["total_proposals_reviewed"] == 12  # 3 + 5 + 7
            assert stats_data["total_votes_cast"] == 6  # 2 per space
            assert stats_data["average_confidence"] == 0.9  # All votes have 0.95 or 0.85
            assert stats_data["success_rate"] == 0.67  # 2/3 runs had no errors

    @pytest.mark.asyncio
    async def test_agent_run_trigger_integration(self, mock_state_dir, monkeypatch):
        """Test triggering an agent run through the API."""
        monkeypatch.setenv("STORE_PATH", str(mock_state_dir))
        
        # Mock the agent run service
        mock_run_agent = AsyncMock(return_value={
            "status": "completed",
            "proposals_evaluated": 3,
            "votes_cast": 2,
            "errors": []
        })
        
        with patch("backend.services.agent_run_service.AgentRunService.run_agent", mock_run_agent):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Trigger agent run
                response = await client.post(
                    "/agent-run",
                    json={"space_id": "test-space", "dry_run": False}
                )
                assert response.status_code == 200
                
                # Verify the agent was called
                mock_run_agent.assert_called_once()
                
                # Check status after run
                response = await client.get("/agent-run/status")
                assert response.status_code == 200
                # Note: Status might still be IDLE if run completed quickly

    @pytest.mark.asyncio
    async def test_dashboard_with_no_data(self, mock_state_dir, monkeypatch):
        """Test dashboard endpoints when no agent runs have occurred."""
        monkeypatch.setenv("STORE_PATH", str(mock_state_dir))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Test status with no runs
            response = await client.get("/agent-run/status")
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["last_run_timestamp"] is None
            assert status_data["current_space_id"] is None
            
            # Test decisions with no data
            response = await client.get("/agent-run/decisions")
            assert response.status_code == 200
            decisions_data = response.json()
            assert decisions_data["decisions"] == []
            assert decisions_data["total"] == 0
            
            # Test statistics with no data
            response = await client.get("/agent-run/statistics")
            assert response.status_code == 200
            stats_data = response.json()
            assert stats_data["total_runs"] == 0
            assert stats_data["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_decision_enrichment_with_snapshot_service(self, setup_test_checkpoints, monkeypatch):
        """Test that decisions are enriched with proposal details from Snapshot."""
        monkeypatch.setenv("STORE_PATH", str(setup_test_checkpoints))
        
        # Mock Snapshot service
        mock_snapshot_service = AsyncMock()
        mock_snapshot_service.get_proposal = AsyncMock(return_value=Proposal(
            id="0x123",
            title="Enhanced Test Proposal 1",
            body="Test body",
            choices=["Yes", "No"],
            state="active",
            space={"id": "test-space", "name": "Test Space"},
            scores=[100, 50],
            scores_total=150,
            author="0xtest",
            created=1234567890,
            end=1234567890,
            snapshot="12345",
            strategies=[],
            quorum=100
        ))
        
        with patch("backend.services.snapshot_service.SnapshotService", return_value=mock_snapshot_service):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/agent-run/decisions?limit=1")
                assert response.status_code == 200
                
                decisions_data = response.json()
                first_decision = decisions_data["decisions"][0]
                
                # The title should be enriched from Snapshot, not the checkpoint
                assert first_decision["proposal_title"] == "Enhanced Test Proposal 1"

    @pytest.mark.asyncio
    async def test_concurrent_dashboard_requests(self, setup_test_checkpoints, monkeypatch):
        """Test that multiple dashboard requests can be handled concurrently."""
        monkeypatch.setenv("STORE_PATH", str(setup_test_checkpoints))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Make multiple concurrent requests
            tasks = [
                client.get("/agent-run/status"),
                client.get("/agent-run/decisions"),
                client.get("/agent-run/statistics"),
                client.get("/agent-run/decisions?limit=10"),
                client.get("/agent-run/status"),
            ]
            
            responses = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_state_transition_during_active_run(self, mock_state_dir, monkeypatch):
        """Test dashboard behavior when agent is actively running."""
        monkeypatch.setenv("STORE_PATH", str(mock_state_dir))
        
        # Mock an active state
        tracker = StateTransitionTracker()
        tracker.transition_to("FETCHING_PROPOSALS")
        
        with patch("backend.services.state_transition_tracker.tracker", tracker):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/agent-run/status")
                assert response.status_code == 200
                
                status_data = response.json()
                assert status_data["current_state"] == "FETCHING_PROPOSALS"
                assert status_data["is_active"] is True

    @pytest.mark.asyncio
    async def test_error_handling_in_dashboard_flow(self, mock_state_dir, monkeypatch):
        """Test error handling across dashboard endpoints."""
        monkeypatch.setenv("STORE_PATH", str(mock_state_dir))
        
        # Create a corrupted checkpoint file
        checkpoint_file = mock_state_dir / "agent_checkpoint_corrupted.json"
        checkpoint_file.write_text("invalid json{")
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Status should handle corrupted files gracefully
            response = await client.get("/agent-run/status")
            assert response.status_code == 200
            
            # Decisions should skip corrupted files
            response = await client.get("/agent-run/decisions")
            assert response.status_code == 200
            
            # Statistics should skip corrupted files
            response = await client.get("/agent-run/statistics")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_data_consistency(self, setup_test_checkpoints, monkeypatch):
        """Test that data is consistent across different dashboard endpoints."""
        monkeypatch.setenv("STORE_PATH", str(setup_test_checkpoints))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get all dashboard data
            status_response = await client.get("/agent-run/status")
            decisions_response = await client.get("/agent-run/decisions?limit=100")
            stats_response = await client.get("/agent-run/statistics")
            
            status_data = status_response.json()
            decisions_data = decisions_response.json()
            stats_data = stats_response.json()
            
            # Verify consistency
            assert stats_data["total_votes_cast"] == decisions_data["total"]
            assert status_data["current_space_id"] in ["test-space", "another-space", "third-space"]
            
            # Verify statistics calculations
            total_confidence = sum(d["confidence"] for d in decisions_data["decisions"])
            expected_avg = total_confidence / len(decisions_data["decisions"])
            assert abs(stats_data["average_confidence"] - expected_avg) < 0.01


class TestAgentDashboardPolling:
    """Test scenarios related to dashboard polling behavior."""

    @pytest.mark.asyncio
    async def test_polling_simulation(self, setup_test_checkpoints, monkeypatch):
        """Simulate frontend polling behavior and verify responses."""
        monkeypatch.setenv("STORE_PATH", str(setup_test_checkpoints))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Simulate 3 polling cycles
            for i in range(3):
                # Poll status
                response = await client.get("/agent-run/status")
                assert response.status_code == 200
                
                # Small delay to simulate 30-second polling interval
                await asyncio.sleep(0.1)
            
            # All polls should succeed without issues
            assert True  # If we get here, polling worked

    @pytest.mark.asyncio
    async def test_data_updates_between_polls(self, mock_state_dir, sample_checkpoint_data, monkeypatch):
        """Test that dashboard reflects updates between polling cycles."""
        monkeypatch.setenv("STORE_PATH", str(mock_state_dir))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Initial poll - no data
            response = await client.get("/agent-run/statistics")
            stats1 = response.json()
            assert stats1["total_runs"] == 0
            
            # Add a checkpoint between polls
            checkpoint_file = mock_state_dir / "agent_checkpoint_new-space.json"
            checkpoint_file.write_text(json.dumps(sample_checkpoint_data))
            
            # Second poll - should see new data
            response = await client.get("/agent-run/statistics")
            stats2 = response.json()
            assert stats2["total_runs"] == 1
            assert stats2["total_votes_cast"] == 2


class TestAgentDashboardUserFlow:
    """Test complete user workflows through the dashboard."""

    @pytest.mark.asyncio
    async def test_user_monitors_agent_activity(self, setup_test_checkpoints, monkeypatch):
        """Simulate a user monitoring agent activity through the dashboard."""
        monkeypatch.setenv("STORE_PATH", str(setup_test_checkpoints))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # User loads dashboard - all components fetch initial data
            initial_requests = await asyncio.gather(
                client.get("/agent-run/status"),
                client.get("/agent-run/decisions?limit=5"),
                client.get("/agent-run/statistics")
            )
            
            # Verify all initial requests succeed
            for response in initial_requests:
                assert response.status_code == 200
            
            # User sees agent is idle and triggers a run
            status = initial_requests[0].json()
            assert status["is_active"] is False
            
            # Mock agent run
            with patch("backend.services.agent_run_service.AgentRunService.run_agent", 
                      AsyncMock(return_value={"status": "completed"})):
                run_response = await client.post(
                    "/agent-run",
                    json={"space_id": status["current_space_id"] or "test-space", "dry_run": False}
                )
                assert run_response.status_code == 200
            
            # User refreshes to see updated status
            refresh_requests = await asyncio.gather(
                client.get("/agent-run/status"),
                client.get("/agent-run/decisions?limit=5"),
                client.get("/agent-run/statistics")
            )
            
            # All refresh requests should succeed
            for response in refresh_requests:
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_reviews_voting_history(self, setup_test_checkpoints, monkeypatch):
        """Test a user reviewing the agent's voting history."""
        monkeypatch.setenv("STORE_PATH", str(setup_test_checkpoints))
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # User wants to see all decisions
            all_decisions = await client.get("/agent-run/decisions?limit=100")
            assert all_decisions.status_code == 200
            
            decisions_data = all_decisions.json()
            assert len(decisions_data["decisions"]) == 6
            
            # User filters to see only high-confidence decisions
            high_confidence = [d for d in decisions_data["decisions"] if d["confidence"] >= 0.9]
            assert len(high_confidence) == 3  # All FOR votes have 0.95 confidence
            
            # Verify decision details
            for decision in high_confidence:
                assert decision["vote"] == "FOR"
                assert decision["confidence"] == 0.95
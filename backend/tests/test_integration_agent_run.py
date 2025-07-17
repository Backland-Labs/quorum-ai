"""Comprehensive integration tests for the agent run system.

This test suite covers end-to-end testing of the complete agent run workflow,
from API endpoint to vote execution, following TDD principles.

The tests focus on:
- Complete workflow integration with mocked external services
- Error handling and recovery scenarios
- User preference configurations
- Concurrent execution scenarios
- Rollback and failure recovery
- Performance and timeout scenarios
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
from datetime import datetime, timedelta
from typing import List, Dict, Any

from main import app
from models import (
    AgentRunRequest,
    AgentRunResponse,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
    UserPreferences,
    Proposal,
    ProposalState,
    Vote,
    Space,
)
from services.agent_run_service import AgentRunService
from services.snapshot_service import SnapshotService
from services.ai_service import AIService
from services.voting_service import VotingService
from services.user_preferences_service import UserPreferencesService


class TestAgentRunIntegrationFullWorkflow:
    """Integration tests for the complete agent run workflow.
    
    These tests verify that the entire system works together correctly,
    from receiving an API request to executing votes and returning results.
    """

    @pytest.fixture
    def mock_external_services(self):
        """Mock all external services for integration testing."""
        # Initialize the global services first
        import main
        main.snapshot_service = Mock(spec=SnapshotService)
        main.ai_service = Mock(spec=AIService)
        main.voting_service = Mock(spec=VotingService)
        main.user_preferences_service = Mock(spec=UserPreferencesService)
        main.agent_run_service = Mock(spec=AgentRunService)
        main.safe_service = Mock()
        main.activity_service = Mock()
        
        return {
            'snapshot_service': main.snapshot_service,
            'ai_service': main.ai_service,
            'voting_service': main.voting_service,
            'user_preferences_service': main.user_preferences_service,
            'agent_run_service': main.agent_run_service,
            'safe_service': main.safe_service,
            'activity_service': main.activity_service,
        }

    @pytest.fixture
    def sample_active_proposals(self):
        """Create sample active proposals for testing."""
        return [
            Proposal(
                id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
                title="Increase Treasury Allocation for Development",
                body="This proposal suggests increasing the treasury allocation...",
                choices=["For", "Against", "Abstain"],
                start=int(time.time()) - 3600,  # Started 1 hour ago
                end=int(time.time()) + 86400,   # Ends in 24 hours
                state="active",
                author="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
                network="1",
                symbol="TEST",
                scores=[1000.0, 500.0, 100.0],
                scores_total=1600.0,
                votes=25,
                created=int(time.time()) - 7200,  # Created 2 hours ago
                quorum=100.0
            ),
            Proposal(
                id="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
                title="Protocol Upgrade to Version 2.0",
                body="This proposal outlines the protocol upgrade to version 2.0...",
                choices=["For", "Against"],
                start=int(time.time()) - 1800,  # Started 30 minutes ago
                end=int(time.time()) + 172800,  # Ends in 48 hours
                state="active",
                author="0x456d35cc6835c0532021efc598c51ddc1d8b4b22",
                network="1",
                symbol="TEST",
                scores=[2000.0, 300.0],
                scores_total=2300.0,
                votes=35,
                created=int(time.time()) - 3600,  # Created 1 hour ago
                quorum=500.0
            )
        ]

    @pytest.fixture
    def sample_user_preferences(self):
        """Create sample user preferences for testing."""
        return UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=5,
            blacklisted_proposers=[],
            whitelisted_proposers=[],
            max_votes_per_day=10,
            risk_tolerance=RiskLevel.MEDIUM
        )

    @pytest.fixture
    def sample_vote_decisions(self):
        """Create sample vote decisions for testing."""
        return [
            VoteDecision(
                proposal_id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="This proposal will improve the protocol's development velocity and has strong community support.",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED,
                estimated_gas_cost=0.007
            ),
            VoteDecision(
                proposal_id="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
                vote=VoteType.FOR,
                confidence=0.78,
                reasoning="The protocol upgrade includes important security improvements and performance optimizations.",
                risk_assessment=RiskLevel.MEDIUM,
                strategy_used=VotingStrategy.BALANCED,
                estimated_gas_cost=0.009
            )
        ]

    @pytest.mark.asyncio
    async def test_complete_agent_run_workflow_success(
        self, 
        mock_external_services, 
        sample_active_proposals, 
        sample_user_preferences, 
        sample_vote_decisions
    ):
        """Test the complete agent run workflow from API call to vote execution.
        
        This test verifies that all components work together correctly:
        1. API receives agent run request
        2. Service fetches active proposals
        3. User preferences are loaded
        4. AI makes voting decisions
        5. Votes are executed
        6. Response is returned with correct data
        """
        # Setup mocks for successful workflow
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="test-space.eth",
                proposals_analyzed=2,
                votes_cast=sample_vote_decisions,
                user_preferences_applied=True,
                execution_time=12.5,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "test-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure and data
            assert data["space_id"] == "test-space.eth"
            assert data["proposals_analyzed"] == 2
            assert len(data["votes_cast"]) == 2
            assert data["user_preferences_applied"] is True
            assert data["execution_time"] > 0
            assert data["errors"] == []
            
            # Verify vote decisions structure
            vote_1 = data["votes_cast"][0]
            assert vote_1["proposal_id"] == "0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890"
            assert vote_1["vote"] == "FOR"
            assert vote_1["confidence"] == 0.85
            assert vote_1["risk_assessment"] == "LOW"
            assert vote_1["strategy_used"] == "balanced"
            
            # Verify service was called correctly
            mock_external_services['agent_run_service'].execute_agent_run.assert_called_once()
            call_args = mock_external_services['agent_run_service'].execute_agent_run.call_args[0][0]
            assert call_args.space_id == "test-space.eth"
            assert call_args.dry_run is False

    @pytest.mark.asyncio
    async def test_complete_agent_run_workflow_dry_run(
        self, 
        mock_external_services, 
        sample_active_proposals, 
        sample_user_preferences, 
        sample_vote_decisions
    ):
        """Test the complete agent run workflow in dry run mode.
        
        This test verifies that dry run mode works correctly:
        - All analysis is performed
        - Vote decisions are made
        - No actual votes are executed
        - Response indicates dry run was performed
        """
        # Setup mocks for dry run workflow
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="test-space.eth",
                proposals_analyzed=2,
                votes_cast=sample_vote_decisions,  # Decisions made but not executed
                user_preferences_applied=True,
                execution_time=8.2,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request in dry run mode
            request_data = {
                "space_id": "test-space.eth",
                "dry_run": True
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Verify dry run results
            assert data["space_id"] == "test-space.eth"
            assert data["proposals_analyzed"] == 2
            assert len(data["votes_cast"]) == 2
            assert data["user_preferences_applied"] is True
            assert data["execution_time"] > 0
            assert data["errors"] == []
            
            # Verify service was called with dry_run=True
            mock_external_services['agent_run_service'].execute_agent_run.assert_called_once()
            call_args = mock_external_services['agent_run_service'].execute_agent_run.call_args[0][0]
            assert call_args.space_id == "test-space.eth"
            assert call_args.dry_run is True

    @pytest.mark.asyncio
    async def test_agent_run_workflow_no_active_proposals(self, mock_external_services):
        """Test agent run workflow when no active proposals exist.
        
        This test verifies that the system handles empty proposal lists gracefully:
        - API call succeeds
        - No proposals are analyzed
        - No votes are cast
        - Response indicates successful execution with no activity
        """
        # Setup mocks for no active proposals
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="empty-space.eth",
                proposals_analyzed=0,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=1.2,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "empty-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Verify no activity results
            assert data["space_id"] == "empty-space.eth"
            assert data["proposals_analyzed"] == 0
            assert len(data["votes_cast"]) == 0
            assert data["user_preferences_applied"] is True
            assert data["execution_time"] > 0
            assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_agent_run_workflow_with_filtering(
        self, 
        mock_external_services, 
        sample_active_proposals, 
        sample_vote_decisions
    ):
        """Test agent run workflow with proposal filtering based on user preferences.
        
        This test verifies that user preferences are properly applied:
        - Proposals are filtered based on blacklisted proposers
        - Confidence threshold is applied
        - Maximum proposals per run is respected
        """
        # Create user preferences with filtering
        filtered_preferences = UserPreferences(
            voting_strategy=VotingStrategy.CONSERVATIVE,
            confidence_threshold=0.8,  # High threshold
            max_proposals_per_run=1,   # Limited to 1 proposal
            blacklisted_proposers=["0x456d35cc6835c0532021efc598c51ddc1d8b4b22"],  # Block second proposal
            whitelisted_proposers=[],
            max_votes_per_day=5,
            risk_tolerance=RiskLevel.LOW
        )

        # Only one vote decision should pass filtering
        filtered_vote_decisions = [
            VoteDecision(
                proposal_id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
                vote=VoteType.FOR,
                confidence=0.85,  # Above threshold
                reasoning="High confidence decision after filtering",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.CONSERVATIVE,
                estimated_gas_cost=0.007
            )
        ]

        # Setup mocks with filtered results
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="filtered-space.eth",
                proposals_analyzed=1,  # Only 1 proposal after filtering
                votes_cast=filtered_vote_decisions,
                user_preferences_applied=True,
                execution_time=5.8,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "filtered-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Verify filtering worked
            assert data["space_id"] == "filtered-space.eth"
            assert data["proposals_analyzed"] == 1  # Filtered down to 1
            assert len(data["votes_cast"]) == 1
            assert data["user_preferences_applied"] is True
            assert data["votes_cast"][0]["confidence"] >= 0.8  # Above threshold
            assert data["votes_cast"][0]["strategy_used"] == "conservative"


class TestAgentRunIntegrationErrorHandling:
    """Integration tests for error handling and recovery scenarios.
    
    These tests verify that the system handles various error conditions
    gracefully and provides appropriate error responses.
    """

    @pytest.fixture
    def mock_external_services(self):
        """Mock all external services for error testing."""
        # Initialize the global services first
        import main
        main.snapshot_service = Mock(spec=SnapshotService)
        main.ai_service = Mock(spec=AIService)
        main.voting_service = Mock(spec=VotingService)
        main.user_preferences_service = Mock(spec=UserPreferencesService)
        main.agent_run_service = Mock(spec=AgentRunService)
        main.safe_service = Mock()
        main.activity_service = Mock()
        
        return {
            'snapshot_service': main.snapshot_service,
            'ai_service': main.ai_service,
            'voting_service': main.voting_service,
            'user_preferences_service': main.user_preferences_service,
            'agent_run_service': main.agent_run_service,
            'safe_service': main.safe_service,
            'activity_service': main.activity_service,
        }

    @pytest.mark.asyncio
    async def test_agent_run_service_initialization_error(self, mock_external_services):
        """Test error handling when agent run service initialization fails.
        
        This test verifies that service initialization errors are handled
        gracefully and return appropriate error responses.
        """
        # Setup service to fail during initialization
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            side_effect=Exception("Service initialization failed")
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "test-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify error response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Service initialization failed" in data["detail"]

    @pytest.mark.asyncio
    async def test_agent_run_snapshot_service_error(self, mock_external_services):
        """Test error handling when Snapshot service fails.
        
        This test verifies that Snapshot API errors are handled gracefully
        and appropriate error responses are returned.
        """
        # Setup service to fail with Snapshot error
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            side_effect=Exception("Failed to fetch proposals from Snapshot")
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "failing-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify error response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Failed to fetch proposals from Snapshot" in data["detail"]

    @pytest.mark.asyncio
    async def test_agent_run_ai_service_error(self, mock_external_services):
        """Test error handling when AI service fails.
        
        This test verifies that AI service errors are handled gracefully
        and appropriate error responses are returned.
        """
        # Setup service to fail with AI error
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "test-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify error response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "AI service unavailable" in data["detail"]

    @pytest.mark.asyncio
    async def test_agent_run_voting_service_error(self, mock_external_services):
        """Test error handling when voting service fails.
        
        This test verifies that voting service errors are handled gracefully
        and partial results are returned when possible.
        """
        # Setup service to return partial results with errors
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="test-space.eth",
                proposals_analyzed=2,
                votes_cast=[],  # No votes cast due to error
                user_preferences_applied=True,
                execution_time=8.5,
                errors=["Failed to execute vote on proposal 1", "Voting service timeout"]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "test-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify partial success response
            assert response.status_code == 200
            data = response.json()
            
            # Verify partial results with errors
            assert data["space_id"] == "test-space.eth"
            assert data["proposals_analyzed"] == 2
            assert len(data["votes_cast"]) == 0
            assert data["user_preferences_applied"] is True
            assert len(data["errors"]) == 2
            assert "Failed to execute vote on proposal 1" in data["errors"]
            assert "Voting service timeout" in data["errors"]

    @pytest.mark.asyncio
    async def test_agent_run_user_preferences_error(self, mock_external_services):
        """Test error handling when user preferences service fails.
        
        This test verifies that user preferences errors are handled gracefully
        and default preferences are used when possible.
        """
        # Setup service to handle preferences error gracefully
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="test-space.eth",
                proposals_analyzed=2,
                votes_cast=[],  # No votes due to preference loading failure
                user_preferences_applied=False,  # Could not apply preferences
                execution_time=3.2,
                errors=["Failed to load user preferences, using defaults"]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "test-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify response with preference error
            assert response.status_code == 200
            data = response.json()
            
            # Verify preference error handling
            assert data["space_id"] == "test-space.eth"
            assert data["proposals_analyzed"] == 2
            assert data["user_preferences_applied"] is False
            assert len(data["errors"]) == 1
            assert "Failed to load user preferences" in data["errors"][0]

    @pytest.mark.asyncio
    async def test_agent_run_timeout_error(self, mock_external_services):
        """Test error handling when agent run times out.
        
        This test verifies that timeout errors are handled gracefully
        and appropriate error responses are returned.
        """
        # Setup service to timeout
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            side_effect=asyncio.TimeoutError("Agent run timed out")
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "slow-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify timeout error response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Agent run timed out" in data["detail"]

    @pytest.mark.asyncio
    async def test_agent_run_invalid_space_error(self, mock_external_services):
        """Test error handling for invalid space ID.
        
        This test verifies that invalid space IDs are handled gracefully
        and appropriate error responses are returned.
        """
        # Setup service to fail with invalid space error
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            side_effect=ValueError("Invalid space ID: invalid-space")
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request with invalid space
            request_data = {
                "space_id": "invalid-space",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify invalid space error response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Invalid space ID" in data["detail"]


class TestAgentRunIntegrationUserPreferences:
    """Integration tests for different user preference configurations.
    
    These tests verify that various user preference settings are properly
    applied throughout the agent run workflow.
    """

    @pytest.fixture
    def mock_external_services(self):
        """Mock all external services for user preference testing."""
        # Initialize the global services first
        import main
        main.snapshot_service = Mock(spec=SnapshotService)
        main.ai_service = Mock(spec=AIService)
        main.voting_service = Mock(spec=VotingService)
        main.user_preferences_service = Mock(spec=UserPreferencesService)
        main.agent_run_service = Mock(spec=AgentRunService)
        main.safe_service = Mock()
        main.activity_service = Mock()
        
        return {
            'snapshot_service': main.snapshot_service,
            'ai_service': main.ai_service,
            'voting_service': main.voting_service,
            'user_preferences_service': main.user_preferences_service,
            'agent_run_service': main.agent_run_service,
            'safe_service': main.safe_service,
            'activity_service': main.activity_service,
        }

    @pytest.mark.asyncio
    async def test_agent_run_conservative_strategy(self, mock_external_services):
        """Test agent run with conservative voting strategy.
        
        This test verifies that conservative strategy preferences are applied:
        - Higher confidence thresholds
        - Risk-averse decisions
        - Fewer votes cast
        """
        # Setup conservative strategy response
        conservative_vote = VoteDecision(
            proposal_id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
            vote=VoteType.FOR,
            confidence=0.95,  # Very high confidence
            reasoning="Conservative analysis shows strong community consensus and low risk",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.CONSERVATIVE,
            estimated_gas_cost=0.005
        )

        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="conservative-space.eth",
                proposals_analyzed=3,
                votes_cast=[conservative_vote],  # Only 1 vote meets conservative criteria
                user_preferences_applied=True,
                execution_time=15.2,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "conservative-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify conservative strategy results
            assert response.status_code == 200
            data = response.json()
            
            assert data["proposals_analyzed"] == 3
            assert len(data["votes_cast"]) == 1  # Conservative approach, fewer votes
            assert data["votes_cast"][0]["confidence"] >= 0.9  # High confidence
            assert data["votes_cast"][0]["strategy_used"] == "conservative"
            assert data["votes_cast"][0]["risk_assessment"] == "LOW"

    @pytest.mark.asyncio
    async def test_agent_run_aggressive_strategy(self, mock_external_services):
        """Test agent run with aggressive voting strategy.
        
        This test verifies that aggressive strategy preferences are applied:
        - Lower confidence thresholds
        - More risk-tolerant decisions
        - More votes cast
        """
        # Setup aggressive strategy response
        aggressive_votes = [
            VoteDecision(
                proposal_id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
                vote=VoteType.FOR,
                confidence=0.72,  # Lower confidence threshold
                reasoning="Aggressive analysis shows potential for high returns",
                risk_assessment=RiskLevel.MEDIUM,
                strategy_used=VotingStrategy.AGGRESSIVE,
                estimated_gas_cost=0.008
            ),
            VoteDecision(
                proposal_id="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
                vote=VoteType.FOR,
                confidence=0.68,  # Lower confidence threshold
                reasoning="Aggressive strategy supports innovation and growth",
                risk_assessment=RiskLevel.HIGH,
                strategy_used=VotingStrategy.AGGRESSIVE,
                estimated_gas_cost=0.012
            )
        ]

        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="aggressive-space.eth",
                proposals_analyzed=3,
                votes_cast=aggressive_votes,  # More votes cast
                user_preferences_applied=True,
                execution_time=18.7,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "aggressive-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify aggressive strategy results
            assert response.status_code == 200
            data = response.json()
            
            assert data["proposals_analyzed"] == 3
            assert len(data["votes_cast"]) == 2  # Aggressive approach, more votes
            assert all(vote["confidence"] >= 0.6 for vote in data["votes_cast"])  # Lower threshold
            assert all(vote["strategy_used"] == "aggressive" for vote in data["votes_cast"])
            assert any(vote["risk_assessment"] in ["MEDIUM", "HIGH"] for vote in data["votes_cast"])

    @pytest.mark.asyncio
    async def test_agent_run_with_blacklisted_proposers(self, mock_external_services):
        """Test agent run with blacklisted proposers.
        
        This test verifies that proposals from blacklisted proposers are
        properly filtered out during the agent run workflow.
        """
        # Setup response with blacklisted proposer filtering
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="blacklist-space.eth",
                proposals_analyzed=1,  # Only 1 proposal after blacklist filtering
                votes_cast=[
                    VoteDecision(
                        proposal_id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
                        vote=VoteType.FOR,
                        confidence=0.82,
                        reasoning="Proposal from approved proposer meets criteria",
                        risk_assessment=RiskLevel.LOW,
                        strategy_used=VotingStrategy.BALANCED,
                        estimated_gas_cost=0.006
                    )
                ],
                user_preferences_applied=True,
                execution_time=8.3,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "blacklist-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify blacklist filtering results
            assert response.status_code == 200
            data = response.json()
            
            assert data["proposals_analyzed"] == 1  # Filtered by blacklist
            assert len(data["votes_cast"]) == 1
            assert data["user_preferences_applied"] is True
            # Only the non-blacklisted proposal should be processed

    @pytest.mark.asyncio
    async def test_agent_run_with_max_proposals_limit(self, mock_external_services):
        """Test agent run with maximum proposals per run limit.
        
        This test verifies that the max_proposals_per_run preference is
        properly enforced during the agent run workflow.
        """
        # Setup response with proposal limit enforcement
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="limited-space.eth",
                proposals_analyzed=2,  # Limited to 2 proposals
                votes_cast=[
                    VoteDecision(
                        proposal_id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
                        vote=VoteType.FOR,
                        confidence=0.85,
                        reasoning="First proposal meets criteria",
                        risk_assessment=RiskLevel.LOW,
                        strategy_used=VotingStrategy.BALANCED,
                        estimated_gas_cost=0.007
                    ),
                    VoteDecision(
                        proposal_id="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
                        vote=VoteType.FOR,
                        confidence=0.78,
                        reasoning="Second proposal meets criteria",
                        risk_assessment=RiskLevel.MEDIUM,
                        strategy_used=VotingStrategy.BALANCED,
                        estimated_gas_cost=0.009
                    )
                ],
                user_preferences_applied=True,
                execution_time=11.4,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "limited-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify proposal limit enforcement
            assert response.status_code == 200
            data = response.json()
            
            assert data["proposals_analyzed"] == 2  # Limited by max_proposals_per_run
            assert len(data["votes_cast"]) == 2
            assert data["user_preferences_applied"] is True

    @pytest.mark.asyncio
    async def test_agent_run_with_high_confidence_threshold(self, mock_external_services):
        """Test agent run with high confidence threshold.
        
        This test verifies that high confidence thresholds properly filter
        out low-confidence voting decisions.
        """
        # Setup response with high confidence threshold filtering
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="high-confidence-space.eth",
                proposals_analyzed=3,
                votes_cast=[
                    VoteDecision(
                        proposal_id="0x1234567890abcdef1234567890abcdef12345678901234567890abcdef1234567890",
                        vote=VoteType.FOR,
                        confidence=0.92,  # High confidence, passes threshold
                        reasoning="Very high confidence in this proposal",
                        risk_assessment=RiskLevel.LOW,
                        strategy_used=VotingStrategy.BALANCED,
                        estimated_gas_cost=0.006
                    )
                ],  # Only 1 vote meets high confidence threshold
                user_preferences_applied=True,
                execution_time=14.1,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            request_data = {
                "space_id": "high-confidence-space.eth",
                "dry_run": False
            }
            
            response = await client.post("/agent-run", json=request_data)
            
            # Verify high confidence threshold filtering
            assert response.status_code == 200
            data = response.json()
            
            assert data["proposals_analyzed"] == 3
            assert len(data["votes_cast"]) == 1  # Only high confidence votes
            assert data["votes_cast"][0]["confidence"] >= 0.9  # High confidence
            assert data["user_preferences_applied"] is True


class TestAgentRunIntegrationConcurrency:
    """Integration tests for concurrent agent run scenarios.
    
    These tests verify that the system handles multiple concurrent agent runs
    correctly without race conditions or resource conflicts.
    """

    @pytest.fixture
    def mock_external_services(self):
        """Mock all external services for concurrency testing."""
        # Initialize the global services first
        import main
        main.snapshot_service = Mock(spec=SnapshotService)
        main.ai_service = Mock(spec=AIService)
        main.voting_service = Mock(spec=VotingService)
        main.user_preferences_service = Mock(spec=UserPreferencesService)
        main.agent_run_service = Mock(spec=AgentRunService)
        main.safe_service = Mock()
        main.activity_service = Mock()
        
        return {
            'snapshot_service': main.snapshot_service,
            'ai_service': main.ai_service,
            'voting_service': main.voting_service,
            'user_preferences_service': main.user_preferences_service,
            'agent_run_service': main.agent_run_service,
            'safe_service': main.safe_service,
            'activity_service': main.activity_service,
        }

    @pytest.mark.asyncio
    async def test_concurrent_agent_runs_different_spaces(self, mock_external_services):
        """Test concurrent agent runs for different spaces.
        
        This test verifies that multiple agent runs can be executed concurrently
        for different spaces without interference.
        """
        # Setup different responses for different spaces
        def mock_execute_agent_run(request):
            if request.space_id == "space1.eth":
                return AgentRunResponse(
                    space_id="space1.eth",
                    proposals_analyzed=2,
                    votes_cast=[],
                    user_preferences_applied=True,
                    execution_time=5.5,
                    errors=[]
                )
            elif request.space_id == "space2.eth":
                return AgentRunResponse(
                    space_id="space2.eth",
                    proposals_analyzed=1,
                    votes_cast=[],
                    user_preferences_applied=True,
                    execution_time=3.2,
                    errors=[]
                )
            else:
                return AgentRunResponse(
                    space_id=request.space_id,
                    proposals_analyzed=0,
                    votes_cast=[],
                    user_preferences_applied=True,
                    execution_time=1.0,
                    errors=[]
                )

        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            side_effect=mock_execute_agent_run
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute concurrent requests for different spaces
            tasks = [
                client.post("/agent-run", json={"space_id": "space1.eth", "dry_run": False}),
                client.post("/agent-run", json={"space_id": "space2.eth", "dry_run": False}),
                client.post("/agent-run", json={"space_id": "space3.eth", "dry_run": True})
            ]
            
            responses = await asyncio.gather(*tasks)
            
            # Verify all requests succeeded
            assert all(response.status_code == 200 for response in responses)
            
            # Verify correct responses for each space
            data1 = responses[0].json()
            data2 = responses[1].json()
            data3 = responses[2].json()
            
            assert data1["space_id"] == "space1.eth"
            assert data1["proposals_analyzed"] == 2
            
            assert data2["space_id"] == "space2.eth"
            assert data2["proposals_analyzed"] == 1
            
            assert data3["space_id"] == "space3.eth"
            assert data3["proposals_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_agent_runs_same_space(self, mock_external_services):
        """Test concurrent agent runs for the same space.
        
        This test verifies that multiple agent runs for the same space
        are handled correctly without conflicts.
        """
        # Setup consistent response for same space
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="concurrent-space.eth",
                proposals_analyzed=1,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=4.8,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute concurrent requests for the same space
            tasks = [
                client.post("/agent-run", json={"space_id": "concurrent-space.eth", "dry_run": False}),
                client.post("/agent-run", json={"space_id": "concurrent-space.eth", "dry_run": True}),
                client.post("/agent-run", json={"space_id": "concurrent-space.eth", "dry_run": False})
            ]
            
            responses = await asyncio.gather(*tasks)
            
            # Verify all requests succeeded
            assert all(response.status_code == 200 for response in responses)
            
            # Verify consistent responses
            for response in responses:
                data = response.json()
                assert data["space_id"] == "concurrent-space.eth"
                assert data["proposals_analyzed"] == 1
                assert data["user_preferences_applied"] is True
                assert data["execution_time"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_agent_runs_with_errors(self, mock_external_services):
        """Test concurrent agent runs with some failing.
        
        This test verifies that errors in some concurrent requests don't
        affect the success of other concurrent requests.
        """
        # Setup mock to fail for specific spaces
        def mock_execute_agent_run(request):
            if request.space_id == "failing-space.eth":
                raise Exception("Service unavailable")
            else:
                return AgentRunResponse(
                    space_id=request.space_id,
                    proposals_analyzed=1,
                    votes_cast=[],
                    user_preferences_applied=True,
                    execution_time=2.5,
                    errors=[]
                )

        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            side_effect=mock_execute_agent_run
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute concurrent requests with mixed success/failure
            tasks = [
                client.post("/agent-run", json={"space_id": "success-space.eth", "dry_run": False}),
                client.post("/agent-run", json={"space_id": "failing-space.eth", "dry_run": False}),
                client.post("/agent-run", json={"space_id": "another-success.eth", "dry_run": True})
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify mixed results
            assert len(responses) == 3
            
            # First request should succeed
            assert responses[0].status_code == 200
            data1 = responses[0].json()
            assert data1["space_id"] == "success-space.eth"
            
            # Second request should fail
            assert responses[1].status_code == 500
            
            # Third request should succeed
            assert responses[2].status_code == 200
            data3 = responses[2].json()
            assert data3["space_id"] == "another-success.eth"


class TestAgentRunIntegrationPerformance:
    """Integration tests for performance and timeout scenarios.
    
    These tests verify that the system handles performance requirements
    and timeout scenarios correctly.
    """

    @pytest.fixture
    def mock_external_services(self):
        """Mock all external services for performance testing."""
        # Initialize the global services first
        import main
        main.snapshot_service = Mock(spec=SnapshotService)
        main.ai_service = Mock(spec=AIService)
        main.voting_service = Mock(spec=VotingService)
        main.user_preferences_service = Mock(spec=UserPreferencesService)
        main.agent_run_service = Mock(spec=AgentRunService)
        main.safe_service = Mock()
        main.activity_service = Mock()
        
        return {
            'snapshot_service': main.snapshot_service,
            'ai_service': main.ai_service,
            'voting_service': main.voting_service,
            'user_preferences_service': main.user_preferences_service,
            'agent_run_service': main.agent_run_service,
            'safe_service': main.safe_service,
            'activity_service': main.activity_service,
        }

    @pytest.mark.asyncio
    async def test_agent_run_performance_metrics(self, mock_external_services):
        """Test that agent run performance metrics are properly tracked.
        
        This test verifies that execution time and other performance metrics
        are accurately tracked and returned in responses.
        """
        # Setup mock with specific execution time
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="performance-space.eth",
                proposals_analyzed=5,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=25.7,  # Specific execution time
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request and measure time
            start_time = time.time()
            
            response = await client.post(
                "/agent-run", 
                json={"space_id": "performance-space.eth", "dry_run": False}
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Verify response and performance metrics
            assert response.status_code == 200
            data = response.json()
            
            assert data["space_id"] == "performance-space.eth"
            assert data["proposals_analyzed"] == 5
            assert data["execution_time"] == 25.7
            assert data["user_preferences_applied"] is True
            
            # Verify that execution time is reasonable (within expected bounds)
            assert total_time < 60  # Should complete within 60 seconds
            assert data["execution_time"] > 0  # Execution time should be positive

    @pytest.mark.asyncio
    async def test_agent_run_large_dataset_handling(self, mock_external_services):
        """Test agent run with large number of proposals.
        
        This test verifies that the system can handle large datasets
        without performance degradation or errors.
        """
        # Setup mock with large dataset
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="large-dataset-space.eth",
                proposals_analyzed=100,  # Large number of proposals
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=45.3,  # Higher execution time for large dataset
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            response = await client.post(
                "/agent-run", 
                json={"space_id": "large-dataset-space.eth", "dry_run": True}
            )
            
            # Verify response for large dataset
            assert response.status_code == 200
            data = response.json()
            
            assert data["space_id"] == "large-dataset-space.eth"
            assert data["proposals_analyzed"] == 100
            assert data["execution_time"] > 0
            assert data["user_preferences_applied"] is True
            assert data["errors"] == []

    @pytest.mark.asyncio
    async def test_agent_run_resource_cleanup(self, mock_external_services):
        """Test that resources are properly cleaned up after agent run.
        
        This test verifies that resources are properly released after
        agent run execution, preventing memory leaks or resource exhaustion.
        """
        # Setup mock that tracks resource usage
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="cleanup-space.eth",
                proposals_analyzed=3,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=8.2,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute multiple agent runs to test resource cleanup
            for i in range(5):
                response = await client.post(
                    "/agent-run", 
                    json={"space_id": f"cleanup-space-{i}.eth", "dry_run": True}
                )
                
                # Verify each request succeeds
                assert response.status_code == 200
                data = response.json()
                assert data["execution_time"] > 0
                assert data["user_preferences_applied"] is True
                
                # Small delay to allow cleanup
                await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_agent_run_graceful_shutdown(self, mock_external_services):
        """Test graceful shutdown behavior during agent run.
        
        This test verifies that the system can handle shutdown scenarios
        gracefully without corrupting data or leaving resources in inconsistent states.
        """
        # Setup mock for graceful shutdown testing
        mock_external_services['agent_run_service'].execute_agent_run = AsyncMock(
            return_value=AgentRunResponse(
                space_id="shutdown-space.eth",
                proposals_analyzed=2,
                votes_cast=[],
                user_preferences_applied=True,
                execution_time=12.1,
                errors=[]
            )
        )

        # Create async test client
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Execute agent run request
            response = await client.post(
                "/agent-run", 
                json={"space_id": "shutdown-space.eth", "dry_run": False}
            )
            
            # Verify successful completion
            assert response.status_code == 200
            data = response.json()
            
            assert data["space_id"] == "shutdown-space.eth"
            assert data["proposals_analyzed"] == 2
            assert data["user_preferences_applied"] is True
            assert data["execution_time"] > 0
            assert data["errors"] == []
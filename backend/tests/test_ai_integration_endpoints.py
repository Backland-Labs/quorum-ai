"""
Integration tests for AI service endpoints to verify Phase 4 agent separation works end-to-end.

These tests verify that the API endpoints work correctly with the separated agents.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from models import (
    Proposal, 
    ProposalSummary, 
    VoteDecision, 
    VoteType, 
    VotingStrategy,
    RiskLevel,
    AiVoteResponse,
    SummarizeRequest,
    AgentRunRequest
)


class TestSummarizationEndpointIntegration:
    """Test /proposals/summarize endpoint with separated agents."""

    def test_summarization_endpoint_returns_proposal_summary_structure(self):
        """Test that the summarization endpoint returns correct ProposalSummary structure."""
        # Import here to avoid circular imports
        from main import app
        
        with TestClient(app) as client:
            # Mock the AI service methods
            mock_proposals = [
                Proposal(
                    id="test-proposal-1",
                    title="Test Proposal 1",
                    body="This is test proposal 1",
                    state="active",
                    author="0x1234567890123456789012345678901234567890",
                    created=1640000000,
                    start=1640000000,
                    end=1640010000,
                    votes=100,
                    scores_total=100.0,
                    choices=["For", "Against"],
                    scores=[60.0, 40.0],
                    snapshot=None,
                    discussion=None,
                    ipfs=None,
                    space_id="test-space",
                    is_active=True,
                    time_remaining=None,
                    vote_choices=[]
                )
            ]
            
            mock_summaries = [
                ProposalSummary(
                    proposal_id="test-proposal-1",
                    title="Test Proposal 1",
                    summary="This is a comprehensive test summary.",
                    key_points=["Key point 1", "Key point 2"],
                    risk_assessment=RiskLevel.MEDIUM,
                    recommendation="Consider voting FOR",
                    confidence=0.90
                )
            ]

            # Set API key first
            client.post("/config/openrouter-key", json={"api_key": "test-api-key"})
            
            with patch('services.snapshot_service.SnapshotService.get_proposals') as mock_get_proposals:
                with patch('services.ai_service.AIService.summarize_multiple_proposals') as mock_summarize:
                    mock_get_proposals.return_value = mock_proposals
                    mock_summarize.return_value = mock_summaries
                    
                    # Test the endpoint
                    response = client.post("/proposals/summarize", json={
                        "proposal_ids": ["test-proposal-1"]
                    })
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    # Verify response structure
                    assert "summaries" in data
                    assert len(data["summaries"]) == 1
                    
                    summary = data["summaries"][0]
                    assert summary["proposal_id"] == "test-proposal-1"
                    assert summary["title"] == "Test Proposal 1"
                    assert "comprehensive test summary" in summary["summary"]
                    assert len(summary["key_points"]) == 2
                    assert summary["risk_assessment"] == "MEDIUM"
                    assert summary["confidence"] == 0.90


class TestAgentRunEndpointIntegration:
    """Test /agent-run endpoint with separated agents."""

    def test_agent_run_endpoint_continues_working_with_vote_decisions(self):
        """Test that the agent run endpoint continues to work with VoteDecision objects."""
        # Import here to avoid circular imports
        from main import app
        
        with TestClient(app) as client:
            mock_vote_decisions = [
                VoteDecision(
                    proposal_id="agent-test-1",
                    vote=VoteType.FOR,
                    confidence=0.85,
                    reasoning="Test voting reasoning",
                    risk_assessment=RiskLevel.MEDIUM,
                    strategy_used=VotingStrategy.BALANCED,
                    space_id="test-space",
                    attestation_status=None,
                    attestation_tx_hash=None,
                    attestation_uid=None,
                    attestation_error=None
                )
            ]

            # Set API key first
            client.post("/config/openrouter-key", json={"api_key": "test-api-key"})
            
            with patch('services.agent_run_service.AgentRunService.execute_agent_run') as mock_execute:
                mock_execute.return_value = {
                    "space_id": "test-space",
                    "proposals_analyzed": 1,
                    "votes_cast": mock_vote_decisions,
                    "user_preferences_applied": True,
                    "execution_time": 2.5,
                    "errors": []
                }
                
                # Test the endpoint
                response = client.post("/agent-run", json={
                    "space_id": "test-space",
                    "dry_run": True
                })
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert data["space_id"] == "test-space"
                assert data["proposals_analyzed"] == 1
                assert len(data["votes_cast"]) == 1
                
                vote = data["votes_cast"][0]
                assert vote["proposal_id"] == "agent-test-1"
                assert vote["vote"] == "FOR"
                assert vote["confidence"] == 0.85
                assert "Test voting reasoning" in vote["reasoning"]


class TestConcurrentEndpointOperations:
    """Test that both endpoints can be called simultaneously without conflicts."""

    def test_concurrent_endpoint_calls(self):
        """Test that summarization and agent run endpoints can be called concurrently."""
        # Import here to avoid circular imports
        from main import app
        import asyncio
        import httpx
        
        async def test_concurrent_operations():
            async with httpx.AsyncClient(base_url="http://test") as client:
                # Set API key first
                await client.post("/config/openrouter-key", json={"api_key": "test-api-key"})
                
                with patch('services.snapshot_service.SnapshotService.get_proposals') as mock_get_proposals:
                    with patch('services.ai_service.AIService.summarize_multiple_proposals') as mock_summarize:
                        with patch('services.agent_run_service.AgentRunService.execute_agent_run') as mock_execute:
                            
                            # Setup mocks
                            mock_proposals = [
                                Proposal(
                                    id="concurrent-test-1",
                                    title="Concurrent Test",
                                    body="Concurrent test proposal",
                                    state="active",
                                    author="0x1234567890123456789012345678901234567890",
                                    created=1640000000,
                                    start=1640000000,
                                    end=1640010000,
                                    votes=100,
                                    scores_total=100.0,
                                    choices=["For", "Against"],
                                    scores=[60.0, 40.0],
                                    snapshot=None,
                                    discussion=None,
                                    ipfs=None,
                                    space_id="test-space",
                                    is_active=True,
                                    time_remaining=None,
                                    vote_choices=[]
                                )
                            ]
                            
                            mock_summaries = [
                                ProposalSummary(
                                    proposal_id="concurrent-test-1",
                                    title="Concurrent Test",
                                    summary="Concurrent test summary.",
                                    key_points=["Concurrent point 1"],
                                    risk_assessment=RiskLevel.LOW,
                                    recommendation="Test concurrent recommendation",
                                    confidence=0.95
                                )
                            ]
                            
                            mock_vote_decisions = [
                                VoteDecision(
                                    proposal_id="concurrent-test-1",
                                    vote=VoteType.AGAINST,
                                    confidence=0.80,
                                    reasoning="Concurrent test voting",
                                    risk_assessment=RiskLevel.HIGH,
                                    strategy_used=VotingStrategy.CONSERVATIVE,
                                    space_id="test-space",
                                    attestation_status=None,
                                    attestation_tx_hash=None,
                                    attestation_uid=None,
                                    attestation_error=None
                                )
                            ]
                            
                            mock_get_proposals.return_value = mock_proposals
                            mock_summarize.return_value = mock_summaries
                            mock_execute.return_value = {
                                "space_id": "test-space",
                                "proposals_analyzed": 1,
                                "votes_cast": mock_vote_decisions,
                                "user_preferences_applied": True,
                                "execution_time": 1.5,
                                "errors": []
                            }
                            
                            # Make concurrent requests
                            summarize_task = client.post("/proposals/summarize", json={
                                "proposal_ids": ["concurrent-test-1"]
                            })
                            
                            agent_run_task = client.post("/agent-run", json={
                                "space_id": "test-space",
                                "dry_run": True
                            })
                            
                            # Wait for both to complete
                            summarize_response, agent_run_response = await asyncio.gather(
                                summarize_task, agent_run_task
                            )
                            
                            # Verify both responses are successful
                            assert summarize_response.status_code == 200
                            assert agent_run_response.status_code == 200
                            
                            # Verify response content
                            summarize_data = summarize_response.json()
                            agent_run_data = agent_run_response.json()
                            
                            assert len(summarize_data["summaries"]) == 1
                            assert summarize_data["summaries"][0]["proposal_id"] == "concurrent-test-1"
                            
                            assert agent_run_data["proposals_analyzed"] == 1
                            assert len(agent_run_data["votes_cast"]) == 1
                            assert agent_run_data["votes_cast"][0]["proposal_id"] == "concurrent-test-1"
        
        # Run the async test
        asyncio.run(test_concurrent_operations())
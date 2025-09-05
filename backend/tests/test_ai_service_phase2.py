"""Tests for Phase 2: AIService Agent Separation.

This module tests the critical functionality of AIService after separating
voting and summarization agents. These tests focus on the core business logic
that must work correctly.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pydantic_ai.models.openai import OpenAIModel

from services.ai_service import AIService, VotingAgent, SummarizationAgent, SummarizationDependencies
from models import Proposal, ProposalSummary, AiVoteResponse, VotingStrategy, RiskLevel


class TestAIServiceAgentSeparation:
    """Test AIService with separated voting and summarization agents."""

    @pytest.fixture
    def mock_openai_model(self):
        """Mock OpenAI model for testing."""
        mock_model = Mock(spec=OpenAIModel)
        return mock_model

    @pytest.fixture  
    def mock_proposal(self):
        """Mock proposal for testing."""
        return Proposal(
            id="test-proposal",
            title="Test Proposal",
            body="Test proposal body",
            space_id="test.eth",
            author="0x1234567890123456789012345678901234567890",  # Valid eth address
            state="active",
            choices=["For", "Against", "Abstain"],
            scores=[100, 50, 25],
            votes=175,
            created=1234567890,
            start=1234567890,
            end=1234567890,
            snapshot="123456",
            discussion="https://forum.test.eth/proposal-1",
            ipfs="QmTest123",
            time_remaining="5 days"
        )

    def test_aiservice_initializes_both_agents_after_implementation(self):
        """Test that AIService has both voting and summarization agents after Phase 2."""
        # Arrange & Act
        ai_service = AIService()
        
        # Assert Phase 2 implementation - both agents should be attributes
        assert hasattr(ai_service, 'voting_agent'), "AIService should have voting_agent attribute"
        assert hasattr(ai_service, 'summarization_agent'), "AIService should have summarization_agent attribute"
        
        # Agents may be None until API key is set, but attributes should exist
        assert ai_service.voting_agent is None or isinstance(ai_service.voting_agent, VotingAgent)
        assert ai_service.summarization_agent is None or isinstance(ai_service.summarization_agent, SummarizationAgent)

    @pytest.mark.asyncio
    async def test_summarization_uses_summarization_agent_after_phase2(self):
        """Test that _call_ai_model_for_summary uses SummarizationAgent after Phase 2."""
        # Arrange
        ai_service = AIService()
        
        # Mock the summarization agent
        mock_summarization_agent = Mock()
        mock_agent_run = AsyncMock()
        mock_result = Mock()
        mock_result.output = ProposalSummary(
            proposal_id="test-proposal",
            title="Test Proposal", 
            summary="Test summary",
            key_points=["Point 1", "Point 2"],
            risk_assessment=RiskLevel.LOW,
            recommendation="Test recommendation",
            confidence=0.8
        )
        mock_agent_run.return_value = mock_result
        mock_summarization_agent.agent.run = mock_agent_run
        ai_service.summarization_agent = mock_summarization_agent
        
        # Act
        result = await ai_service._call_ai_model_for_summary("test prompt")
        
        # Assert - Should call summarization agent, not legacy agent
        mock_agent_run.assert_called_once()
        assert isinstance(result, dict), "Should return dictionary result"
        assert result.get("proposal_id") == "test-proposal", "Should return correct proposal data"

    @pytest.mark.asyncio  
    async def test_voting_uses_voting_agent_after_phase2(self, mock_proposal):
        """Test that voting decision methods use VotingAgent after Phase 2."""
        # Arrange
        ai_service = AIService()
        
        # Mock the voting agent 
        mock_voting_agent = Mock()
        mock_agent_run = AsyncMock()
        mock_result = Mock()
        mock_result.output = AiVoteResponse(
            vote="FOR",
            reasoning="Test reasoning", 
            confidence=0.8,
            risk_level="MEDIUM"
        )
        mock_agent_run.return_value = mock_result
        mock_voting_agent.agent.run = mock_agent_run
        mock_voting_agent._get_system_prompt_for_strategy.return_value = "Test prompt"
        ai_service.voting_agent = mock_voting_agent
        
        # Mock the response processor
        ai_service.response_processor.parse_and_validate_vote_response = Mock(return_value={
            "vote": "FOR",
            "reasoning": "Test reasoning",
            "confidence": 0.8,
            "risk_level": "MEDIUM"
        })
        
        # Act
        result = await ai_service._generate_vote_decision(mock_proposal, VotingStrategy.BALANCED)
        
        # Assert - Should call voting agent
        mock_agent_run.assert_called_once()
        assert result["vote"] == "FOR", "Should return correct vote decision"
        assert result["confidence"] == 0.8, "Should return correct confidence"
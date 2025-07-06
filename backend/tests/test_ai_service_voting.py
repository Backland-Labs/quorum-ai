"""Tests for AI service voting decision functionality."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from services.ai_service import AIService
from models import Proposal, ProposalState, VoteDecision, VoteType, VotingStrategy, RiskLevel


@pytest.fixture
def mock_ai_service():
    """Create a mocked AIService for testing."""
    with patch("services.ai_service.settings") as mock_settings:
        mock_settings.openrouter_api_key = "test-key"
        service = AIService()
        return service


class TestAIServiceDecideVote:
    """Test AIService decide_vote method."""

    @pytest.mark.asyncio
    async def test_decide_vote_exists(self, mock_ai_service: AIService, sample_proposal: Proposal) -> None:
        """Test that decide_vote method exists and can be called."""
        # This test should fail since decide_vote doesn't exist yet
        assert hasattr(mock_ai_service, 'decide_vote')
        
        # Mock the internal AI call
        with patch.object(mock_ai_service, "_generate_vote_decision") as mock_generate:
            mock_generate.return_value = {
                "vote": "FOR",
                "confidence": 0.85,
                "reasoning": "Strong proposal with clear benefits",
                "risk_level": "MEDIUM"
            }
            
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            assert isinstance(result, VoteDecision)

    @pytest.mark.asyncio
    async def test_decide_vote_returns_vote_decision(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote returns a VoteDecision object."""
        with patch.object(mock_ai_service, "_generate_vote_decision") as mock_generate:
            mock_generate.return_value = {
                "vote": "FOR",
                "confidence": 0.85,
                "reasoning": "This proposal increases development funding appropriately.",
                "risk_level": "MEDIUM"
            }

            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)

            assert isinstance(result, VoteDecision)
            assert result.proposal_id == sample_proposal.id
            assert result.vote == VoteType.FOR
            assert result.confidence == 0.85
            assert result.strategy_used == VotingStrategy.BALANCED
            assert result.risk_assessment == RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_decide_vote_with_different_strategies(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test decide_vote with different voting strategies."""
        strategies = [VotingStrategy.CONSERVATIVE, VotingStrategy.BALANCED, VotingStrategy.AGGRESSIVE]
        
        for strategy in strategies:
            with patch.object(mock_ai_service, "_generate_vote_decision") as mock_generate:
                mock_generate.return_value = {
                    "vote": "AGAINST" if strategy == VotingStrategy.CONSERVATIVE else "FOR",
                    "confidence": 0.9 if strategy == VotingStrategy.CONSERVATIVE else 0.7,
                    "reasoning": f"Decision based on {strategy.value} strategy",
                    "risk_level": "HIGH" if strategy == VotingStrategy.CONSERVATIVE else "MEDIUM"
                }

                result = await mock_ai_service.decide_vote(sample_proposal, strategy)
                
                assert result.strategy_used == strategy
                assert result.reasoning == f"Decision based on {strategy.value} strategy"

    @pytest.mark.asyncio
    async def test_decide_vote_handles_all_vote_types(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote can return all vote types."""
        vote_types = ["FOR", "AGAINST", "ABSTAIN"]
        
        for vote_type in vote_types:
            with patch.object(mock_ai_service, "_generate_vote_decision") as mock_generate:
                mock_generate.return_value = {
                    "vote": vote_type,
                    "confidence": 0.8,
                    "reasoning": f"Voting {vote_type} based on analysis",
                    "risk_level": "MEDIUM"
                }

                result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
                
                assert result.vote.value == vote_type

    @pytest.mark.asyncio
    async def test_decide_vote_no_caching(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote does not use caching (cache service removed)."""
        # The service should not have cache service initialized
        assert mock_ai_service.cache_service is None
        
        with patch.object(mock_ai_service, "_generate_vote_decision") as mock_generate:
            mock_generate.return_value = {
                "vote": "FOR",
                "confidence": 0.85,
                "reasoning": "Good proposal",
                "risk_level": "LOW"
            }

            # Call twice to ensure no caching
            result1 = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            result2 = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should call AI model both times (no caching)
            assert mock_generate.call_count == 2

    @pytest.mark.asyncio
    async def test_decide_vote_handles_ai_error(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that AI errors are handled gracefully in decide_vote."""
        with patch.object(mock_ai_service, "_generate_vote_decision") as mock_generate:
            mock_generate.side_effect = Exception("AI service unavailable")

            with pytest.raises(Exception, match="AI service unavailable"):
                await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)


class TestAIServiceInitializationWithoutCache:
    """Test AIService initialization without cache service."""

    def test_ai_service_initializes_without_cache(self) -> None:
        """Test that AIService initializes without cache service."""
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            assert service.cache_service is None



class TestAIServiceRemovedMethods:
    """Test that old summarization methods are removed."""

    def test_summarize_proposal_method_removed(self) -> None:
        """Test that summarize_proposal method is removed."""
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            assert not hasattr(service, 'summarize_proposal')

    def test_summarize_multiple_proposals_method_removed(self) -> None:
        """Test that summarize_multiple_proposals method is removed."""
        with patch("services.ai_service.settings") as mock_settings:
            mock_settings.openrouter_api_key = "test-key"
            service = AIService()
            assert not hasattr(service, 'summarize_multiple_proposals')
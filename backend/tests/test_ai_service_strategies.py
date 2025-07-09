"""Tests for AI service strategy-specific voting behavior."""

import pytest
from unittest.mock import patch, MagicMock

from services.ai_service import AIService
from models import Proposal, VoteType, VotingStrategy, RiskLevel


@pytest.fixture
def mock_ai_service():
    """Create a mocked AIService for testing."""
    with patch("services.ai_service.settings") as mock_settings:
        mock_settings.openrouter_api_key = "test-key"
        service = AIService()
        return service


class TestStrategySpecificPrompts:
    """Test that different strategies generate different prompts."""

    @pytest.mark.asyncio
    async def test_conservative_strategy_prompt_content(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that CONSERVATIVE strategy generates risk-averse prompts."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "vote": "AGAINST",
                "confidence": 0.9,
                "reasoning": "Conservative approach - high risk detected",
                "risk_level": "HIGH"
            }

            # Capture the prompt that gets generated
            await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.CONSERVATIVE)
            
            # Get the prompt that was passed to the AI model
            call_args = mock_call.call_args[0]
            prompt = call_args[0]
            
            # Conservative strategy prompt should contain risk-averse language
            assert "conservative" in prompt.lower()
            assert "risk" in prompt.lower()
            assert "treasury protection" in prompt.lower()
            assert "minimal risk" in prompt.lower()
            assert "proven track records" in prompt.lower()

    @pytest.mark.asyncio
    async def test_balanced_strategy_prompt_content(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that BALANCED strategy generates balanced evaluation prompts."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": 0.75,
                "reasoning": "Balanced assessment shows good risk/reward ratio",
                "risk_level": "MEDIUM"
            }

            await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            call_args = mock_call.call_args[0]
            prompt = call_args[0]
            
            # Balanced strategy prompt should contain balanced language
            assert "balanced" in prompt.lower()
            assert "risk vs reward" in prompt.lower()
            assert "community benefit" in prompt.lower()
            assert "long-term sustainability" in prompt.lower()

    @pytest.mark.asyncio
    async def test_aggressive_strategy_prompt_content(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that AGGRESSIVE strategy generates growth-oriented prompts."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": 0.8,
                "reasoning": "Aggressive growth strategy - high potential upside",
                "risk_level": "MEDIUM"
            }

            await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.AGGRESSIVE)
            
            call_args = mock_call.call_args[0]
            prompt = call_args[0]
            
            # Aggressive strategy prompt should contain growth language
            assert "aggressive" in prompt.lower() or "growth" in prompt.lower()
            assert "innovation" in prompt.lower()
            assert "growth opportunities" in prompt.lower()
            assert "new initiatives" in prompt.lower()

    @pytest.mark.asyncio
    async def test_strategy_prompts_are_different(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that each strategy generates distinctly different prompts."""
        prompts = {}
        
        for strategy in [VotingStrategy.CONSERVATIVE, VotingStrategy.BALANCED, VotingStrategy.AGGRESSIVE]:
            with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
                mock_call.return_value = {
                    "vote": "FOR",
                    "confidence": 0.8,
                    "reasoning": f"Decision based on {strategy.value} strategy",
                    "risk_level": "MEDIUM"
                }

                await mock_ai_service.decide_vote(sample_proposal, strategy)
                
                call_args = mock_call.call_args[0]
                prompts[strategy] = call_args[0]
        
        # Each strategy should generate a different prompt
        conservative_prompt = prompts[VotingStrategy.CONSERVATIVE]
        balanced_prompt = prompts[VotingStrategy.BALANCED]
        aggressive_prompt = prompts[VotingStrategy.AGGRESSIVE]
        
        assert conservative_prompt != balanced_prompt
        assert balanced_prompt != aggressive_prompt
        assert conservative_prompt != aggressive_prompt


class TestStrategySpecificBehavior:
    """Test that strategies influence voting behavior as expected."""

    @pytest.mark.asyncio
    async def test_conservative_strategy_risk_bias(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that conservative strategy tends toward AGAINST votes for risky proposals."""
        # Mock the AI to simulate conservative behavior
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "vote": "AGAINST",
                "confidence": 0.95,
                "reasoning": "High risk proposal - treasury protection prioritized",
                "risk_level": "HIGH"
            }

            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.CONSERVATIVE)
            
            # Conservative strategy should result in AGAINST vote for risky proposal
            assert result.vote == VoteType.AGAINST
            assert result.risk_assessment == RiskLevel.HIGH
            assert result.confidence >= 0.9  # High confidence in conservative decisions
            assert "risk" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_aggressive_strategy_growth_bias(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that aggressive strategy tends toward FOR votes for growth opportunities."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": 0.85,
                "reasoning": "Strong growth potential - innovation opportunity",
                "risk_level": "MEDIUM"
            }

            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.AGGRESSIVE)
            
            # Aggressive strategy should result in FOR vote for growth proposals
            assert result.vote == VoteType.FOR
            assert result.confidence >= 0.8
            assert "growth" in result.reasoning.lower() or "innovation" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_balanced_strategy_moderate_approach(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that balanced strategy takes moderate approach."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": 0.75,
                "reasoning": "Reasonable risk/reward balance with community benefits",
                "risk_level": "MEDIUM"
            }

            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Balanced strategy should show moderate confidence and reasoning
            assert result.vote in [VoteType.FOR, VoteType.AGAINST]  # Either vote is valid
            assert 0.6 <= result.confidence <= 0.9  # Moderate confidence range
            assert result.risk_assessment == RiskLevel.MEDIUM
            assert "balance" in result.reasoning.lower() or "reasonable" in result.reasoning.lower()


class TestStrategyPromptConstruction:
    """Test the internal prompt construction methods for strategies."""

    def test_get_strategy_prompt_exists(self, mock_ai_service: AIService) -> None:
        """Test that _get_strategy_prompt method exists."""
        # This test should fail since the method doesn't exist yet
        assert hasattr(mock_ai_service, '_get_strategy_prompt')

    def test_get_strategy_prompt_conservative(self, mock_ai_service: AIService) -> None:
        """Test that conservative strategy prompt contains proper instructions."""
        prompt = mock_ai_service._get_strategy_prompt(VotingStrategy.CONSERVATIVE)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 50  # Should be substantial prompt
        assert "conservative" in prompt.lower()
        assert "treasury protection" in prompt.lower()
        assert "minimal risk" in prompt.lower()

    def test_get_strategy_prompt_balanced(self, mock_ai_service: AIService) -> None:
        """Test that balanced strategy prompt contains proper instructions."""
        prompt = mock_ai_service._get_strategy_prompt(VotingStrategy.BALANCED)
        
        assert isinstance(prompt, str)
        assert "balanced" in prompt.lower()
        assert "risk vs reward" in prompt.lower()
        assert "community benefit" in prompt.lower()

    def test_get_strategy_prompt_aggressive(self, mock_ai_service: AIService) -> None:
        """Test that aggressive strategy prompt contains proper instructions."""
        prompt = mock_ai_service._get_strategy_prompt(VotingStrategy.AGGRESSIVE)
        
        assert isinstance(prompt, str)
        assert "growth" in prompt.lower() or "aggressive" in prompt.lower()
        assert "innovation" in prompt.lower()
        assert "opportunities" in prompt.lower()

    def test_strategy_prompts_mapping_exists(self, mock_ai_service: AIService) -> None:
        """Test that STRATEGY_PROMPTS mapping exists at module level."""
        from services.ai_service import STRATEGY_PROMPTS
        
        # Module-level STRATEGY_PROMPTS should exist and contain all strategies
        assert STRATEGY_PROMPTS is not None
        assert VotingStrategy.CONSERVATIVE in STRATEGY_PROMPTS
        assert VotingStrategy.BALANCED in STRATEGY_PROMPTS
        assert VotingStrategy.AGGRESSIVE in STRATEGY_PROMPTS
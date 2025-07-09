"""Tests for AI service vote decision validation."""

import pytest
from unittest.mock import patch, MagicMock

from services.ai_service import AIService
from models import Proposal, VoteDecision, VoteType, VotingStrategy, RiskLevel
from pydantic import ValidationError


@pytest.fixture
def mock_ai_service():
    """Create a mocked AIService for testing."""
    with patch("services.ai_service.settings") as mock_settings:
        mock_settings.openrouter_api_key = "test-key"
        service = AIService()
        return service


class TestAIServiceValidation:
    """Test AI service validation of vote decisions."""

    @pytest.mark.asyncio
    async def test_decide_vote_validates_ai_response_format(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote validates AI response format."""
        # This test should fail since validation doesn't exist yet
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            # Invalid response missing required fields
            mock_call.return_value = {
                "invalid": "response"
            }
            
            # Should validate and provide fallback values
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should have fallback values due to validation
            assert result.vote == VoteType.ABSTAIN
            assert result.confidence == 0.5
            assert result.reasoning == "No reasoning provided"
            assert result.risk_assessment == RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_decide_vote_validates_confidence_range(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote validates confidence values are in range."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            # Invalid confidence out of range
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": 1.5,  # Invalid - over 1.0
                "reasoning": "Good proposal",
                "risk_level": "LOW"
            }
            
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should clamp confidence to valid range
            assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_decide_vote_validates_vote_type(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote validates vote type values."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            # Invalid vote type
            mock_call.return_value = {
                "vote": "INVALID_VOTE",
                "confidence": 0.8,
                "reasoning": "Some reasoning",
                "risk_level": "MEDIUM"
            }
            
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should default to ABSTAIN for invalid vote types
            assert result.vote == VoteType.ABSTAIN

    @pytest.mark.asyncio
    async def test_decide_vote_validates_risk_level(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote validates risk level values."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            # Invalid risk level
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": 0.8,
                "reasoning": "Good proposal",
                "risk_level": "INVALID_RISK"
            }
            
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should default to MEDIUM for invalid risk levels
            assert result.risk_assessment == RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_decide_vote_handles_missing_reasoning(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote handles missing reasoning field."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            # Missing reasoning field
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": 0.8,
                "risk_level": "LOW"
                # Missing reasoning
            }
            
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should provide default reasoning
            assert result.reasoning == "No reasoning provided"

    @pytest.mark.asyncio
    async def test_decide_vote_handles_negative_confidence(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote handles negative confidence values."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            # Negative confidence
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": -0.2,  # Invalid - negative
                "reasoning": "Good proposal",
                "risk_level": "LOW"
            }
            
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should clamp to minimum valid value
            assert result.confidence >= 0.0

    @pytest.mark.asyncio
    async def test_decide_vote_handles_non_numeric_confidence(
        self, mock_ai_service: AIService, sample_proposal: Proposal
    ) -> None:
        """Test that decide_vote handles non-numeric confidence values."""
        with patch.object(mock_ai_service, "_call_ai_model") as mock_call:
            # Non-numeric confidence
            mock_call.return_value = {
                "vote": "FOR",
                "confidence": "high",  # Invalid - not numeric
                "reasoning": "Good proposal",
                "risk_level": "LOW"
            }
            
            result = await mock_ai_service.decide_vote(sample_proposal, VotingStrategy.BALANCED)
            
            # Should provide default confidence value
            assert result.confidence == 0.5

    @pytest.mark.asyncio
    async def test_parse_vote_response_method_exists(
        self, mock_ai_service: AIService
    ) -> None:
        """Test that _parse_vote_response method exists."""
        # This test should fail since the method doesn't exist yet
        assert hasattr(mock_ai_service, '_parse_vote_response')

    def test_parse_vote_response_validates_all_fields(
        self, mock_ai_service: AIService
    ) -> None:
        """Test that _parse_vote_response validates all required fields."""
        # Complete valid response
        valid_response = {
            "vote": "FOR",
            "confidence": 0.85,
            "reasoning": "Strong proposal with clear benefits",
            "risk_level": "MEDIUM"
        }
        
        result = mock_ai_service._parse_vote_response(valid_response)
        
        assert result["vote"] == "FOR"
        assert result["confidence"] == 0.85
        assert result["reasoning"] == "Strong proposal with clear benefits"
        assert result["risk_level"] == "MEDIUM"

    def test_parse_vote_response_handles_empty_response(
        self, mock_ai_service: AIService
    ) -> None:
        """Test that _parse_vote_response handles empty responses."""
        empty_response = {}
        
        result = mock_ai_service._parse_vote_response(empty_response)
        
        # Should provide all default values
        assert result["vote"] == "ABSTAIN"
        assert result["confidence"] == 0.5
        assert result["reasoning"] == "No reasoning provided"
        assert result["risk_level"] == "MEDIUM"

    def test_parse_vote_response_clamps_confidence_upper_bound(
        self, mock_ai_service: AIService
    ) -> None:
        """Test that _parse_vote_response clamps confidence to upper bound."""
        response = {
            "vote": "FOR",
            "confidence": 2.5,  # Over 1.0
            "reasoning": "Very confident",
            "risk_level": "LOW"
        }
        
        result = mock_ai_service._parse_vote_response(response)
        
        assert result["confidence"] == 1.0  # Clamped to maximum

    def test_parse_vote_response_clamps_confidence_lower_bound(
        self, mock_ai_service: AIService
    ) -> None:
        """Test that _parse_vote_response clamps confidence to lower bound."""
        response = {
            "vote": "AGAINST",
            "confidence": -0.3,  # Below 0.0
            "reasoning": "Risky proposal",
            "risk_level": "HIGH"
        }
        
        result = mock_ai_service._parse_vote_response(response)
        
        assert result["confidence"] == 0.0  # Clamped to minimum

    def test_parse_vote_response_validates_vote_options(
        self, mock_ai_service: AIService
    ) -> None:
        """Test that _parse_vote_response validates vote options."""
        invalid_votes = ["MAYBE", "UNSURE", "YES", "NO", ""]
        
        for invalid_vote in invalid_votes:
            response = {
                "vote": invalid_vote,
                "confidence": 0.8,
                "reasoning": "Some reasoning",
                "risk_level": "MEDIUM"
            }
            
            result = mock_ai_service._parse_vote_response(response)
            
            # Should default to ABSTAIN for invalid votes
            assert result["vote"] == "ABSTAIN"

    def test_parse_vote_response_validates_risk_levels(
        self, mock_ai_service: AIService
    ) -> None:
        """Test that _parse_vote_response validates risk levels."""
        invalid_risks = ["VERY_HIGH", "MINIMAL", "EXTREME", ""]
        
        for invalid_risk in invalid_risks:
            response = {
                "vote": "FOR",
                "confidence": 0.8,
                "reasoning": "Some reasoning",
                "risk_level": invalid_risk
            }
            
            result = mock_ai_service._parse_vote_response(response)
            
            # Should default to MEDIUM for invalid risk levels
            assert result["risk_level"] == "MEDIUM"


class TestVoteDecisionModelValidation:
    """Test VoteDecision model validation directly."""

    def test_vote_decision_validates_empty_proposal_id(self) -> None:
        """Test that VoteDecision validates empty proposal IDs."""
        with pytest.raises(ValidationError, match="Proposal ID cannot be empty"):
            VoteDecision(
                proposal_id="",  # Empty
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Good proposal with clear benefits",
                strategy_used=VotingStrategy.BALANCED
            )

    def test_vote_decision_validates_short_proposal_id(self) -> None:
        """Test that VoteDecision validates short proposal IDs."""
        with pytest.raises(ValidationError, match="Proposal ID too short"):
            VoteDecision(
                proposal_id="ab",  # Too short
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Good proposal with clear benefits",
                strategy_used=VotingStrategy.BALANCED
            )

    def test_vote_decision_validates_whitespace_proposal_id(self) -> None:
        """Test that VoteDecision validates whitespace-only proposal IDs."""
        with pytest.raises(ValidationError, match="Proposal ID cannot be empty"):
            VoteDecision(
                proposal_id="   ",  # Only whitespace
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Good proposal with clear benefits",
                strategy_used=VotingStrategy.BALANCED
            )

    def test_vote_decision_validates_short_reasoning(self) -> None:
        """Test that VoteDecision validates short reasoning text."""
        with pytest.raises(ValidationError, match="reasoning too short"):
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="short",  # Too short
                strategy_used=VotingStrategy.BALANCED
            )

    def test_vote_decision_validates_empty_reasoning(self) -> None:
        """Test that VoteDecision validates empty reasoning text."""
        with pytest.raises(ValidationError, match="reasoning cannot be empty"):
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="",  # Empty
                strategy_used=VotingStrategy.BALANCED
            )

    def test_vote_decision_validates_negative_gas_cost(self) -> None:
        """Test that VoteDecision validates negative gas costs."""
        with pytest.raises(ValidationError, match="Gas cost cannot be negative"):
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Good proposal with clear benefits",
                strategy_used=VotingStrategy.BALANCED,
                estimated_gas_cost=-0.1  # Negative
            )

    def test_vote_decision_validates_excessive_gas_cost(self) -> None:
        """Test that VoteDecision validates excessively high gas costs."""
        with pytest.raises(ValidationError, match="Gas cost seems unreasonably high"):
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Good proposal with clear benefits",
                strategy_used=VotingStrategy.BALANCED,
                estimated_gas_cost=1500.0  # Too high
            )

    def test_vote_decision_validates_confidence_precision(self) -> None:
        """Test that VoteDecision rounds confidence to specified precision."""
        vote_decision = VoteDecision(
            proposal_id="prop-123",
            vote=VoteType.FOR,
            confidence=0.123456789,  # Many decimal places
            reasoning="Good proposal with clear benefits",
            strategy_used=VotingStrategy.BALANCED
        )
        
        # Should be rounded to 3 decimal places (CONFIDENCE_DECIMAL_PLACES)
        assert vote_decision.confidence == 0.123

    def test_vote_decision_validates_nan_confidence(self) -> None:
        """Test that VoteDecision validates NaN confidence values."""
        with pytest.raises(ValidationError, match="Confidence cannot be NaN"):
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=float('nan'),  # NaN
                reasoning="Good proposal with clear benefits",
                strategy_used=VotingStrategy.BALANCED
            )

    def test_vote_decision_validates_infinite_confidence(self) -> None:
        """Test that VoteDecision validates infinite confidence values."""
        with pytest.raises(ValidationError, match="Confidence cannot be infinite"):
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=float('inf'),  # Infinite
                reasoning="Good proposal with clear benefits",
                strategy_used=VotingStrategy.BALANCED
            )
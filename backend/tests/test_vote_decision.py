"""Tests for VoteDecision model."""

import pytest
from datetime import datetime

from models import VoteDecision, VoteType, RiskLevel, VotingStrategy
from pydantic import ValidationError


class TestVoteDecision:
    """Test cases for VoteDecision model."""
    
    def test_vote_decision_creation_with_strategy(self):
        """Test that VoteDecision can be created with a voting strategy."""
        vote_decision = VoteDecision(
            proposal_id="prop-123",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="This proposal shows strong fundamentals and clear execution plan.",
            strategy_used=VotingStrategy.BALANCED
        )
        
        assert vote_decision.proposal_id == "prop-123"
        assert vote_decision.vote == VoteType.FOR
        assert vote_decision.confidence == 0.85
        assert vote_decision.strategy_used == VotingStrategy.BALANCED
        assert vote_decision.risk_assessment == RiskLevel.MEDIUM  # default
    
    def test_vote_decision_requires_strategy_field(self):
        """Test that VoteDecision requires strategy_used field."""
        with pytest.raises(ValidationError) as exc_info:
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="Some reasoning"
                # Missing strategy_used field
            )
        
        assert "strategy_used" in str(exc_info.value)
    
    def test_vote_decision_strategy_validation(self):
        """Test that strategy_used field validates VotingStrategy enum."""
        # Valid strategy should work
        vote_decision = VoteDecision(
            proposal_id="prop-123",
            vote=VoteType.AGAINST,
            confidence=0.75,
            reasoning="High risk proposal.",
            strategy_used=VotingStrategy.CONSERVATIVE
        )
        assert vote_decision.strategy_used == VotingStrategy.CONSERVATIVE
        
        # Invalid strategy should fail
        with pytest.raises(ValidationError):
            VoteDecision(
                proposal_id="prop-123",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="Some reasoning",
                strategy_used="invalid_strategy"
            )
    
    def test_vote_decision_with_all_strategy_types(self):
        """Test VoteDecision creation with all strategy types."""
        strategies = [
            VotingStrategy.CONSERVATIVE,
            VotingStrategy.BALANCED,
            VotingStrategy.AGGRESSIVE
        ]
        
        for strategy in strategies:
            vote_decision = VoteDecision(
                proposal_id=f"prop-{strategy.value}",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning=f"Decision based on {strategy.value} strategy",
                strategy_used=strategy
            )
            assert vote_decision.strategy_used == strategy
    
    def test_vote_decision_conservative_strategy_defaults(self):
        """Test that conservative strategy has appropriate defaults."""
        vote_decision = VoteDecision(
            proposal_id="prop-123",
            vote=VoteType.AGAINST,
            confidence=0.9,
            reasoning="Conservative approach - avoiding risk",
            strategy_used=VotingStrategy.CONSERVATIVE,
            risk_assessment=RiskLevel.HIGH
        )
        
        assert vote_decision.strategy_used == VotingStrategy.CONSERVATIVE
        assert vote_decision.vote == VoteType.AGAINST
        assert vote_decision.risk_assessment == RiskLevel.HIGH
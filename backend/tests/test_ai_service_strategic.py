"""Test suite for AIService strategic briefing capabilities.

This test suite verifies the strategic briefing enhancement for the AI agent,
ensuring it can generate context-aware briefings and incorporate voting history.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.services.ai_service import AIService
from backend.models import (
    Proposal,
    UserPreferences,
    VoteDecision,
    VotingStrategy,
    VoteType,
    RiskLevel,
    StrategicBriefing,
)


@pytest.mark.asyncio
async def test_generate_strategic_briefing():
    """Test that strategic briefing incorporates preferences and history.
    
    This test verifies that the AI service can generate a comprehensive strategic
    briefing that includes user voting strategy, recent voting history analysis,
    and active proposal count.
    """
    ai_service = AIService()
    
    # Setup test data
    proposals = [
        Proposal(
            id="0x1",
            title="Test Proposal",
            body="Test proposal description",
            state="active",
            author="0x1234567890123456789012345678901234567890",
            created=1700000000,
            start=1700000000,
            end=1700086400,
            votes=100,
            scores_total=1000.0,
            choices=["For", "Against", "Abstain"],
            scores=[600.0, 300.0, 100.0],
        )
    ]
    
    preferences = UserPreferences(
        voting_strategy=VotingStrategy.BALANCED,
        confidence_threshold=0.7,
        max_proposals_per_run=5,
        blacklisted_proposers=[],
        whitelisted_proposers=[],
    )
    
    history = [
        VoteDecision(
            proposal_id="0x0",
            vote=VoteType.FOR,
            confidence=0.9,
            reasoning="Previous vote for treasury proposal",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED,
        )
    ]
    
    # Generate briefing
    briefing = await ai_service.generate_strategic_briefing(
        proposals, preferences, history
    )
    
    # Verify briefing contains key elements
    assert briefing.__class__.__name__ == "StrategicBriefing"
    assert "balanced voting strategy" in briefing.summary.lower()
    assert "recent voting history" in briefing.summary.lower()
    assert "1 active proposal" in briefing.summary.lower()
    
    # Verify briefing structure
    assert len(briefing.key_insights) > 0
    assert isinstance(briefing.historical_patterns, dict)
    assert len(briefing.recommendations) > 0


@pytest.mark.asyncio
async def test_strategic_briefing_with_multiple_proposals():
    """Test strategic briefing with multiple proposals and rich history.
    
    This test ensures the briefing can handle complex scenarios with multiple
    proposals and a comprehensive voting history.
    """
    ai_service = AIService()
    
    # Setup multiple proposals
    proposals = [
        Proposal(
            id=f"0x{i}",
            title=f"Proposal {i}",
            body=f"Description for proposal {i}",
            state="active",
            author=f"0x{i:040x}",
            created=1700000000 + i * 3600,
            start=1700000000 + i * 3600,
            end=1700086400 + i * 3600,
            votes=100 + i * 10,
            scores_total=1000.0 + i * 100,
            choices=["For", "Against", "Abstain"],
            scores=[600.0, 300.0, 100.0],
        )
        for i in range(3)
    ]
    
    # Setup varied voting history
    history = [
        VoteDecision(
            proposal_id=f"0xh{i}",
            vote=VoteType.FOR if i % 2 == 0 else VoteType.AGAINST,
            confidence=0.8 + (i * 0.05),
            reasoning=f"Historical vote {i}",
            risk_assessment=RiskLevel.MEDIUM,
            strategy_used=VotingStrategy.BALANCED,
        )
        for i in range(5)
    ]
    
    preferences = UserPreferences(
        voting_strategy=VotingStrategy.CONSERVATIVE,
        confidence_threshold=0.8,
    )
    
    briefing = await ai_service.generate_strategic_briefing(
        proposals, preferences, history
    )
    
    # Verify briefing reflects multiple proposals
    assert "3 active proposals" in briefing.summary.lower() or "three active proposals" in briefing.summary.lower()
    assert "conservative" in briefing.summary.lower()
    
    # Verify historical patterns analysis
    assert "voting_pattern" in briefing.historical_patterns
    assert briefing.historical_patterns["total_votes"] == 5
    assert briefing.historical_patterns["for_votes"] == 3
    assert briefing.historical_patterns["against_votes"] == 2


@pytest.mark.asyncio
async def test_strategic_briefing_empty_history():
    """Test strategic briefing with no voting history.
    
    This test verifies that the briefing system handles new agents gracefully
    when they have no voting history.
    """
    ai_service = AIService()
    
    proposals = [
        Proposal(
            id="0x1",
            title="First Proposal",
            body="New agent's first proposal",
            state="active",
            author="0xabc0000000000000000000000000000000000def",
            created=1700000000,
            start=1700000000,
            end=1700086400,
            votes=50,
            scores_total=500.0,
            choices=["For", "Against"],
            scores=[300.0, 200.0],
        )
    ]
    
    preferences = UserPreferences(
        voting_strategy=VotingStrategy.AGGRESSIVE,
        confidence_threshold=0.6,
    )
    
    history = []  # No voting history
    
    briefing = await ai_service.generate_strategic_briefing(
        proposals, preferences, history
    )
    
    assert briefing.__class__.__name__ == "StrategicBriefing"
    assert ("no voting history" in briefing.summary.lower()) or ("new agent" in briefing.summary.lower())
    assert "aggressive" in briefing.summary.lower()
    assert briefing.historical_patterns.get("total_votes", 0) == 0


@pytest.mark.asyncio
async def test_strategic_system_prompt_includes_briefing():
    """Test that system prompt properly includes strategic briefing.
    
    This test ensures that the AI agent's system prompt is enhanced with
    the strategic briefing context for better decision-making.
    """
    ai_service = AIService()
    
    # Create a sample briefing
    briefing = StrategicBriefing(
        summary="Strategic context: Conservative approach needed due to recent market volatility",
        key_insights=[
            "Recent votes show cautious trend",
            "Treasury proposals require careful evaluation",
        ],
        historical_patterns={
            "total_votes": 10,
            "average_confidence": 0.75,
            "risk_distribution": {"LOW": 3, "MEDIUM": 5, "HIGH": 2},
        },
        recommendations=[
            "Maintain conservative stance on treasury proposals",
            "Prioritize proposals from whitelisted authors",
        ],
    )
    
    # Get strategic system prompt
    prompt = ai_service._get_strategic_system_prompt(
        briefing, VotingStrategy.CONSERVATIVE
    )
    
    # Verify briefing is included
    assert briefing.summary in prompt
    assert "conservative" in prompt.lower()
    assert "KEY INSIGHTS:" in prompt or "Key Insights:" in prompt
    assert "RECOMMENDATIONS:" in prompt or "Recommendations:" in prompt
    
    # Verify all insights and recommendations are included
    for insight in briefing.key_insights:
        assert insight in prompt
    for recommendation in briefing.recommendations:
        assert recommendation in prompt


@pytest.mark.asyncio
async def test_strategic_briefing_with_preferences_integration():
    """Test that strategic briefing reflects user preferences accurately.
    
    This test verifies that user preferences like blacklisted/whitelisted
    proposers and confidence thresholds are incorporated into the briefing.
    """
    ai_service = AIService()
    
    proposals = [
        Proposal(
            id="0x1",
            title="Blacklisted Author Proposal",
            body="Proposal from blacklisted author",
            state="active",
            author="0xblacklisted0000000000000000000000000001",
            created=1700000000,
            start=1700000000,
            end=1700086400,
            votes=100,
            scores_total=1000.0,
            choices=["For", "Against"],
            scores=[700.0, 300.0],
        ),
        Proposal(
            id="0x2",
            title="Whitelisted Author Proposal",
            body="Proposal from trusted author",
            state="active",
            author="0xwhitelisted0000000000000000000000000002",
            created=1700003600,
            start=1700003600,
            end=1700090000,
            votes=80,
            scores_total=800.0,
            choices=["For", "Against"],
            scores=[500.0, 300.0],
        ),
    ]
    
    preferences = UserPreferences(
        voting_strategy=VotingStrategy.BALANCED,
        confidence_threshold=0.85,
        blacklisted_proposers=["0xblacklisted0000000000000000000000000001"],
        whitelisted_proposers=["0xwhitelisted0000000000000000000000000002"],
        max_proposals_per_run=2,
    )
    
    history = []
    
    briefing = await ai_service.generate_strategic_briefing(
        proposals, preferences, history
    )
    
    # Verify preferences are reflected in briefing
    assert "confidence threshold: 0.85" in briefing.summary.lower() or "85%" in briefing.summary
    assert any("blacklist" in insight.lower() for insight in briefing.key_insights)
    assert any("whitelist" in recommendation.lower() for recommendation in briefing.recommendations)


@pytest.mark.asyncio
async def test_strategic_briefing_analyzes_voting_patterns():
    """Test that strategic briefing correctly analyzes historical voting patterns.
    
    This test ensures that the briefing can identify trends in voting behavior
    and provide meaningful insights based on past decisions.
    """
    ai_service = AIService()
    
    # Create a history with clear patterns
    history = [
        # Treasury proposals - mostly against
        VoteDecision(
            proposal_id="0xt1",
            vote=VoteType.AGAINST,
            confidence=0.9,
            reasoning="High treasury impact",
            risk_assessment=RiskLevel.HIGH,
            strategy_used=VotingStrategy.CONSERVATIVE,
        ),
        VoteDecision(
            proposal_id="0xt2",
            vote=VoteType.AGAINST,
            confidence=0.85,
            reasoning="Excessive spending",
            risk_assessment=RiskLevel.HIGH,
            strategy_used=VotingStrategy.CONSERVATIVE,
        ),
        VoteDecision(
            proposal_id="0xt3",
            vote=VoteType.FOR,
            confidence=0.7,
            reasoning="Reasonable treasury allocation",
            risk_assessment=RiskLevel.MEDIUM,
            strategy_used=VotingStrategy.CONSERVATIVE,
        ),
        # Governance proposals - mostly for
        VoteDecision(
            proposal_id="0xg1",
            vote=VoteType.FOR,
            confidence=0.95,
            reasoning="Improves governance",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED,
        ),
        VoteDecision(
            proposal_id="0xg2",
            vote=VoteType.FOR,
            confidence=0.88,
            reasoning="Enhances decentralization",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED,
        ),
    ]
    
    proposals = [
        Proposal(
            id="0xnew",
            title="New Treasury Request",
            body="Request for 100,000 USDC",
            state="active",
            author="0xabc0000000000000000000000000000000000def",
            created=1700000000,
            start=1700000000,
            end=1700086400,
            votes=20,
            scores_total=200.0,
            choices=["For", "Against"],
            scores=[120.0, 80.0],
        )
    ]
    
    preferences = UserPreferences(voting_strategy=VotingStrategy.CONSERVATIVE)
    
    briefing = await ai_service.generate_strategic_briefing(
        proposals, preferences, history
    )
    
    # Verify pattern analysis
    assert briefing.historical_patterns["total_votes"] == 5
    assert briefing.historical_patterns["average_confidence"] > 0.8
    assert "treasury" in str(briefing.historical_patterns).lower()
    
    # Verify insights reflect the patterns
    assert any("treasury" in insight.lower() for insight in briefing.key_insights)
    assert any("cautious" in insight.lower() or "conservative" in insight.lower() 
              for insight in briefing.key_insights)
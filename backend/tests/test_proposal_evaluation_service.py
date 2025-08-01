"""Test proposal evaluation service tools."""

import pytest
from services.proposal_evaluation_service import ProposalEvaluationService
from models import Proposal, VoteDecision, VoteType, VotingStrategy
import re


@pytest.mark.asyncio
async def test_analyze_proposal_impact():
    """Test proposal impact analysis tool.
    
    Why this test matters: The impact analysis tool helps the AI agent
    understand the potential consequences of a proposal. This is crucial
    for making informed voting decisions based on the scale and type
    of impact a proposal might have.
    """
    service = ProposalEvaluationService()
    proposal = Proposal(
        id="0x1",
        title="Increase Treasury Allocation",
        body="Allocate 500,000 USDC for development",
        choices=["For", "Against"],
        author="0x742d35Cc6634C0532925a3b844Bc9e7595f4fE6b",
        space={"id": "test.eth", "name": "Test DAO"},
        state="active",
        created=1699900000,
        start=1700000000,
        end=1700086400,
        quorum=100.0
    )
    
    impact = await service.analyze_proposal_impact(proposal)
    
    assert impact["has_financial_impact"] is True
    assert impact["estimated_amount"] == 500000
    assert impact["impact_level"] in ["high", "medium", "low"]


@pytest.mark.asyncio
async def test_assess_treasury_implications():
    """Test treasury impact assessment with regex patterns.
    
    Why this test matters: Treasury management is a critical aspect of
    DAO governance. This tool helps identify and quantify financial
    implications of proposals, enabling the agent to make fiscally
    responsible decisions based on the DAO's financial strategy.
    """
    service = ProposalEvaluationService()
    
    # Test various financial patterns
    test_cases = [
        ("Request 1,000,000 DAI", {"amount": 1000000, "currency": "DAI"}),
        ("Allocate $2.5M USDC", {"amount": 2500000, "currency": "USDC"}),
        ("Transfer 50 ETH", {"amount": 50, "currency": "ETH"}),
        ("Budget of 100,000.50 USDT", {"amount": 100000.50, "currency": "USDT"}),
        ("No financial impact", None)
    ]
    
    for body, expected in test_cases:
        proposal = Proposal(
            id="0x1", 
            title="Test", 
            body=body,
            choices=["For", "Against"],
            author="0x742d35Cc6634C0532925a3b844Bc9e7595f4fE6b",
            space={"id": "test.eth", "name": "Test DAO"},
            state="active",
            created=1699900000,
            start=1700000000,
            end=1700086400,
            quorum=100.0
        )
        result = await service.assess_treasury_implications(proposal)
        
        if expected is None:
            assert result["treasury_impact"] is None
        else:
            assert result["treasury_impact"]["amount"] == expected["amount"]
            assert result["treasury_impact"]["currency"] == expected["currency"]


@pytest.mark.asyncio
async def test_evaluate_governance_risk():
    """Test governance risk evaluation.
    
    Why this test matters: Governance changes can have far-reaching
    consequences for a DAO. This tool helps assess the risk level
    of proposals that modify governance parameters, voting mechanisms,
    or power structures, ensuring cautious evaluation of such changes.
    """
    service = ProposalEvaluationService()
    
    # High risk proposal - changing voting mechanism
    high_risk_proposal = Proposal(
        id="0x1",
        title="Change Voting Mechanism to Quadratic Voting",
        body="This proposal changes our voting mechanism from token-weighted to quadratic voting",
        choices=["For", "Against"],
        author="0x742d35Cc6634C0532925a3b844Bc9e7595f4fE6b",
        space={"id": "test.eth", "name": "Test DAO"},
        state="active",
        created=1699900000,
        start=1700000000,
        end=1700086400,
        quorum=100.0
    )
    
    risk = await service.evaluate_governance_risk(high_risk_proposal)
    
    assert risk["risk_level"] == "high"
    assert "voting" in risk["risk_factors"]
    assert risk["requires_careful_review"] is True
    
    # Low risk proposal - minor update
    low_risk_proposal = Proposal(
        id="0x2",
        title="Update Documentation",
        body="Fix typos in governance documentation",
        choices=["For", "Against"],
        author="0x742d35Cc6634C0532925a3b844Bc9e7595f4fE6b",
        space={"id": "test.eth", "name": "Test DAO"},
        state="active",
        created=1699900000,
        start=1700000000,
        end=1700086400,
        quorum=100.0
    )
    
    risk = await service.evaluate_governance_risk(low_risk_proposal)
    
    assert risk["risk_level"] == "low"
    assert risk["requires_careful_review"] is False


@pytest.mark.asyncio
async def test_check_proposal_precedent():
    """Test precedent checking against voting history.
    
    Why this test matters: Historical voting patterns provide valuable
    context for decision-making. This tool helps the agent maintain
    consistency in voting behavior by identifying similar past proposals
    and how they were handled, promoting coherent governance participation.
    """
    service = ProposalEvaluationService()
    proposal = Proposal(
        id="0x1", 
        title="Treasury Allocation",
        body="Allocate funds from treasury",
        choices=["For", "Against"],
        author="0x742d35Cc6634C0532925a3b844Bc9e7595f4fE6b",
        space={"id": "test.eth", "name": "Test DAO"},
        state="active",
        created=1699900000,
        start=1700000000,
        end=1700086400,
        quorum=100.0
    )
    
    history = [
        VoteDecision(
            proposal_id="0x0",
            vote=VoteType.FOR,
            confidence=0.9,
            reasoning="Supported similar treasury proposal",
            strategy_used=VotingStrategy.BALANCED
        )
    ]
    
    precedent = await service.check_proposal_precedent(proposal, history)
    
    assert precedent["has_precedent"] is True
    assert precedent["similar_votes"] == 1
    assert precedent["historical_stance"] == "supportive"


@pytest.mark.asyncio
async def test_analyze_community_sentiment():
    """Test community sentiment analysis.
    
    Why this test matters: Understanding community sentiment helps the
    agent align its voting decisions with the broader DAO community.
    This tool analyzes current voting patterns and participation to
    gauge community support, enabling more representative decision-making.
    """
    service = ProposalEvaluationService()
    
    # Proposal with strong support
    proposal = Proposal(
        id="0x1",
        title="Community Initiative",
        body="Launch community rewards program",
        choices=["For", "Against", "Abstain"],
        author="0x742d35Cc6634C0532925a3b844Bc9e7595f4fE6b",
        space={"id": "test.eth", "name": "Test DAO"},
        state="active",
        created=1699900000,
        start=1700000000,
        end=1700086400,
        quorum=100.0,
        scores=[800.0, 150.0, 50.0],  # Strong FOR support
        scores_total=1000.0
    )
    
    sentiment = await service.analyze_community_sentiment(proposal)
    
    assert sentiment["sentiment"] == "positive"
    assert sentiment["support_percentage"] == 80.0
    assert sentiment["participation_level"] == "high"  # 1000 votes is high


@pytest.mark.asyncio
async def test_multiple_currency_formats():
    """Test that treasury assessment handles various currency formats.
    
    Why this test matters: Proposals may express amounts in various
    formats. The tool must reliably parse different representations
    to ensure accurate financial impact assessment across diverse
    proposal styles.
    """
    service = ProposalEvaluationService()
    
    # Test edge cases and various formats
    test_cases = [
        ("Send 1000000 tokens", None),  # No currency specified
        ("1,234,567.89 WETH needed", {"amount": 1234567.89, "currency": "WETH"}),
        ("Requesting $5M in USDC", {"amount": 5000000, "currency": "USDC"}),
        ("0.5 BTC for operations", {"amount": 0.5, "currency": "BTC"}),
        ("Fund with 999,999,999 DAI", {"amount": 999999999, "currency": "DAI"}),
    ]
    
    for body, expected in test_cases:
        proposal = Proposal(
            id="0x1", 
            title="Test", 
            body=body,
            choices=["For", "Against"],
            author="0x742d35Cc6634C0532925a3b844Bc9e7595f4fE6b",
            space={"id": "test.eth", "name": "Test DAO"},
            state="active",
            created=1699900000,
            start=1700000000,
            end=1700086400,
            quorum=100.0
        )
        result = await service.assess_treasury_implications(proposal)
        
        if expected is None:
            assert result["treasury_impact"] is None
        else:
            assert result["treasury_impact"]["amount"] == expected["amount"]
            assert result["treasury_impact"]["currency"] == expected["currency"]
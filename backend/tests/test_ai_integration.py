#!/usr/bin/env python3
"""
Integration test script for AI voting decision making.
Tests real OpenRouter/Claude integration with fake proposal data.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Proposal, VotingStrategy
from services.ai_service import AIService
from config import settings


def generate_fake_proposals() -> List[Proposal]:
    """Generate realistic fake DAO proposals for testing."""
    proposals = [
        Proposal(
            id="prop-001",
            title="Increase Development Funding by 500,000 USDC",
            body="""
            This proposal requests an allocation of 500,000 USDC from the treasury to fund critical 
            development initiatives for Q2 2024. The funds will be used for:
            
            1. Core protocol improvements (60% - 300,000 USDC)
            2. New DeFi integrations (25% - 125,000 USDC) 
            3. Security audits (15% - 75,000 USDC)
            
            Our development team has identified key areas that need immediate attention to maintain 
            our competitive edge. The core protocol improvements include gas optimizations that 
            could reduce transaction costs by 40%, new yield farming strategies, and enhanced 
            governance mechanisms.
            
            Timeline: 6 months
            Expected ROI: 15-25% increase in TVL
            Risk Level: Medium - funds are well-allocated across proven initiatives
            """,
            choices=["For", "Against", "Abstain"],
            start=int((datetime.now() - timedelta(days=2)).timestamp()),
            end=int((datetime.now() + timedelta(days=5)).timestamp()),
            state="active",
            author="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            network="1",
            symbol="COMP",
            scores=[2500.0, 800.0, 200.0],  # Simplified vote counts
            scores_total=3500.0,
            votes=350,  # Number of voters
            created=int((datetime.now() - timedelta(days=3)).timestamp()),
            quorum=1000.0,
            discussion="https://compound.finance/governance/proposals/001"
        ),
        
        Proposal(
            id="prop-002", 
            title="Emergency Protocol Pause Mechanism",
            body="""
            This proposal introduces an emergency pause mechanism that allows the core team to 
            immediately halt protocol operations in case of critical vulnerabilities or exploits.
            
            Key Features:
            - Multi-sig controlled pause function (3/5 signers required)
            - Maximum pause duration: 48 hours
            - Automatic unpause unless extended by governance vote
            - Transparent on-chain logging of all pause events
            
            This mechanism is inspired by recent DeFi exploits where protocols lost millions due to 
            inability to quickly respond to threats. The pause mechanism would only affect:
            - New deposits and withdrawals
            - Automated yield farming strategies 
            - Oracle price updates
            
            Existing positions remain safe and can be emergency-withdrawn during pause.
            
            Security considerations: The pause mechanism itself has been audited by Trail of Bits.
            """,
            choices=["For", "Against", "Abstain"],
            start=int((datetime.now() - timedelta(days=1)).timestamp()),
            end=int((datetime.now() + timedelta(days=6)).timestamp()),
            state="active",
            author="0x123abc456def789012345678901234567890abcd",
            network="1",
            symbol="AAVE",
            scores=[1200.0, 2100.0, 300.0],  # Simplified vote counts
            scores_total=3600.0,
            votes=450,  # Number of voters
            created=int((datetime.now() - timedelta(days=2)).timestamp()),
            quorum=1500.0,
            discussion="https://aave.com/governance/proposals/002"
        ),
        
        Proposal(
            id="prop-003",
            title="Launch Experimental NFT Marketplace Integration", 
            body="""
            This proposal seeks approval to integrate our DeFi protocol with the emerging NFT 
            marketplace ecosystem. The integration would allow users to:
            
            1. Use DeFi tokens as collateral for NFT purchases
            2. Earn yield on NFT collections through our vaults
            3. Access fractionalized NFT investing opportunities
            4. Participate in NFT-backed lending markets
            
            Requested funding: 200,000 DAI for development and partnerships
            
            Partnerships under consideration:
            - OpenSea for marketplace integration
            - Fractional.art for fractionalization tech
            - NFTfi for lending infrastructure
            
            Market opportunity: The NFT market reached $25B in 2021 and continues growing.
            Early DeFi-NFT integration could capture significant market share.
            
            Risks: NFT market volatility, regulatory uncertainty, technical complexity
            
            Timeline: 4 months for MVP, 8 months for full launch
            Success metrics: $10M+ in NFT-backed TVL within 12 months
            """,
            choices=["For", "Against", "Abstain"],
            start=int((datetime.now() - timedelta(hours=12)).timestamp()),
            end=int((datetime.now() + timedelta(days=7)).timestamp()),
            state="active",
            author="0xdef456789abc012345678901234567890abcdef",
            network="1",
            symbol="UNI",
            scores=[900.0, 1800.0, 100.0],  # Simplified vote counts
            scores_total=2800.0,
            votes=280,  # Number of voters
            created=int((datetime.now() - timedelta(days=1)).timestamp()),
            quorum=1200.0,
            discussion="https://uniswap.org/governance/proposals/003"
        ),
        
        Proposal(
            id="prop-004",
            title="Reduce Gas Costs Through L2 Migration",
            body="""
            This proposal outlines a comprehensive plan to migrate 80% of protocol operations 
            to Arbitrum One to reduce gas costs for users by an estimated 90%.
            
            Migration Plan:
            Phase 1 (Month 1-2): Deploy core contracts to Arbitrum
            Phase 2 (Month 3-4): Migrate liquidity pools and yield farms  
            Phase 3 (Month 5-6): Full user migration with incentives
            
            Benefits:
            - 90% reduction in transaction costs
            - Faster confirmation times (2-3 seconds vs 15 seconds)
            - Access to Arbitrum DeFi ecosystem
            - Maintained Ethereum security guarantees
            
            Costs:
            - 150,000 USDC for development and audits
            - Temporary liquidity fragmentation during migration
            - User education and support overhead
            
            Risk mitigation:
            - Gradual migration approach
            - Extensive testing on testnet
            - Bridge security audits by Consensys Diligence
            - Emergency rollback procedures
            
            Expected user adoption: 70% within 6 months based on similar migrations
            """,
            choices=["For", "Against", "Abstain"],
            start=int((datetime.now() - timedelta(hours=6)).timestamp()),
            end=int((datetime.now() + timedelta(days=8)).timestamp()),
            state="active",
            author="0x456789abcdef012345678901234567890abcdef4",
            network="1",
            symbol="MKR",
            scores=[3200.0, 400.0, 150.0],  # Simplified vote counts
            scores_total=3750.0,
            votes=375,  # Number of voters
            created=int((datetime.now() - timedelta(hours=12)).timestamp()),
            quorum=1800.0,
            discussion="https://makerdao.com/governance/proposals/004"
        ),
        
        Proposal(
            id="prop-005",
            title="Controversial: Allocate 50% Treasury to Bitcoin",
            body="""
            This proposal suggests allocating 50% of our 10M USDC treasury to Bitcoin as a hedge 
            against inflation and to diversify our holdings beyond stablecoins.
            
            Rationale:
            - Bitcoin has outperformed most assets over 5+ year periods
            - Treasury currently earning minimal yield in USDC (2-3% APY)
            - Bitcoin allocation could provide 15-20% annual returns historically
            - Protects against USD debasement and stablecoin risks
            
            Allocation Strategy:
            - Purchase 5M USDC worth of Bitcoin over 6 months (dollar-cost averaging)
            - Use Coinbase Institutional for custody and execution
            - Monthly reporting on performance vs USDC holdings
            
            Risks:
            - Bitcoin volatility could reduce treasury value short-term
            - Regulatory risks around Bitcoin holdings
            - Opportunity cost if DeFi yields exceed Bitcoin returns
            - Potential community backlash from conservative members
            
            This is a bold move that positions us as forward-thinking but comes with significant 
            volatility. Recent corporate adoptions by Tesla, MicroStrategy show institutional 
            acceptance growing.
            
            Vote carefully - this decision shapes our financial future for years.
            """,
            choices=["For", "Against", "Abstain"],
            start=int((datetime.now() - timedelta(minutes=30)).timestamp()),
            end=int((datetime.now() + timedelta(days=9)).timestamp()),
            state="active",
            author="0x789abcdef0123456789012345678901234567890",
            network="1",
            symbol="YFI",
            scores=[800.0, 2800.0, 600.0],  # Simplified vote counts
            scores_total=4200.0,
            votes=420,  # Number of voters
            created=int((datetime.now() - timedelta(hours=1)).timestamp()),
            quorum=2000.0,
            discussion="https://yearn.finance/governance/proposals/005"
        )
    ]
    
    return proposals


async def test_voting_strategies(demo_mode: bool = False):
    """Test all voting strategies against fake proposals."""
    print("🚀 Starting AI Voting Integration Test")
    print("=" * 60)
    
    # Check API key
    if not settings.openrouter_api_key and not demo_mode:
        print("❌ OPENROUTER_API_KEY not configured!")
        print("Set your OpenRouter API key or run with --demo for mock responses.")
        print("\nTo set API key:")
        print("export OPENROUTER_API_KEY='your-api-key-here'")
        print("uv run python test_ai_integration.py")
        print("\nOr run demo mode:")
        print("uv run python test_ai_integration.py --demo")
        return
    
    if demo_mode:
        print("🎭 Running in DEMO MODE with mock AI responses")
    else:
        print(f"✅ OpenRouter API key configured: {settings.openrouter_api_key[:8]}...")
    
    # Initialize AI service
    try:
        if demo_mode:
            # Patch settings for demo mode
            settings.openrouter_api_key = 'demo-key-for-testing'
        
        ai_service = AIService()
        print("✅ AI Service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize AI service: {e}")
        return
    
    # Generate test proposals
    proposals = generate_fake_proposals()
    print(f"✅ Generated {len(proposals)} fake proposals")
    
    strategies = [VotingStrategy.CONSERVATIVE, VotingStrategy.BALANCED, VotingStrategy.AGGRESSIVE]
    
    results = []
    
    for i, proposal in enumerate(proposals, 1):
        print(f"\n📋 Testing Proposal {i}: {proposal.title}")
        print(f"Symbol: {proposal.symbol}")
        print(f"Current votes: {proposal.scores[0]:.1f}, {proposal.scores[1]:.1f}, {proposal.scores[2]:.1f} (For/Against/Abstain)")
        
        for strategy in strategies:
            try:
                print(f"\n  🤖 Testing {strategy.value.upper()} strategy...")
                
                # Make AI voting decision (mock in demo mode)
                if demo_mode:
                    # Create mock responses based on strategy and proposal content
                    from models import VoteDecision, VoteType, RiskLevel
                    import random
                    
                    # Strategy-based mock responses
                    if strategy == VotingStrategy.CONSERVATIVE:
                        vote = VoteType.AGAINST if ("experimental" in proposal.title.lower() or 
                                                   "bitcoin" in proposal.title.lower()) else VoteType.FOR
                        confidence = random.uniform(0.7, 0.9)
                        risk = RiskLevel.HIGH if vote == VoteType.AGAINST else RiskLevel.MEDIUM
                        reasoning = f"Conservative approach: {'Rejecting high-risk proposal' if vote == VoteType.AGAINST else 'Approving low-risk initiative'}"
                    elif strategy == VotingStrategy.AGGRESSIVE:
                        vote = VoteType.FOR if ("experimental" in proposal.title.lower() or 
                                               "nft" in proposal.title.lower()) else VoteType.FOR
                        confidence = random.uniform(0.6, 0.85)
                        risk = RiskLevel.MEDIUM
                        reasoning = f"Aggressive growth strategy: Supporting innovation and expansion opportunities"
                    else:  # BALANCED
                        vote = VoteType.FOR if int(proposal.votes_for) > int(proposal.votes_against) else VoteType.AGAINST
                        confidence = random.uniform(0.65, 0.85)
                        risk = RiskLevel.MEDIUM
                        reasoning = f"Balanced analysis: {'Following community consensus' if vote == VoteType.FOR else 'Community concerns noted'}"
                    
                    decision = VoteDecision(
                        proposal_id=proposal.id,
                        vote=vote,
                        confidence=confidence,
                        reasoning=reasoning,
                        risk_assessment=risk,
                        strategy_used=strategy
                    )
                else:
                    decision = await ai_service.decide_vote(proposal, strategy)
                
                result = {
                    "proposal_id": proposal.id,
                    "proposal_title": proposal.title[:50] + "...",
                    "dao": proposal.dao_name,
                    "strategy": strategy.value,
                    "vote": decision.vote.value,
                    "confidence": decision.confidence,
                    "risk_level": decision.risk_assessment.value,
                    "reasoning": decision.reasoning[:100] + "..."
                }
                results.append(result)
                
                # Display result
                vote_emoji = {"FOR": "✅", "AGAINST": "❌", "ABSTAIN": "⚪"}
                risk_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
                
                print(f"    {vote_emoji[decision.vote.value]} Vote: {decision.vote.value}")
                print(f"    📊 Confidence: {decision.confidence:.2f}")
                print(f"    {risk_emoji[decision.risk_assessment.value]} Risk: {decision.risk_assessment.value}")
                print(f"    💭 Reasoning: {decision.reasoning[:80]}...")
                
            except Exception as e:
                print(f"    ❌ Error with {strategy.value} strategy: {e}")
                results.append({
                    "proposal_id": proposal.id,
                    "strategy": strategy.value,
                    "error": str(e)
                })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VOTING RESULTS SUMMARY")
    print("=" * 60)
    
    # Group results by proposal
    for proposal in proposals:
        prop_results = [r for r in results if r.get("proposal_id") == proposal.id and "error" not in r]
        if prop_results:
            print(f"\n{proposal.title[:40]}...")
            for result in prop_results:
                print(f"  {result['strategy'].upper():12} -> {result['vote']:7} (conf: {result['confidence']:.2f}, risk: {result['risk_level']})")
    
    # Strategy analysis
    print(f"\n📈 STRATEGY ANALYSIS")
    print("-" * 30)
    
    for strategy in strategies:
        strategy_results = [r for r in results if r.get("strategy") == strategy.value and "error" not in r]
        if strategy_results:
            votes = [r["vote"] for r in strategy_results]
            avg_confidence = sum(r["confidence"] for r in strategy_results) / len(strategy_results)
            
            vote_counts = {vote: votes.count(vote) for vote in ["FOR", "AGAINST", "ABSTAIN"]}
            
            print(f"{strategy.value.upper():12}: FOR:{vote_counts['FOR']} AGAINST:{vote_counts['AGAINST']} ABSTAIN:{vote_counts['ABSTAIN']} (avg conf: {avg_confidence:.2f})")
    
    # Export results
    with open("ai_voting_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_proposals": len(proposals),
            "total_decisions": len([r for r in results if "error" not in r]),
            "errors": len([r for r in results if "error" in r]),
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Results exported to ai_voting_test_results.json")
    print("🎉 Integration test complete!")


if __name__ == "__main__":
    import sys
    demo_mode = "--demo" in sys.argv
    asyncio.run(test_voting_strategies(demo_mode))
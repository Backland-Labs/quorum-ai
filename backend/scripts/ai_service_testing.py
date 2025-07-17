#!/usr/bin/env python3
"""
AI Service Vote Decision Quality Testing Script

This script tests the AI's actual voting decision-making process by presenting
various proposal scenarios and evaluating the quality of the vote decisions.

Input: Proposal + Strategy
Output: Vote Decision (FOR/AGAINST/ABSTAIN) + Reasoning + Confidence

Usage:
    python ai_service_testing.py
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add backend to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.ai_service import AIService
from models import (
    Proposal,
    VotingStrategy,
)


class VoteDecisionTester:
    """Test AI voting decision quality and reasoning."""
    
    def __init__(self):
        """Initialize the tester."""
        self.ai_service = None
        self.test_scenarios = []
        
    async def initialize(self):
        """Initialize the AI service."""
        try:
            print("🚀 Initializing AI Service...")
            self.ai_service = AIService()
            print("✅ AI Service initialized successfully\n")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize AI Service: {e}")
            return False
    
    def create_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create various proposal scenarios to test AI decision-making."""
        
        scenarios = [
            {
                "name": "CLEAR BENEFICIAL PROPOSAL",
                "description": "Obviously good proposal that should get FOR votes",
                "expected_vote": "FOR",
                "proposal": Proposal(
                    id="good-proposal",
                    title="Increase Security Audit Budget by 20%",
                    choices=["For", "Against", "Abstain"],
                    start=int(datetime.now().timestamp()) - 86400,
                    end=int(datetime.now().timestamp()) + 86400 * 6,
                    state="active",
                    author="0xSecurityTeam123456789",
                    network="1",
                    symbol="SAFE",
                    scores=[850000.0, 50000.0, 100000.0],  # Strong FOR majority
                    scores_total=1000000.0,
                    votes=450,
                    created=int(datetime.now().timestamp()) - 172800,
                    quorum=500000.0,
                    body="""
# Proposal: Increase Security Audit Budget

## Summary
Increase the annual security audit budget from $500K to $600K to hire additional top-tier security firms.

## Benefits
- Enhanced protocol security through more comprehensive audits
- Reduced risk of exploits and user fund loss
- Increased user confidence and adoption
- Industry-leading security standards

## Implementation
- Allocate additional $100K from treasury reserves
- Engage 2 additional tier-1 audit firms
- Implement quarterly audit schedule
- Public audit report publication

## Risk Assessment
- LOW RISK: Improved security significantly outweighs costs
- Treasury has sufficient reserves for this allocation
- All proposed audit firms are well-established and reputable
                    """,
                    strategies=[{"name": "erc20-balance-of", "params": {"address": "0x123", "symbol": "SAFE"}}]
                )
            },
            
            {
                "name": "CLEARLY HARMFUL PROPOSAL", 
                "description": "Obviously bad proposal that should get AGAINST votes",
                "expected_vote": "AGAINST",
                "proposal": Proposal(
                    id="bad-proposal",
                    title="Remove All Security Measures and Sell Treasury",
                    choices=["For", "Against", "Abstain"],
                    start=int(datetime.now().timestamp()) - 43200,
                    end=int(datetime.now().timestamp()) + 86400 * 2,
                    state="active",
                    author="0xSuspiciousActor987654321",
                    network="1", 
                    symbol="RISK",
                    scores=[25000.0, 750000.0, 25000.0],  # Strong AGAINST majority
                    scores_total=800000.0,
                    votes=234,
                    created=int(datetime.now().timestamp()) - 86400,
                    quorum=400000.0,
                    body="""
# Proposal: Emergency Liquidation and Deregulation

## Summary
Remove all security controls, multisig requirements, and liquidate 90% of treasury immediately.

## Proposed Changes
- Disable all smart contract security features
- Remove multisig wallet requirements
- Liquidate $50M treasury and distribute to single address
- Eliminate all governance processes
- Transfer admin keys to proposer

## Justification
"Trust me, this will make everyone rich quickly. Regulations are holding us back."

## Timeline
- Immediate implementation if passed
- No review period or safeguards
- Irreversible changes

## Risks
- [No risk assessment provided]
                    """,
                    strategies=[{"name": "erc20-balance-of", "params": {"address": "0x456", "symbol": "RISK"}}]
                )
            },
            
            {
                "name": "COMPLEX TRADEOFF PROPOSAL",
                "description": "Nuanced proposal requiring careful analysis", 
                "expected_vote": "ABSTAIN",  # Could go either way
                "proposal": Proposal(
                    id="complex-proposal",
                    title="Migrate to New Blockchain with 6-Month Protocol Halt",
                    choices=["For", "Against", "Abstain"],
                    start=int(datetime.now().timestamp()) - 21600,
                    end=int(datetime.now().timestamp()) + 86400 * 4,
                    state="active",
                    author="0xDeveloperTeam456789",
                    network="1",
                    symbol="COMPLEX",
                    scores=[320000.0, 280000.0, 200000.0],  # Close vote
                    scores_total=800000.0,
                    votes=189,
                    created=int(datetime.now().timestamp()) - 129600,
                    quorum=500000.0,
                    body="""
# Proposal: Major Protocol Migration

## Summary
Migrate the entire protocol to a new, more efficient blockchain requiring 6-month development halt.

## Benefits
- 95% reduction in transaction costs
- 10x faster transaction processing
- Modern smart contract capabilities
- Future-proof architecture

## Drawbacks
- 6-month complete protocol shutdown during migration
- $2M development costs
- Risk of migration bugs or exploits
- Loss of current user base during downtime
- Unproven new blockchain ecosystem

## Implementation Plan
- Phase 1: 2 months development and testing
- Phase 2: 4 months gradual user migration
- Phase 3: Legacy system shutdown
- Full protocol audit on new chain

## Risks
- HIGH: Extended downtime could kill project momentum
- MEDIUM: Migration complexity may introduce vulnerabilities  
- LOW: New blockchain ecosystem is relatively stable

## Financial Impact
- Cost: $2M development + $500K audits
- Treasury can afford costs
- Potential for 5x user growth post-migration
                    """,
                    strategies=[{"name": "erc20-balance-of", "params": {"address": "0x789", "symbol": "COMPLEX"}}]
                )
            },
            
            {
                "name": "EMERGENCY TIME-SENSITIVE PROPOSAL",
                "description": "Urgent proposal requiring quick decision",
                "expected_vote": "FOR",  # Should recognize urgency
                "proposal": Proposal(
                    id="emergency-proposal", 
                    title="Emergency Security Patch Deployment",
                    choices=["For", "Against", "Abstain"],
                    start=int(datetime.now().timestamp()) - 3600,
                    end=int(datetime.now().timestamp()) + 86400,  # Only 24 hours!
                    state="active",
                    author="0xSecurityTeamEmergency",
                    network="1",
                    symbol="URGENT",
                    scores=[450000.0, 25000.0, 75000.0],  # Strong support
                    scores_total=550000.0,
                    votes=123,
                    created=int(datetime.now().timestamp()) - 7200,
                    quorum=300000.0,
                    body="""
# 🚨 EMERGENCY SECURITY PATCH

## Critical Vulnerability Discovered
A critical vulnerability has been identified that could allow:
- Unauthorized fund withdrawals
- Contract state manipulation
- Total protocol compromise

## Immediate Action Required
Deploy pre-audited security patch within 24 hours to prevent:
- Estimated $10M+ potential loss
- Complete protocol shutdown
- User fund compromises

## Patch Details
- Developed by core security team
- Pre-audited by 3 independent firms
- Minimal functionality changes
- Backwards compatible
- Emergency multisig controls added

## Timeline
- Deploy immediately if approved
- 2-hour deployment window
- Monitor for 48 hours post-deployment

## Risk Assessment
- WITHOUT PATCH: CRITICAL risk of total fund loss
- WITH PATCH: LOW risk of minor disruption
- Delay increases exploitation probability exponentially
                    """,
                    strategies=[{"name": "erc20-balance-of", "params": {"address": "0xabc", "symbol": "URGENT"}}]
                )
            },
            
            {
                "name": "QUESTIONABLE FUNDING PROPOSAL",
                "description": "Proposal with unclear benefits and high costs",
                "expected_vote": "AGAINST",
                "proposal": Proposal(
                    id="questionable-proposal",
                    title="$5M Marketing Campaign for Celebrity Endorsements", 
                    choices=["For", "Against", "Abstain"],
                    start=int(datetime.now().timestamp()) - 36000,
                    end=int(datetime.now().timestamp()) + 86400 * 3,
                    state="active", 
                    author="0xMarketingGuru123",
                    network="1",
                    symbol="SPEND",
                    scores=[150000.0, 400000.0, 150000.0],  # Community against it
                    scores_total=700000.0,
                    votes=167,
                    created=int(datetime.now().timestamp()) - 172800,
                    quorum=350000.0,
                    body="""
# Proposal: Celebrity Marketing Campaign

## Summary  
Allocate $5M treasury funds for celebrity endorsement marketing campaign.

## Proposed Activities
- $3M for A-list celebrity spokesperson
- $1M for Super Bowl commercial
- $500K for influencer partnerships  
- $500K for marketing agency fees

## Expected Outcomes
- "Massive brand awareness"
- "10x user growth" 
- "Mainstream adoption"

## Details
- Celebrity contracts for 6-month campaign
- No performance guarantees or metrics
- All payments upfront with no refunds
- Marketing agency is owned by proposer's cousin

## Budget Breakdown
- 25% of total treasury for this campaign
- No other marketing budget for 2 years
- Reduces development funding by 60%

## Success Metrics
- [None specified]
- [No measurement plan provided]
- [No fallback strategy if campaign fails]
                    """,
                    strategies=[{"name": "erc20-balance-of", "params": {"address": "0xdef", "symbol": "SPEND"}}]
                )
            }
        ]
        
        return scenarios
    
    async def test_vote_decision(self, scenario: Dict[str, Any], strategy: VotingStrategy) -> Dict[str, Any]:
        """Test AI vote decision for a specific scenario and strategy."""
        
        print(f"\n{'='*60}")
        print(f"🎯 TESTING: {scenario['name']}")
        print(f"📋 Description: {scenario['description']}")
        print(f"🔮 Expected Vote: {scenario['expected_vote']}")
        print(f"⚡ Strategy: {strategy.value.upper()}")
        print(f"{'='*60}")
        
        try:
            # Get AI vote decision
            decision = await self.ai_service.decide_vote(scenario['proposal'], strategy)
            
            
            return decision
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            return {
                "scenario": scenario['name'],
                "strategy": strategy.value,
                "status": "FAILED",
                "error": str(e)
            }
    
    def print_test_summary(self, results: List[Dict[str, Any]]) -> None:
        """Print comprehensive test summary."""
        
        print(f"\n{'='*80}")
        print(f"📊 AI VOTE DECISION QUALITY SUMMARY")
        print(f"{'='*80}")
        
        successful_tests = [r for r in results if r["status"] == "SUCCESS"]
        failed_tests = [r for r in results if r["status"] == "FAILED"]
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   Total Tests: {len(results)}")
        print(f"   ✅ Successful: {len(successful_tests)}")
        print(f"   ❌ Failed: {len(failed_tests)}")
        
        if successful_tests:
            correct_votes = len([r for r in successful_tests if r["vote_correct"]])
            vote_accuracy = (correct_votes / len(successful_tests)) * 100
            
            print(f"\n🗳️  VOTE ACCURACY:")
            print(f"   Correct Votes: {correct_votes}/{len(successful_tests)}")
            print(f"   Accuracy Rate: {vote_accuracy:.1f}%")
            
            # Show vote breakdown by scenario
            print(f"\n📋 VOTE BREAKDOWN BY SCENARIO:")
            for result in successful_tests:
                status = "✅" if result["vote_correct"] else "❌"
                print(f"   {status} {result['scenario']}: {result['ai_vote']} (expected: {result['expected_vote']})")
            
            # Average confidence and reasoning quality
            avg_confidence = sum(r["confidence"] for r in successful_tests) / len(successful_tests)
            print(f"\n📈 CONFIDENCE ANALYSIS:")
            print(f"   Average Confidence: {avg_confidence:.3f}")
            
            # Reasoning quality analysis
            if successful_tests and "reasoning_quality" in successful_tests[0]:
                print(f"\n💭 REASONING QUALITY ANALYSIS:")
                quality_averages = {}
                for criterion in successful_tests[0]["reasoning_quality"].keys():
                    avg_score = sum(r["reasoning_quality"][criterion] for r in successful_tests) / len(successful_tests)
                    quality_averages[criterion] = avg_score
                    print(f"   {criterion}: {avg_score:.1f}/5.0")
        
        # Strategy comparison
        print(f"\n⚡ STRATEGY COMPARISON:")
        strategies = ["conservative", "balanced", "aggressive"]
        for strategy in strategies:
            strategy_results = [r for r in successful_tests if r["strategy"] == strategy]
            if strategy_results:
                correct = len([r for r in strategy_results if r["vote_correct"]])
                accuracy = (correct / len(strategy_results)) * 100
                print(f"   {strategy.upper()}: {correct}/{len(strategy_results)} correct ({accuracy:.1f}%)")
        
        if failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for result in failed_tests:
                print(f"   - {result['scenario']} ({result['strategy']}): {result.get('error', 'Unknown error')}")
    
    async def run_vote_decision_tests(self) -> None:
        """Run comprehensive vote decision testing."""
        
        print("🗳️  AI VOTE DECISION QUALITY TEST SUITE")
        print("="*60)
        print("Testing AI's ability to make good voting decisions")
        print("based on proposal content and reasoning quality.\n")
        
        # Initialize
        if not await self.initialize():
            return
        
        # Create test scenarios
        scenarios = self.create_test_scenarios()
        strategies = [VotingStrategy.CONSERVATIVE, VotingStrategy.BALANCED, VotingStrategy.AGGRESSIVE]
        
        print(f"📋 Testing {len(scenarios)} scenarios with {len(strategies)} strategies")
        print(f"📊 Total tests: {len(scenarios) * len(strategies)}\n")
        
        # Run all tests
        all_results = []
        
        for scenario in scenarios:
            for strategy in strategies:
                result = await self.test_vote_decision(scenario, strategy)
                all_results.append(result)
        
        # Print comprehensive summary
        self.print_test_summary(all_results)


async def main():
    """Main function to run vote decision tests."""
    tester = VoteDecisionTester()
    await tester.run_vote_decision_tests()


if __name__ == "__main__":
    print("🚀 Starting AI Vote Decision Quality Tests...")
    print("🎯 This tests whether the AI makes good voting decisions")
    print("⏳ Please wait while tests execute...\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Testing failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 Vote decision tests complete!")
"""Test fixtures for VotingAgent testing.

This module provides reusable test fixtures for comprehensive agent testing,
including mock data, sample responses, and utility functions.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from models import (
    Proposal,
    ProposalVoter,
    Space,
    UserPreferences,
    VotingStrategy,
    VoteType,
    SummarizeResponse,
    AiVoteResponse,
)


class AgentTestFixtures:
    """Collection of test fixtures for VotingAgent testing."""

    @staticmethod
    def create_sample_proposal(
        proposal_id: str = "test-proposal-1",
        title: str = "Test Proposal",
        author: str = "0xTestAuthor",
        state: str = "active",
        space_id: str = "test.eth",
        **kwargs,
    ) -> Proposal:
        """Create a sample proposal with customizable fields."""
        now = datetime.now(timezone.utc)

        defaults = {
            "id": proposal_id,
            "title": title,
            "body": "This is a test proposal body with detailed description.",
            "choices": ["For", "Against", "Abstain"],
            "state": state,
            "start": int((now - timedelta(days=1)).timestamp()),
            "end": int((now + timedelta(days=1)).timestamp()),
            "snapshot": "17890123",
            "author": author,
            "space": {"id": space_id, "name": f"{space_id} DAO"},
            "type": "single-choice",
            "quorum": 100000.0,
            "privacy": "",
            "validation": {"name": "basic"},
            "strategies": [{"name": "erc20-balance-of", "params": {}}],
            "scores": [5000.0, 2000.0, 1000.0],
            "scores_total": 8000.0,
            "created": int((now - timedelta(days=2)).timestamp()),
            "updated": int((now - timedelta(days=1)).timestamp()),
            "votes": 100,
            "link": f"https://snapshot.org/#/{space_id}/proposal/{proposal_id}",
        }

        # Override with any provided kwargs
        defaults.update(kwargs)

        return Proposal(**defaults)

    @staticmethod
    def create_sample_proposals_batch(count: int = 5) -> List[Proposal]:
        """Create a batch of diverse sample proposals."""
        proposals = []

        # Different proposal types
        proposal_types = [
            (
                "Treasury Management",
                "Allocate funds for development",
                VotingStrategy.CONSERVATIVE,
            ),
            ("Protocol Upgrade", "Implement new features", VotingStrategy.BALANCED),
            ("Community Grant", "Fund community projects", VotingStrategy.AGGRESSIVE),
            (
                "Governance Change",
                "Update voting parameters",
                VotingStrategy.CONSERVATIVE,
            ),
            ("Emergency Action", "Address critical issue", VotingStrategy.BALANCED),
        ]

        for i in range(min(count, len(proposal_types))):
            title, body_prefix, _ = proposal_types[i]
            proposals.append(
                AgentTestFixtures.create_sample_proposal(
                    proposal_id=f"proposal-{i + 1}",
                    title=title,
                    body=f"{body_prefix}. This requires careful consideration and community input.",
                    author=f"0xAuthor{i + 1}",
                    votes=50 + i * 20,
                )
            )

        # Add more generic proposals if needed
        for i in range(len(proposal_types), count):
            proposals.append(
                AgentTestFixtures.create_sample_proposal(
                    proposal_id=f"proposal-{i + 1}",
                    title=f"Proposal {i + 1}",
                    author=f"0xAuthor{i + 1}",
                )
            )

        return proposals

    @staticmethod
    def create_sample_space_details(
        space_id: str = "test.eth", name: str = "Test DAO"
    ) -> Space:
        """Create sample space details."""
        return Space(
            id=space_id,
            name=name,
            about="A test DAO for testing purposes",
            network="1",  # Mainnet
            symbol="TEST",
            members=["0xMember1", "0xMember2", "0xMember3"],
            admins=["0xAdmin1"],
            strategies=[
                {
                    "name": "erc20-balance-of",
                    "params": {"address": "0xTokenAddress", "decimals": 18},
                }
            ],
            validation={"name": "basic"},
            filters={"minScore": 1, "onlyMembers": False},
            voting={
                "delay": 0,
                "period": 604800,  # 7 days
                "type": "single-choice",
                "quorum": 100000,
            },
        )

    @staticmethod
    def create_sample_voters(count: int = 5) -> List[ProposalVoter]:
        """Create sample voters for testing."""
        voters = []

        for i in range(count):
            voters.append(
                ProposalVoter(
                    address=f"0xVoter{i + 1:040x}",
                    votes=1000.0 + i * 500,
                    voting_power_percentage=(10.0 + i * 2.5),
                    choice="For"
                    if i % 3 == 0
                    else "Against"
                    if i % 3 == 1
                    else "Abstain",
                )
            )

        return voters

    @staticmethod
    def create_sample_ai_summary_response() -> SummarizeResponse:
        """Create a sample AI summary response."""
        return SummarizeResponse(
            summary="This proposal aims to improve the protocol's efficiency and security.",
            key_points=[
                "Implements new optimization techniques",
                "Enhances security measures",
                "Reduces gas costs by 30%",
            ],
            potential_impact="High positive impact on user experience and protocol sustainability",
            voter_recommendation="Consider supporting if technical review is positive",
        )

    @staticmethod
    def create_sample_ai_vote_response(
        decision: VoteType = VoteType.FOR, confidence: float = 0.75
    ) -> AiVoteResponse:
        """Create a sample AI vote response."""
        return AiVoteResponse(
            decision=decision,
            confidence=confidence,
            reasoning="Based on comprehensive analysis of the proposal's technical merit and community benefit.",
            risk_level="medium" if decision == VoteType.FOR else "low",
        )

    @staticmethod
    def create_user_preferences_variants() -> List[UserPreferences]:
        """Create different user preference configurations for testing."""
        return [
            # Conservative user
            UserPreferences(
                voting_strategy=VotingStrategy.CONSERVATIVE,
                confidence_threshold=0.8,
                max_proposals_per_run=3,
                blacklisted_proposers=["0xBadActor1", "0xBadActor2"],
                whitelisted_proposers=["0xTrusted1"],
            ),
            # Balanced user
            UserPreferences(
                voting_strategy=VotingStrategy.BALANCED,
                confidence_threshold=0.7,
                max_proposals_per_run=5,
                blacklisted_proposers=["0xBadActor1"],
                whitelisted_proposers=["0xTrusted1", "0xTrusted2"],
            ),
            # Aggressive user
            UserPreferences(
                voting_strategy=VotingStrategy.AGGRESSIVE,
                confidence_threshold=0.6,
                max_proposals_per_run=10,
                blacklisted_proposers=[],
                whitelisted_proposers=[],
            ),
            # Minimal configuration
            UserPreferences(
                voting_strategy=VotingStrategy.BALANCED,
                confidence_threshold=0.7,
                max_proposals_per_run=5,
            ),
        ]

    @staticmethod
    def create_mock_agent_responses() -> Dict[str, Any]:
        """Create mock responses for different agent scenarios."""
        return {
            "successful_vote": {
                "decision": "FOR",
                "confidence": 0.85,
                "reasoning": "Strong technical proposal with clear benefits",
                "risk_level": "low",
            },
            "low_confidence_vote": {
                "decision": "ABSTAIN",
                "confidence": 0.45,
                "reasoning": "Insufficient information to make confident decision",
                "risk_level": "high",
            },
            "against_vote": {
                "decision": "AGAINST",
                "confidence": 0.9,
                "reasoning": "Proposal has significant security risks",
                "risk_level": "high",
            },
            "error_response": {
                "error": "Failed to analyze proposal",
                "details": "Network timeout while fetching data",
            },
        }

    @staticmethod
    def create_large_proposal_body(size_kb: int = 10) -> str:
        """Create a large proposal body for testing truncation."""
        base_text = "This is a very detailed proposal with extensive documentation. "
        repeat_count = (size_kb * 1024) // len(base_text)
        return base_text * repeat_count

    @staticmethod
    def create_edge_case_proposals() -> List[Proposal]:
        """Create proposals with edge case scenarios."""
        now = datetime.now(timezone.utc)

        return [
            # Proposal with empty body
            AgentTestFixtures.create_sample_proposal(
                proposal_id="edge-empty-body", title="Proposal with Empty Body", body=""
            ),
            # Proposal with very long body
            AgentTestFixtures.create_sample_proposal(
                proposal_id="edge-long-body",
                title="Proposal with Long Body",
                body=AgentTestFixtures.create_large_proposal_body(50),
            ),
            # Proposal with special characters
            AgentTestFixtures.create_sample_proposal(
                proposal_id="edge-special-chars",
                title="Proposal with Special Characters: !@#$%^&*()",
                body="Body with émojis 🚀 and spëcial çharacters",
            ),
            # Expired proposal
            AgentTestFixtures.create_sample_proposal(
                proposal_id="edge-expired",
                title="Expired Proposal",
                state="closed",
                start=int((now - timedelta(days=10)).timestamp()),
                end=int((now - timedelta(days=3)).timestamp()),
            ),
            # Proposal with no votes
            AgentTestFixtures.create_sample_proposal(
                proposal_id="edge-no-votes",
                title="Proposal with No Votes",
                votes=0,
                scores=[0.0, 0.0, 0.0],
                scores_total=0.0,
            ),
            # Multi-choice proposal
            AgentTestFixtures.create_sample_proposal(
                proposal_id="edge-multi-choice",
                title="Multi-Choice Proposal",
                type="ranked-choice",
                choices=["Option A", "Option B", "Option C", "Option D", "None"],
            ),
        ]

    @staticmethod
    def generate_mock_tool_responses() -> Dict[str, Any]:
        """Generate mock responses for agent tools."""
        return {
            "query_active_proposals": [
                {
                    "id": "prop-1",
                    "title": "Active Proposal 1",
                    "state": "active",
                    "end_timestamp": int(
                        (datetime.now(timezone.utc) + timedelta(days=2)).timestamp()
                    ),
                    "scores_total": 50000.0,
                },
                {
                    "id": "prop-2",
                    "title": "Active Proposal 2",
                    "state": "active",
                    "end_timestamp": int(
                        (datetime.now(timezone.utc) + timedelta(days=1)).timestamp()
                    ),
                    "scores_total": 75000.0,
                },
            ],
            "get_proposal_details": {
                "id": "prop-1",
                "title": "Detailed Proposal",
                "body": "Full proposal content with details",
                "choices": ["For", "Against"],
                "author": "0xProposer",
                "space": {"id": "test.eth", "name": "Test DAO"},
                "scores": [30000.0, 20000.0],
                "quorum": 40000.0,
                "state": "active",
            },
            "get_voting_power": 1500.75,
        }

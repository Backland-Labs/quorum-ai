"""Pytest configuration and fixtures for the test suite."""

import pytest
from datetime import datetime

from models import (
    Proposal,
    ProposalState,
    DAO,
)
from services.ai_service import AIService
from services.tally_service import TallyService


@pytest.fixture
def ai_service() -> AIService:
    """Create an AIService instance for testing."""
    return AIService()


@pytest.fixture
def tally_service() -> TallyService:
    """Create a TallyService instance for testing."""
    return TallyService()


@pytest.fixture
def sample_proposal() -> Proposal:
    """Create a sample proposal for testing."""
    return Proposal(
        id="prop-123",
        title="Increase Treasury Allocation for Development",
        description="""
        This proposal suggests increasing the treasury allocation for development 
        activities from 10% to 15% of total funds. The additional 5% will be used 
        to hire more developers and accelerate the roadmap implementation.
        
        Key benefits:
        - Faster development cycles
        - More robust security audits
        - Enhanced user experience
        
        Risks:
        - Reduced funds for other activities
        - Potential for scope creep
        """,
        state=ProposalState.ACTIVE,
        created_at=datetime.now(),
        start_block=1000,
        end_block=2000,
        votes_for="1000000",
        votes_against="250000",
        votes_abstain="50000",
        dao_id="dao-123",
        dao_name="Test DAO",
    )


@pytest.fixture
def complex_proposal() -> Proposal:
    """Create a complex proposal for testing edge cases."""
    return Proposal(
        id="prop-456",
        title="Multi-Phase Protocol Upgrade with Governance Changes",
        description="""
        This comprehensive proposal outlines a multi-phase protocol upgrade that includes:
        
        Phase 1: Smart Contract Upgrades
        - Upgrade core protocol contracts to v2.0
        - Implement new fee structure
        - Add support for cross-chain transactions
        
        Phase 2: Governance Mechanism Changes
        - Reduce proposal threshold from 100,000 to 50,000 tokens
        - Implement quadratic voting for certain proposal types
        - Add time-locked voting for critical proposals
        
        Phase 3: Economic Model Adjustments
        - Modify tokenomics to include staking rewards
        - Implement burn mechanism for excess tokens
        - Introduce liquidity mining incentives
        
        Timeline: 6 months total
        Budget: 2.5M tokens
        Team: 15 developers, 3 auditors, 2 project managers
        
        Technical Requirements:
        - Solidity 0.8.19+
        - Multi-signature wallet support
        - Integration with existing DeFi protocols
        
        Risk Assessment:
        - High technical complexity
        - Potential for smart contract vulnerabilities
        - Community resistance to governance changes
        - Market volatility impact on budget
        """,
        state=ProposalState.ACTIVE,
        created_at=datetime.now(),
        start_block=2000,
        end_block=3000,
        votes_for="5000000",
        votes_against="1200000",
        votes_abstain="300000",
        dao_id="dao-456",
        dao_name="Complex DAO",
    )


@pytest.fixture
def sample_dao() -> DAO:
    """Create a sample DAO for testing."""
    return DAO(
        id="dao-123",
        name="Test DAO",
        slug="test-dao",
        description="A test DAO for unit testing",
        organization_id="org-123",
        active_proposals_count=3,
        total_proposals_count=10,
    )


@pytest.fixture
def mock_dao_response() -> dict:
    """Mock response data for DAO API calls."""
    return {
        "data": {
            "governors": {
                "nodes": [
                    {
                        "id": "dao-1",
                        "name": "Test DAO 1",
                        "slug": "test-dao-1",
                        "metadata": {"description": "A test DAO"},
                        "organization": {"id": "org-1"},
                        "proposalStats": {"total": 10, "active": 3},
                    },
                    {
                        "id": "dao-2",
                        "name": "Test DAO 2",
                        "slug": "test-dao-2",
                        "metadata": {"description": None},
                        "organization": {"id": "org-2"},
                        "proposalStats": {"total": 5, "active": 1},
                    },
                ],
                "pageInfo": {"lastCursor": None},
            }
        }
    }


@pytest.fixture
def mock_single_dao_response() -> dict:
    """Mock response data for single DAO API call."""
    return {
        "data": {
            "governor": {
                "id": "dao-1",
                "name": "Test DAO",
                "slug": "test-dao",
                "metadata": {"description": "A test DAO"},
                "organization": {"id": "org-1"},
                "proposalStats": {"total": 10, "active": 3},
            }
        }
    }


@pytest.fixture
def mock_proposals_response() -> dict:
    """Mock response data for proposals API calls."""
    return {
        "data": {
            "proposals": {
                "nodes": [
                    {
                        "id": "prop-1",
                        "status": "ACTIVE",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "metadata": {
                            "title": "Test Proposal 1",
                            "description": "Test description 1",
                        },
                        "governor": {"id": "dao-1", "name": "Test DAO"},
                        "voteStats": [
                            {"type": "FOR", "votesCount": "1000000"},
                            {"type": "AGAINST", "votesCount": "250000"},
                            {"type": "ABSTAIN", "votesCount": "50000"}
                        ]
                    },
                    {
                        "id": "prop-2",
                        "status": "SUCCEEDED",
                        "createdAt": "2024-01-02T00:00:00Z",
                        "metadata": {
                            "title": "Test Proposal 2",
                            "description": "Test description 2",
                        },
                        "governor": {"id": "dao-1", "name": "Test DAO"},
                        "voteStats": [
                            {"type": "FOR", "votesCount": "2000000"},
                            {"type": "AGAINST", "votesCount": "100000"},
                            {"type": "ABSTAIN", "votesCount": "25000"}
                        ]
                    },
                ],
                "pageInfo": {"lastCursor": None},
            }
        }
    }


@pytest.fixture
def mock_single_proposal_response() -> dict:
    """Mock response data for single proposal API call."""
    return {
        "data": {
            "proposal": {
                "id": "prop-1",
                "status": "ACTIVE",
                "createdAt": "2024-01-01T00:00:00Z",
                "metadata": {
                    "title": "Test Proposal",
                    "description": "Test description",
                },
                "governor": {"id": "dao-1", "name": "Test DAO"},
                "voteStats": [
                    {"type": "FOR", "votesCount": "1000000"},
                    {"type": "AGAINST", "votesCount": "250000"},
                    {"type": "ABSTAIN", "votesCount": "50000"}
                ]
            }
        }
    }


@pytest.fixture
def mock_proposals_with_vote_counts_response() -> dict:
    """Mock response for proposals sorted by vote count."""
    return {
        "data": {
            "proposals": {
                "nodes": [
                    {
                        "id": "prop-high-votes",
                        "status": "ACTIVE",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "metadata": {
                            "title": "High Vote Proposal",
                            "description": "This proposal has the most votes",
                        },
                        "governor": {"id": "dao-1", "name": "Test DAO"},
                        "voteStats": [
                            {"type": "FOR", "votesCount": "5000000"},
                            {"type": "AGAINST", "votesCount": "500000"},
                            {"type": "ABSTAIN", "votesCount": "100000"}
                        ]
                    },
                    {
                        "id": "prop-medium-votes",
                        "status": "ACTIVE",
                        "createdAt": "2024-01-02T00:00:00Z",
                        "metadata": {
                            "title": "Medium Vote Proposal",
                            "description": "This proposal has medium votes",
                        },
                        "governor": {"id": "dao-1", "name": "Test DAO"},
                        "voteStats": [
                            {"type": "FOR", "votesCount": "2000000"},
                            {"type": "AGAINST", "votesCount": "300000"},
                            {"type": "ABSTAIN", "votesCount": "50000"}
                        ]
                    },
                    {
                        "id": "prop-low-votes",
                        "status": "ACTIVE",
                        "createdAt": "2024-01-03T00:00:00Z",
                        "metadata": {
                            "title": "Low Vote Proposal",
                            "description": "This proposal has the least votes",
                        },
                        "governor": {"id": "dao-1", "name": "Test DAO"},
                        "voteStats": [
                            {"type": "FOR", "votesCount": "100000"},
                            {"type": "AGAINST", "votesCount": "50000"},
                            {"type": "ABSTAIN", "votesCount": "10000"}
                        ]
                    },
                ],
                "pageInfo": {"lastCursor": None},
            }
        }
    }


@pytest.fixture
def mock_organization_overview_response() -> dict:
    """Mock response data for organization overview API call."""
    return {
        "data": {
            "organization": {
                "id": "org-123",
                "name": "Test DAO",
                "slug": "test-dao",
                "metadata": {"description": "A test DAO organization"},
                "delegatesCount": 150,
                "tokenOwnersCount": 1000,
                "proposalsCount": 50,
                "hasActiveProposals": True,
                "chainIds": ["1"],
                "tokenIds": ["token-123"],
                "governorIds": ["gov-123"],
                "delegatesVotesCount": "1500000",
            }
        }
    }

"""Pytest configuration and fixtures for the test suite."""

import pytest
from datetime import datetime
from unittest.mock import patch

from models import (
    Proposal,
    ProposalState,
    Space,
    Vote,
)
from services.ai_service import AIService
from services.snapshot_service import SnapshotService


@pytest.fixture
def ai_service() -> AIService:
    """Create an AIService instance for testing."""
    with patch("services.ai_service.settings") as mock_settings:
        mock_settings.openrouter_api_key = "test-api-key"
        return AIService()




@pytest.fixture
def sample_proposal() -> Proposal:
    """Create a sample proposal for testing."""
    return Proposal(
        id="prop-123",
        title="Increase Treasury Allocation for Development",
        choices=["For", "Against"],
        start=1698768000,
        end=1699372800,
        state="active",
        author="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
        network="1",
        symbol="TEST",
        scores=[1000.0, 500.0],
        scores_total=1500.0,
        votes=25,
        created=1698681600,
        quorum=100.0,
        body="""
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
        """
    )


@pytest.fixture
def complex_proposal() -> Proposal:
    """Create a complex proposal for testing edge cases."""
    return Proposal(
        id="prop-456",
        title="Multi-Phase Protocol Upgrade with Governance Changes",
        choices=["For", "Against", "Abstain"],
        start=1698768000,
        end=1699372800,
        state="active",
        author="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
        network="1",
        symbol="COMPLEX",
        scores=[5000.0, 1200.0, 300.0],
        scores_total=6500.0,
        votes=150,
        created=1698681600,
        quorum=1000.0,
        body="""
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
        """
    )


# Snapshot-specific fixtures
@pytest.fixture
def snapshot_service() -> SnapshotService:
    """Create a SnapshotService instance for testing."""
    return SnapshotService()


@pytest.fixture
def sample_snapshot_space() -> Space:
    """Create a sample Snapshot space for testing."""
    return Space(
        id="arbitrumfoundation.eth",
        name="Arbitrum DAO",
        about="The official snapshot space for the Arbitrum DAO",
        network="42161",
        symbol="ARB",
        strategies=[
            {
                "name": "erc20-votes",
                "params": {
                    "symbol": "ARB",
                    "address": "0x912CE59144191C1204E64559FE8253a0e49E6548",
                    "decimals": 18
                }
            }
        ],
        admins=[],
        moderators=[],
        members=[],
        private=False,
        verified=True,
        created=1679581634,
        proposalsCount=381,
        followersCount=322117,
        votesCount=5617324
    )


@pytest.fixture
def sample_snapshot_proposal() -> Proposal:
    """Create a sample Snapshot proposal for testing."""
    return Proposal(
        id="0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671",
        title="[CONSTITUTIONAL] Register $BORING in the Arbitrum generic-custom gateway",
        body="# Disclaimer from L2BEAT\n\nThis proposal is one of several similar maintenance proposals...",
        choices=["For", "Against", "Abstain"],
        start=1752181200,
        end=1752786000,
        state="active",
        author="0x1B686eE8E31c5959D9F5BBd8122a58682788eeaD",
        network="42161",
        symbol="ARB",
        scores=[25177522.19316251, 3378.620131354955, 1851.3438606284724],
        scores_total=25182752.15715449,
        votes=2211,
        created=1752179470,
        quorum=0.0
    )


@pytest.fixture
def sample_snapshot_votes() -> list[Vote]:
    """Create sample Snapshot votes for testing."""
    return [
        Vote(
            id="0x9b92e0e63479e3fd32674c326399ef81ea61b738af665f917f1d87410b26fc89",
            voter="0xB933AEe47C438f22DE0747D57fc239FE37878Dd1",
            choice=1,
            vp=13301332.647183005,
            vp_by_strategy=[13301332.647183005],
            created=1752229989,
            reason=""
        ),
        Vote(
            id="0xcd3e06ff1d54411fbacd9673b8c12c6134a4dbc23fec04a6e55f8c037d80377c",
            voter="0xb5B069370Ef24BC67F114e185D185063CE3479f8",
            choice=1,
            vp=7174084.70601726,
            vp_by_strategy=[7174084.70601726],
            created=1752187945,
            reason=""
        )
    ]


@pytest.fixture
def mock_snapshot_space_response() -> dict:
    """Mock Snapshot API response for space query."""
    return {
        "space": {
            "id": "arbitrumfoundation.eth",
            "name": "Arbitrum DAO",
            "about": "The official snapshot space for the Arbitrum DAO",
            "network": "42161",
            "symbol": "ARB",
            "strategies": [
                {
                    "name": "erc20-votes",
                    "params": {
                        "symbol": "ARB",
                        "address": "0x912CE59144191C1204E64559FE8253a0e49E6548",
                        "decimals": 18
                    }
                }
            ],
            "admins": [],
            "moderators": [],
            "members": [],
            "private": False,
            "verified": True,
            "created": 1679581634,
            "proposalsCount": 381,
            "followersCount": 322117,
            "votesCount": 5617324
        }
    }


@pytest.fixture
def mock_snapshot_proposals_response() -> dict:
    """Mock Snapshot API response for proposals query."""
    return {
        "proposals": [
            {
                "id": "0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671",
                "title": "[CONSTITUTIONAL] Register $BORING in the Arbitrum generic-custom gateway",
                "body": "# Disclaimer from L2BEAT\n\nThis proposal is one of several similar maintenance proposals...",
                "choices": ["For", "Against", "Abstain"],
                "start": 1752181200,
                "end": 1752786000,
                "state": "active",
                "scores": [25177522.19316251, 3378.620131354955, 1851.3438606284724],
                "scores_total": 25182752.15715449,
                "votes": 2211,
                "created": 1752179470,
                "quorum": 0,
                "author": "0x1B686eE8E31c5959D9F5BBd8122a58682788eeaD",
                "network": "42161",
                "symbol": "ARB"
            }
        ]
    }


@pytest.fixture
def mock_snapshot_votes_response() -> dict:
    """Mock Snapshot API response for votes query."""
    return {
        "votes": [
            {
                "id": "0x9b92e0e63479e3fd32674c326399ef81ea61b738af665f917f1d87410b26fc89",
                "voter": "0xB933AEe47C438f22DE0747D57fc239FE37878Dd1",
                "choice": 1,
                "vp": 13301332.647183005,
                "vp_by_strategy": [13301332.647183005],
                "created": 1752229989,
                "reason": ""
            },
            {
                "id": "0xcd3e06ff1d54411fbacd9673b8c12c6134a4dbc23fec04a6e55f8c037d80377c",
                "voter": "0xb5B069370Ef24BC67F114e185D185063CE3479f8",
                "choice": 1,
                "vp": 7174084.70601726,
                "vp_by_strategy": [7174084.70601726],
                "created": 1752187945,
                "reason": ""
            }
        ]
    }

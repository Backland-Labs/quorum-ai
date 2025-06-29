"""Tests for client-side vote sorting functionality."""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from services.tally_service import TallyService
from models import (
    Proposal, 
    ProposalState, 
    ProposalFilters, 
    SortCriteria, 
    SortOrder
)


class TestVoteSorting:
    """Test cases for client-side vote sorting."""

    @pytest.fixture
    def proposals_with_different_votes(self):
        """Create proposals with different vote counts for testing sorting."""
        return [
            Proposal(
                id="prop-1",
                title="Low Vote Proposal",
                description="A proposal with low votes",
                state=ProposalState.ACTIVE,
                created_at=datetime.now(),
                start_block=1000,
                end_block=2000,
                votes_for="100",  # Total: 120
                votes_against="15",
                votes_abstain="5",
                dao_id="dao-1",
                dao_name="Test DAO",
            ),
            Proposal(
                id="prop-2", 
                title="High Vote Proposal",
                description="A proposal with high votes",
                state=ProposalState.ACTIVE,
                created_at=datetime.now(),
                start_block=1000,
                end_block=2000,
                votes_for="1000000",  # Total: 1,250,000
                votes_against="200000",
                votes_abstain="50000",
                dao_id="dao-1",
                dao_name="Test DAO",
            ),
            Proposal(
                id="prop-3",
                title="Medium Vote Proposal", 
                description="A proposal with medium votes",
                state=ProposalState.ACTIVE,
                created_at=datetime.now(),
                start_block=1000,
                end_block=2000,
                votes_for="50000",  # Total: 60,000
                votes_against="8000",
                votes_abstain="2000",
                dao_id="dao-1",
                dao_name="Test DAO",
            ),
            Proposal(
                id="prop-4",
                title="Zero Vote Proposal",
                description="A proposal with no votes",
                state=ProposalState.PENDING,
                created_at=datetime.now(),
                start_block=1000,
                end_block=2000,
                votes_for="0",  # Total: 0
                votes_against="0",
                votes_abstain="0",
                dao_id="dao-1",
                dao_name="Test DAO",
            ),
        ]

    @pytest.fixture
    def mock_proposals_response_vote_sorting(self):
        """Mock GraphQL response with vote stats for testing."""
        return {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-1",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "start": {"number": 1000},
                            "end": {"number": 2000},
                            "metadata": {
                                "title": "Low Vote Proposal",
                                "description": "A proposal with low votes"
                            },
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            "voteStats": [
                                {"type": "FOR", "votesCount": "100", "votersCount": "10", "percent": 83.33},
                                {"type": "AGAINST", "votesCount": "15", "votersCount": "2", "percent": 12.5},
                                {"type": "ABSTAIN", "votesCount": "5", "votersCount": "1", "percent": 4.17}
                            ]
                        },
                        {
                            "id": "prop-2", 
                            "status": "ACTIVE",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "start": {"number": 1000},
                            "end": {"number": 2000},
                            "metadata": {
                                "title": "High Vote Proposal",
                                "description": "A proposal with high votes"
                            },
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            "voteStats": [
                                {"type": "FOR", "votesCount": "1000000", "votersCount": "100", "percent": 80.0},
                                {"type": "AGAINST", "votesCount": "200000", "votersCount": "25", "percent": 16.0},
                                {"type": "ABSTAIN", "votesCount": "50000", "votersCount": "5", "percent": 4.0}
                            ]
                        },
                        {
                            "id": "prop-3",
                            "status": "ACTIVE", 
                            "createdAt": "2024-01-03T00:00:00Z",
                            "start": {"number": 1000},
                            "end": {"number": 2000},
                            "metadata": {
                                "title": "Medium Vote Proposal",
                                "description": "A proposal with medium votes"
                            },
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            "voteStats": [
                                {"type": "FOR", "votesCount": "50000", "votersCount": "50", "percent": 83.33},
                                {"type": "AGAINST", "votesCount": "8000", "votersCount": "8", "percent": 13.33},
                                {"type": "ABSTAIN", "votesCount": "2000", "votersCount": "2", "percent": 3.33}
                            ]
                        },
                        {
                            "id": "prop-4",
                            "status": "PENDING",
                            "createdAt": "2024-01-04T00:00:00Z", 
                            "start": {"number": 1000},
                            "end": {"number": 2000},
                            "metadata": {
                                "title": "Zero Vote Proposal",
                                "description": "A proposal with no votes"
                            },
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            "voteStats": []
                        }
                    ],
                    "pageInfo": {"lastCursor": None}
                }
            }
        }

    async def test_get_proposals_with_vote_sorting(
        self, 
        tally_service: TallyService,
        mock_proposals_response_vote_sorting: dict,
        httpx_mock
    ):
        """Test that proposals can be fetched and sorted by vote count."""
        from pytest_httpx import HTTPXMock
        httpx_mock: HTTPXMock
        
        # Mock the API response
        httpx_mock.add_response(
            method="POST",
            url="https://api.tally.xyz/query",
            json=mock_proposals_response_vote_sorting
        )
        
        # Create filters with vote count sorting
        filters = ProposalFilters(
            organization_id="test-org",
            limit=10,
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.DESC
        )
        
        # Fetch proposals
        proposals, next_cursor = await tally_service.get_proposals(filters)
        
        # Verify proposals are returned
        assert len(proposals) == 4
        assert next_cursor is None
        
        # Verify proposals are sorted by total vote count (descending)
        # Expected order: prop-2 (1,250,000), prop-3 (60,000), prop-1 (120), prop-4 (0)
        assert proposals[0].id == "prop-2"  # Highest votes
        assert proposals[1].id == "prop-3"  # Medium votes
        assert proposals[2].id == "prop-1"  # Low votes
        assert proposals[3].id == "prop-4"  # Zero votes
        
        # Verify vote counts are calculated correctly
        prop_high_votes = proposals[0]
        total_votes_high = int(prop_high_votes.votes_for) + int(prop_high_votes.votes_against) + int(prop_high_votes.votes_abstain)
        assert total_votes_high == 1250000
        
        prop_medium_votes = proposals[1]
        total_votes_medium = int(prop_medium_votes.votes_for) + int(prop_medium_votes.votes_against) + int(prop_medium_votes.votes_abstain)
        assert total_votes_medium == 60000

    async def test_get_proposals_with_vote_sorting_ascending(
        self,
        tally_service: TallyService, 
        mock_proposals_response_vote_sorting: dict,
        httpx_mock
    ):
        """Test that proposals can be sorted by vote count in ascending order."""
        from pytest_httpx import HTTPXMock
        httpx_mock: HTTPXMock
        
        # Mock the API response
        httpx_mock.add_response(
            method="POST",
            url="https://api.tally.xyz/query",
            json=mock_proposals_response_vote_sorting
        )
        
        # Create filters with vote count sorting (ascending)
        filters = ProposalFilters(
            organization_id="test-org",
            limit=10,
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.ASC
        )
        
        # Fetch proposals
        proposals, _ = await tally_service.get_proposals(filters)
        
        # Verify proposals are sorted by total vote count (ascending)
        # Expected order: prop-4 (0), prop-1 (120), prop-3 (60,000), prop-2 (1,250,000)
        assert proposals[0].id == "prop-4"  # Zero votes
        assert proposals[1].id == "prop-1"  # Low votes
        assert proposals[2].id == "prop-3"  # Medium votes
        assert proposals[3].id == "prop-2"  # Highest votes

    async def test_get_proposals_with_vote_sorting_limited(
        self,
        tally_service: TallyService,
        mock_proposals_response_vote_sorting: dict,
        httpx_mock
    ):
        """Test that vote sorting respects limit parameter for 'top N' functionality."""
        from pytest_httpx import HTTPXMock
        httpx_mock: HTTPXMock
        
        # Mock the API response
        httpx_mock.add_response(
            method="POST",
            url="https://api.tally.xyz/query",
            json=mock_proposals_response_vote_sorting
        )
        
        # Create filters for top 2 proposals by vote count
        filters = ProposalFilters(
            organization_id="test-org",
            limit=2,
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.DESC
        )
        
        # Fetch proposals  
        proposals, _ = await tally_service.get_proposals(filters)
        
        # Should return exactly 2 proposals (the top 2 by votes)
        assert len(proposals) == 2
        assert proposals[0].id == "prop-2"  # Highest votes
        assert proposals[1].id == "prop-3"  # Second highest votes

    async def test_get_proposals_vote_sorting_with_created_date_fallback(
        self,
        tally_service: TallyService,
        mock_proposals_response_vote_sorting: dict,
        httpx_mock
    ):
        """Test that when vote counts are equal, proposals are sorted by created date."""
        from pytest_httpx import HTTPXMock
        httpx_mock: HTTPXMock
        
        # Create mock response with equal vote counts
        equal_votes_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-1",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",  # Older
                            "start": {"number": 1000},
                            "end": {"number": 2000},
                            "metadata": {"title": "Older Proposal", "description": "Older"},
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            "voteStats": [
                                {"type": "FOR", "votesCount": "1000", "votersCount": "10", "percent": 100.0}
                            ]
                        },
                        {
                            "id": "prop-2",
                            "status": "ACTIVE", 
                            "createdAt": "2024-01-02T00:00:00Z",  # Newer
                            "start": {"number": 1000},
                            "end": {"number": 2000},
                            "metadata": {"title": "Newer Proposal", "description": "Newer"},
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            "voteStats": [
                                {"type": "FOR", "votesCount": "1000", "votersCount": "10", "percent": 100.0}
                            ]
                        }
                    ],
                    "pageInfo": {"lastCursor": None}
                }
            }
        }
        
        httpx_mock.add_response(
            method="POST",
            url="https://api.tally.xyz/query",
            json=equal_votes_response
        )
        
        filters = ProposalFilters(
            organization_id="test-org",
            limit=10,
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.DESC
        )
        
        proposals, _ = await tally_service.get_proposals(filters)
        
        # When votes are equal, should fall back to creation date (newer first for DESC)
        assert len(proposals) == 2
        assert proposals[0].id == "prop-2"  # Newer proposal first
        assert proposals[1].id == "prop-1"  # Older proposal second

    def test_calculate_total_votes_utility_function(self, proposals_with_different_votes):
        """Test utility function for calculating total votes from a proposal."""
        proposals = proposals_with_different_votes
        
        # Test calculation for different proposals
        def calculate_total_votes(proposal: Proposal) -> int:
            return int(proposal.votes_for) + int(proposal.votes_against) + int(proposal.votes_abstain)
        
        assert calculate_total_votes(proposals[0]) == 120  # Low vote proposal
        assert calculate_total_votes(proposals[1]) == 1250000  # High vote proposal
        assert calculate_total_votes(proposals[2]) == 60000  # Medium vote proposal
        assert calculate_total_votes(proposals[3]) == 0  # Zero vote proposal

    async def test_get_proposals_handles_missing_vote_stats(
        self,
        tally_service: TallyService,
        httpx_mock
    ):
        """Test that proposals with missing vote stats are handled gracefully."""
        from pytest_httpx import HTTPXMock
        httpx_mock: HTTPXMock
        
        # Mock response with missing vote stats
        response_missing_votes = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-1",
                            "status": "PENDING",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "start": {"number": 1000},
                            "end": {"number": 2000}, 
                            "metadata": {"title": "No Vote Stats", "description": "Missing vote stats"},
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            "voteStats": []  # Empty vote stats
                        }
                    ],
                    "pageInfo": {"lastCursor": None}
                }
            }
        }
        
        httpx_mock.add_response(
            method="POST",
            url="https://api.tally.xyz/query",
            json=response_missing_votes
        )
        
        filters = ProposalFilters(
            organization_id="test-org",
            sort_by=SortCriteria.VOTE_COUNT
        )
        
        proposals, _ = await tally_service.get_proposals(filters)
        
        # Should handle missing vote stats gracefully
        assert len(proposals) == 1
        proposal = proposals[0]
        assert proposal.votes_for == "0"
        assert proposal.votes_against == "0" 
        assert proposal.votes_abstain == "0"
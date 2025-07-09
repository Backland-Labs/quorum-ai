"""Tests for TallyService."""

import pytest
from datetime import datetime
from unittest.mock import patch
import httpx
from pytest_httpx import HTTPXMock

from services.tally_service import TallyService
from models import (
    ProposalFilters,
    ProposalState,
    ProposalVoter,
    SortCriteria,
    SortOrder,
    VoteType,
)
from config import settings


class TestTallyService:
    """Test cases for TallyService."""


class TestTallyServiceInitialization:
    """Test TallyService initialization."""

    def test_tally_service_initialization_uses_settings(self) -> None:
        """Test that TallyService initialization uses configuration settings."""
        service = TallyService()

        assert service.base_url == settings.tally_api_base_url
        assert service.api_key == settings.tally_api_key
        assert service.timeout == settings.request_timeout


class TestTallyServiceGetDAOs:
    """Test TallyService get_daos method."""

    async def test_get_daos_success(
        self,
        tally_service: TallyService,
        mock_dao_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful DAO fetching."""
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=mock_dao_response
        )

        daos, next_cursor = await tally_service.get_daos(
            organization_id="org-1", limit=10
        )

        assert len(daos) == 2
        assert next_cursor is None  # No cursor in mock response

        dao1 = daos[0]
        assert dao1.id == "dao-1"
        assert dao1.name == "Test DAO 1"
        assert dao1.description == "A test DAO"
        assert dao1.total_proposals_count == 10
        assert dao1.active_proposals_count == 3
        assert dao1.organization_id == "org-1"

        dao2 = daos[1]
        assert dao2.id == "dao-2"
        assert dao2.description is None
        assert dao2.organization_id == "org-2"

    async def test_get_daos_with_api_key(
        self, mock_dao_response: dict, httpx_mock: HTTPXMock
    ) -> None:
        """Test DAO fetching with API key."""
        with patch.object(settings, "tally_api_key", "test-api-key"):
            service = TallyService()

            def check_headers(request):
                assert request.headers.get("Api-Key") == "test-api-key"
                return httpx.Response(200, json=mock_dao_response)

            httpx_mock.add_callback(check_headers)

            await service.get_daos(organization_id="org-test")

    async def test_get_daos_network_error(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test DAO fetching with network error."""
        httpx_mock.add_exception(httpx.RequestError("Network error"))

        with pytest.raises(httpx.RequestError):
            await tally_service.get_daos(organization_id="org-test")

    async def test_get_daos_http_error(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test DAO fetching with HTTP error."""
        httpx_mock.add_response(status_code=500)

        with pytest.raises(httpx.HTTPStatusError):
            await tally_service.get_daos(organization_id="org-test")


class TestTallyServiceGetDAOById:
    """Test TallyService get_dao_by_id method."""

    async def test_get_dao_by_id_success(
        self,
        tally_service: TallyService,
        mock_single_dao_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful DAO fetching by ID."""
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_single_dao_response,
        )

        dao = await tally_service.get_dao_by_id("dao-1")

        assert dao is not None
        assert dao.id == "dao-1"
        assert dao.name == "Test DAO"
        assert dao.description == "A test DAO"

    async def test_get_dao_by_id_not_found(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test DAO fetching when DAO not found."""
        response_data = {"data": {"dao": None}}
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=response_data
        )

        dao = await tally_service.get_dao_by_id("nonexistent-dao")

        assert dao is None


class TestTallyServiceGetProposals:
    """Test TallyService get_proposals method."""

    async def test_get_proposals_success(
        self,
        tally_service: TallyService,
        mock_proposals_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful proposals fetching."""
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=mock_proposals_response
        )

        filters = ProposalFilters(limit=20, organization_id="org-1")
        proposals, next_cursor = await tally_service.get_proposals(filters)

        assert len(proposals) == 2
        assert next_cursor is None  # No cursor in mock response

        prop1 = proposals[0]
        assert prop1.id == "prop-1"
        assert prop1.title == "Test Proposal 1"
        assert prop1.state == ProposalState.ACTIVE
        assert prop1.votes_for == "1000000"  # Now we parse vote counts from voteStats
        assert prop1.votes_against == "250000"
        assert prop1.votes_abstain == "50000"
        assert prop1.dao_id == "dao-1"

    async def test_get_proposals_with_filters(
        self,
        tally_service: TallyService,
        mock_proposals_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test proposals fetching with filters."""

        def check_query(request):
            body = request.content.decode()
            # Should contain the DAO filter (using governorId in new API)
            assert '"governorId":"dao-1"' in body or '"governorId": "dao-1"' in body
            return httpx.Response(200, json=mock_proposals_response)

        httpx_mock.add_callback(check_query)

        filters = ProposalFilters(
            dao_id="dao-1",
            state=ProposalState.ACTIVE,
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.ASC,
        )

        await tally_service.get_proposals(filters)

    async def test_get_proposals_with_vote_count_sorting(
        self,
        tally_service: TallyService,
        mock_proposals_with_vote_counts_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test proposals fetching with vote count sorting."""
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_proposals_with_vote_counts_response,
        )

        filters = ProposalFilters(
            organization_id="org-1",
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.DESC,
            limit=3,
        )

        proposals, next_cursor = await tally_service.get_proposals(filters)

        assert len(proposals) == 3
        assert next_cursor is None

        # Check that proposals have vote data populated
        prop_high = proposals[0]
        assert prop_high.id == "prop-high-votes"
        assert prop_high.votes_for == "5000000"
        assert prop_high.votes_against == "500000"
        assert prop_high.votes_abstain == "100000"

        prop_medium = proposals[1]
        assert prop_medium.id == "prop-medium-votes"
        assert prop_medium.votes_for == "2000000"

        prop_low = proposals[2]
        assert prop_low.id == "prop-low-votes"
        assert prop_low.votes_for == "100000"

    async def test_get_proposals_vote_stats_parsing(
        self,
        tally_service: TallyService,
        mock_proposals_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that voteStats are correctly parsed into vote fields."""
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=mock_proposals_response
        )

        filters = ProposalFilters(organization_id="org-1")
        proposals, _ = await tally_service.get_proposals(filters)

        # Check first proposal vote stats
        prop1 = proposals[0]
        assert prop1.votes_for == "1000000"
        assert prop1.votes_against == "250000"
        assert prop1.votes_abstain == "50000"

        # Check second proposal vote stats
        prop2 = proposals[1]
        assert prop2.votes_for == "2000000"
        assert prop2.votes_against == "100000"
        assert prop2.votes_abstain == "25000"

    async def test_get_proposals_missing_vote_stats(
        self,
        tally_service: TallyService,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test handling of proposals without voteStats."""
        response_without_votes = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-no-votes",
                            "status": "PENDING",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "metadata": {
                                "title": "No Votes Proposal",
                                "description": "This proposal has no votes yet",
                            },
                            "governor": {"id": "dao-1", "name": "Test DAO"},
                            # No voteStats field
                        },
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }

        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=response_without_votes
        )

        filters = ProposalFilters(organization_id="org-1")
        proposals, _ = await tally_service.get_proposals(filters)

        assert len(proposals) == 1
        prop = proposals[0]
        assert prop.id == "prop-no-votes"
        # Should default to "0" when no vote stats available
        assert prop.votes_for == "0"
        assert prop.votes_against == "0"
        assert prop.votes_abstain == "0"

    async def test_get_proposals_datetime_parsing(
        self,
        tally_service: TallyService,
        mock_proposals_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that proposal datetime fields are correctly parsed."""
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=mock_proposals_response
        )

        filters = ProposalFilters(organization_id="org-1")
        proposals, _ = await tally_service.get_proposals(filters)

        # Compare just the date/time parts (ignoring timezone)
        assert proposals[0].created_at.replace(tzinfo=None) == datetime(
            2024, 1, 1, 0, 0, 0
        )
        assert proposals[1].created_at.replace(tzinfo=None) == datetime(
            2024, 1, 2, 0, 0, 0
        )


class TestTallyServiceGetProposalById:
    """Test TallyService get_proposal_by_id method."""

    async def test_get_proposal_by_id_success(
        self,
        tally_service: TallyService,
        mock_single_proposal_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful proposal fetching by ID."""
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_single_proposal_response,
        )

        proposal = await tally_service.get_proposal_by_id("prop-1")

        assert proposal is not None
        assert proposal.id == "prop-1"
        assert proposal.title == "Test Proposal"
        assert proposal.state == ProposalState.ACTIVE
        assert proposal.url == "https://www.tally.xyz/gov/dao-1/proposal/prop-1"

    async def test_get_proposal_by_id_not_found(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test proposal fetching when proposal not found."""
        response_data = {"data": {"proposal": None}}
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=response_data
        )

        proposal = await tally_service.get_proposal_by_id("nonexistent-prop")

        assert proposal is None


class TestTallyServiceGetMultipleProposals:
    """Test TallyService get_multiple_proposals method."""

    async def test_get_multiple_proposals_success(
        self,
        tally_service: TallyService,
        mock_single_proposal_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful fetching of multiple proposals."""
        # Mock responses for multiple proposal requests
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_single_proposal_response,
        )
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json={
                "data": {
                    "proposal": {
                        "id": "prop-2",
                        "status": "SUCCEEDED",
                        "createdAt": "2024-01-02T00:00:00Z",
                        "metadata": {
                            "title": "Test Proposal 2",
                            "description": "Test description 2",
                        },
                        "governor": {"id": "dao-1", "name": "Test DAO"},
                    }
                }
            },
        )

        proposals = await tally_service.get_multiple_proposals(["prop-1", "prop-2"])

        assert len(proposals) == 2
        assert proposals[0].id == "prop-1"
        assert proposals[1].id == "prop-2"

    async def test_get_multiple_proposals_with_failures(
        self,
        tally_service: TallyService,
        mock_single_proposal_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test fetching multiple proposals with some failures."""
        # First request succeeds
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_single_proposal_response,
        )
        # Second request fails
        httpx_mock.add_exception(httpx.RequestError("Network error"))

        with patch("logfire.error") as mock_error:
            proposals = await tally_service.get_multiple_proposals(["prop-1", "prop-2"])

            # Should return only the successful proposal
            assert len(proposals) == 1
            assert proposals[0].id == "prop-1"

            # Should log the error (may be called multiple times due to retries)
            assert mock_error.call_count >= 1

    async def test_get_multiple_proposals_empty_list(
        self, tally_service: TallyService
    ) -> None:
        """Test fetching multiple proposals with empty list."""
        proposals = await tally_service.get_multiple_proposals([])

        assert len(proposals) == 0


class TestTallyServiceGetOrganizationOverview:
    """Test TallyService get_organization_overview method."""

    async def test_get_organization_overview_success(
        self,
        tally_service: TallyService,
        mock_organization_overview_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful organization overview fetching."""
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_organization_overview_response,
        )

        overview = await tally_service.get_organization_overview("org-123")

        assert overview is not None
        assert overview["organization_id"] == "org-123"
        assert overview["organization_name"] == "Test DAO"
        assert overview["delegate_count"] == 150
        assert overview["token_holder_count"] == 1000
        assert overview["total_proposals_count"] == 50

    async def test_get_organization_overview_not_found(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test organization overview fetching when organization not found."""
        response_data = {"data": {"organization": None}}
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=response_data
        )

        overview = await tally_service.get_organization_overview("nonexistent-org")

        assert overview is None

    async def test_get_organization_overview_network_error(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test organization overview fetching with network error."""
        httpx_mock.add_exception(httpx.RequestError("Network error"))

        with pytest.raises(httpx.RequestError):
            await tally_service.get_organization_overview("org-123")

    async def test_get_organization_overview_http_error(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test organization overview fetching with HTTP error."""
        httpx_mock.add_response(status_code=500)

        with pytest.raises(httpx.HTTPStatusError):
            await tally_service.get_organization_overview("org-123")


class TestTallyServiceGetProposalVotes:
    """Test TallyService get_proposal_votes method."""

    async def test_get_proposal_votes_basic_functionality(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test basic get_proposal_votes functionality returns ProposalVoter objects."""
        # Mock the API response
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json={"data": {"votes": {"nodes": []}}},
        )

        proposal_id = "prop-123"
        limit = 5

        voters = await tally_service.get_proposal_votes(proposal_id, limit)

        assert isinstance(voters, list)
        assert len(voters) <= limit

    async def test_get_proposal_votes_graphql_query_structure(
        self,
        tally_service: TallyService,
        mock_proposal_votes_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that get_proposal_votes uses correct GraphQL query structure."""
        proposal_id = "prop-123"
        limit = 10

        def check_graphql_query(request):
            """Verify the GraphQL query structure matches specification."""
            body = request.content.decode()

            # Should contain the GetProposalVotes query
            assert "GetProposalVotes" in body
            assert "votes(input: $input)" in body
            assert '"amount"' in body or "amount" in body
            assert '"type"' in body or "type" in body
            assert '"voter"' in body or "voter" in body
            assert '"address"' in body or "address" in body

            # Should contain variables with proposal ID and limit
            assert (
                f'"proposalId":"{proposal_id}"' in body
                or f'"proposalId": "{proposal_id}"' in body
            )
            assert f'"limit":{limit}' in body or f'"limit": {limit}' in body

            return httpx.Response(200, json=mock_proposal_votes_response)

        httpx_mock.add_callback(check_graphql_query)

        await tally_service.get_proposal_votes(proposal_id, limit)


class TestTallyServiceGetProposalsByGovernorIds:
    """Test TallyService get_proposals_by_governor_ids method."""

    async def test_get_proposals_by_governor_ids_single_governor(
        self,
        tally_service: TallyService,
        mock_proposals_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test proposals fetching with single governor ID."""
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=mock_proposals_response
        )

        governor_ids = ["gov-1"]
        proposals = await tally_service.get_proposals_by_governor_ids(governor_ids)

        assert len(proposals) == 2
        assert proposals[0].id == "prop-1"
        assert proposals[1].id == "prop-2"

    async def test_get_proposals_by_governor_ids_multiple_governors(
        self,
        tally_service: TallyService,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test proposals fetching with multiple governor IDs."""
        # Mock response for first governor
        first_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-1",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "metadata": {"title": "Proposal 1", "description": "Test"},
                            "governor": {"id": "gov-1", "name": "DAO 1"},
                            "voteStats": [],
                        }
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }
        
        # Mock response for second governor
        second_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-2",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "metadata": {"title": "Proposal 2", "description": "Test"},
                            "governor": {"id": "gov-2", "name": "DAO 2"},
                            "voteStats": [],
                        }
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }

        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=first_response
        )
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=second_response
        )

        governor_ids = ["gov-1", "gov-2"]
        proposals = await tally_service.get_proposals_by_governor_ids(governor_ids)

        assert len(proposals) == 2
        assert proposals[0].id == "prop-1"
        assert proposals[1].id == "prop-2"

    async def test_get_proposals_by_governor_ids_deduplication(
        self,
        tally_service: TallyService,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test proposal deduplication when same proposal appears in multiple governors."""
        # Mock response for first governor with duplicate proposal
        first_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-duplicate",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "metadata": {"title": "Duplicate Proposal", "description": "Test"},
                            "governor": {"id": "gov-1", "name": "DAO 1"},
                            "voteStats": [],
                        },
                        {
                            "id": "prop-unique-1",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "metadata": {"title": "Unique Proposal 1", "description": "Test"},
                            "governor": {"id": "gov-1", "name": "DAO 1"},
                            "voteStats": [],
                        }
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }
        
        # Mock response for second governor with same duplicate proposal
        second_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-duplicate",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "metadata": {"title": "Duplicate Proposal", "description": "Test"},
                            "governor": {"id": "gov-2", "name": "DAO 2"},
                            "voteStats": [],
                        },
                        {
                            "id": "prop-unique-2",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-03T00:00:00Z",
                            "metadata": {"title": "Unique Proposal 2", "description": "Test"},
                            "governor": {"id": "gov-2", "name": "DAO 2"},
                            "voteStats": [],
                        }
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }

        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=first_response
        )
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=second_response
        )

        governor_ids = ["gov-1", "gov-2"]
        proposals = await tally_service.get_proposals_by_governor_ids(governor_ids)

        # Should have 3 unique proposals (prop-duplicate, prop-unique-1, prop-unique-2)
        assert len(proposals) == 3
        proposal_ids = [p.id for p in proposals]
        assert "prop-duplicate" in proposal_ids
        assert "prop-unique-1" in proposal_ids
        assert "prop-unique-2" in proposal_ids
        
        # Ensure no duplicates
        assert len(set(proposal_ids)) == 3

    async def test_get_proposals_by_governor_ids_partial_failures(
        self,
        tally_service: TallyService,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test graceful handling when some governor requests fail."""
        # Mock successful response for first governor
        success_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-success",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "metadata": {"title": "Success Proposal", "description": "Test"},
                            "governor": {"id": "gov-success", "name": "Success DAO"},
                            "voteStats": [],
                        }
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }

        # First request succeeds
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=success_response
        )
        
        # Second request fails with network error
        httpx_mock.add_exception(httpx.RequestError("Network timeout"))

        governor_ids = ["gov-success", "gov-failure"]
        proposals = await tally_service.get_proposals_by_governor_ids(governor_ids)

        # Should return proposals from successful request only
        assert len(proposals) == 1
        assert proposals[0].id == "prop-success"
        assert proposals[0].dao_id == "gov-success"

    async def test_get_proposals_by_governor_ids_all_failures(
        self,
        tally_service: TallyService,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test handling when all governor requests fail."""
        # Both requests fail
        httpx_mock.add_exception(httpx.RequestError("Network timeout"))
        httpx_mock.add_response(status_code=500)

        governor_ids = ["gov-fail-1", "gov-fail-2"]
        proposals = await tally_service.get_proposals_by_governor_ids(governor_ids)

        # Should return empty list when all requests fail
        assert len(proposals) == 0

    async def test_get_proposals_by_governor_ids_active_only_filter(
        self,
        tally_service: TallyService,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test active-only filtering in governor proposals fetching."""
        # Mock response with mixed proposal states
        mixed_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-active",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "metadata": {"title": "Active Proposal", "description": "Test"},
                            "governor": {"id": "gov-1", "name": "DAO 1"},
                            "voteStats": [],
                        },
                        {
                            "id": "prop-succeeded",
                            "status": "SUCCEEDED",
                            "createdAt": "2024-01-02T00:00:00Z",
                            "metadata": {"title": "Succeeded Proposal", "description": "Test"},
                            "governor": {"id": "gov-1", "name": "DAO 1"},
                            "voteStats": [],
                        }
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }

        def check_active_filter(request):
            body = request.content.decode()
            # Should contain ACTIVE state filter
            assert '"state":"ACTIVE"' in body or '"state": "ACTIVE"' in body
            return httpx.Response(200, json=mixed_response)

        httpx_mock.add_callback(check_active_filter)

        governor_ids = ["gov-1"]
        proposals = await tally_service.get_proposals_by_governor_ids(
            governor_ids, active_only=True
        )

        # Should only return active proposals
        assert len(proposals) == 2  # Both proposals in response since we filtered at API level
        # But in real scenario, API would only return ACTIVE proposals


class TestTallyServiceGetProposalsByOrganizationGovernors:
    """Test TallyService get_proposals_by_organization_governors method."""

    async def test_get_proposals_by_organization_governors_success(
        self,
        tally_service: TallyService,
        mock_proposals_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test successful proposals fetching by organization ID."""
        httpx_mock.add_response(
            method="POST", url=settings.tally_api_base_url, json=mock_proposals_response
        )

        organization_id = "org-123"
        proposals = await tally_service.get_proposals_by_organization_governors(organization_id)

        assert len(proposals) == 2
        assert proposals[0].id == "prop-1"
        assert proposals[1].id == "prop-2"

    async def test_get_proposals_by_organization_governors_with_limit(
        self,
        tally_service: TallyService,
        mock_proposals_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test proposals fetching by organization ID with custom limit."""
        def check_limit(request):
            body = request.content.decode()
            # Should contain the custom limit
            assert '"limit":10' in body or '"limit": 10' in body
            return httpx.Response(200, json=mock_proposals_response)

        httpx_mock.add_callback(check_limit)

        organization_id = "org-123"
        limit = 10
        proposals = await tally_service.get_proposals_by_organization_governors(
            organization_id, limit=limit
        )

        assert len(proposals) == 2

    async def test_get_proposals_by_organization_governors_active_only(
        self,
        tally_service: TallyService,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test active-only filtering in organization governors fetching."""
        active_response = {
            "data": {
                "proposals": {
                    "nodes": [
                        {
                            "id": "prop-active-org",
                            "status": "ACTIVE",
                            "createdAt": "2024-01-01T00:00:00Z",
                            "metadata": {"title": "Active Org Proposal", "description": "Test"},
                            "governor": {"id": "gov-org", "name": "Org DAO"},
                            "voteStats": [],
                        }
                    ],
                    "pageInfo": {"lastCursor": None},
                }
            }
        }

        def check_organization_active_filter(request):
            body = request.content.decode()
            # Should contain both organization filter and ACTIVE state filter
            assert '"organizationId":"org-123"' in body or '"organizationId": "org-123"' in body
            assert '"state":"ACTIVE"' in body or '"state": "ACTIVE"' in body
            return httpx.Response(200, json=active_response)

        httpx_mock.add_callback(check_organization_active_filter)

        organization_id = "org-123"
        proposals = await tally_service.get_proposals_by_organization_governors(
            organization_id, active_only=True
        )

        assert len(proposals) == 1
        assert proposals[0].id == "prop-active-org"


class TestTallyServiceHasVoted:
    """Test TallyService has_voted method."""

    async def test_has_voted_returns_true_when_vote_exists(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test has_voted returns True when voter has cast a vote on proposal."""
        mock_response = {
            "data": {
                "votes": {
                    "nodes": [
                        {
                            "id": "vote-123"
                        }
                    ],
                    "pageInfo": {
                        "count": 1
                    }
                }
            }
        }
        
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_response,
        )

        result = await tally_service.has_voted("prop-123", "0x1234567890abcdef")

        assert result is True

    async def test_has_voted_returns_false_when_no_vote_exists(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test has_voted returns False when voter has not cast a vote on proposal."""
        mock_response = {
            "data": {
                "votes": {
                    "nodes": [],
                    "pageInfo": {
                        "count": 0
                    }
                }
            }
        }
        
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_response,
        )

        result = await tally_service.has_voted("prop-123", "0x1234567890abcdef")

        assert result is False

    async def test_has_voted_handles_api_errors_gracefully(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test has_voted handles GraphQL API errors gracefully and returns False."""
        # Mock a network error
        httpx_mock.add_exception(httpx.RequestError("Network error"))

        # Should return False and not raise exception
        result = await tally_service.has_voted("prop-123", "0x1234567890abcdef")

        assert result is False

    async def test_has_voted_handles_both_vote_types(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test has_voted correctly handles both OnchainVote and VetoVote types."""
        # Test with OnchainVote
        onchain_response = {
            "data": {
                "votes": {
                    "nodes": [
                        {
                            "id": "onchain-vote-123"
                        }
                    ],
                    "pageInfo": {
                        "count": 1
                    }
                }
            }
        }
        
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=onchain_response,
        )

        result = await tally_service.has_voted("prop-123", "0x1234567890abcdef")
        assert result is True

        # Test with VetoVote
        veto_response = {
            "data": {
                "votes": {
                    "nodes": [
                        {
                            "id": "veto-vote-456"
                        }
                    ],
                    "pageInfo": {
                        "count": 1
                    }
                }
            }
        }
        
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=veto_response,
        )

        result = await tally_service.has_voted("prop-456", "0x1234567890abcdef")
        assert result is True


    async def test_get_proposal_votes_data_transformation(
        self,
        tally_service: TallyService,
        mock_proposal_votes_response: dict,
        httpx_mock: HTTPXMock,
    ) -> None:
        """Test that API response is correctly transformed to ProposalVoter objects."""
        httpx_mock.add_response(
            method="POST",
            url=settings.tally_api_base_url,
            json=mock_proposal_votes_response,
        )

        proposal_id = "prop-123"
        voters = await tally_service.get_proposal_votes(proposal_id, 10)

        assert len(voters) == 3

        # Check first voter (highest amount)
        voter1 = voters[0]
        assert isinstance(voter1, ProposalVoter)
        assert voter1.address == "0x123...abc"
        assert voter1.amount == "1000000"
        assert voter1.vote_type == VoteType.FOR

        # Check second voter
        voter2 = voters[1]
        assert voter2.address == "0x456...def"
        assert voter2.amount == "750000"
        assert voter2.vote_type == VoteType.FOR

        # Check third voter (different vote type)
        voter3 = voters[2]
        assert voter3.address == "0x789...ghi"
        assert voter3.amount == "500000"
        assert voter3.vote_type == VoteType.AGAINST


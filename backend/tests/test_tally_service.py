"""Tests for TallyService."""

import pytest
from datetime import datetime
from unittest.mock import patch
import httpx
from pytest_httpx import HTTPXMock

from services.tally_service import TallyService
from models import ProposalFilters, ProposalState, SortCriteria, SortOrder
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

        daos = await tally_service.get_daos(limit=10, offset=0)

        assert len(daos) == 2

        dao1 = daos[0]
        assert dao1.id == "dao-1"
        assert dao1.name == "Test DAO 1"
        assert dao1.description == "A test DAO"
        assert dao1.total_proposals_count == 10
        assert dao1.active_proposals_count == 3

        dao2 = daos[1]
        assert dao2.id == "dao-2"
        assert dao2.description is None

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

            await service.get_daos()

    async def test_get_daos_network_error(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test DAO fetching with network error."""
        httpx_mock.add_exception(httpx.RequestError("Network error"))

        with pytest.raises(httpx.RequestError):
            await tally_service.get_daos()

    async def test_get_daos_http_error(
        self, tally_service: TallyService, httpx_mock: HTTPXMock
    ) -> None:
        """Test DAO fetching with HTTP error."""
        httpx_mock.add_response(status_code=500)

        with pytest.raises(httpx.HTTPStatusError):
            await tally_service.get_daos()


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

        filters = ProposalFilters(limit=20, offset=0)
        proposals, total_count = await tally_service.get_proposals(filters)

        assert len(proposals) == 2
        assert total_count == 2

        prop1 = proposals[0]
        assert prop1.id == "prop-1"
        assert prop1.title == "Test Proposal 1"
        assert prop1.state == ProposalState.ACTIVE
        assert prop1.votes_for == "100"
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
            # Should contain the DAO filter
            assert 'daoIds: ["dao-1"]' in body
            # Should contain the state filter
            assert "states: [ACTIVE]" in body
            return httpx.Response(200, json=mock_proposals_response)

        httpx_mock.add_callback(check_query)

        filters = ProposalFilters(
            dao_id="dao-1",
            state=ProposalState.ACTIVE,
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.ASC,
        )

        await tally_service.get_proposals(filters)

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

        filters = ProposalFilters()
        proposals, _ = await tally_service.get_proposals(filters)

        assert proposals[0].created_at == datetime(2024, 1, 1, 0, 0, 0)
        assert proposals[1].created_at == datetime(2024, 1, 2, 0, 0, 0)


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
                        "title": "Test Proposal 2",
                        "description": "Test description 2",
                        "state": "SUCCEEDED",
                        "createdAt": "2024-01-02T00:00:00Z",
                        "startBlock": 2000,
                        "endBlock": 3000,
                        "votesFor": "200",
                        "votesAgainst": "25",
                        "votesAbstain": "5",
                        "dao": {"id": "dao-1", "name": "Test DAO"},
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

            # Should log the error
            mock_error.assert_called_once()

    async def test_get_multiple_proposals_empty_list(
        self, tally_service: TallyService
    ) -> None:
        """Test fetching multiple proposals with empty list."""
        proposals = await tally_service.get_multiple_proposals([])

        assert len(proposals) == 0

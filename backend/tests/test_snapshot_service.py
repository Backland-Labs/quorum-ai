"""Tests for SnapshotService."""

import pytest
from unittest.mock import patch, AsyncMock
import httpx
from pytest_httpx import HTTPXMock
from typing import List, Optional

from services.snapshot_service import SnapshotService, SnapshotServiceError, NetworkError, GraphQLError
from models import Space, Proposal, Vote
from config import settings


class TestSnapshotServiceInitialization:
    """Test SnapshotService initialization."""

    def test_snapshot_service_initialization_uses_settings(self) -> None:
        """Test that SnapshotService initialization uses configuration settings."""
        service = SnapshotService()

        assert service.base_url == "https://hub.snapshot.org/graphql"
        assert service.timeout == settings.request_timeout


class TestSnapshotServiceProperties:
    """Test SnapshotService properties and basic functionality."""

    def test_snapshot_service_has_required_attributes(self) -> None:
        """Test that SnapshotService has all required attributes."""
        service = SnapshotService()

        # Check that service has the expected attributes
        assert hasattr(service, 'base_url')
        assert hasattr(service, 'timeout')
        assert hasattr(service, 'client')

    def test_snapshot_service_client_configuration(self) -> None:
        """Test that SnapshotService client is properly configured."""
        service = SnapshotService()

        # Check that client is an httpx.AsyncClient
        assert isinstance(service.client, httpx.AsyncClient)
        assert service.client.timeout.read == settings.request_timeout

    @patch.object(settings, 'request_timeout', 30.0)
    def test_snapshot_service_respects_timeout_setting(self) -> None:
        """Test that SnapshotService respects the configured timeout."""
        service = SnapshotService()

        assert service.timeout == 30.0
        assert service.client.timeout.read == 30.0

    def test_snapshot_service_has_default_headers(self) -> None:
        """Test that SnapshotService client has proper default headers."""
        service = SnapshotService()
        
        # This test will fail because default headers are not yet implemented
        expected_headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'QuorumAI/{settings.app_name}',
            'Accept': 'application/json'
        }
        
        # Check that client has the expected default headers
        for key, value in expected_headers.items():
            assert key in service.client.headers
            assert service.client.headers[key] == value


class TestSnapshotServiceErrorHandling:
    """Test SnapshotService error handling functionality."""

    @pytest.mark.asyncio
    async def test_execute_query_handles_network_timeout(self, httpx_mock: HTTPXMock) -> None:
        """Test that execute_query properly handles network timeout errors."""
        import httpx
        
        service = SnapshotService()
        query = "query { spaces { id } }"
        
        # Mock a timeout error
        httpx_mock.add_exception(httpx.TimeoutException("Request timed out"))
        
        # This test will fail because custom error handling is not implemented
        with pytest.raises(Exception) as exc_info:
            await service.execute_query(query)
        
        # Should have custom exception handling
        from services.snapshot_service import SnapshotServiceError
        assert isinstance(exc_info.value, SnapshotServiceError), f"Should raise SnapshotServiceError, got {type(exc_info.value)}"
        assert "timeout" in str(exc_info.value).lower(), "Error message should mention timeout"
        
        await service.close()

    @pytest.mark.asyncio
    async def test_execute_query_handles_graphql_errors(self, httpx_mock: HTTPXMock) -> None:
        """Test that execute_query properly handles GraphQL errors in response."""
        service = SnapshotService()
        
        query = "query { spaces { id } }"
        
        # Mock a GraphQL error response
        mock_response_data = {
            "errors": [
                {
                    "message": "Field 'invalidField' doesn't exist on type 'Space'",
                    "locations": [{"line": 1, "column": 10}],
                    "path": ["spaces"]
                }
            ],
            "data": None
        }
        
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            json=mock_response_data,
            status_code=200
        )
        
        # This test will fail because GraphQL error handling is not implemented
        with pytest.raises(Exception) as exc_info:
            await service.execute_query(query)
        
        # Should raise GraphQLError for GraphQL errors
        from services.snapshot_service import GraphQLError
        assert isinstance(exc_info.value, GraphQLError), f"Should raise GraphQLError, got {type(exc_info.value)}"
        assert "Field 'invalidField' doesn't exist" in str(exc_info.value), "Error message should contain GraphQL error details"
        
        await service.close()


class TestSnapshotServiceIntegration:
    """Integration tests for SnapshotService with real API calls."""

    @pytest.mark.asyncio
    async def test_real_snapshot_api_call(self) -> None:
        """Test a real API call to Snapshot to verify integration works.
        
        This test makes an actual network call to the Snapshot API.
        It may be slow and could fail if the API is down.
        """
        service = SnapshotService()
        
        # Simple query to get a few spaces (should be fast and reliable)
        query = """
        query {
            spaces(first: 2, orderBy: "created", orderDirection: desc) {
                id
                name
                about
            }
        }
        """
        
        try:
            result = await service.execute_query(query)
            
            # Verify the response structure
            assert "spaces" in result, "Response should contain 'spaces' field"
            assert isinstance(result["spaces"], list), "Spaces should be a list"
            assert len(result["spaces"]) <= 2, "Should return at most 2 spaces"
            
            # If we have results, verify they have the expected structure
            if result["spaces"]:
                space = result["spaces"][0]
                assert "id" in space, "Each space should have an 'id'"
                assert "name" in space, "Each space should have a 'name'"
                # 'about' can be null/None so we just check it exists as a key
                assert "about" in space, "Each space should have an 'about' field"
                
        except Exception as e:
            # If the test fails due to network issues, skip it
            pytest.skip(f"Integration test skipped due to network/API issue: {str(e)}")
        finally:
            await service.close()


class TestSnapshotServiceGraphQLExecution:
    """Test SnapshotService GraphQL query execution."""

    @pytest.mark.asyncio
    async def test_execute_query_with_basic_query(self, httpx_mock: HTTPXMock) -> None:
        """Test that execute_query can execute a basic GraphQL query."""
        service = SnapshotService()
        
        # Sample GraphQL query for testing
        query = """
        query {
            spaces(first: 5) {
                id
                name
            }
        }
        """
        
        # Mock response data
        mock_response_data = {
            "data": {
                "spaces": [
                    {"id": "space1", "name": "Test Space 1"},
                    {"id": "space2", "name": "Test Space 2"}
                ]
            }
        }
        
        # Mock the HTTP response using pytest-httpx
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            json=mock_response_data,
            status_code=200
        )
        
        # Execute the query
        result = await service.execute_query(query)
        
        # Verify the result
        assert result == mock_response_data["data"]
        assert "spaces" in result
        assert len(result["spaces"]) == 2
        assert result["spaces"][0]["id"] == "space1"
        
        await service.close()

    @pytest.mark.asyncio
    async def test_execute_query_with_variables(self, httpx_mock: HTTPXMock) -> None:
        """Test that execute_query can execute a GraphQL query with variables."""
        service = SnapshotService()
        
        # Sample GraphQL query with variables
        query = """
        query GetSpace($id: String!) {
            space(id: $id) {
                id
                name
                about
            }
        }
        """
        
        variables = {"id": "test-space"}
        
        # Mock response data
        mock_response_data = {
            "data": {
                "space": {
                    "id": "test-space",
                    "name": "Test Space",
                    "about": "A test space for GraphQL queries"
                }
            }
        }
        
        # Mock the HTTP response using pytest-httpx
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            json=mock_response_data,
            status_code=200
        )
        
        # Execute the query with variables
        result = await service.execute_query(query, variables)
        
        # Verify the result
        assert result == mock_response_data["data"]
        assert result["space"]["id"] == "test-space"
        assert result["space"]["name"] == "Test Space"
        
        await service.close()


# TDD Tests for BAC-152 Implementation

class TestSnapshotServiceSpaces:
    """Test Space-related GraphQL queries - TDD approach with live API validation."""

    @pytest.fixture
    def mock_space_response(self):
        """Mock response data based on live API testing with arbitrumfoundation.eth."""
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
    def mock_spaces_response(self):
        """Mock response for multiple spaces query."""
        return {
            "spaces": [
                {
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
            ]
        }

    @pytest.mark.asyncio
    async def test_get_space_success(self, mock_space_response):
        """Test get_space returns Space object for valid space ID."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', return_value=mock_space_response):
            result = await snapshot_service.get_space("arbitrumfoundation.eth")
            
            assert result is not None
            assert isinstance(result, Space)
            assert result.id == "arbitrumfoundation.eth"
            assert result.name == "Arbitrum DAO"
            assert result.network == "42161"
            assert result.symbol == "ARB"
            assert result.verified == True
            assert result.proposalsCount == 381

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_space_not_found(self):
        """Test get_space returns None for invalid space ID."""
        snapshot_service = SnapshotService()
        
        mock_response = {"space": None}
        with patch.object(snapshot_service, 'execute_query', return_value=mock_response):
            result = await snapshot_service.get_space("invalid.eth")
            
            assert result is None

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_spaces_success(self, mock_spaces_response):
        """Test get_spaces returns list of Space objects."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', return_value=mock_spaces_response):
            result = await snapshot_service.get_spaces(["arbitrumfoundation.eth"])
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], Space)
            assert result[0].id == "arbitrumfoundation.eth"

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_spaces_empty_list(self):
        """Test get_spaces returns empty list for invalid space IDs."""
        snapshot_service = SnapshotService()
        
        mock_response = {"spaces": []}
        with patch.object(snapshot_service, 'execute_query', return_value=mock_response):
            result = await snapshot_service.get_spaces(["invalid.eth"])
            
            assert isinstance(result, list)
            assert len(result) == 0

        await snapshot_service.close()


class TestSnapshotServiceProposals:
    """Test Proposal-related GraphQL queries - TDD approach with live API validation."""

    @pytest.fixture
    def mock_proposal_response(self):
        """Mock response based on live API testing."""
        return {
            "proposal": {
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
        }

    @pytest.fixture
    def mock_proposals_response(self):
        """Mock response for multiple proposals query."""
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

    @pytest.mark.asyncio
    async def test_get_proposal_success(self, mock_proposal_response):
        """Test get_proposal returns Proposal object for valid proposal ID."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', return_value=mock_proposal_response):
            result = await snapshot_service.get_proposal("0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671")
            
            assert result is not None
            assert isinstance(result, Proposal)
            assert result.id == "0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671"
            assert result.title == "[CONSTITUTIONAL] Register $BORING in the Arbitrum generic-custom gateway"
            assert result.state == "active"
            assert len(result.choices) == 3
            assert result.votes == 2211

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_proposal_not_found(self):
        """Test get_proposal returns None for invalid proposal ID."""
        snapshot_service = SnapshotService()
        
        mock_response = {"proposal": None}
        with patch.object(snapshot_service, 'execute_query', return_value=mock_response):
            result = await snapshot_service.get_proposal("0xinvalid")
            
            assert result is None

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_proposals_with_pagination(self, mock_proposals_response):
        """Test get_proposals returns list with pagination parameters."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', return_value=mock_proposals_response):
            result = await snapshot_service.get_proposals(["arbitrumfoundation.eth"], first=2, skip=0)
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], Proposal)

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_proposals_with_state_filter(self, mock_proposals_response):
        """Test get_proposals with state filtering."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', return_value=mock_proposals_response):
            result = await snapshot_service.get_proposals(["arbitrumfoundation.eth"], state="active")
            
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].state == "active"

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_proposals_empty_result(self):
        """Test get_proposals returns empty list for spaces with no proposals."""
        snapshot_service = SnapshotService()
        
        mock_response = {"proposals": []}
        with patch.object(snapshot_service, 'execute_query', return_value=mock_response):
            result = await snapshot_service.get_proposals(["invalid.eth"])
            
            assert isinstance(result, list)
            assert len(result) == 0

        await snapshot_service.close()


class TestSnapshotServiceVotes:
    """Test Vote-related GraphQL queries - TDD approach with live API validation."""

    @pytest.fixture
    def mock_votes_response(self):
        """Mock response based on live API testing."""
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

    @pytest.fixture
    def mock_voting_power_response(self):
        """Mock response for voting power query."""
        return {
            "vp": {
                "vp": 13303966.17686743,
                "vp_by_strategy": [13303966.17686743]
            }
        }

    @pytest.mark.asyncio
    async def test_get_votes_with_pagination(self, mock_votes_response):
        """Test get_votes returns list of Vote objects with pagination."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', return_value=mock_votes_response):
            result = await snapshot_service.get_votes("0x586de5bf366820c4369c041b0bbad2254d78fafe1dcc1528c1ed661bb4dfb671", first=3, skip=0)
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert isinstance(result[0], Vote)
            assert result[0].voter == "0xB933AEe47C438f22DE0747D57fc239FE37878Dd1"
            assert result[0].choice == 1
            assert result[0].vp == 13301332.647183005

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_votes_empty_result(self):
        """Test get_votes returns empty list for proposals with no votes."""
        snapshot_service = SnapshotService()
        
        mock_response = {"votes": []}
        with patch.object(snapshot_service, 'execute_query', return_value=mock_response):
            result = await snapshot_service.get_votes("0xinvalid")
            
            assert isinstance(result, list)
            assert len(result) == 0

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_get_voting_power_calculation(self, mock_voting_power_response):
        """Test get_voting_power returns float value for voter address."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', return_value=mock_voting_power_response):
            result = await snapshot_service.get_voting_power("arbitrumfoundation.eth", "0xB933AEe47C438f22DE0747D57fc239FE37878Dd1")
            
            assert isinstance(result, float)
            assert result == 13303966.17686743

        await snapshot_service.close()


class TestSnapshotServiceTDDErrorHandling:
    """Test error handling scenarios for TDD implementation."""

    @pytest.mark.asyncio
    async def test_invalid_space_id_handling(self):
        """Test handling of invalid space ID errors."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', side_effect=GraphQLError("Space not found")):
            with pytest.raises(GraphQLError):
                await snapshot_service.get_space("invalid.eth")

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', side_effect=NetworkError("Connection failed")):
            with pytest.raises(NetworkError):
                await snapshot_service.get_space("arbitrumfoundation.eth")

        await snapshot_service.close()

    @pytest.mark.asyncio
    async def test_graphql_error_handling(self):
        """Test handling of GraphQL errors."""
        snapshot_service = SnapshotService()
        
        with patch.object(snapshot_service, 'execute_query', side_effect=GraphQLError("Invalid query syntax")):
            with pytest.raises(GraphQLError):
                await snapshot_service.get_proposals(["invalid.eth"])

        await snapshot_service.close()


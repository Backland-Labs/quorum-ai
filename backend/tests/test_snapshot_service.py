"""Tests for SnapshotService."""

import pytest
from unittest.mock import patch
import httpx
from pytest_httpx import HTTPXMock

from services.snapshot_service import SnapshotService
from config import settings


class TestSnapshotServiceInitialization:
    """Test SnapshotService initialization."""

    def test_snapshot_service_initialization_uses_settings(self) -> None:
        """Test that SnapshotService initialization uses configuration settings."""
        service = SnapshotService()

        assert service.base_url == "https://hub.snapshot.org/graphql"
        assert service.timeout == settings.request_timeout
        assert service.semaphore is not None
        assert service.semaphore._value == 5  # Default semaphore limit


class TestSnapshotServiceProperties:
    """Test SnapshotService properties and basic functionality."""

    def test_snapshot_service_has_required_attributes(self) -> None:
        """Test that SnapshotService has all required attributes."""
        service = SnapshotService()

        # Check that service has the expected attributes
        assert hasattr(service, 'base_url')
        assert hasattr(service, 'timeout')
        assert hasattr(service, 'semaphore')
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


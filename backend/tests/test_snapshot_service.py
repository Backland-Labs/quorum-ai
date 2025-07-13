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


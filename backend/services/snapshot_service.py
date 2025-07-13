"""Service for interacting with the Snapshot API."""

import asyncio
from typing import Any, Dict, Optional

import httpx

from config import settings

# Custom exceptions for better error handling
class SnapshotServiceError(Exception):
    """Base exception for SnapshotService errors."""
    pass

class NetworkError(SnapshotServiceError):
    """Raised when network operations fail."""
    pass

class GraphQLError(SnapshotServiceError):
    """Raised when GraphQL operations fail."""
    pass

# Constants for better code clarity and maintainability
DEFAULT_SEMAPHORE_LIMIT = 5  # Default semaphore limit for parallel requests
SNAPSHOT_GRAPHQL_ENDPOINT = "https://hub.snapshot.org/graphql"  # Snapshot GraphQL API endpoint


class SnapshotService:
    """Service for interacting with the Snapshot API with proper async resource management."""

    def __init__(self) -> None:
        """Initialize SnapshotService with required configuration and validation."""
        # Runtime assertions for critical method validation
        assert hasattr(settings, 'request_timeout'), (
            "Settings object must have a 'request_timeout' attribute"
        )
        assert settings.request_timeout > 0, (
            f"Request timeout must be positive, got {settings.request_timeout}"
        )
        
        self.base_url = SNAPSHOT_GRAPHQL_ENDPOINT
        self.timeout = settings.request_timeout
        self.semaphore = asyncio.Semaphore(DEFAULT_SEMAPHORE_LIMIT)
        
        # Configure default headers for GraphQL requests
        default_headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'QuorumAI/{settings.app_name}',
            'Accept': 'application/json'
        }
        
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=default_headers)

    async def __aenter__(self) -> "SnapshotService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit with proper resource cleanup."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self.client:
            await self.client.aclose()

    async def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the Snapshot API.
        
        Args:
            query: GraphQL query string
            variables: Optional dictionary of query variables
            
        Returns:
            Dictionary containing the response data
            
        Raises:
            NetworkError: When network operations fail
            GraphQLError: When GraphQL operations fail
        """
        # Runtime assertions for critical method validation
        assert query and query.strip(), "GraphQL query cannot be empty or whitespace"
        assert isinstance(query, str), f"Query must be a string, got {type(query)}"
        
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
            
        try:
            response = await self.client.post(self.base_url, json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            return response_data.get("data", {})
        except httpx.TimeoutException as e:
            raise NetworkError(f"Request timeout occurred: {str(e)}") from e
        except httpx.ConnectError as e:
            raise NetworkError(f"Failed to connect to Snapshot API: {str(e)}") from e
        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP error {e.response.status_code}: {str(e)}") from e
        except Exception as e:
            raise SnapshotServiceError(f"Unexpected error during query execution: {str(e)}") from e
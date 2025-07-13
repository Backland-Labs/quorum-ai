"""Service for interacting with the Snapshot API."""

import asyncio
from typing import Any, Dict, Optional

import httpx
import logfire

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
        
        with logfire.span(
            "snapshot_api_request", 
            query=query[:100] + "..." if len(query) > 100 else query,
            has_variables=variables is not None
        ):
            payload: Dict[str, Any] = {"query": query}
            if variables:
                payload["variables"] = variables
                
            try:
                logfire.info("Sending GraphQL request to Snapshot API", 
                            endpoint=self.base_url, 
                            query_length=len(query),
                            has_variables=variables is not None,
                            request_payload=payload)
                
                # Make HTTP request to Snapshot GraphQL endpoint
                response = await self.client.post(self.base_url, json=payload)
                
                logfire.info("Received HTTP response from Snapshot API", 
                            status_code=response.status_code,
                            content_type=response.headers.get("content-type"))
                
                # Check for HTTP errors (4xx, 5xx status codes)
                response.raise_for_status()
                
                # Parse JSON response from Snapshot API
                try:
                    response_data = response.json()
                except Exception as e:
                    logfire.error("Failed to parse JSON response from Snapshot API", 
                                 response_text=response.text[:500],
                                 error=str(e))
                    raise SnapshotServiceError(f"Snapshot API returned invalid JSON response: {str(e)}") from e
                
                # Check for GraphQL errors returned by Snapshot API
                if "errors" in response_data and response_data["errors"]:
                    error_details = response_data["errors"]
                    error_messages = []
                    
                    for error in error_details:
                        msg = error.get("message", "Unknown GraphQL error")
                        location = error.get("locations", [])
                        path = error.get("path", [])
                        
                        error_context = []
                        if location:
                            error_context.append(f"at line {location[0].get('line', '?')}")
                        if path:
                            error_context.append(f"in path {'.'.join(map(str, path))}")
                        
                        full_msg = msg
                        if error_context:
                            full_msg += f" ({', '.join(error_context)})"
                        error_messages.append(full_msg)
                    
                    error_msg = f"Snapshot API returned GraphQL errors: {'; '.join(error_messages)}"
                    logfire.error("GraphQL query failed at Snapshot API", 
                                 graphql_errors=error_details,
                                 error_count=len(error_details))
                    raise GraphQLError(error_msg)
                
                # Validate response structure
                if "data" not in response_data:
                    logfire.error("Snapshot API response missing 'data' field", 
                                 response_keys=list(response_data.keys()))
                    raise SnapshotServiceError("Snapshot API response missing 'data' field")
                
                data_result = response_data.get("data", {})
                logfire.info("Snapshot GraphQL query completed successfully", 
                            data_keys=list(data_result.keys()) if isinstance(data_result, dict) else "non-dict-data",
                            response_size=len(str(data_result)))
                
                return data_result
                
            except GraphQLError:
                # Re-raise GraphQL errors without wrapping
                raise
            except httpx.TimeoutException as e:
                logfire.error("Network timeout connecting to Snapshot API", 
                             endpoint=self.base_url,
                             timeout_seconds=self.timeout,
                             error=str(e))
                raise NetworkError(f"Network timeout connecting to Snapshot API ({self.base_url}): {str(e)}") from e
            except httpx.ConnectError as e:
                logfire.error("Failed to establish connection to Snapshot API", 
                             endpoint=self.base_url,
                             error=str(e))
                raise NetworkError(f"Cannot connect to Snapshot API ({self.base_url}): {str(e)}") from e
            except httpx.HTTPStatusError as e:
                response_text = getattr(e.response, 'text', 'No response text available')
                logfire.error("Snapshot API returned HTTP error", 
                             status_code=e.response.status_code,
                             endpoint=self.base_url,
                             response_text=response_text[:500],
                             error=str(e))
                raise NetworkError(f"Snapshot API HTTP {e.response.status_code} error: {str(e)}. Response: {response_text[:200]}") from e
            except SnapshotServiceError:
                # Re-raise our custom errors without wrapping
                raise
            except Exception as e:
                logfire.error("Unexpected error during Snapshot API interaction", 
                             endpoint=self.base_url,
                             error=str(e), 
                             error_type=type(e).__name__)
                raise SnapshotServiceError(f"Unexpected error during Snapshot API query execution: {str(e)}") from e
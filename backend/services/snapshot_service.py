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
DEFAULT_CONTENT_TYPE = 'application/json'
DEFAULT_USER_AGENT_PREFIX = 'QuorumAI'
DEFAULT_ACCEPT_TYPE = 'application/json'
MAX_LOG_QUERY_LENGTH = 100
MAX_LOG_RESPONSE_LENGTH = 500
QUERY_TRUNCATION_SUFFIX = "..."


class SnapshotService:
    """Service for interacting with the Snapshot API with proper async resource management."""

    def __init__(self) -> None:
        """Initialize SnapshotService with required configuration and validation."""
        
        self.base_url = SNAPSHOT_GRAPHQL_ENDPOINT
        self.timeout = settings.request_timeout
        
        # Configure default headers for GraphQL requests
        default_headers = {
            'Content-Type': DEFAULT_CONTENT_TYPE,
            'User-Agent': f'{DEFAULT_USER_AGENT_PREFIX}/{settings.app_name}',
            'Accept': DEFAULT_ACCEPT_TYPE
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

    def _parse_graphql_errors(self, error_details: list) -> str:
        """Parse GraphQL errors and return formatted error message."""
        # Runtime assertions for critical method validation
        assert isinstance(error_details, list), f"Error details must be a list, got {type(error_details)}"
        assert all(isinstance(error, dict) for error in error_details), "Each error must be a dictionary"
        
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
        
        return f"Snapshot API returned GraphQL errors: {'; '.join(error_messages)}"

    def _truncate_query_for_logging(self, query: str) -> str:
        """Truncate query string for logging purposes."""
        if len(query) > MAX_LOG_QUERY_LENGTH:
            return query[:MAX_LOG_QUERY_LENGTH] + QUERY_TRUNCATION_SUFFIX
        return query

    def _log_and_raise_network_error(self, error_type: str, exception: Exception, **context) -> None:
        """Log network error and raise NetworkError with context."""
        logfire.error(f"Network error: {error_type}", 
                     endpoint=self.base_url,
                     error=str(exception),
                     **context)
        
        if isinstance(exception, httpx.TimeoutException):
            raise NetworkError(f"Network timeout connecting to Snapshot API ({self.base_url}): {str(exception)}") from exception
        elif isinstance(exception, httpx.ConnectError):
            raise NetworkError(f"Cannot connect to Snapshot API ({self.base_url}): {str(exception)}") from exception
        elif isinstance(exception, httpx.HTTPStatusError):
            response_text = getattr(exception.response, 'text', 'No response text available')
            raise NetworkError(f"Snapshot API HTTP {exception.response.status_code} error: {str(exception)}. Response: {response_text[:200]}") from exception
        else:
            # Fallback for any other httpx exception types
            raise NetworkError(f"Network error during Snapshot API call: {str(exception)}") from exception

    def _validate_query_inputs(self, query: str, variables: Optional[Dict[str, Any]]) -> None:
        """Validate query inputs with comprehensive runtime assertions."""
        assert query and query.strip(), "GraphQL query cannot be empty or whitespace"
        assert self.client is not None, "HTTP client must be initialized"
        if variables is not None:
            assert isinstance(variables, dict), f"Variables must be dict or None, got {type(variables)}"

    def _prepare_graphql_payload(self, query: str, variables: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare GraphQL request payload."""
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        return payload

    async def _send_graphql_request(self, payload: Dict[str, Any]) -> httpx.Response:
        """Send GraphQL request and return raw HTTP response."""
        logfire.info("Sending GraphQL request to Snapshot API", 
                    endpoint=self.base_url, 
                    query_length=len(payload.get("query", "")),
                    has_variables=payload.get("variables") is not None,
                    request_payload=payload)
        
        response = await self.client.post(self.base_url, json=payload)
        
        logfire.info("Received HTTP response from Snapshot API", 
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type"))
        
        response.raise_for_status()
        return response

    def _parse_json_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse JSON response with error handling."""
        try:
            return response.json()
        except Exception as e:
            logfire.error("Failed to parse JSON response from Snapshot API", 
                         response_text=response.text[:MAX_LOG_RESPONSE_LENGTH],
                         error=str(e))
            raise SnapshotServiceError(f"Snapshot API returned invalid JSON response: {str(e)}") from e

    def _validate_graphql_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate GraphQL response structure and handle errors."""
        # Check for GraphQL errors returned by Snapshot API
        if "errors" in response_data and response_data["errors"]:
            error_details = response_data["errors"]
            error_msg = self._parse_graphql_errors(error_details)
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
        self._validate_query_inputs(query, variables)
        
        with logfire.span(
            "snapshot_api_request", 
            query=self._truncate_query_for_logging(query),
            has_variables=variables is not None
        ):
            payload = self._prepare_graphql_payload(query, variables)
                
            try:
                response = await self._send_graphql_request(payload)
                response_data = self._parse_json_response(response)
                return self._validate_graphql_response(response_data)
                
            except (GraphQLError, SnapshotServiceError):
                # Re-raise our custom errors without wrapping
                raise
            except httpx.TimeoutException as e:
                self._log_and_raise_network_error("timeout", e, timeout_seconds=self.timeout)
            except httpx.ConnectError as e:
                self._log_and_raise_network_error("connection", e)
            except httpx.HTTPStatusError as e:
                response_text = getattr(e.response, 'text', 'No response text available')
                self._log_and_raise_network_error("HTTP error", e, 
                                                 status_code=e.response.status_code,
                                                 response_text=response_text[:MAX_LOG_RESPONSE_LENGTH])
            except Exception as e:
                logfire.error("Unexpected error during Snapshot API interaction", 
                             endpoint=self.base_url,
                             error=str(e), 
                             error_type=type(e).__name__)
                raise SnapshotServiceError(f"Unexpected error during Snapshot API query execution: {str(e)}") from e
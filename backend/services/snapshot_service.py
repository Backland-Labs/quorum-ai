"""Service for interacting with the Snapshot API."""

from typing import Any, Dict, List, Optional

import httpx

from config import settings
from logging_config import setup_pearl_logger, log_span
from models import Space, Proposal, Vote

# Initialize Pearl-compliant logger
logger = setup_pearl_logger(__name__)


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
DEFAULT_CONTENT_TYPE = "application/json"
DEFAULT_USER_AGENT_PREFIX = "QuorumAI"
DEFAULT_ACCEPT_TYPE = "application/json"
MAX_LOG_QUERY_LENGTH = 100
MAX_LOG_RESPONSE_LENGTH = 500
QUERY_TRUNCATION_SUFFIX = "..."

# Pagination and default values
DEFAULT_PROPOSALS_LIMIT = 20
DEFAULT_VOTES_LIMIT = 100
DEFAULT_PAGINATION_SKIP = 0
DEFAULT_VOTING_POWER = 0.0
NO_RESPONSE_TEXT_FALLBACK = "No response text available"


class SnapshotService:
    """Service for interacting with the Snapshot API with proper async resource management."""

    def __init__(self) -> None:
        """Initialize SnapshotService with required configuration and validation."""

        self.base_url = settings.snapshot_graphql_endpoint
        self.timeout = settings.request_timeout

        # Configure default headers for GraphQL requests
        default_headers = {
            "Content-Type": DEFAULT_CONTENT_TYPE,
            "User-Agent": f"{DEFAULT_USER_AGENT_PREFIX}/{settings.app_name}",
            "Accept": DEFAULT_ACCEPT_TYPE,
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
        assert isinstance(
            error_details, list
        ), f"Error details must be a list, got {type(error_details)}"
        assert all(
            isinstance(error, dict) for error in error_details
        ), "Each error must be a dictionary"

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

    def _extract_response_text(self, response: Optional[httpx.Response]) -> str:
        """Extract response text safely with fallback."""
        if response is None:
            return "No response available"
        return getattr(response, "text", NO_RESPONSE_TEXT_FALLBACK)

    def _log_and_raise_network_error(
        self, error_type: str, exception: Exception, **context
    ) -> None:
        """Log network error and raise NetworkError with context."""
        # Build log message based on available context
        log_parts = [
            f"Network error: {error_type}",
            f"endpoint={self.base_url}",
            f"error={str(exception)}",
        ]

        # Add context-specific fields
        context_fields = ["timeout_seconds", "status_code", "response_text"]
        for field in context_fields:
            if field in context:
                log_parts.append(f"{field}={context[field]}")

        log_message = ", ".join(log_parts)
        logger.error(log_message)

        if isinstance(exception, httpx.TimeoutException):
            raise NetworkError(
                f"Network timeout connecting to Snapshot API ({self.base_url}): {str(exception)}"
            ) from exception
        elif isinstance(exception, httpx.ConnectError):
            raise NetworkError(
                f"Cannot connect to Snapshot API ({self.base_url}): {str(exception)}"
            ) from exception
        elif isinstance(exception, httpx.HTTPStatusError):
            response_text = self._extract_response_text(exception.response)
            raise NetworkError(
                f"Snapshot API HTTP {exception.response.status_code} error: {str(exception)}. Response: {response_text[:200]}"
            ) from exception
        else:
            # Fallback for any other httpx exception types
            raise NetworkError(
                f"Network error during Snapshot API call: {str(exception)}"
            ) from exception

    def _validate_query_inputs(
        self, query: str, variables: Optional[Dict[str, Any]]
    ) -> None:
        """Validate query inputs with comprehensive runtime assertions."""
        assert query and query.strip(), "GraphQL query cannot be empty or whitespace"
        assert self.client is not None, "HTTP client must be initialized"
        if variables is not None:
            assert isinstance(
                variables, dict
            ), f"Variables must be dict or None, got {type(variables)}"

    def _prepare_graphql_payload(
        self, query: str, variables: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare GraphQL request payload."""
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        return payload

    async def _send_graphql_request(self, payload: Dict[str, Any]) -> httpx.Response:
        """Send GraphQL request and return raw HTTP response."""
        # Extract query metadata for cleaner logging
        query = payload.get("query", "")
        query_length = len(query)
        has_variables = payload.get("variables") is not None

        logger.info(
            "Sending GraphQL request to Snapshot API, endpoint=%s, query_length=%s, has_variables=%s",
            self.base_url,
            query_length,
            has_variables,
        )

        response = await self.client.post(self.base_url, json=payload)

        content_type = response.headers.get("content-type")
        logger.info(
            "Received HTTP response from Snapshot API, status_code=%s, content_type=%s",
            response.status_code,
            content_type,
        )

        response.raise_for_status()
        return response

    def _parse_json_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Parse JSON response with error handling."""
        try:
            return response.json()
        except Exception as e:
            logger.error(
                "Failed to parse JSON response from Snapshot API, response_text=%s, error=%s",
                response.text[:MAX_LOG_RESPONSE_LENGTH],
                str(e),
            )
            raise SnapshotServiceError(
                f"Snapshot API returned invalid JSON response: {str(e)}"
            ) from e

    def _validate_graphql_response(
        self, response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate GraphQL response structure and handle errors."""
        # Runtime assertions for critical validation
        assert isinstance(response_data, dict), "Response data must be a dictionary"
        assert (
            "data" in response_data or "errors" in response_data
        ), "Response must contain 'data' or 'errors'"

        # Check for GraphQL errors returned by Snapshot API
        errors = response_data.get("errors", [])
        if errors:
            error_msg = self._parse_graphql_errors(errors)
            error_count = len(errors)
            logger.error(
                "GraphQL query failed at Snapshot API, graphql_errors=%s, error_count=%s",
                str(errors),
                error_count,
            )
            raise GraphQLError(error_msg)

        # Validate response structure
        if "data" not in response_data:
            response_keys = list(response_data.keys())
            logger.error(
                "Snapshot API response missing 'data' field, response_keys=%s",
                str(response_keys),
            )
            raise SnapshotServiceError("Snapshot API response missing 'data' field")

        data_result = response_data.get("data", {})
        data_keys_for_logging = self._extract_data_keys_for_logging(data_result)
        response_size = len(str(data_result))

        logger.info(
            "Snapshot GraphQL query completed successfully, data_keys=%s, response_size=%s",
            str(data_keys_for_logging),
            response_size,
        )

        return data_result

    def _extract_data_keys_for_logging(self, data_result: Any) -> Any:
        """Extract data keys for logging from the result."""
        if isinstance(data_result, dict):
            return list(data_result.keys())
        return "non-dict-data"

    async def execute_query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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

        with log_span(
            logger,
            "snapshot_api_request",
            query=self._truncate_query_for_logging(query),
            has_variables=variables is not None,
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
                self._log_and_raise_network_error(
                    "timeout", e, timeout_seconds=self.timeout
                )
            except httpx.ConnectError as e:
                self._log_and_raise_network_error("connection", e)
            except httpx.HTTPStatusError as e:
                response_text = self._extract_response_text(e.response)
                self._log_and_raise_network_error(
                    "HTTP error",
                    e,
                    status_code=e.response.status_code,
                    response_text=response_text[:MAX_LOG_RESPONSE_LENGTH],
                )
            except Exception as e:
                logger.error(
                    "Unexpected error during Snapshot API interaction, endpoint=%s, error=%s, error_type=%s",
                    self.base_url,
                    str(e),
                    type(e).__name__,
                )
                raise SnapshotServiceError(
                    f"Unexpected error during Snapshot API query execution: {str(e)}"
                ) from e

    # GraphQL Query Constants - Based on live API testing
    GET_SPACE_QUERY = """
    query GetSpace($id: String!) {
        space(id: $id) {
            id
            name
            about
            network
            symbol
            strategies {
                name
                params
            }
            admins
            moderators
            members
            private
            verified
            created
            proposalsCount
            followersCount
            votesCount
        }
    }
    """

    GET_SPACES_QUERY = """
    query GetSpaces($ids: [String!]!) {
        spaces(where: {id_in: $ids}) {
            id
            name
            about
            network
            symbol
            strategies {
                name
                params
            }
            admins
            moderators
            members
            private
            verified
            created
            proposalsCount
            followersCount
            votesCount
        }
    }
    """

    GET_PROPOSAL_QUERY = """
    query GetProposal($id: String!) {
        proposal(id: $id) {
            id
            title
            body
            choices
            start
            end
            state
            scores
            scores_total
            votes
            created
            quorum
            author
            network
            symbol
        }
    }
    """

    GET_PROPOSALS_QUERY = """
    query GetProposals($spaces: [String!]!, $state: String, $first: Int, $skip: Int) {
        proposals(where: {space_in: $spaces, state: $state}, first: $first, skip: $skip, orderBy: "created", orderDirection: desc) {
            id
            title
            body
            choices
            start
            end
            state
            scores
            scores_total
            votes
            created
            quorum
            author
            network
            symbol
        }
    }
    """

    GET_VOTES_QUERY = """
    query GetVotes($proposal: String!, $first: Int, $skip: Int) {
        votes(where: {proposal: $proposal}, first: $first, skip: $skip, orderBy: "vp", orderDirection: desc) {
            id
            voter
            choice
            vp
            vp_by_strategy
            created
            reason
        }
    }
    """

    GET_VOTING_POWER_QUERY = """
    query GetVotingPower($voter: String!, $space: String!) {
        vp(voter: $voter, space: $space) {
            vp
            vp_by_strategy
        }
    }
    """

    # Space Methods
    async def get_space(self, space_id: str) -> Optional[Space]:
        """Get a single space by ID.

        Args:
            space_id: The space identifier

        Returns:
            Space object if found, None otherwise
        """
        # Runtime assertion for critical input
        assert space_id and isinstance(
            space_id, str
        ), "Space ID must be a non-empty string"

        variables = {"id": space_id}

        with log_span(logger, "get_space", space_id=space_id):
            result = await self.execute_query(self.GET_SPACE_QUERY, variables)

            space_data = result.get("space")
            if space_data is None:
                return None

            return Space(**space_data)

    async def get_spaces(self, space_ids: List[str]) -> List[Space]:
        """Get multiple spaces by IDs.

        Args:
            space_ids: List of space identifiers

        Returns:
            List of Space objects
        """
        variables = {"ids": space_ids}

        with log_span(logger, "get_spaces", space_ids=space_ids, count=len(space_ids)):
            result = await self.execute_query(self.GET_SPACES_QUERY, variables)

            return [Space(**space_data) for space_data in result.get("spaces", [])]

    # Proposal Methods
    async def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get a single proposal by ID.

        Args:
            proposal_id: The proposal identifier

        Returns:
            Proposal object if found, None otherwise
        """
        # Runtime assertion for critical input
        assert proposal_id and isinstance(
            proposal_id, str
        ), "Proposal ID must be a non-empty string"

        variables = {"id": proposal_id}

        with log_span(logger, "get_proposal", proposal_id=proposal_id):
            result = await self.execute_query(self.GET_PROPOSAL_QUERY, variables)

            proposal_data = result.get("proposal")
            if proposal_data is None:
                return None

            return Proposal(**proposal_data)

    async def get_proposals(
        self,
        space_ids: List[str],
        state: Optional[str] = None,
        first: int = DEFAULT_PROPOSALS_LIMIT,
        skip: int = DEFAULT_PAGINATION_SKIP,
    ) -> List[Proposal]:
        """Get proposals for given spaces with optional filtering and pagination.

        Args:
            space_ids: List of space identifiers
            state: Optional state filter (e.g., "active", "closed", "pending")
            first: Number of proposals to fetch (default: 20)
            skip: Number of proposals to skip for pagination (default: 0)

        Returns:
            List of Proposal objects
        """
        base_variables = {"spaces": space_ids, "first": first, "skip": skip}

        query_variables = base_variables.copy()
        if state is not None:
            query_variables["state"] = state

        with log_span(
            logger,
            "get_proposals",
            space_ids=space_ids,
            state=state,
            first=first,
            skip=skip,
        ):
            result = await self.execute_query(self.GET_PROPOSALS_QUERY, query_variables)

            return [
                Proposal(**proposal_data)
                for proposal_data in result.get("proposals", [])
            ]

    # Vote Methods
    async def get_votes(
        self,
        proposal_id: str,
        first: int = DEFAULT_VOTES_LIMIT,
        skip: int = DEFAULT_PAGINATION_SKIP,
    ) -> List[Vote]:
        """Get votes for a proposal with pagination.

        Args:
            proposal_id: The proposal identifier
            first: Number of votes to fetch (default: 100)
            skip: Number of votes to skip for pagination (default: 0)

        Returns:
            List of Vote objects ordered by voting power (descending)
        """
        variables = {"proposal": proposal_id, "first": first, "skip": skip}

        with log_span(
            logger, "get_votes", proposal_id=proposal_id, first=first, skip=skip
        ):
            result = await self.execute_query(self.GET_VOTES_QUERY, variables)

            return [Vote(**vote_data) for vote_data in result.get("votes", [])]

    async def get_voting_power(self, space_id: str, voter_address: str) -> float:
        """Get voting power for a voter in a specific space.

        Args:
            space_id: The space identifier
            voter_address: The voter's wallet address

        Returns:
            Voting power as float
        """
        variables = {"space": space_id, "voter": voter_address}

        with log_span(
            logger, "get_voting_power", space_id=space_id, voter_address=voter_address
        ):
            result = await self.execute_query(self.GET_VOTING_POWER_QUERY, variables)

            voting_power_result = result.get("vp", {})
            return voting_power_result.get("vp", DEFAULT_VOTING_POWER)

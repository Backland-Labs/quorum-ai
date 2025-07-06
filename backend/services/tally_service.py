"""Service for interacting with the Tally API."""

import asyncio
import time # For timing API calls
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import logfire

from backend.utils.logging import APICallLogger, log_function_call, logger, DataFlowLogger
from config import settings
from models import (
    DAO,
    Organization,
    Proposal,
    ProposalFilters,
    ProposalState,
    ProposalVoter,
    SortCriteria,
    SortOrder,
    VoteType,
)


class TallyService:
    """Service for interacting with the Tally API."""

    def __init__(self) -> None:
        self.base_url = settings.tally_api_base_url
        self.api_key = settings.tally_api_key
        self.timeout = settings.request_timeout

    async def _make_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Make a GraphQL request to the Tally API."""
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Api-Key"] = self.api_key

        payload = {"query": query, "variables": variables or {}}

        # Attempt to get a more specific endpoint name from the GraphQL query
        query_lines = query.strip().splitlines()
        first_line = query_lines[0].strip() if query_lines else ""
        endpoint_name = "GraphQL Query" # Default
        if first_line.startswith("query ") and len(first_line.split()) > 1:
            name_part = first_line.split()[1]
            if "(" in name_part: # Handles queries like "query GetOrganizations($input: OrganizationsInput)"
                endpoint_name = name_part.split("(", 1)[0]
            else:
                endpoint_name = name_part
        elif first_line.startswith("mutation ") and len(first_line.split()) > 1:
            endpoint_name = first_line.split()[1].split("(", 1)[0]


        APICallLogger.log_request(
            service="Tally",
            endpoint=endpoint_name,
            method="POST",
            # Log only variable keys for brevity and to avoid exposing too much data by default
            # The full query string can be very long.
            graphql_variables=list(variables.keys()) if variables else None,
            graphql_query_preview=f"{query[:100]}..." if len(query) > 100 else query
        )

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url, json=payload, headers=headers
                )
            execution_time_ms = (time.time() - start_time) * 1000
            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses

            APICallLogger.log_response(
                service="Tally",
                endpoint=endpoint_name,
                status_code=response.status_code,
                response_size=len(response.content),
                execution_time_ms=execution_time_ms
            )
            return response.json()
        except httpx.HTTPStatusError as e:
            execution_time_ms = (time.time() - start_time) * 1000
            APICallLogger.log_error(
                service="Tally",
                endpoint=endpoint_name,
                error=e,
                status_code=e.response.status_code,
                response_text=e.response.text[:200], # Log snippet of error response
                execution_time_ms=execution_time_ms
            )
            raise # Re-raise the exception to be handled by the caller
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            APICallLogger.log_error(
                service="Tally",
                endpoint=endpoint_name,
                error=e,
                execution_time_ms=execution_time_ms
            )
            raise # Re-raise the exception

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_organizations(
        self, limit: int = 100, after_cursor: Optional[str] = None
    ) -> tuple[List[Organization], Optional[str]]:
        """Fetch a list of organizations."""
        query = self._build_organizations_query()
        variables = self._build_organizations_variables(limit, after_cursor)

        try:
            result = await self._make_request(query, variables)
            return self._process_organizations_response(result)
        except Exception as e:
            logfire.error("Failed to fetch organizations", exc_info=e)
            raise

    def _build_organizations_query(self) -> str:
        """Build GraphQL query for fetching organizations."""
        return """
        query GetOrganizations($input: OrganizationsInput) {
            organizations(input: $input) {
                nodes {
                    ... on Organization {
                        id
                        name
                        slug
                        chainIds
                        tokenIds
                        governorIds
                        hasActiveProposals
                        proposalsCount
                        delegatesCount
                        delegatesVotesCount
                        tokenOwnersCount
                    }
                }
                pageInfo {
                    lastCursor
                }
            }
        }
        """

    def _build_organizations_variables(
        self, limit: int, after_cursor: Optional[str]
    ) -> Dict:
        """Build variables for organizations query."""
        page_input: Dict[str, Any] = {"limit": limit}
        if after_cursor:
            page_input["afterCursor"] = after_cursor

        return {
            "input": {
                "page": page_input,
                "sort": {"sortBy": "explore", "isDescending": True},
            }
        }

    def _process_organizations_response(
        self, result: Dict
    ) -> tuple[List[Organization], Optional[str]]:
        """Process organizations API response into Organization objects."""
        org_data = result.get("data", {}).get("organizations", {})
        org_nodes = org_data.get("nodes", [])

        DataFlowLogger.log_data_transformation(
            stage="_process_organizations_response_input",
            input_count=len(org_nodes),
            output_count=0, # Input stage
            transformation_type="raw_tally_organization_nodes"
        )

        organizations = [
            self._create_organization_from_node(org) for org in org_nodes if org
        ]

        last_cursor = org_data.get("pageInfo", {}).get("lastCursor")
        logfire.info("Processed and fetched organizations", count=len(organizations)) # Message updated slightly

        DataFlowLogger.log_data_transformation(
            stage="_process_organizations_response_output",
            input_count=len(org_nodes), # Can repeat input_count for context
            output_count=len(organizations),
            transformation_type="pydantic_organization_models"
        )
        return organizations, last_cursor

    def _create_organization_from_node(self, org: Dict) -> Organization:
        """Create Organization object from API node data."""
        return Organization(
            id=org["id"],
            name=org["name"],
            slug=org["slug"],
            chain_ids=org.get("chainIds", []),
            token_ids=org.get("tokenIds", []),
            governor_ids=org.get("governorIds", []),
            has_active_proposals=org.get("hasActiveProposals", False),
            proposals_count=org.get("proposalsCount", 0),
            delegates_count=org.get("delegatesCount", 0),
            delegates_votes_count=str(org.get("delegatesVotesCount", "0")),
            token_owners_count=org.get("tokenOwnersCount", 0),
        )

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_daos(
        self,
        organization_id: str,
        limit: int = 50,
        after_cursor: Optional[str] = None,
        sort_desc: bool = True,
    ) -> tuple[List[DAO], Optional[str]]:
        """Fetch list of available DAOs for a given organization."""
        query = """
        query GetGovernors($input: GovernorsInput!) {
            governors(input: $input) {
                nodes {
                    ... on Governor {
                        id
                        name
                        slug
                        organization {
                            id
                        }
                        metadata {
                            description
                        }
                        proposalStats {
                            active
                            total
                        }
                    }
                }
                pageInfo {
                    lastCursor
                }
            }
        }
        """

        page_input: Dict[str, Any] = {"limit": limit}
        if after_cursor:
            page_input["afterCursor"] = after_cursor

        variables = {
            "input": {
                "page": page_input,
                "sort": {"sortBy": "id", "isDescending": sort_desc},
                "filters": {"organizationId": organization_id},
            }
        }

        try:
            result = await self._make_request(query, variables)
            governors_data = result.get("data", {}).get("governors", {})
            dao_data = governors_data.get("nodes", [])

            daos = []
            for dao in dao_data:
                if not dao:
                    continue
                daos.append(
                    DAO(
                        id=dao["id"],
                        name=dao["name"],
                        slug=dao["slug"],
                        description=dao.get("metadata", {}).get("description"),
                        organization_id=dao["organization"]["id"],
                        active_proposals_count=dao.get("proposalStats", {}).get(
                            "active", 0
                        ),
                        total_proposals_count=dao.get("proposalStats", {}).get(
                            "total", 0
                        ),
                    )
                )

            last_cursor = governors_data.get("pageInfo", {}).get("lastCursor")

            logfire.info("Fetched DAOs", count=len(daos))
            return daos, last_cursor

        except Exception as e:
            logfire.error("Failed to fetch DAOs", organization_id=organization_id, exc_info=e)
            raise

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_dao_by_id(self, dao_id: str) -> Optional[DAO]:
        """Fetch a specific DAO by ID."""
        query = """
        query GetGovernor($input: GovernorInput!) {
            governor(input: $input) {
                id
                name
                slug
                organization {
                    id
                }
                metadata {
                    description
                }
                proposalStats {
                    active
                    total
                }
            }
        }
        """

        variables = {"input": {"id": dao_id}}

        try:
            result = await self._make_request(query, variables)
            dao_data = result.get("data", {}).get("governor")

            if not dao_data:
                return None

            return DAO(
                id=dao_data["id"],
                name=dao_data["name"],
                slug=dao_data["slug"],
                description=dao_data.get("metadata", {}).get("description"),
                organization_id=dao_data["organization"]["id"],
                active_proposals_count=dao_data.get("proposalStats", {}).get(
                    "active", 0
                ),
                total_proposals_count=dao_data.get("proposalStats", {}).get("total", 0),
            )

        except Exception as e:
            logfire.error("Failed to fetch DAO", dao_id=dao_id, exc_info=e)
            raise

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_proposals(
        self, filters: ProposalFilters
    ) -> tuple[List[Proposal], Optional[str]]:
        """Fetch proposals based on filters."""
        assert filters, "Filters cannot be None"
        assert isinstance(
            filters, ProposalFilters
        ), "Filters must be ProposalFilters instance"

        query = self._build_proposals_query()

        # For vote count sorting, we need to fetch more proposals to sort client-side
        # since Tally API doesn't support sorting by vote count
        original_limit = filters.limit
        if filters.sort_by == SortCriteria.VOTE_COUNT:
            logger.debug(
                "get_proposals: Vote count sort requested. Modifying fetch strategy.",
                original_limit=original_limit,
                requested_sort_by=filters.sort_by.value
            )
            # Fetch more proposals to ensure we have enough for sorting
            # Use 3x the requested limit to get a good selection for sorting
            fetch_filters = filters.model_copy()
            fetch_filters.limit = min(original_limit * 3, 100)  # Cap at API limit
            fetch_filters.sort_by = SortCriteria.CREATED_DATE  # Use default API sorting
            logger.debug("get_proposals: Fetching with modified filters for vote count sort.", fetch_limit=fetch_filters.limit, fetch_sort_by=fetch_filters.sort_by.value)
            variables = self._build_proposals_variables(fetch_filters)
        else:
            variables = self._build_proposals_variables(filters)

        try:
            result = await self._make_request(query, variables)
            proposals, next_cursor = self._process_proposals_response(result)

            # Apply client-side sorting if needed
            if filters.sort_by == SortCriteria.VOTE_COUNT and proposals:
                logger.debug("get_proposals: Performing client-side sorting by vote count.", proposal_count_before_sort=len(proposals), sort_order=filters.sort_order.value)
                proposals = self._sort_proposals_by_vote_count(
                    proposals, filters.sort_order
                )
                proposals_after_sort_count = len(proposals)
                # Limit to requested amount after sorting
                proposals = proposals[:original_limit]
                logger.debug(
                    "get_proposals: Client-side sort completed.",
                    proposal_count_after_sort=proposals_after_sort_count,
                    proposal_count_after_limit=len(proposals)
                )
                # Note: next_cursor may not be accurate for vote sorting
                # since we're doing client-side sorting
                if len(proposals) == original_limit:
                    logger.debug("get_proposals: Resetting next_cursor due to client-side sort and limit.")
                    next_cursor = None  # Don't provide cursor for vote sorting

            return proposals, next_cursor
        except Exception as e:
            logfire.error(
                "Failed to fetch proposals", filters=filters.dict(), exc_info=e
            )
            raise

    def _build_proposals_query(self) -> str:
        """Build GraphQL query for fetching proposals with vote statistics."""
        return """
            query GetProposals($input: ProposalsInput!) {
                proposals(input: $input) {
                    nodes {
                        ... on Proposal {
                            id
                            status
                            createdAt
                            metadata {
                                title
                                description
                            }
                            governor {
                                id
                                name
                            }
                            voteStats {
                                type
                                votesCount
                            }
                        }
                    }
                    pageInfo {
                        lastCursor
                    }
                }
            }
        """

    def _build_proposals_variables(self, filters: ProposalFilters) -> Dict:
        """Build GraphQL variables for proposals query."""
        assert filters, "Filters are required"
        assert filters.limit > 0, "Limit must be positive"

        page_input = self._build_page_input(filters)
        sort_input = self._build_sort_input(filters)
        filter_input = self._build_filter_input(filters)

        return {
            "input": {"page": page_input, "sort": sort_input, "filters": filter_input}
        }

    def _build_page_input(self, filters: ProposalFilters) -> Dict[str, Any]:
        """Build pagination input for proposals query."""
        assert filters, "Filters are required"
        assert filters.limit > 0, "Limit must be positive"

        page_input: Dict[str, Any] = {"limit": filters.limit}
        if filters.after_cursor:
            page_input["afterCursor"] = filters.after_cursor

        return page_input

    def _build_sort_input(self, filters: ProposalFilters) -> Dict:
        """Build sort input for proposals query."""
        assert filters, "Filters are required"
        assert filters.sort_by, "Sort criteria is required"

        sort_by = (
            "id"
            if filters.sort_by == SortCriteria.CREATED_DATE
            else filters.sort_by.value
        )

        return {
            "sortBy": sort_by,
            "isDescending": filters.sort_order == SortOrder.DESC,
        }

    def _build_filter_input(self, filters: ProposalFilters) -> Dict:
        """Build filter input for proposals query."""
        assert filters, "Filters are required"

        filter_input = {}
        if filters.organization_id:
            filter_input["organizationId"] = filters.organization_id
        elif filters.dao_id:
            filter_input["governorId"] = filters.dao_id

        # Note: API doesn't support state filtering in current version
        return filter_input

    def _process_proposals_response(
        self, result: Dict
    ) -> tuple[List[Proposal], Optional[str]]:
        """Process proposals API response into Proposal objects."""
        assert result, "API result cannot be empty"
        assert "data" in result, "API result must contain data"

        proposals_data = result.get("data", {}).get("proposals", {})
        proposal_nodes = proposals_data.get("nodes", [])
        last_cursor = proposals_data.get("pageInfo", {}).get("lastCursor")

        DataFlowLogger.log_data_transformation(
            stage="_process_proposals_response_input",
            input_count=len(proposal_nodes),
            output_count=0, # Input stage
            transformation_type="raw_tally_proposal_nodes"
        )

        proposals = [
            self._create_proposal_from_data(node) for node in proposal_nodes if node
        ]

        logfire.info("Processed and fetched proposals", count=len(proposals)) # Message updated

        DataFlowLogger.log_data_transformation(
            stage="_process_proposals_response_output",
            input_count=len(proposal_nodes),
            output_count=len(proposals),
            transformation_type="pydantic_proposal_models"
        )
        return proposals, last_cursor

    def _create_proposal_from_data(self, data: Dict) -> Proposal:
        """Create Proposal object from API data with common logic."""
        assert data, "Data is required"
        assert "id" in data, "Data must contain id"

        governor_info = data.get("governor", {})
        metadata = data.get("metadata", {})
        status = data["status"].upper()

        # Parse vote statistics using helper method
        vote_stats = data.get("voteStats", [])
        votes_for, votes_against, votes_abstain = self._parse_vote_statistics(
            vote_stats
        )

        return Proposal(
            id=data["id"],
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            state=ProposalState(status),
            created_at=datetime.fromisoformat(data["createdAt"].replace("Z", "+00:00")),
            start_block=0,  # Will be populated later if needed
            end_block=0,  # Will be populated later if needed
            votes_for=votes_for,
            votes_against=votes_against,
            votes_abstain=votes_abstain,
            dao_id=governor_info.get("id", ""),
            dao_name=governor_info.get("name", ""),
            url=f"https://www.tally.xyz/gov/{governor_info.get('id', '')}/proposal/{data['id']}",
        )

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_proposal_by_id(self, proposal_id: str) -> Optional[Proposal]:
        """Fetch a specific proposal by ID."""
        assert proposal_id, "Proposal ID cannot be empty"
        assert isinstance(proposal_id, str), "Proposal ID must be a string"

        # Fetch from API
        proposal = await self._fetch_proposal_from_api(proposal_id)
        return proposal

    async def _fetch_proposal_from_api(self, proposal_id: str) -> Optional[Proposal]:
        """Fetch proposal from API."""
        query = self._build_single_proposal_query()
        variables = {"input": {"id": proposal_id}}

        try:
            result = await self._make_request(query, variables)
            prop_data = result.get("data", {}).get("proposal")

            if not prop_data:
                return None

            return self._create_proposal_from_api_data(prop_data)

        except Exception as e:
            logfire.error(
                "Failed to fetch proposal", proposal_id=proposal_id, exc_info=e
            )
            raise

    def _create_proposal_from_api_data(self, prop_data: Dict) -> Proposal:
        """Create Proposal object from API data."""
        return self._create_proposal_from_data(prop_data)

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_multiple_proposals(self, proposal_ids: List[str]) -> List[Proposal]:
        """Fetch multiple proposals by their IDs."""
        # Use asyncio.gather to fetch proposals concurrently
        tasks = [self.get_proposal_by_id(pid) for pid in proposal_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        proposals: List[Proposal] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logfire.error(
                    "Failed to fetch proposal in batch", # Differentiate message
                    proposal_id=proposal_ids[i],
                    exc_info=result, # result is the exception object
                )
                continue
            if result is not None:
                proposals.append(result)

        return proposals

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_top_organizations_with_proposals(self) -> List[Dict]:
        """Fetch the top organizations with their 3 most active proposals each."""
        # Fetch data from API
        result = await self._get_organizations_data()
        return result

    async def _get_organizations_data(self) -> List[Dict]:
        """Internal method to fetch organizations data from API."""
        top_org_slugs = settings.top_organizations
        results = []

        logfire.info(
            "Starting to fetch top organizations with proposals",
            organization_slugs=top_org_slugs,
            org_count=len(top_org_slugs),
        )

        # First, get organization details for each slug
        for org_slug in top_org_slugs:
            try:
                logfire.info(f"Fetching organization: {org_slug}")

                # Get organization by slug
                org_data = await self._get_organization_by_slug(org_slug)
                if not org_data:
                    logfire.warning(f"Organization not found: {org_slug}")
                    continue

                logfire.info(
                    f"Found organization: {org_data['name']}",
                    org_id=org_data["id"],
                    proposals_count=org_data["proposals_count"],
                    has_active=org_data["has_active_proposals"],
                )

                # Get the 3 most active proposals for this organization
                proposals = await self._get_most_active_proposals_for_org(
                    org_data["id"], limit=3
                )

                logfire.info(
                    f"Retrieved proposals for {org_data['name']}",
                    proposals_found=len(proposals),
                    proposal_titles=[p.title for p in proposals],
                )

                results.append({"organization": org_data, "proposals": proposals})

            except Exception as e:
                logfire.error(
                    f"Failed to fetch data for organization {org_slug}",
                    org_slug=org_slug,
                    error_type=type(e).__name__,
                    exc_info=e
                )
                continue

        logfire.info(
            "Completed fetching organizations with proposals",
            total_orgs_found=len(results),
            total_proposals=sum(len(r["proposals"]) for r in results),
        )

        return results

    async def _get_organization_by_slug(self, slug: str) -> Optional[Dict]:
        """Get organization details by slug."""
        # First, let's try to find the organization by getting all orgs and filtering
        # since the direct slug filter might not be working as expected
        try:
            organizations, _ = await self.get_organizations(limit=200)

            for org in organizations:
                if org.slug.lower() == slug.lower():
                    return {
                        "id": org.id,
                        "name": org.name,
                        "slug": org.slug,
                        "chain_ids": org.chain_ids,
                        "token_ids": org.token_ids,
                        "governor_ids": org.governor_ids,
                        "has_active_proposals": org.has_active_proposals,
                        "proposals_count": org.proposals_count,
                        "delegates_count": org.delegates_count,
                        "delegates_votes_count": org.delegates_votes_count,
                        "token_owners_count": org.token_owners_count,
                    }

            return None

        except Exception as e:
            logfire.error(f"Failed to fetch organization by slug: {slug}", slug=slug, exc_info=e)
            return None

    async def _get_most_active_proposals_for_org(
        self, org_id: str, limit: int = 3
    ) -> List[Proposal]:
        """Get the most active proposals for an organization."""
        assert org_id, "Organization ID cannot be empty"
        assert limit > 0, "Limit must be positive"

        try:
            query = self._build_active_proposals_query()
            variables = self._build_active_proposals_variables(org_id, limit)
            result = await self._make_request(query, variables)
            proposals = self._process_active_proposals_response(result, limit)
            return proposals

        except Exception as e:
            logfire.error(
                f"Failed to fetch proposals for organization {org_id}", org_id=org_id, exc_info=e
            )
            return []

    def _build_active_proposals_query(self) -> str:
        """Build GraphQL query for fetching active proposals."""
        return """
        query GetActiveProposals($input: ProposalsInput!) {
            proposals(input: $input) {
                nodes {
                    ... on Proposal {
                        id
                        status
                        createdAt
                        metadata {
                            title
                            description
                        }
                        governor {
                            id
                            name
                        }
                        voteStats {
                            type
                            votesCount
                        }
                    }
                }
            }
        }
        """

    def _build_active_proposals_variables(self, org_id: str, limit: int) -> Dict:
        """Build variables for active proposals query."""
        assert org_id, "Organization ID is required"
        assert limit > 0, "Limit must be positive"

        return {
            "input": {
                "page": {"limit": limit * 2},  # Get more to filter for active ones
                "sort": {"sortBy": "id", "isDescending": True},  # Most recent first
                "filters": {"organizationId": org_id},
            }
        }

    def _process_active_proposals_response(
        self, result: Dict, limit: int
    ) -> List[Proposal]:
        """Process API response and categorize proposals by activity."""
        assert result, "API result cannot be empty"
        assert limit > 0, "Limit must be positive"

        proposals_data = result.get("data", {}).get("proposals", {})
        proposal_nodes = proposals_data.get("nodes", [])

        DataFlowLogger.log_data_transformation(
            stage="_process_active_proposals_response_input",
            input_count=len(proposal_nodes),
            output_count=0, # Input stage
            transformation_type="raw_tally_proposal_nodes_for_active_selection"
        )

        active_proposals = []
        other_proposals = []

        for prop in proposal_nodes:
            if not prop:
                continue

            proposal = self._create_proposal_from_active_node(prop)

            # Prioritize active proposals
            if proposal.state == ProposalState.ACTIVE:
                active_proposals.append(proposal)
            else:
                other_proposals.append(proposal)

        logger.debug(
            "_process_active_proposals_response: Categorized proposals.",
            active_count=len(active_proposals),
            other_count=len(other_proposals)
        )

        selected_proposals = self._select_top_proposals(active_proposals, other_proposals, limit)

        DataFlowLogger.log_data_transformation(
            stage="_process_active_proposals_response_output",
            input_count=len(proposal_nodes),
            output_count=len(selected_proposals),
            transformation_type="selected_pydantic_proposal_models"
        )
        return selected_proposals

    def _create_proposal_from_active_node(self, prop: Dict) -> Proposal:
        """Create Proposal object from active proposals API node data."""
        assert prop, "Proposal node data cannot be empty"
        assert "id" in prop, "Proposal node must contain id"
        return self._create_proposal_from_data(prop)

    def _select_top_proposals(
        self,
        active_proposals: List[Proposal],
        other_proposals: List[Proposal],
        limit: int,
    ) -> List[Proposal]:
        """Select top proposals prioritizing active ones first."""
        assert isinstance(active_proposals, list), "Active proposals must be a list"
        assert isinstance(other_proposals, list), "Other proposals must be a list"

        logger.debug(
            "_select_top_proposals: Selecting proposals.",
            active_available=len(active_proposals),
            other_available=len(other_proposals),
            requested_limit=limit
        )

        # Return active proposals first, then others, up to limit
        result_proposals = active_proposals[:limit]
        if len(result_proposals) < limit:
            needed_from_others = limit - len(result_proposals)
            logger.debug(
                "_select_top_proposals: Filling with other proposals.",
                filled_from_active=len(result_proposals),
                needed_from_others=needed_from_others
            )
            result_proposals.extend(other_proposals[:needed_from_others])

        logger.debug("_select_top_proposals: Selection complete.", final_count=len(result_proposals))
        return result_proposals[:limit]

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_organization_overview(self, org_id: str) -> Optional[Dict]:
        """Get comprehensive overview data for a specific organization."""
        assert org_id, "Organization ID cannot be empty"
        assert isinstance(org_id, str), "Organization ID must be a string"

        org_data = await self._fetch_organization_data(org_id)
        if not org_data:
            return None

        result = self._build_organization_overview_response(org_data)
        return result

    async def _fetch_organization_data(self, org_id: str) -> Optional[Dict]:
        """Fetch raw organization data from Tally API."""
        assert org_id, "Organization ID is required"
        assert len(org_id.strip()) > 0, "Organization ID cannot be empty string"

        query = self._build_organization_overview_query()
        variables = {"input": {"slug": org_id}}

        try:
            result = await self._make_request(query, variables)
            return result.get("data", {}).get("organization")
        except Exception as e:
            logfire.error(
                "Failed to fetch organization overview", org_id=org_id, exc_info=e
            )
            raise

    def _build_organization_overview_query(self) -> str:
        """Build GraphQL query for organization overview."""
        return """
        query GetOrganizationOverview($input: OrganizationInput!) {
            organization(input: $input) {
                id
                name
                slug
                chainIds
                tokenIds
                governorIds
                proposalsCount
                delegatesCount
                delegatesVotesCount
                tokenOwnersCount
                hasActiveProposals
                metadata {
                    description
                    color
                    icon
                }
            }
        }
        """

    def _build_organization_overview_response(self, org_data: Dict) -> Dict:
        """Build organization overview response from raw API data."""
        assert org_data, "Organization data cannot be empty"
        assert "id" in org_data, "Organization data must contain id"

        delegate_count = org_data.get("delegatesCount", 0)
        token_holder_count = org_data.get("tokenOwnersCount", 0)
        total_proposals = org_data.get("proposalsCount", 0)

        proposal_counts = self._calculate_proposal_counts_by_status(
            org_data, total_proposals
        )
        participation_rate = self._calculate_governance_participation_rate(
            delegate_count, token_holder_count
        )

        overview_data = {
            "organization_id": org_data["id"],
            "organization_name": org_data["name"],
            "organization_slug": org_data["slug"],
            "description": org_data.get("metadata", {}).get("description"),
            "delegate_count": delegate_count,
            "token_holder_count": token_holder_count,
            "total_proposals_count": total_proposals,
            "proposal_counts_by_status": proposal_counts,
            "recent_activity_count": proposal_counts.get("ACTIVE", 0),
            "governance_participation_rate": participation_rate,
        }

        logfire.info(
            "Fetched organization overview",
            org_id=org_data["id"],
            delegate_count=delegate_count,
        )
        return overview_data

    def _calculate_proposal_counts_by_status(
        self, org_data: Dict, total_proposals: int
    ) -> Dict[str, int]:
        """Calculate proposal counts by status from organization data."""
        assert org_data, "Organization data is required"
        assert isinstance(org_data, dict), "Organization data must be a dictionary"

        has_active_proposals = org_data.get("hasActiveProposals", False)
        proposal_counts = {}

        if has_active_proposals:
            # Estimate active proposals based on available data
            proposal_counts["ACTIVE"] = min(total_proposals, 3)

        return proposal_counts

    def _calculate_governance_participation_rate(
        self, delegate_count: int, token_holder_count: int
    ) -> float:
        """Calculate governance participation rate as delegates/token_holders."""
        assert delegate_count >= 0, "Delegate count must be non-negative"
        assert token_holder_count >= 0, "Token holder count must be non-negative"

        if token_holder_count == 0:
            return 0.0

        return min(delegate_count / token_holder_count, 1.0)

    def _parse_vote_statistics(
        self, vote_stats_data: List[Dict]
    ) -> tuple[str, str, str]:
        """Parse vote statistics from API response data.

        Args:
            vote_stats_data: List of vote statistics from API

        Returns:
            Tuple of (votes_for, votes_against, votes_abstain) as strings
        """
        assert isinstance(vote_stats_data, list), "Vote stats data must be a list"
        assert vote_stats_data is not None, "Vote stats data cannot be None"

        votes_for = "0"
        votes_against = "0"
        votes_abstain = "0"

        for vote_stat in vote_stats_data:
            vote_type = vote_stat.get("type", "").upper()
            vote_count = vote_stat.get("votesCount", "0")

            if vote_type == "FOR":
                votes_for = vote_count
            elif vote_type == "AGAINST":
                votes_against = vote_count
            elif vote_type == "ABSTAIN":
                votes_abstain = vote_count

        return votes_for, votes_against, votes_abstain

    def _sort_proposals_by_vote_count(
        self, proposals: List[Proposal], sort_order: SortOrder
    ) -> List[Proposal]:
        """Sort proposals by total vote count (for + against + abstain)."""
        assert proposals, "Proposals list cannot be empty"
        assert sort_order, "Sort order is required"

        def get_total_votes(proposal: Proposal) -> int:
            """Get total vote count for a proposal."""
            try:
                votes_for = int(proposal.votes_for) if proposal.votes_for else 0
                votes_against = (
                    int(proposal.votes_against) if proposal.votes_against else 0
                )
                votes_abstain = (
                    int(proposal.votes_abstain) if proposal.votes_abstain else 0
                )
                return votes_for + votes_against + votes_abstain
            except ValueError:
                # If vote counts are not valid numbers, treat as 0
                return 0

        reverse_order = sort_order == SortOrder.DESC
        sorted_proposals = sorted(proposals, key=get_total_votes, reverse=reverse_order)

        logfire.info(
            "Sorted proposals by vote count",
            count=len(sorted_proposals),
            sort_order=sort_order.value,
            top_vote_count=get_total_votes(sorted_proposals[0])
            if sorted_proposals
            else 0,
        )

        return sorted_proposals

    def _build_single_proposal_query(self) -> str:
        """Build GraphQL query for fetching a single proposal by ID."""
        return """
        query GetProposal($input: ProposalInput!) {
            proposal(input: $input) {
                ... on Proposal {
                    id
                    status
                    createdAt
                    metadata {
                        title
                        description
                    }
                    governor {
                        id
                        name
                    }
                    voteStats {
                        type
                        votesCount
                    }
                    organization {
                        id
                        name
                        slug
                    }
                }
            }
        }
        """

    @log_function_call(log_args=True, log_result=True, log_timing=True)
    async def get_proposal_votes(
        self, proposal_id: str, limit: int = 10
    ) -> List[ProposalVoter]:
        """Fetch individual vote data from the Tally API for a specific proposal.

        Args:
            proposal_id: The proposal ID to fetch votes for
            limit: Maximum number of voters to return (default: 10)

        Returns:
            List of ProposalVoter objects sorted by voting power
        """
        self._validate_proposal_votes_params(proposal_id, limit)

        # Fetch from API
        voters = await self._fetch_proposal_votes_from_api(proposal_id, limit)
        return voters

    def _validate_proposal_votes_params(self, proposal_id: str, limit: int) -> None:
        """Validate parameters for get_proposal_votes method."""
        assert proposal_id, "Proposal ID cannot be empty"
        assert isinstance(proposal_id, str), "Proposal ID must be a string"
        assert limit > 0, "Limit must be positive"
        assert isinstance(limit, int), "Limit must be an integer"

    async def _fetch_proposal_votes_from_api(
        self, proposal_id: str, limit: int
    ) -> List[ProposalVoter]:
        """Fetch proposal votes from the Tally API."""
        query = self._build_proposal_votes_query()
        variables = self._build_proposal_votes_variables(proposal_id, limit)

        try:
            result = await self._make_request(query, variables)
            return self._process_proposal_votes_response(result)
        except Exception as e:
            logfire.error(
                "Failed to fetch proposal votes",
                proposal_id=proposal_id,
                limit=limit,
                exc_info=e
            )
            return []

    def _build_proposal_votes_query(self) -> str:
        """Build GraphQL query for fetching proposal votes."""
        assert hasattr(self, "base_url"), "TallyService must be properly initialized"
        assert self.base_url, "Base URL must be configured"

        return """
        query GetProposalVotes($input: VotesInput!) {
            votes(input: $input) {
                nodes {
                    ... on OnchainVote {
                        amount
                        type
                        voter {
                            address
                        }
                    }
                }
            }
        }
        """

    def _build_proposal_votes_variables(self, proposal_id: str, limit: int) -> Dict:
        """Build variables for proposal votes query."""
        assert proposal_id, "Proposal ID is required"
        assert limit > 0, "Limit must be positive"

        return {
            "input": {"filters": {"proposalId": proposal_id}, "page": {"limit": limit}}
        }

    def _process_proposal_votes_response(self, result: Dict) -> List[ProposalVoter]:
        """Process proposal votes API response into ProposalVoter objects."""
        assert result, "API result cannot be empty"
        assert "data" in result, "API result must contain data"

        votes_data = result.get("data", {}).get("votes", {})
        vote_nodes = votes_data.get("nodes", [])

        DataFlowLogger.log_data_transformation(
            stage="_process_proposal_votes_response_input",
            input_count=len(vote_nodes),
            output_count=0, # Input stage
            transformation_type="raw_tally_vote_nodes"
        )

        voters = []
        invalid_vote_type_count = 0
        for vote in vote_nodes:
            if not vote:
                continue

            voter_info = vote.get("voter", {})
            address = voter_info.get("address", "")
            amount = vote.get("amount", "0")
            vote_type_str = vote.get("type", "").upper()

            # Convert string to VoteType enum
            try:
                vote_type = VoteType(vote_type_str)
            except ValueError:
                # Skip invalid vote types
                invalid_vote_type_count += 1
                continue

            voters.append(
                ProposalVoter(address=address, amount=amount, vote_type=vote_type)
            )

        if invalid_vote_type_count > 0:
            logger.warning(
                "_process_proposal_votes_response: Skipped entries due to invalid vote type.",
                skipped_count=invalid_vote_type_count,
                total_nodes=len(vote_nodes)
            )

        logfire.info("Processed proposal votes", count=len(voters)) # Keep this high-level info

        DataFlowLogger.log_data_transformation(
            stage="_process_proposal_votes_response_output",
            input_count=len(vote_nodes),
            output_count=len(voters),
            transformation_type="pydantic_proposal_voter_models",
            skipped_invalid_type=invalid_vote_type_count
        )
        return voters

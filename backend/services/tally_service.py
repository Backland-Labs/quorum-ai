"""Service for interacting with the Tally API."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import logfire

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
from utils.cache_utils import generate_cache_key, serialize_for_cache, deserialize_from_cache


class TallyService:
    """Service for interacting with the Tally API."""

    def __init__(self, cache_service: Optional[Any] = None) -> None:
        self.base_url = settings.tally_api_base_url
        self.api_key = settings.tally_api_key
        self.timeout = settings.request_timeout
        self.cache_service = cache_service

    async def _make_request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Make a GraphQL request to the Tally API."""
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Api-Key"] = self.api_key

        payload = {"query": query, "variables": variables or {}}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with logfire.span("tally_api_request", query=query):
                response = await client.post(
                    self.base_url, json=payload, headers=headers
                )
                response.raise_for_status()
                return response.json()

    async def get_organizations(
        self, limit: int = 100, after_cursor: Optional[str] = None
    ) -> tuple[List[Organization], Optional[str]]:
        """Fetch a list of organizations."""
        query = """
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

        page_input: Dict[str, Any] = {"limit": limit}
        if after_cursor:
            page_input["afterCursor"] = after_cursor

        variables = {
            "input": {
                "page": page_input,
                "sort": {"sortBy": "explore", "isDescending": True},
            }
        }

        try:
            result = await self._make_request(query, variables)
            org_data = result.get("data", {}).get("organizations", {})
            org_nodes = org_data.get("nodes", [])

            organizations = [
                Organization(
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
                for org in org_nodes
                if org
            ]

            last_cursor = org_data.get("pageInfo", {}).get("lastCursor")

            logfire.info("Fetched organizations", count=len(organizations))
            return organizations, last_cursor

        except Exception as e:
            logfire.error("Failed to fetch organizations", error=str(e))
            raise

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
            logfire.error("Failed to fetch DAOs", error=str(e))
            raise

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
            logfire.error("Failed to fetch DAO", dao_id=dao_id, error=str(e))
            raise

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
            # Fetch more proposals to ensure we have enough for sorting
            # Use 3x the requested limit to get a good selection for sorting
            fetch_filters = filters.model_copy()
            fetch_filters.limit = min(original_limit * 3, 100)  # Cap at API limit
            fetch_filters.sort_by = SortCriteria.CREATED_DATE  # Use default API sorting
            variables = self._build_proposals_variables(fetch_filters)
        else:
            variables = self._build_proposals_variables(filters)

        try:
            result = await self._make_request(query, variables)
            proposals, next_cursor = self._process_proposals_response(result)
            
            # Apply client-side sorting if needed
            if filters.sort_by == SortCriteria.VOTE_COUNT and proposals:
                proposals = self._sort_proposals_by_vote_count(proposals, filters.sort_order)
                # Limit to requested amount after sorting
                proposals = proposals[:original_limit]
                # Note: next_cursor may not be accurate for vote sorting
                # since we're doing client-side sorting
                if len(proposals) == original_limit:
                    next_cursor = None  # Don't provide cursor for vote sorting
            
            return proposals, next_cursor
        except Exception as e:
            logfire.error(
                "Failed to fetch proposals", filters=filters.dict(), error=str(e)
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

    def _build_page_input(self, filters: ProposalFilters) -> Dict:
        """Build pagination input for proposals query."""
        assert filters, "Filters are required"
        assert filters.limit > 0, "Limit must be positive"

        page_input = {"limit": filters.limit}
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

        proposals = [
            self._create_proposal_from_node(node) for node in proposal_nodes if node
        ]

        logfire.info("Fetched proposals", count=len(proposals))
        return proposals, last_cursor

    def _create_proposal_from_node(self, node: Dict) -> Proposal:
        """Create Proposal object from API node data."""
        assert node, "Node data is required"
        assert "id" in node, "Node must contain id"

        governor_info = node.get("governor", {})
        metadata = node.get("metadata", {})
        status = node["status"].upper()
        
        # Parse vote statistics using helper method
        vote_stats = node.get("voteStats", [])
        votes_for, votes_against, votes_abstain = self._parse_vote_statistics(vote_stats)

        return Proposal(
            id=node["id"],
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            state=ProposalState(status),
            created_at=datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00")),
            start_block=0,  # Will be populated later if needed
            end_block=0,  # Will be populated later if needed
            votes_for=votes_for,
            votes_against=votes_against,
            votes_abstain=votes_abstain,
            dao_id=governor_info.get("id", ""),
            dao_name=governor_info.get("name", ""),
            url=f"https://www.tally.xyz/gov/{governor_info.get('id', '')}/proposal/{node['id']}",
        )

    async def get_proposal_by_id(self, proposal_id: str) -> Optional[Proposal]:
        """Fetch a specific proposal by ID."""
        assert proposal_id, "Proposal ID cannot be empty"
        assert isinstance(proposal_id, str), "Proposal ID must be a string"

        # Generate cache key
        cache_key = generate_cache_key("get_proposal_by_id", (proposal_id,), {})
        
        # Try to get from cache if cache service is available
        if self.cache_service and self.cache_service.is_available:
            try:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result is not None:
                    logfire.info("Cache hit for get_proposal_by_id", proposal_id=proposal_id)
                    cached_data = deserialize_from_cache(cached_result)
                    # Reconstruct Proposal object from cached data
                    if isinstance(cached_data, dict):
                        return Proposal(**cached_data)
                    return cached_data
                logfire.info("Cache miss for get_proposal_by_id", proposal_id=proposal_id)
            except Exception as e:
                logfire.warning(f"Cache error for get_proposal_by_id: {e}")

        query = self._build_single_proposal_query()
        variables = {"id": proposal_id}

        try:
            result = await self._make_request(query, variables)
            prop_data = result.get("data", {}).get("proposal")

            if not prop_data:
                return None

            proposal = self._create_proposal_from_api_data(prop_data)
            
            # Cache the result with dynamic TTL based on proposal status
            if self.cache_service and self.cache_service.is_available and proposal:
                try:
                    ttl = self._get_proposal_cache_ttl(proposal.state)
                    serialized_result = serialize_for_cache(proposal)
                    await self.cache_service.set(cache_key, serialized_result, expire_seconds=ttl)
                    logfire.info("Cached get_proposal_by_id result", proposal_id=proposal_id, ttl=ttl)
                except Exception as e:
                    logfire.warning(f"Failed to cache get_proposal_by_id result: {e}")
            
            return proposal

        except Exception as e:
            logfire.error(
                "Failed to fetch proposal", proposal_id=proposal_id, error=str(e)
            )
            raise

    def _get_proposal_cache_ttl(self, state: ProposalState) -> int:
        """Get cache TTL based on proposal state."""
        # Active proposals change frequently, cache for 30 minutes
        if state == ProposalState.ACTIVE:
            return 1800  # 30 minutes
        
        # Completed proposals (succeeded, defeated, etc.) are stable, cache for 6 hours
        return 21600  # 6 hours

    def _create_proposal_from_api_data(self, prop_data: Dict) -> Proposal:
        """Create Proposal object from API data."""
        governor_info = prop_data.get("governor", {})
        metadata = prop_data.get("metadata", {})

        # Convert API status to our enum format
        status = prop_data["status"].upper()
        
        # Parse vote statistics using helper method
        vote_stats = prop_data.get("voteStats", [])
        votes_for, votes_against, votes_abstain = self._parse_vote_statistics(vote_stats)

        return Proposal(
            id=prop_data["id"],
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            state=ProposalState(status),
            created_at=datetime.fromisoformat(
                prop_data["createdAt"].replace("Z", "+00:00")
            ),
            start_block=0,  # Will be populated later if needed
            end_block=0,  # Will be populated later if needed
            votes_for=votes_for,
            votes_against=votes_against,
            votes_abstain=votes_abstain,
            dao_id=governor_info.get("id", ""),
            dao_name=governor_info.get("name", ""),
            url=f"https://www.tally.xyz/gov/{governor_info.get('id', '')}/proposal/{prop_data['id']}",
        )

    # Cache invalidation methods
    async def invalidate_organization_cache(self, org_id: str) -> int:
        """Invalidate all cache entries related to a specific organization."""
        if not self.cache_service or not self.cache_service.is_available:
            return 0
            
        try:
            # Find all keys related to this organization
            patterns = [
                f"cache:*{org_id}*",
                "cache:get_top_organizations_with_proposals:*",  # This might contain the org
            ]
            
            total_deleted = 0
            for pattern in patterns:
                keys = await self.cache_service.keys(pattern)
                if keys:
                    deleted_count = await self.cache_service.delete(*keys)
                    total_deleted += deleted_count
            
            logfire.info(f"Invalidated {total_deleted} cache keys for organization: {org_id}")
            return total_deleted
            
        except Exception as e:
            logfire.warning(f"Failed to invalidate organization cache: {e}")
            return 0

    async def invalidate_proposal_cache(self, proposal_id: str) -> int:
        """Invalidate all cache entries related to a specific proposal."""
        if not self.cache_service or not self.cache_service.is_available:
            return 0
            
        try:
            # Find all keys related to this proposal
            patterns = [
                f"cache:*{proposal_id}*",
            ]
            
            total_deleted = 0
            for pattern in patterns:
                keys = await self.cache_service.keys(pattern)
                if keys:
                    deleted_count = await self.cache_service.delete(*keys)
                    total_deleted += deleted_count
            
            logfire.info(f"Invalidated {total_deleted} cache keys for proposal: {proposal_id}")
            return total_deleted
            
        except Exception as e:
            logfire.warning(f"Failed to invalidate proposal cache: {e}")
            return 0

    async def invalidate_all_cache(self) -> int:
        """Invalidate all Tally-related cache entries."""
        if not self.cache_service or not self.cache_service.is_available:
            return 0
            
        try:
            # Find all cache keys
            keys = await self.cache_service.keys("cache:*")
            if keys:
                deleted_count = await self.cache_service.delete(*keys)
                logfire.info(f"Invalidated {deleted_count} total cache keys")
                return deleted_count
            return 0
            
        except Exception as e:
            logfire.warning(f"Failed to invalidate all cache: {e}")
            return 0

    # Cache warming methods
    async def warm_top_organizations_cache(self) -> bool:
        """Warm the cache for top organizations data."""
        if not self.cache_service or not self.cache_service.is_available:
            return False
            
        try:
            # Check if cache already exists
            cache_key = generate_cache_key("get_top_organizations_with_proposals", (), {})
            
            if await self.cache_service.exists(cache_key):
                logfire.info("Top organizations cache already warmed")
                return True
            
            # Fetch and cache the data
            data = await self._get_organizations_data()
            if data:
                serialized_data = serialize_for_cache(data)
                await self.cache_service.set(cache_key, serialized_data, expire_seconds=7200)  # 2 hours
                logfire.info("Successfully warmed top organizations cache")
                return True
            
            return False
            
        except Exception as e:
            logfire.warning(f"Failed to warm top organizations cache: {e}")
            return False

    async def warm_organization_overview_cache(self) -> bool:
        """Warm the cache for organization overview data for top organizations."""
        if not self.cache_service or not self.cache_service.is_available:
            return False
            
        try:
            top_orgs = settings.top_organizations
            success_count = 0
            
            for org_slug in top_orgs:
                try:
                    cache_key = generate_cache_key("get_organization_overview", (org_slug,), {})
                    
                    # Skip if already cached
                    if await self.cache_service.exists(cache_key):
                        continue
                    
                    # Fetch and cache the overview data
                    org_data = await self._fetch_organization_data(org_slug)
                    if org_data:
                        overview_data = self._build_organization_overview_response(org_data)
                        serialized_data = serialize_for_cache(overview_data)
                        await self.cache_service.set(cache_key, serialized_data, expire_seconds=7200)  # 2 hours
                        success_count += 1
                        
                except Exception as e:
                    logfire.warning(f"Failed to warm cache for organization {org_slug}: {e}")
                    continue
            
            logfire.info(f"Successfully warmed overview cache for {success_count}/{len(top_orgs)} organizations")
            return True
            
        except Exception as e:
            logfire.warning(f"Failed to warm organization overview cache: {e}")
            return False

    async def get_multiple_proposals(self, proposal_ids: List[str]) -> List[Proposal]:
        """Fetch multiple proposals by their IDs."""
        # Use asyncio.gather to fetch proposals concurrently
        tasks = [self.get_proposal_by_id(pid) for pid in proposal_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        proposals: List[Proposal] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logfire.error(
                    "Failed to fetch proposal",
                    proposal_id=proposal_ids[i],
                    error=str(result),
                )
                continue
            if result is not None:
                proposals.append(result)

        return proposals

    async def get_top_organizations_with_proposals(self) -> List[Dict]:
        """Fetch the top organizations with their 3 most active proposals each."""
        # Generate cache key
        cache_key = generate_cache_key("get_top_organizations_with_proposals", (), {})
        
        # Try to get from cache if cache service is available
        if self.cache_service and self.cache_service.is_available:
            try:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result is not None:
                    logfire.info("Cache hit for get_top_organizations_with_proposals")
                    return deserialize_from_cache(cached_result)
                logfire.info("Cache miss for get_top_organizations_with_proposals")
            except Exception as e:
                logfire.warning(f"Cache error for get_top_organizations_with_proposals: {e}")
        
        # Fetch data from API
        result = await self._get_organizations_data()
        
        # Cache the result with 2-hour TTL if cache service is available
        if self.cache_service and self.cache_service.is_available and result:
            try:
                serialized_result = serialize_for_cache(result)
                await self.cache_service.set(cache_key, serialized_result, expire_seconds=7200)  # 2 hours
                logfire.info("Cached get_top_organizations_with_proposals result")
            except Exception as e:
                logfire.warning(f"Failed to cache get_top_organizations_with_proposals result: {e}")
        
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
                    error=str(e),
                    error_type=type(e).__name__,
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
            logfire.error(f"Failed to fetch organization by slug: {slug}", error=str(e))
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
                f"Failed to fetch proposals for organization {org_id}", error=str(e)
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

        return self._select_top_proposals(active_proposals, other_proposals, limit)

    def _create_proposal_from_active_node(self, prop: Dict) -> Proposal:
        """Create Proposal object from active proposals API node data."""
        assert prop, "Proposal node data cannot be empty"
        assert "id" in prop, "Proposal node must contain id"
        
        governor_info = prop.get("governor", {})
        metadata = prop.get("metadata", {})
        status = prop["status"].upper()

        # Parse vote statistics using helper method
        vote_stats = prop.get("voteStats", [])
        votes_for, votes_against, votes_abstain = self._parse_vote_statistics(vote_stats)

        return Proposal(
            id=prop["id"],
            title=metadata.get("title", ""),
            description=metadata.get("description", ""),
            state=ProposalState(status),
            created_at=datetime.fromisoformat(
                prop["createdAt"].replace("Z", "+00:00")
            ),
            start_block=0,
            end_block=0,
            votes_for=votes_for,
            votes_against=votes_against,
            votes_abstain=votes_abstain,
            dao_id=governor_info.get("id", ""),
            dao_name=governor_info.get("name", ""),
            url=f"https://www.tally.xyz/gov/{governor_info.get('id', '')}/proposal/{prop['id']}",
        )

    def _select_top_proposals(
        self, active_proposals: List[Proposal], other_proposals: List[Proposal], limit: int
    ) -> List[Proposal]:
        """Select top proposals prioritizing active ones first."""
        assert isinstance(active_proposals, list), "Active proposals must be a list"
        assert isinstance(other_proposals, list), "Other proposals must be a list"
        
        # Return active proposals first, then others, up to limit
        result_proposals = active_proposals[:limit]
        if len(result_proposals) < limit:
            result_proposals.extend(
                other_proposals[: limit - len(result_proposals)]
            )

        return result_proposals[:limit]

    async def get_organization_overview(self, org_id: str) -> Optional[Dict]:
        """Get comprehensive overview data for a specific organization."""
        assert org_id, "Organization ID cannot be empty"
        assert isinstance(org_id, str), "Organization ID must be a string"

        # Generate cache key
        cache_key = generate_cache_key("get_organization_overview", (org_id,), {})
        
        # Try to get from cache if cache service is available
        if self.cache_service and self.cache_service.is_available:
            try:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result is not None:
                    logfire.info("Cache hit for get_organization_overview", org_id=org_id)
                    return deserialize_from_cache(cached_result)
                logfire.info("Cache miss for get_organization_overview", org_id=org_id)
            except Exception as e:
                logfire.warning(f"Cache error for get_organization_overview: {e}")

        org_data = await self._fetch_organization_data(org_id)
        if not org_data:
            return None

        result = self._build_organization_overview_response(org_data)
        
        # Cache the result with 2-hour TTL if cache service is available
        if self.cache_service and self.cache_service.is_available and result:
            try:
                serialized_result = serialize_for_cache(result)
                await self.cache_service.set(cache_key, serialized_result, expire_seconds=7200)  # 2 hours
                logfire.info("Cached get_organization_overview result", org_id=org_id)
            except Exception as e:
                logfire.warning(f"Failed to cache get_organization_overview result: {e}")
        
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
                "Failed to fetch organization overview", org_id=org_id, error=str(e)
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

    def _parse_vote_statistics(self, vote_stats_data: List[Dict]) -> tuple[str, str, str]:
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
                votes_against = int(proposal.votes_against) if proposal.votes_against else 0
                votes_abstain = int(proposal.votes_abstain) if proposal.votes_abstain else 0
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
            top_vote_count=get_total_votes(sorted_proposals[0]) if sorted_proposals else 0
        )
        
        return sorted_proposals

    def _build_single_proposal_query(self) -> str:
        """Build GraphQL query for fetching a single proposal by ID."""
        return """
        query GetProposal($id: ID!) {
            proposal(id: $id) {
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
        """

    async def get_proposal_votes(self, proposal_id: str, limit: int = 10) -> List[ProposalVoter]:
        """Fetch individual vote data from the Tally API for a specific proposal.
        
        Args:
            proposal_id: The proposal ID to fetch votes for
            limit: Maximum number of voters to return (default: 10)
            
        Returns:
            List of ProposalVoter objects sorted by voting power
        """
        assert proposal_id, "Proposal ID cannot be empty"
        assert limit > 0, "Limit must be positive"
        
        # Generate cache key
        cache_key = generate_cache_key("proposal_votes", (proposal_id, limit), {})
        
        # Try to get from cache if cache service is available
        if self.cache_service and self.cache_service.is_available:
            try:
                cached_result = await self.cache_service.get(cache_key)
                if cached_result is not None:
                    logfire.info("Cache hit for get_proposal_votes", proposal_id=proposal_id, limit=limit)
                    cached_data = deserialize_from_cache(cached_result)
                    # Reconstruct ProposalVoter objects from cached data
                    if isinstance(cached_data, list):
                        return [ProposalVoter(**item) if isinstance(item, dict) else item for item in cached_data]
                    return cached_data
                logfire.info("Cache miss for get_proposal_votes", proposal_id=proposal_id, limit=limit)
            except Exception as e:
                logfire.warning(f"Cache error for get_proposal_votes: {e}")
        
        query = self._build_proposal_votes_query()
        variables = self._build_proposal_votes_variables(proposal_id, limit)
        
        try:
            result = await self._make_request(query, variables)
            voters = self._process_proposal_votes_response(result)
            
            # Cache the result with dynamic TTL based on proposal state
            if self.cache_service and self.cache_service.is_available and voters is not None:
                try:
                    proposal_state = await self._get_proposal_state(proposal_id)
                    ttl = self._get_proposal_votes_cache_ttl(proposal_state)
                    serialized_result = serialize_for_cache(voters)
                    await self.cache_service.set(cache_key, serialized_result, expire_seconds=ttl)
                    logfire.info("Cached get_proposal_votes result", proposal_id=proposal_id, limit=limit, ttl=ttl)
                except Exception as e:
                    logfire.warning(f"Failed to cache get_proposal_votes result: {e}")
            
            return voters
        except Exception as e:
            logfire.error(
                "Failed to fetch proposal votes", 
                proposal_id=proposal_id, 
                limit=limit,
                error=str(e)
            )
            # Return empty list on failure as per requirement
            return []

    def _build_proposal_votes_query(self) -> str:
        """Build GraphQL query for fetching proposal votes."""
        return """
        query GetProposalVotes($input: VotesInput!) {
            votes(input: $input) {
                nodes {
                    amount
                    type
                    voter {
                        address
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
            "input": {
                "proposalId": proposal_id,
                "limit": limit
            }
        }

    def _process_proposal_votes_response(self, result: Dict) -> List[ProposalVoter]:
        """Process proposal votes API response into ProposalVoter objects."""
        assert result, "API result cannot be empty"
        assert "data" in result, "API result must contain data"
        
        votes_data = result.get("data", {}).get("votes", {})
        vote_nodes = votes_data.get("nodes", [])
        
        voters = []
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
                continue
                
            voters.append(ProposalVoter(
                address=address,
                amount=amount,
                vote_type=vote_type
            ))
        
        logfire.info("Processed proposal votes", count=len(voters))
        return voters

    async def _get_proposal_state(self, proposal_id: str) -> ProposalState:
        """Get the current state of a proposal."""
        assert proposal_id, "Proposal ID is required"
        
        try:
            proposal = await self.get_proposal_by_id(proposal_id)
            if proposal:
                return proposal.state
            # Default to ACTIVE if proposal not found
            return ProposalState.ACTIVE
        except Exception as e:
            logfire.warning(f"Failed to get proposal state for {proposal_id}: {e}")
            # Default to ACTIVE for safety (shorter cache TTL)
            return ProposalState.ACTIVE

    def _get_proposal_votes_cache_ttl(self, state: ProposalState) -> int:
        """Get cache TTL for proposal votes based on proposal state."""
        assert state, "Proposal state is required"
        
        # Active proposals: 15 minutes TTL
        if state == ProposalState.ACTIVE:
            return 900  # 15 minutes
        
        # Completed proposals (succeeded, executed, queued): 6 hours TTL
        if state in [ProposalState.SUCCEEDED, ProposalState.EXECUTED, ProposalState.QUEUED]:
            return 21600  # 6 hours
        
        # Failed/expired proposals (defeated, expired, canceled): 24 hours TTL
        if state in [ProposalState.DEFEATED, ProposalState.EXPIRED, ProposalState.CANCELED]:
            return 86400  # 24 hours
        
        # Default to 6 hours for other states
        return 21600

    async def invalidate_proposal_votes_cache(self, proposal_id: str) -> int:
        """Invalidate all cache entries related to proposal votes for a specific proposal.
        
        Args:
            proposal_id: The proposal ID to invalidate votes cache for
            
        Returns:
            Number of cache entries deleted
        """
        assert proposal_id, "Proposal ID cannot be empty"
        
        if not self.cache_service or not self.cache_service.is_available:
            return 0
            
        try:
            # Find all keys related to this proposal's votes
            pattern = f"*{proposal_id}*"
            keys = await self.cache_service.keys(pattern)
            
            if keys:
                deleted_count = await self.cache_service.delete(*keys)
                logfire.info(f"Invalidated {deleted_count} proposal votes cache keys for proposal: {proposal_id}")
                return deleted_count
            
            return 0
            
        except Exception as e:
            logfire.warning(f"Failed to invalidate proposal votes cache: {e}")
            return 0

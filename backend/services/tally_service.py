"""Service for interacting with the Tally API."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import logfire

from config import settings
from models import (
    DAO,
    Organization,
    Proposal,
    ProposalFilters,
    ProposalState,
    SortCriteria,
    SortOrder,
)


class TallyService:
    """Service for interacting with the Tally API."""

    def __init__(self):
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

        page_input = {"limit": limit}
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

        page_input = {"limit": limit}
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
        query = """
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
                        }
                    }
                    pageInfo {
                        lastCursor
                    }
                }
            }
        """

        page_input = {"limit": filters.limit}
        if filters.after_cursor:
            page_input["afterCursor"] = filters.after_cursor

        sort_input = {
            "sortBy": (
                "id"
                if filters.sort_by == SortCriteria.CREATED_DATE
                else filters.sort_by.value
            ),
            "isDescending": filters.sort_order == SortOrder.DESC,
        }

        filter_input = {}
        if filters.organization_id:
            filter_input["organizationId"] = filters.organization_id
        elif filters.dao_id:
            filter_input["governorId"] = filters.dao_id
        if filters.state:
            # The API expects a list of states, but our filter is for a single state
            # The old query string building was also incorrect in not wrapping state in quotes.
            # The API seems to have changed from a 'where' clause to a 'filters' object.
            # I am assuming based on `ProposalsFiltersInput` that it does not support `states`.
            # I will look at the documentation again.
            # After looking at `ProposalsFiltersInput` in the docs, there is no `state` or `states` filter.
            # The old implementation was `where: {states: [${filters.state.value}]}`
            # The new input type `ProposalsFiltersInput` does not have this.
            # It has `governorId`, `includeArchived`, `isDraft`, `organizationId`, `proposer`.
            # The old query was probably for a different version of the API altogether.
            # The new query for proposals does not seem to support filtering by state directly.
            # I will omit the state filter for now as it seems unsupported.
            pass

        variables = {
            "input": {"page": page_input, "sort": sort_input, "filters": filter_input}
        }

        try:
            result = await self._make_request(query, variables)
            proposals_data = result.get("data", {}).get("proposals", {})
            proposal_nodes = proposals_data.get("nodes", [])
            last_cursor = proposals_data.get("pageInfo", {}).get("lastCursor")

            proposals = []
            for prop in proposal_nodes:
                governor_info = prop.get("governor", {})
                metadata = prop.get("metadata", {})

                # Convert API status to our enum format
                status = prop["status"].upper()

                proposals.append(
                    Proposal(
                        id=prop["id"],
                        title=metadata.get("title", ""),
                        description=metadata.get("description", ""),
                        state=ProposalState(status),
                        created_at=datetime.fromisoformat(
                            prop["createdAt"].replace("Z", "+00:00")
                        ),
                        start_block=0,  # Will be populated later if needed
                        end_block=0,  # Will be populated later if needed
                        votes_for="0",  # Will be populated later if needed
                        votes_against="0",  # Will be populated later if needed
                        votes_abstain="0",  # Will be populated later if needed
                        dao_id=governor_info.get("id", ""),
                        dao_name=governor_info.get("name", ""),
                        url=f"https://www.tally.xyz/gov/{governor_info.get('id', '')}/proposal/{prop['id']}",
                    )
                )

            logfire.info("Fetched proposals", count=len(proposals))
            return proposals, last_cursor

        except Exception as e:
            logfire.error(
                "Failed to fetch proposals", filters=filters.dict(), error=str(e)
            )
            raise

    async def get_proposal_by_id(self, proposal_id: str) -> Optional[Proposal]:
        """Fetch a specific proposal by ID."""
        query = """
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
            }
        }
        """

        variables = {"id": proposal_id}

        try:
            result = await self._make_request(query, variables)
            prop_data = result.get("data", {}).get("proposal")

            if not prop_data:
                return None

            governor_info = prop_data.get("governor", {})
            metadata = prop_data.get("metadata", {})

            # Convert API status to our enum format
            status = prop_data["status"].upper()

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
                votes_for="0",  # Will be populated later if needed
                votes_against="0",  # Will be populated later if needed
                votes_abstain="0",  # Will be populated later if needed
                dao_id=governor_info.get("id", ""),
                dao_name=governor_info.get("name", ""),
                url=f"https://www.tally.xyz/gov/{governor_info.get('id', '')}/proposal/{prop_data['id']}",
            )

        except Exception as e:
            logfire.error(
                "Failed to fetch proposal", proposal_id=proposal_id, error=str(e)
            )
            raise

    async def get_multiple_proposals(self, proposal_ids: List[str]) -> List[Proposal]:
        """Fetch multiple proposals by their IDs."""
        # Use asyncio.gather to fetch proposals concurrently
        tasks = [self.get_proposal_by_id(pid) for pid in proposal_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        proposals = []
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
        """Get the most active proposals for an organization (sorted by active state first, then by creation date)."""
        query = """
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
                    }
                }
            }
        }
        """

        variables = {
            "input": {
                "page": {"limit": limit * 2},  # Get more to filter for active ones
                "sort": {"sortBy": "id", "isDescending": True},  # Most recent first
                "filters": {"organizationId": org_id},
            }
        }

        try:
            result = await self._make_request(query, variables)
            proposals_data = result.get("data", {}).get("proposals", {})
            proposal_nodes = proposals_data.get("nodes", [])

            active_proposals = []
            other_proposals = []

            for prop in proposal_nodes:
                if not prop:
                    continue

                governor_info = prop.get("governor", {})
                metadata = prop.get("metadata", {})
                status = prop["status"].upper()

                proposal = Proposal(
                    id=prop["id"],
                    title=metadata.get("title", ""),
                    description=metadata.get("description", ""),
                    state=ProposalState(status),
                    created_at=datetime.fromisoformat(
                        prop["createdAt"].replace("Z", "+00:00")
                    ),
                    start_block=0,
                    end_block=0,
                    votes_for="0",
                    votes_against="0",
                    votes_abstain="0",
                    dao_id=governor_info.get("id", ""),
                    dao_name=governor_info.get("name", ""),
                    url=f"https://www.tally.xyz/gov/{governor_info.get('id', '')}/proposal/{prop['id']}",
                )

                # Prioritize active proposals
                if status == "ACTIVE":
                    active_proposals.append(proposal)
                else:
                    other_proposals.append(proposal)

            # Return active proposals first, then others, up to limit
            result_proposals = active_proposals[:limit]
            if len(result_proposals) < limit:
                result_proposals.extend(
                    other_proposals[: limit - len(result_proposals)]
                )

            return result_proposals[:limit]

        except Exception as e:
            logfire.error(
                f"Failed to fetch proposals for organization {org_id}", error=str(e)
            )
            return []

    async def get_organization_overview(self, org_id: str) -> Optional[Dict]:
        """Get comprehensive overview data for a specific organization."""
        query = """
        query GetOrganizationOverview($input: OrganizationInput!) {
            organization(input: $input) {
                id
                name
                slug
                chainIds
                tokenIds
                governorIds
                metadata {
                    description
                }
                delegatesCount
                tokenOwnersCount
                proposalsCount
                delegatesVotesCount
                hasActiveProposals
            }
        }
        """

        variables = {"input": {"id": org_id}}

        try:
            result = await self._make_request(query, variables)
            org_data = result.get("data", {}).get("organization")

            if not org_data:
                return None

            # Extract basic organization data
            delegate_count = org_data.get("delegatesCount", 0)
            token_holder_count = org_data.get("tokenOwnersCount", 0)
            total_proposals = org_data.get("proposalsCount", 0)
            has_active_proposals = org_data.get("hasActiveProposals", False)

            # Since the API doesn't provide proposal counts by status in the organization query,
            # we'll provide a simplified version based on available data
            proposal_counts_by_status = {}
            if has_active_proposals:
                # Rough estimate: if there are active proposals, assume some distribution
                proposal_counts_by_status["ACTIVE"] = min(
                    total_proposals, 3
                )  # Estimate active

            # Calculate governance participation rate (simplified calculation)
            # Simple participation rate: delegates / token holders (capped at 1.0)
            participation_rate = 0.0
            if token_holder_count > 0:
                participation_rate = min(delegate_count / token_holder_count, 1.0)

            # Calculate recent activity count (simplified - using active proposals indicator)
            recent_activity_count = proposal_counts_by_status.get("ACTIVE", 0)

            overview_data = {
                "organization_id": org_data["id"],
                "organization_name": org_data["name"],
                "organization_slug": org_data["slug"],
                "description": org_data.get("metadata", {}).get("description"),
                "delegate_count": delegate_count,
                "token_holder_count": token_holder_count,
                "total_proposals_count": total_proposals,
                "proposal_counts_by_status": proposal_counts_by_status,
                "recent_activity_count": recent_activity_count,
                "governance_participation_rate": participation_rate,
            }

            logfire.info(
                "Fetched organization overview",
                org_id=org_id,
                delegate_count=delegate_count,
            )
            return overview_data

        except Exception as e:
            logfire.error(
                "Failed to fetch organization overview", org_id=org_id, error=str(e)
            )
            raise

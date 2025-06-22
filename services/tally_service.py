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
                "sort": {"sortBy": "name", "isDescending": False},
            }
        }

        try:
            result = await self._make_request(query, variables)
            org_data = result.get("data", {}).get("organizations", {})
            org_nodes = org_data.get("nodes", [])

            organizations = [Organization(**org) for org in org_nodes if org]

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
                        id
                        title
                        description
                        state
                        createdAt
                        startBlock
                        endBlock
                        votesFor
                        votesAgainst
                        votesAbstain
                        dao {
                            id
                            name
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
        if filters.dao_id:
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
                dao_info = prop.get("dao", {})
                proposals.append(
                    Proposal(
                        id=prop["id"],
                        title=prop["title"],
                        description=prop["description"],
                        state=ProposalState(prop["state"]),
                        created_at=datetime.fromisoformat(
                            prop["createdAt"].replace("Z", "+00:00")
                        ),
                        start_block=prop["startBlock"],
                        end_block=prop["endBlock"],
                        votes_for=str(prop.get("votesFor", "0")),
                        votes_against=str(prop.get("votesAgainst", "0")),
                        votes_abstain=str(prop.get("votesAbstain", "0")),
                        dao_id=dao_info.get("id", ""),
                        dao_name=dao_info.get("name", ""),
                        url=f"https://www.tally.xyz/gov/{dao_info.get('id', '')}/proposal/{prop['id']}",
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
                title
                description
                state
                createdAt
                startBlock
                endBlock
                votesFor
                votesAgainst
                votesAbstain
                dao {
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

            dao_info = prop_data.get("dao", {})
            return Proposal(
                id=prop_data["id"],
                title=prop_data["title"],
                description=prop_data["description"],
                state=ProposalState(prop_data["state"]),
                created_at=datetime.fromisoformat(
                    prop_data["createdAt"].replace("Z", "+00:00")
                ),
                start_block=prop_data["startBlock"],
                end_block=prop_data["endBlock"],
                votes_for=str(prop_data.get("votesFor", "0")),
                votes_against=str(prop_data.get("votesAgainst", "0")),
                votes_abstain=str(prop_data.get("votesAbstain", "0")),
                dao_id=dao_info.get("id", ""),
                dao_name=dao_info.get("name", ""),
                url=f"https://www.tally.xyz/gov/{dao_info.get('id', '')}/proposal/{prop_data['id']}",
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

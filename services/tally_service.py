"""Service for interacting with the Tally API."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import logfire

from config import settings
from models import DAO, Proposal, ProposalFilters, ProposalState, SortOrder


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
            
        payload = {
            "query": query,
            "variables": variables or {}
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with logfire.span("tally_api_request", query=query):
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
    
    async def get_daos(self, organization_id: str, limit: int = 50, offset: int = 0, sort_desc: bool = True) -> List[DAO]:
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
            }
        }
        """
        
        variables = {
            "input": {
                "page": {"limit": limit, "offset": offset},
                "sort": {"sortBy": "id", "isDescending": sort_desc},
                "filters": {"organizationId": organization_id}
            }
        }
        
        try:
            result = await self._make_request(query, variables)
            dao_data = result.get("data", {}).get("governors", {}).get("nodes", [])
            
            daos = []
            for dao in dao_data:
                if not dao:
                    continue
                daos.append(DAO(
                    id=dao["id"],
                    name=dao["name"],
                    slug=dao["slug"],
                    description=dao.get("metadata", {}).get("description"),
                    organization_id=dao["organization"]["id"],
                    active_proposals_count=dao.get("proposalStats", {}).get("active", 0),
                    total_proposals_count=dao.get("proposalStats", {}).get("total", 0)
                ))
            
            logfire.info("Fetched DAOs", count=len(daos))
            return daos
            
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
                active_proposals_count=dao_data.get("proposalStats", {}).get("active", 0),
                total_proposals_count=dao_data.get("proposalStats", {}).get("total", 0)
            )
            
        except Exception as e:
            logfire.error("Failed to fetch DAO", dao_id=dao_id, error=str(e))
            raise
    
    async def get_proposals(self, filters: ProposalFilters) -> tuple[List[Proposal], int]:
        """Fetch proposals based on filters using the official Tally ProposalsInput schema."""
        query = """
        query GetProposals($input: ProposalsInput!) {
            proposals(input: $input) {
                pageInfo {
                    count
                }
                nodes {
                    ... on Proposal {
                        id
                        metadata {
                            title
                            description
                        }
                        status
                        start {
                            ... on Block { timestamp }
                            ... on BlocklessTimestamp { timestamp }
                        }
                        end {
                            ... on Block { timestamp }
                            ... on BlocklessTimestamp { timestamp }
                        }
                        voteStats {
                            type
                            votesCount
                        }
                        governor {
                            id
                            name
                        }
                        organization {
                            id
                            name
                        }
                    }
                }
            }
        }
        """

        # Build ProposalsInput variables based on our local ProposalFilters model
        sort_input = {"sortBy": "id", "isDescending": filters.sort_order == SortOrder.DESC}

        # Convert our local ProposalState enum to Tally's ProposalStatus (lower-case)
        filters_input: Dict[str, object] = {}
        if filters.dao_id:
            # In the Tally schema the field is governorId (AccountID)
            filters_input["governorId"] = filters.dao_id
        if filters.state:
            filters_input["status"] = filters.state.value.lower()

        page_input: Dict[str, object] = {
            "limit": filters.limit,
        }
        # The legacy tests rely on offset – we approximate offset based pagination by converting
        # the offset to a string cursor. If offset is 0 we simply omit the cursor.
        if filters.offset:
            page_input["afterCursor"] = str(filters.offset)

        input_obj: Dict[str, object] = {
            "page": page_input,
            "sort": sort_input,
        }
        if filters_input:
            input_obj["filters"] = filters_input

        variables = {
            "input": input_obj
        }

        try:
            result = await self._make_request(query, variables)
            proposals_data = result.get("data", {}).get("proposals", {})
            proposal_nodes = proposals_data.get("nodes", [])
            total_count = proposals_data.get("pageInfo", {}).get("count", len(proposal_nodes))

            proposals: List[Proposal] = []
            for node in proposal_nodes:
                if not node:
                    continue

                # created timestamp: prefer start.timestamp fallback to current time
                start_block = node.get("start", {})
                ts = start_block.get("timestamp") or start_block.get("ts")
                created_at = datetime.utcfromtimestamp(ts) if ts is not None else datetime.utcnow()

                # vote counts – aggregate from voteStats
                vote_stats = {vs["type"].upper(): str(vs.get("votesCount", "0")) for vs in node.get("voteStats", [])}
                votes_for = vote_stats.get("FOR", "0")
                votes_against = vote_stats.get("AGAINST", "0")
                votes_abstain = vote_stats.get("ABSTAIN", "0")

                dao_id = node.get("governor", {}).get("id", "")
                dao_name = node.get("governor", {}).get("name", "")

                proposals.append(
                    Proposal(
                        id=node["id"],
                        title=node.get("metadata", {}).get("title", ""),
                        description=node.get("metadata", {}).get("description", ""),
                        state=ProposalState(node["status"].upper()),
                        created_at=created_at,
                        start_block=start_block.get("number", 0),
                        end_block=node.get("end", {}).get("number", 0),
                        votes_for=votes_for,
                        votes_against=votes_against,
                        votes_abstain=votes_abstain,
                        dao_id=dao_id,
                        dao_name=dao_name,
                        url=f"https://www.tally.xyz/gov/{dao_id}/proposal/{node['id']}"
                    )
                )

            logfire.info("Fetched proposals", count=len(proposals), total_count=total_count)
            return proposals, total_count

        except Exception as e:
            logfire.error("Failed to fetch proposals", filters=filters.dict(), error=str(e))
            raise
    
    async def get_proposal_by_id(self, proposal_id: str) -> Optional[Proposal]:
        """Fetch a specific proposal by ID using the ProposalInput schema."""
        query = """
        query GetProposal($input: ProposalInput!) {
            proposal(input: $input) {
                id
                metadata { title description }
                status
                start {
                    ... on Block { timestamp number }
                    ... on BlocklessTimestamp { timestamp }
                }
                end {
                    ... on Block { timestamp number }
                    ... on BlocklessTimestamp { timestamp }
                }
                voteStats { type votesCount }
                governor { id name }
            }
        }
        """

        variables_input = {}
        if proposal_id.isdigit():
            variables_input["id"] = int(proposal_id)
        else:
            variables_input["onchainId"] = proposal_id
        variables = {"input": variables_input}

        try:
            result = await self._make_request(query, variables)
            node = result.get("data", {}).get("proposal")
            if not node:
                return None

            start_block = node.get("start", {})
            ts = start_block.get("timestamp") or start_block.get("ts")
            created_at = datetime.utcfromtimestamp(ts) if ts is not None else datetime.utcnow()

            vote_stats = {vs["type"].upper(): str(vs.get("votesCount", "0")) for vs in node.get("voteStats", [])}
            votes_for = vote_stats.get("FOR", "0")
            votes_against = vote_stats.get("AGAINST", "0")
            votes_abstain = vote_stats.get("ABSTAIN", "0")

            dao_id = node.get("governor", {}).get("id", "")
            dao_name = node.get("governor", {}).get("name", "")

            return Proposal(
                id=node["id"],
                title=node.get("metadata", {}).get("title", ""),
                description=node.get("metadata", {}).get("description", ""),
                state=ProposalState(node["status"].upper()),
                created_at=created_at,
                start_block=start_block.get("number", 0),
                end_block=node.get("end", {}).get("number", 0),
                votes_for=votes_for,
                votes_against=votes_against,
                votes_abstain=votes_abstain,
                dao_id=dao_id,
                dao_name=dao_name,
                url=f"https://www.tally.xyz/gov/{dao_id}/proposal/{node['id']}"
            )

        except Exception as e:
            logfire.error("Failed to fetch proposal", proposal_id=proposal_id, error=str(e))
            raise
    
    async def get_multiple_proposals(self, proposal_ids: List[str]) -> List[Proposal]:
        """Fetch multiple proposals by their IDs."""
        # Use asyncio.gather to fetch proposals concurrently
        tasks = [self.get_proposal_by_id(pid) for pid in proposal_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        proposals = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logfire.error("Failed to fetch proposal", proposal_id=proposal_ids[i], error=str(result))
                continue
            if result is not None:
                proposals.append(result)
        
        return proposals
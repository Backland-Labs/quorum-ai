"""Main FastAPI application for Quorum AI backend."""

import hashlib
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import logfire
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models import (
    DAO,
    Organization,
    OrganizationWithProposals,
    OrganizationOverviewResponse,
    Proposal,
    ProposalFilters,
    ProposalListResponse,
    ProposalState,
    SortCriteria,
    SortOrder,
    SummarizeRequest,
    SummarizeResponse,
    TopOrganizationsResponse,
    OrganizationListResponse,
    DAOListResponse,
    ProposalTopVoters,
    GovernorVoteRequest,
    GovernorVoteResponse,
    BatchVoteRequest,
    GovernorInfo,
    AIVoteRecommendation,
    VotingStrategy,
)
from services.tally_service import TallyService
from services.ai_service import AIService
from services.cache_service import CacheService
from services.governor_integration_service import GovernorIntegrationService


# Global service instances
tally_service: TallyService
ai_service: AIService
cache_service: CacheService
governor_integration_service: GovernorIntegrationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    global tally_service, ai_service, cache_service, governor_integration_service

    # Initialize services
    tally_service = TallyService()
    ai_service = AIService()
    cache_service = CacheService()
    governor_integration_service = GovernorIntegrationService(
        ai_service=ai_service,
        tally_service=tally_service,
        cache_service=cache_service
    )

    # Configure Logfire if credentials are available
    if settings.logfire_token:
        logfire.configure(
            token=settings.logfire_token, project_name=settings.logfire_project
        )

    logfire.info("Application started", version="0.1.0")

    yield

    # Shutdown
    logfire.info("Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="Quorum AI",
    description="Backend for sorting and summarizing DAO proposals using AI",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logfire.error("Unhandled exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500, content={"error": "Internal server error", "message": str(exc)}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
    }


# Organization endpoints
@app.get("/organizations", response_model=TopOrganizationsResponse)
async def get_organizations():
    """Get top 3 organizations with their 3 most active proposals, summarized with AI."""
    start_time = time.time()

    try:
        with logfire.span("get_top_organizations_with_proposals"):
            # Fetch top organizations with their proposals
            org_data = await tally_service.get_top_organizations_with_proposals()

            if not org_data:
                return TopOrganizationsResponse(
                    organizations=[],
                    processing_time=time.time() - start_time,
                    model_used=settings.ai_model,
                )

            organizations_with_proposals = []

            for org_info in org_data:
                org_dict = org_info["organization"]
                proposals = org_info["proposals"]

                # Create Organization object
                organization = Organization(
                    id=org_dict["id"],
                    name=org_dict["name"],
                    slug=org_dict["slug"],
                    chain_ids=org_dict["chain_ids"],
                    token_ids=org_dict["token_ids"],
                    governor_ids=org_dict["governor_ids"],
                    has_active_proposals=org_dict["has_active_proposals"],
                    proposals_count=org_dict["proposals_count"],
                    delegates_count=org_dict["delegates_count"],
                    delegates_votes_count=org_dict["delegates_votes_count"],
                    token_owners_count=org_dict["token_owners_count"],
                )

                # Summarize proposals if any exist
                summarized_proposals = []
                if proposals:
                    summaries = await ai_service.summarize_multiple_proposals(proposals)
                    summarized_proposals = summaries

                organizations_with_proposals.append(
                    OrganizationWithProposals(
                        organization=organization, proposals=summarized_proposals
                    )
                )

            processing_time = time.time() - start_time

            return TopOrganizationsResponse(
                organizations=organizations_with_proposals,
                processing_time=processing_time,
                model_used=settings.ai_model,
            )

    except Exception as e:
        logfire.error("Failed to fetch top organizations with proposals", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch top organizations with proposals: {str(e)}",
        )


@app.get("/organizations/list", response_model=OrganizationListResponse)
async def get_organizations_list(
    limit: int = Query(default=100, ge=1, le=200),
    after_cursor: Optional[str] = Query(default=None),
):
    """Get list of available organizations, sorted alphabetically."""
    try:
        with logfire.span("get_organizations", limit=limit, after_cursor=after_cursor):
            organizations, next_cursor = await tally_service.get_organizations(
                limit=limit, after_cursor=after_cursor
            )
            return OrganizationListResponse(
                organizations=organizations, next_cursor=next_cursor
            )

    except Exception as e:
        logfire.error("Failed to fetch organizations", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch organizations: {str(e)}"
        )


@app.get(
    "/organizations/{org_id}/overview", response_model=OrganizationOverviewResponse
)
async def get_organization_overview(org_id: str):
    """Get comprehensive overview data for a specific organization."""
    assert org_id, "Organization ID cannot be empty"
    assert isinstance(org_id, str), "Organization ID must be a string"

    try:
        with logfire.span("get_organization_overview", org_id=org_id):
            overview_data = await tally_service.get_organization_overview(org_id)

            if not overview_data:
                raise HTTPException(
                    status_code=404, detail=f"Organization with ID {org_id} not found"
                )

            return OrganizationOverviewResponse(**overview_data)

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(
            "Failed to fetch organization overview", org_id=org_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch organization overview: {str(e)}"
        )


# DAO endpoints
@app.get("/daos", response_model=DAOListResponse)
async def get_daos(
    organization_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    after_cursor: Optional[str] = Query(default=None),
):
    """Get list of available DAOs."""
    try:
        with logfire.span("get_daos", limit=limit, after_cursor=after_cursor):
            daos, next_cursor = await tally_service.get_daos(
                organization_id=organization_id, limit=limit, after_cursor=after_cursor
            )
            return DAOListResponse(daos=daos, next_cursor=next_cursor)

    except Exception as e:
        logfire.error("Failed to fetch DAOs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch DAOs: {str(e)}")


@app.get("/organizations/{org_id}/proposals", response_model=ProposalListResponse)
async def get_organization_proposals(
    org_id: str,
    state: Optional[ProposalState] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    after_cursor: Optional[str] = Query(default=None),
    sort_by: SortCriteria = Query(default=SortCriteria.CREATED_DATE),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
):
    """Get list of proposals for a specific organization."""
    try:
        filters = _build_proposal_filters(
            dao_id=None,
            organization_id=org_id,
            state=state,
            limit=limit,
            after_cursor=after_cursor,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        with logfire.span(
            "get_organization_proposals", org_id=org_id, filters=filters.dict()
        ):
            proposals, next_cursor = await tally_service.get_proposals(filters)

            return ProposalListResponse(
                proposals=proposals,
                next_cursor=next_cursor,
            )

    except Exception as e:
        logfire.error(
            "Failed to fetch organization proposals", org_id=org_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch organization proposals: {str(e)}"
        )


@app.get("/daos/{dao_id}", response_model=DAO)
async def get_dao_by_id(dao_id: str):
    """Get a specific DAO by ID."""
    try:
        with logfire.span("get_dao_by_id", dao_id=dao_id):
            dao = await tally_service.get_dao_by_id(dao_id)

            if not dao:
                raise HTTPException(
                    status_code=404, detail=f"DAO with ID {dao_id} not found"
                )

            return dao

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to fetch DAO", dao_id=dao_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch DAO: {str(e)}")


# Proposal endpoints
@app.get("/proposals", response_model=ProposalListResponse)
async def get_proposals(
    dao_id: Optional[str] = Query(default=None),
    organization_id: Optional[str] = Query(default=None),
    state: Optional[ProposalState] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    after_cursor: Optional[str] = Query(default=None),
    sort_by: SortCriteria = Query(default=SortCriteria.CREATED_DATE),
    sort_order: SortOrder = Query(default=SortOrder.DESC),
):
    """Get list of proposals with optional filtering and sorting."""
    try:
        filters = _build_proposal_filters(
            dao_id, organization_id, state, limit, after_cursor, sort_by, sort_order
        )

        with logfire.span("get_proposals", filters=filters.dict()):
            proposals, next_cursor = await tally_service.get_proposals(filters)

            return ProposalListResponse(
                proposals=proposals,
                next_cursor=next_cursor,
            )

    except Exception as e:
        logfire.error("Failed to fetch proposals", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch proposals: {str(e)}"
        )


@app.get("/proposals/{proposal_id}", response_model=Proposal)
async def get_proposal_by_id(proposal_id: str):
    """Get a specific proposal by ID."""
    try:
        with logfire.span("get_proposal_by_id", proposal_id=proposal_id):
            proposal = await tally_service.get_proposal_by_id(proposal_id)

            if not proposal:
                raise HTTPException(
                    status_code=404, detail=f"Proposal with ID {proposal_id} not found"
                )

            return proposal

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to fetch proposal", proposal_id=proposal_id, error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch proposal: {str(e)}"
        )


# AI Summarization endpoints
@app.post("/proposals/summarize", response_model=SummarizeResponse)
async def summarize_proposals(request: SummarizeRequest):
    """Summarize multiple proposals using AI."""
    start_time = time.time()

    try:
        with logfire.span(
            "summarize_proposals", proposal_count=len(request.proposal_ids)
        ):
            # Fetch proposals
            proposals = await _fetch_proposals_for_summarization(request.proposal_ids)

            if not proposals:
                raise HTTPException(
                    status_code=404, detail="No proposals found for the provided IDs"
                )

            # Generate summaries
            summaries = await _generate_proposal_summaries(request)

            processing_time = time.time() - start_time

            return SummarizeResponse(
                summaries=summaries,
                processing_time=processing_time,
                model_used=settings.ai_model,
            )

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to summarize proposals", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to summarize proposals: {str(e)}"
        )


@app.get("/proposals/{proposal_id}/top-voters", response_model=ProposalTopVoters)
async def get_proposal_top_voters(
    proposal_id: str,
    limit: int = Query(
        default=settings.default_top_voters_limit,
        ge=settings.min_top_voters_limit,
        le=settings.max_top_voters_limit,
    ),
):
    """Get top voters for a specific proposal by voting power."""
    _validate_proposal_id(proposal_id)

    try:
        with logfire.span(
            "get_proposal_top_voters", proposal_id=proposal_id, limit=limit
        ):
            # Fetch data
            voters = await tally_service.get_proposal_votes(proposal_id, limit)
            proposal = await _validate_proposal_exists(proposal_id)

            # Build response
            response_data = ProposalTopVoters(proposal_id=proposal_id, voters=voters)
            headers = _build_cache_headers(proposal, response_data)

            # Log if no voters found
            if not voters:
                logfire.info("No voters found for proposal", proposal_id=proposal_id)

            return JSONResponse(content=response_data.model_dump(), headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logfire.error(
            "Failed to fetch proposal top voters", proposal_id=proposal_id, error=str(e)
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch proposal top voters: {str(e)}"
        )


# Private helper functions for top voters endpoint
def _validate_proposal_id(proposal_id: str) -> None:
    """Validate proposal ID parameter."""
    assert proposal_id, "Proposal ID cannot be empty"
    assert isinstance(proposal_id, str), "Proposal ID must be a string"
    assert proposal_id.strip(), "Proposal ID cannot be whitespace only"


async def _validate_proposal_exists(proposal_id: str) -> Proposal:
    """Validate that proposal exists and return it."""
    proposal = await tally_service.get_proposal_by_id(proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=404, detail=f"Proposal with ID {proposal_id} not found"
        )
    return proposal


def _build_cache_headers(proposal: Proposal, response_data: ProposalTopVoters) -> dict:
    """Build HTTP cache headers based on proposal state."""
    headers = {}

    # Set appropriate cache TTL based on proposal state
    if proposal.state == ProposalState.ACTIVE:
        # Active proposals change frequently, shorter cache time (5 minutes)
        max_age = 300
    else:
        # Completed proposals don't change, longer cache time (1 hour)
        max_age = 3600

    headers["Cache-Control"] = f"public, max-age={max_age}"

    # Generate ETag based on response content
    response_json = response_data.model_dump_json()
    etag = hashlib.md5(response_json.encode()).hexdigest()
    headers["ETag"] = f'"{etag}"'

    return headers


# Private helper functions
def _build_proposal_filters(
    dao_id: Optional[str],
    organization_id: Optional[str],
    state: Optional[ProposalState],
    limit: int,
    after_cursor: Optional[str],
    sort_by: SortCriteria,
    sort_order: SortOrder,
) -> ProposalFilters:
    """Build ProposalFilters object from query parameters."""
    return ProposalFilters(
        dao_id=dao_id,
        organization_id=organization_id,
        state=state,
        limit=limit,
        after_cursor=after_cursor,
        sort_by=sort_by,
        sort_order=sort_order,
    )


async def _fetch_proposals_for_summarization(proposal_ids: List[str]) -> List[Proposal]:
    """Fetch proposals for summarization."""
    with logfire.span("fetch_proposals_for_summarization"):
        proposals = await tally_service.get_multiple_proposals(proposal_ids)
        logfire.info("Fetched proposals for summarization", count=len(proposals))
        return proposals


async def _generate_proposal_summaries(proposals: List[Proposal]) -> List:
    """Generate AI summaries for proposals."""
    with logfire.span("generate_proposal_summaries"):
        summaries = await ai_service.summarize_multiple_proposals(proposals)

        logfire.info("Generated proposal summaries", count=len(summaries))
        return summaries


# Governor Vote Encoding Endpoints

@app.post("/proposals/{proposal_id}/vote/encode", response_model=GovernorVoteResponse)
async def encode_proposal_vote(proposal_id: str, request: GovernorVoteRequest):
    """Encode a single vote for a proposal."""
    try:
        with logfire.span("encode_proposal_vote", proposal_id=proposal_id):
            # Validate that governor voting is enabled
            if not settings.governor_voting_enabled:
                raise HTTPException(
                    status_code=403, 
                    detail="Governor voting is currently disabled"
                )
            
            # Encode the vote using the integration service
            encoding_result = await governor_integration_service.encode_vote_with_ai_decision(
                proposal_id=proposal_id,
                vote_type=request.vote_type,
                voter_address=request.voter_address,
                reason=request.reason
            )
            
            return GovernorVoteResponse(
                success=encoding_result.success,
                encoded_data=encoding_result.encoded_data,
                gas_estimate=150000,  # Default estimate
                function_signature=encoding_result.function_name,
                governor_type=encoding_result.governor_type
            )

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to encode proposal vote", 
                    proposal_id=proposal_id, 
                    error=str(e))
        return GovernorVoteResponse(
            success=False,
            error_message=str(e)
        )


@app.post("/proposals/vote/encode-batch")
async def encode_batch_votes(request: BatchVoteRequest):
    """Encode multiple votes in batch."""
    try:
        with logfire.span("encode_batch_votes", vote_count=len(request.votes)):
            # Validate that batch encoding is enabled
            if not settings.batch_encoding_enabled:
                raise HTTPException(
                    status_code=403, 
                    detail="Batch encoding is currently disabled"
                )
            
            # Validate batch size
            if len(request.votes) > settings.max_batch_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"Batch size cannot exceed {settings.max_batch_size}"
                )
            
            # Extract unique voter addresses
            voter_addresses = list(set(vote.get("voter_address") for vote in request.votes))
            
            # Process batch using integration service
            # For simplicity, process first proposal with first voter
            if request.votes:
                first_vote = request.votes[0]
                proposal_ids = [vote.get("proposal_id") for vote in request.votes]
                
                batch_result = await governor_integration_service.process_proposals_batch(
                    proposal_ids=proposal_ids,
                    voter_address=first_vote.get("voter_address"),
                    voting_strategy=VotingStrategy.BALANCED
                )
                
                return {
                    "success": True,
                    "total_votes": len(request.votes),
                    "successful_count": batch_result.successful_count,
                    "failed_count": batch_result.failed_count,
                    "processing_time_ms": batch_result.processing_time_ms,
                    "errors": batch_result.errors
                }
            else:
                return {
                    "success": True,
                    "total_votes": 0,
                    "successful_count": 0,
                    "failed_count": 0,
                    "processing_time_ms": 0,
                    "errors": []
                }

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to encode batch votes", error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to encode batch votes: {str(e)}"
        )


@app.get("/proposals/{proposal_id}/governor-info", response_model=GovernorInfo)
async def get_proposal_governor_info(proposal_id: str):
    """Get governor information for a proposal."""
    try:
        with logfire.span("get_proposal_governor_info", proposal_id=proposal_id):
            # Get proposal to extract DAO ID
            proposal = await tally_service.get_proposal_by_id(proposal_id)
            if not proposal:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Proposal with ID {proposal_id} not found"
                )
            
            # Get governor info
            governor_info = await tally_service.detect_governor_type(proposal_id, proposal.dao_id)
            
            return governor_info

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to get governor info", proposal_id=proposal_id, error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get governor info: {str(e)}"
        )


@app.post("/proposals/{proposal_id}/ai-vote-recommendation", response_model=AIVoteRecommendation)
async def get_ai_vote_recommendation(proposal_id: str, voter_address: str = Query(...)):
    """Get AI-enhanced vote recommendation with encoding parameters."""
    try:
        with logfire.span("get_ai_vote_recommendation", 
                         proposal_id=proposal_id, 
                         voter_address=voter_address):
            
            # Get AI recommendation with encoding
            recommendation = await governor_integration_service.get_ai_vote_recommendation_with_encoding(
                proposal_id=proposal_id,
                voter_address=voter_address
            )
            
            return recommendation

    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to get AI vote recommendation", 
                    proposal_id=proposal_id, 
                    voter_address=voter_address, 
                    error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get AI vote recommendation: {str(e)}"
        )


# Development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )

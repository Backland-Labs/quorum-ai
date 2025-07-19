"""Main FastAPI application for Quorum AI backend."""

import hashlib
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from logging_config import setup_pearl_logger, log_span

from config import settings
from models import (
    AgentRunRequest,
    AgentRunResponse,
    Proposal,
    ProposalFilters,
    ProposalListResponse,
    ProposalState,
    SortCriteria,
    SortOrder,
    SummarizeRequest,
    SummarizeResponse,
    ProposalTopVoters,
    ProposalVoter,
    Vote,
    VoteType,
)
from services.ai_service import AIService
from services.agent_run_service import AgentRunService
from services.safe_service import SafeService
from services.activity_service import ActivityService
from services.user_preferences_service import UserPreferencesService
from services.voting_service import VotingService
from services.snapshot_service import SnapshotService

# Initialize Pearl-compliant logger
logger = setup_pearl_logger(__name__)

# Global service instances
ai_service: AIService
agent_run_service: AgentRunService
safe_service: SafeService
activity_service: ActivityService
user_preferences_service: UserPreferencesService
voting_service: VotingService
snapshot_service: SnapshotService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    global \
        ai_service, \
        agent_run_service, \
        safe_service, \
        activity_service, \
        user_preferences_service, \
        voting_service, \
        snapshot_service

    # Initialize services
    ai_service = AIService()
    agent_run_service = AgentRunService()
    safe_service = SafeService()
    activity_service = ActivityService()
    user_preferences_service = UserPreferencesService()
    voting_service = VotingService()
    snapshot_service = SnapshotService()

    logger.info("Application started version=0.1.0")

    yield

    # Shutdown
    logger.info("Application shutdown")


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
    logger.error(f"Unhandled exception error={str(exc)} path={str(request.url)}")
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


# Proposal endpoints
@app.get("/proposals", response_model=ProposalListResponse)
async def get_proposals(
    space_id: str = Query(..., description="Snapshot space ID to fetch proposals from"),
    state: Optional[ProposalState] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    skip: int = Query(default=0, ge=0, description="Number of proposals to skip"),
):
    """Get list of proposals from a Snapshot space with optional filtering."""
    try:
        with log_span(logger, "get_proposals", space_id=space_id, state=state, limit=limit):
            # Use Snapshot service
            space_ids = [space_id]
            snapshot_state = state.value.lower() if state else None
            proposals = await snapshot_service.get_proposals(
                space_ids=space_ids, state=snapshot_state, first=limit, skip=skip
            )

            return ProposalListResponse(
                proposals=proposals,
                next_cursor=None,  # Use skip-based pagination instead
            )

    except Exception as e:
        logger.error(f"Failed to fetch proposals error={str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch proposals: {str(e)}"
        )


@app.get("/proposals/{proposal_id}", response_model=Proposal)
async def get_proposal_by_id(proposal_id: str):
    """Get a specific proposal by ID."""
    try:
        with log_span(logger, "get_proposal_by_id", proposal_id=proposal_id):
            proposal = await snapshot_service.get_proposal(proposal_id)

            if not proposal:
                raise HTTPException(
                    status_code=404, detail=f"Proposal with ID {proposal_id} not found"
                )

            return proposal

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch proposal proposal_id={proposal_id} error={str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch proposal: {str(e)}"
        )


# AI Summarization endpoints
@app.post("/proposals/summarize", response_model=SummarizeResponse)
async def summarize_proposals(request: SummarizeRequest):
    """Summarize multiple proposals using AI."""
    start_time = time.time()

    try:
        with log_span(
            logger, "summarize_proposals", proposal_count=len(request.proposal_ids)
        ):
            # Fetch proposals
            proposals = await _fetch_proposals_for_summarization(request.proposal_ids)

            if not proposals:
                raise HTTPException(
                    status_code=404, detail="No proposals found for the provided IDs"
                )

            # Generate summaries
            summaries = await _generate_proposal_summaries(proposals)

            processing_time = time.time() - start_time

            return SummarizeResponse(
                summaries=summaries,
                processing_time=processing_time,
                model_used=settings.ai_model,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to summarize proposals error={str(e)}")
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
        with log_span(
            logger, "get_proposal_top_voters", proposal_id=proposal_id, limit=limit
        ):
            # Fetch data using Snapshot
            votes = await snapshot_service.get_votes(proposal_id, first=limit)
            proposal = await _validate_proposal_exists(proposal_id)

            # Transform Snapshot votes to ProposalVoter format
            voters = _transform_snapshot_votes_to_voters(votes)

            # Build response
            response_data = ProposalTopVoters(proposal_id=proposal_id, voters=voters)
            headers = _build_cache_headers(proposal, response_data)

            # Log if no voters found
            if not voters:
                logger.info(f"No voters found for proposal proposal_id={proposal_id}")

            return JSONResponse(content=response_data.model_dump(), headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to fetch proposal top voters proposal_id={proposal_id} error={str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch proposal top voters: {str(e)}"
        )


# Agent Run endpoint
@app.post("/agent-run", response_model=AgentRunResponse)
async def agent_run(request: AgentRunRequest):
    """Execute an autonomous agent run for a given Snapshot space.

    This endpoint orchestrates the complete agent run workflow:
    1. Fetches active proposals from the specified Snapshot space
    2. Loads user preferences to guide voting decisions
    3. Uses AI to analyze proposals and make voting decisions
    4. Executes votes (or simulates them in dry run mode)

    Args:
        request: AgentRunRequest containing space_id and dry_run flag

    Returns:
        AgentRunResponse with execution results and vote decisions

    Raises:
        HTTPException: If space_id is invalid or execution fails
    """
    try:
        with log_span(
            logger, "agent_run", space_id=request.space_id, dry_run=request.dry_run
        ):
            # Execute the agent run using the service
            response = await agent_run_service.execute_agent_run(request)

            logger.info(
                f"Agent run completed space_id={request.space_id} "
                f"proposals_analyzed={response.proposals_analyzed} "
                f"votes_cast={len(response.votes_cast)} "
                f"execution_time={response.execution_time} "
                f"errors={response.errors} "
                f"dry_run={request.dry_run}"
            )

            return response

    except Exception as e:
        logger.error(
            f"Failed to execute agent run space_id={request.space_id} error={str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to execute agent run: {str(e)}"
        )


# Private helper functions for top voters endpoint
def _validate_proposal_id(proposal_id: str) -> None:
    """Validate proposal ID parameter."""
    assert proposal_id, "Proposal ID cannot be empty"
    assert isinstance(proposal_id, str), "Proposal ID must be a string"
    assert proposal_id.strip(), "Proposal ID cannot be whitespace only"


async def _validate_proposal_exists(proposal_id: str) -> Proposal:
    """Validate that proposal exists and return it."""
    proposal = await snapshot_service.get_proposal(proposal_id)
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


def _transform_snapshot_votes_to_voters(votes: List[Vote]) -> List[ProposalVoter]:
    """Transform Snapshot Vote objects to ProposalVoter objects."""
    voters = []
    for vote in votes:
        vote_type = _map_snapshot_choice_to_vote_type(vote.choice)
        amount_wei = _convert_voting_power_to_wei(vote.vp)

        voter = ProposalVoter(
            address=vote.voter, amount=amount_wei, vote_type=vote_type
        )
        voters.append(voter)

    return voters


def _map_snapshot_choice_to_vote_type(choice: Any) -> VoteType:
    """Map Snapshot choice to VoteType with proper type handling."""
    # Snapshot choice mapping: 1=For, 2=Against, 3=Abstain (typical convention)
    SNAPSHOT_CHOICE_MAP = {1: VoteType.FOR, 2: VoteType.AGAINST, 3: VoteType.ABSTAIN}
    DEFAULT_VOTE_TYPE = VoteType.FOR

    if isinstance(choice, int):
        return SNAPSHOT_CHOICE_MAP.get(choice, DEFAULT_VOTE_TYPE)
    else:
        # If choice is not an int, default to FOR
        return DEFAULT_VOTE_TYPE


def _convert_voting_power_to_wei(voting_power: float) -> str:
    """Convert voting power from float to Wei format string."""
    WEI_DECIMAL_PLACES = 18
    return str(int(voting_power * 10**WEI_DECIMAL_PLACES))


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
    """Fetch proposals for summarization using Snapshot."""
    with log_span(logger, "fetch_proposals_for_summarization"):
        proposals = []

        for proposal_id in proposal_ids:
            try:
                proposal = await snapshot_service.get_proposal(proposal_id)
                if proposal:
                    proposals.append(proposal)
            except Exception:
                pass  # Skip if Snapshot fails

        logger.info(f"Fetched proposals for summarization count={len(proposals)}")
        return proposals


async def _generate_proposal_summaries(proposals: List[Proposal]) -> List:
    """Generate AI summaries for proposals."""
    with log_span(logger, "generate_proposal_summaries"):
        summaries = await ai_service.summarize_multiple_proposals(proposals)

        logger.info(f"Generated proposal summaries count={len(summaries)}")
        return summaries


# Development server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )

"""Main FastAPI application for Quorum AI backend."""

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import logfire
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from models import (
    DAO,
    Proposal,
    ProposalFilters,
    ProposalListResponse,
    ProposalState,
    SortCriteria,
    SortOrder,
    SummarizeRequest,
    SummarizeResponse,
)
from services.tally_service import TallyService
from services.ai_service import AIService


# Global service instances
tally_service: TallyService
ai_service: AIService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    global tally_service, ai_service
    tally_service = TallyService()
    ai_service = AIService()
    
    # Configure Logfire if credentials are available
    if settings.logfire_token:
        logfire.configure(token=settings.logfire_token, project_name=settings.logfire_project)
    
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
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }


# DAO endpoints
@app.get("/daos", response_model=List[DAO])
async def get_daos(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get list of available DAOs."""
    try:
        with logfire.span("get_daos", limit=limit, offset=offset):
            daos = await tally_service.get_daos(limit=limit, offset=offset)
            return daos
            
    except Exception as e:
        logfire.error("Failed to fetch DAOs", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch DAOs: {str(e)}")


@app.get("/daos/{dao_id}", response_model=DAO)
async def get_dao_by_id(dao_id: str):
    """Get a specific DAO by ID."""
    try:
        with logfire.span("get_dao_by_id", dao_id=dao_id):
            dao = await tally_service.get_dao_by_id(dao_id)
            
            if not dao:
                raise HTTPException(status_code=404, detail=f"DAO with ID {dao_id} not found")
                
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
    state: Optional[ProposalState] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: SortCriteria = Query(default=SortCriteria.CREATED_DATE),
    sort_order: SortOrder = Query(default=SortOrder.DESC)
):
    """Get list of proposals with optional filtering and sorting."""
    try:
        filters = _build_proposal_filters(
            dao_id, state, limit, offset, sort_by, sort_order
        )
        
        with logfire.span("get_proposals", filters=filters.dict()):
            proposals, total_count = await tally_service.get_proposals(filters)
            
            return ProposalListResponse(
                proposals=proposals,
                total_count=total_count,
                has_more=offset + len(proposals) < total_count
            )
            
    except Exception as e:
        logfire.error("Failed to fetch proposals", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch proposals: {str(e)}")


@app.get("/proposals/{proposal_id}", response_model=Proposal)
async def get_proposal_by_id(proposal_id: str):
    """Get a specific proposal by ID."""
    try:
        with logfire.span("get_proposal_by_id", proposal_id=proposal_id):
            proposal = await tally_service.get_proposal_by_id(proposal_id)
            
            if not proposal:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Proposal with ID {proposal_id} not found"
                )
                
            return proposal
            
    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to fetch proposal", proposal_id=proposal_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch proposal: {str(e)}")


# AI Summarization endpoints
@app.post("/proposals/summarize", response_model=SummarizeResponse)
async def summarize_proposals(request: SummarizeRequest):
    """Summarize multiple proposals using AI."""
    start_time = time.time()
    
    try:
        with logfire.span("summarize_proposals", proposal_count=len(request.proposal_ids)):
            # Fetch proposals
            proposals = await _fetch_proposals_for_summarization(request.proposal_ids)
            
            if not proposals:
                raise HTTPException(
                    status_code=404,
                    detail="No proposals found for the provided IDs"
                )
            
            # Generate summaries
            summaries = await _generate_proposal_summaries(request, proposals)
            
            processing_time = time.time() - start_time
            
            return SummarizeResponse(
                summaries=summaries,
                processing_time=processing_time,
                model_used=settings.ai_model
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logfire.error("Failed to summarize proposals", error=str(e))
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to summarize proposals: {str(e)}"
        )


# Private helper functions
def _build_proposal_filters(
    dao_id: Optional[str],
    state: Optional[ProposalState],
    limit: int,
    offset: int,
    sort_by: SortCriteria,
    sort_order: SortOrder
) -> ProposalFilters:
    """Build ProposalFilters object from query parameters."""
    return ProposalFilters(
        dao_id=dao_id,
        state=state,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )


async def _fetch_proposals_for_summarization(proposal_ids: List[str]) -> List[Proposal]:
    """Fetch proposals for summarization."""
    with logfire.span("fetch_proposals_for_summarization"):
        proposals = await tally_service.get_multiple_proposals(proposal_ids)
        logfire.info("Fetched proposals for summarization", count=len(proposals))
        return proposals


async def _generate_proposal_summaries(
    request: SummarizeRequest, 
    proposals: List[Proposal]
) -> List:
    """Generate AI summaries for proposals."""
    with logfire.span("generate_proposal_summaries"):
        summaries = await ai_service.summarize_multiple_proposals(
            proposals,
            include_risk_assessment=request.include_risk_assessment,
            include_recommendations=request.include_recommendations
        )
        
        logfire.info("Generated proposal summaries", count=len(summaries))
        return summaries


# Development server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )
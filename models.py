"""Pydantic models for DAO and proposal data structures."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ProposalState(str, Enum):
    """Proposal state enumeration."""
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    DEFEATED = "DEFEATED"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    SUCCEEDED = "SUCCEEDED"


class VoteType(str, Enum):
    """Vote type enumeration."""
    FOR = "FOR"
    AGAINST = "AGAINST"
    ABSTAIN = "ABSTAIN"


class Vote(BaseModel):
    """Individual vote on a proposal."""
    voter: str = Field(..., description="Address of the voter")
    support: VoteType = Field(..., description="Vote direction")
    weight: str = Field(..., description="Voting weight")
    reason: Optional[str] = Field(None, description="Reason for vote if provided")


class DAO(BaseModel):
    """DAO (Decentralized Autonomous Organization) model."""
    id: str = Field(..., description="Unique DAO identifier")
    name: str = Field(..., description="DAO name")
    slug: str = Field(..., description="DAO slug for URLs")
    description: Optional[str] = Field(None, description="DAO description")
    organization_id: str = Field(..., description="Organization identifier")
    active_proposals_count: int = Field(0, description="Number of active proposals")
    total_proposals_count: int = Field(0, description="Total number of proposals")


class Proposal(BaseModel):
    """DAO proposal model."""
    id: str = Field(..., description="Unique proposal identifier")
    title: str = Field(..., description="Proposal title")
    description: str = Field(..., description="Proposal description")
    state: ProposalState = Field(..., description="Current proposal state")
    created_at: datetime = Field(..., description="Creation timestamp")
    start_block: int = Field(..., description="Block number when voting starts")
    end_block: int = Field(..., description="Block number when voting ends")
    votes_for: str = Field("0", description="Total votes in favor")
    votes_against: str = Field("0", description="Total votes against")
    votes_abstain: str = Field("0", description="Total abstain votes")
    dao_id: str = Field(..., description="DAO this proposal belongs to")
    dao_name: str = Field(..., description="Name of the DAO")
    url: Optional[str] = Field(None, description="URL to view proposal")


class ProposalSummary(BaseModel):
    """AI-generated proposal summary."""
    proposal_id: str = Field(..., description="Original proposal ID")
    title: str = Field(..., description="Original proposal title")
    summary: str = Field(..., description="AI-generated summary in plain English")
    key_points: List[str] = Field(..., description="Key points extracted from proposal")
    risk_level: str = Field(..., description="Assessed risk level (LOW/MEDIUM/HIGH)")
    recommendation: str = Field(..., description="AI recommendation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in analysis")


class SortCriteria(str, Enum):
    """Criteria for sorting proposals."""
    CREATED_DATE = "created_date"
    VOTE_COUNT = "vote_count" 
    STATE = "state"
    TITLE = "title"


class SortOrder(str, Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


class ProposalFilters(BaseModel):
    """Filters for proposal queries."""
    state: Optional[ProposalState] = None
    dao_id: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: SortCriteria = Field(default=SortCriteria.CREATED_DATE)
    sort_order: SortOrder = Field(default=SortOrder.DESC)


class ProposalListResponse(BaseModel):
    """Response model for proposal listing."""
    proposals: List[Proposal] = Field(..., description="List of proposals")
    total_count: int = Field(..., description="Total number of proposals")
    has_more: bool = Field(..., description="Whether more results exist")


class SummarizeRequest(BaseModel):
    """Request model for proposal summarization."""
    proposal_ids: List[str] = Field(..., min_items=1, max_items=50)
    include_risk_assessment: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)


class SummarizeResponse(BaseModel):
    """Response model for proposal summarization."""
    summaries: List[ProposalSummary] = Field(..., description="AI-generated summaries")
    processing_time: float = Field(..., description="Time taken to process in seconds")
    model_used: str = Field(..., description="AI model used for summarization")
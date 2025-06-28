"""Pydantic models for DAO and proposal data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Organization(BaseModel):
    """Represents a DAO organization."""

    id: str
    name: str
    slug: str
    chain_ids: List[str] = Field(default_factory=list)
    token_ids: List[str] = Field(default_factory=list)
    governor_ids: List[str] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    creator: Optional[Dict[str, Any]] = None
    has_active_proposals: bool = False
    proposals_count: int = 0
    delegates_count: int = 0
    delegates_votes_count: str = "0"
    token_owners_count: int = 0
    endorsement_service: Optional[Dict[str, Any]] = None


class ProposalState(str, Enum):
    """Proposal state enumeration."""

    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    CROSSCHAINEXECUTED = "CROSSCHAINEXECUTED"
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
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in analysis"
    )


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
    organization_id: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    after_cursor: Optional[str] = None
    sort_by: SortCriteria = Field(default=SortCriteria.CREATED_DATE)
    sort_order: SortOrder = Field(default=SortOrder.DESC)


class ProposalListResponse(BaseModel):
    """Response model for proposal listing."""

    proposals: List[Proposal] = Field(..., description="List of proposals")
    next_cursor: Optional[str] = Field(
        None, description="Cursor for the next page of results"
    )


class OrganizationListResponse(BaseModel):
    """Response model for organization listing."""

    organizations: List[Organization] = Field(..., description="List of organizations")
    next_cursor: Optional[str] = Field(
        None, description="Cursor for the next page of results"
    )


class DAOListResponse(BaseModel):
    """Response model for DAO listing."""

    daos: List[DAO] = Field(..., description="List of DAOs")
    next_cursor: Optional[str] = Field(
        None, description="Cursor for the next page of results"
    )


class SummarizeRequest(BaseModel):
    """Request model for proposal summarization."""

    proposal_ids: List[str] = Field(..., min_length=1, max_length=50)
    include_risk_assessment: bool = Field(default=True)
    include_recommendations: bool = Field(default=True)


class SummarizeResponse(BaseModel):
    """Response model for proposal summarization."""

    summaries: List[ProposalSummary] = Field(..., description="AI-generated summaries")
    processing_time: float = Field(..., description="Time taken to process in seconds")
    model_used: str = Field(..., description="AI model used for summarization")


class OrganizationWithProposals(BaseModel):
    """Organization with its top proposals."""
    
    organization: Organization = Field(..., description="Organization details")
    proposals: List[ProposalSummary] = Field(..., description="Top 3 summarized proposals")


class TopOrganizationsResponse(BaseModel):
    """Response model for top organizations with proposals."""
    
    organizations: List[OrganizationWithProposals] = Field(..., description="Top organizations with proposals")
    processing_time: float = Field(..., description="Time taken to process in seconds")
    model_used: str = Field(..., description="AI model used for summarization")

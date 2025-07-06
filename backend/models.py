"""Pydantic models for DAO and proposal data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# Constants for VoteDecision model
DEFAULT_RISK_ASSESSMENT = "MEDIUM"
DEFAULT_ESTIMATED_GAS_COST = 0.005  # CELO
CONFIDENCE_DECIMAL_PLACES = 3

# Constants for AgentState model
DEFAULT_FSM_ROUND = "IdleRound"

# Risk assessment levels
class RiskLevel(str, Enum):
    """Risk assessment levels for proposals."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

# FSM round types
class FSMRoundType(str, Enum):
    """Finite State Machine round types for agent monitoring."""
    IDLE = "IdleRound"
    VOTING = "VotingRound"
    EXECUTION = "ExecutionRound"
    HEALTH_CHECK = "HealthCheckRound"

# Voting strategy types
class VotingStrategy(str, Enum):
    """Voting strategies for autonomous agent decision making."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class ModelValidationHelper:
    """Centralized validation helper for model business rules."""
    
    @staticmethod
    def validate_blockchain_address(address: str) -> str:
        """Validate blockchain address format."""
        assert isinstance(address, str), f"Address must be string, got {type(address)}"
        assert address.strip(), "Address cannot be empty or whitespace"
        
        cleaned_address = address.strip()
        
        # Basic format checks
        assert len(cleaned_address) >= 10, f"Address too short: {cleaned_address}"
        assert not cleaned_address.isspace(), "Address cannot be only whitespace"
        
        return cleaned_address
    
    @staticmethod
    def validate_positive_amount(amount: str, field_name: str = "amount") -> str:
        """Validate that a string amount represents a positive number."""
        assert isinstance(amount, str), f"{field_name} must be string, got {type(amount)}"
        assert amount.strip(), f"{field_name} cannot be empty"
        
        try:
            numeric_value = float(amount)
            assert numeric_value >= 0, f"{field_name} cannot be negative: {numeric_value}"
        except (ValueError, TypeError) as e:
            raise ValueError(f"{field_name} must be a valid number: {e}")
        
        return amount
    
    @staticmethod
    def validate_meaningful_text(text: str, min_length: int = 10, field_name: str = "text") -> str:
        """Validate that text has meaningful content."""
        assert isinstance(text, str), f"{field_name} must be string, got {type(text)}"
        assert text.strip(), f"{field_name} cannot be empty or whitespace"
        
        cleaned_text = text.strip()
        assert len(cleaned_text) >= min_length, f"{field_name} too short, must be at least {min_length} chars: {len(cleaned_text)}"
        
        return cleaned_text
    
    @staticmethod
    def validate_staking_consistency(is_staked: bool, stake_amount: float, rewards_earned: float) -> List[str]:
        """Validate staking state consistency and return list of warnings."""
        warnings = []
        
        # Type validation (these are still critical errors)
        assert isinstance(is_staked, bool), f"is_staked must be bool, got {type(is_staked)}"
        assert isinstance(stake_amount, (int, float)), f"stake_amount must be numeric, got {type(stake_amount)}"
        assert isinstance(rewards_earned, (int, float)), f"rewards_earned must be numeric, got {type(rewards_earned)}"
        
        # Business rule validation (converted to warnings)
        if is_staked and stake_amount <= 0:
            warnings.append(f"Agent marked as staked but has zero/negative stake amount: {stake_amount}")
        
        if rewards_earned < 0:
            warnings.append(f"Negative staking rewards detected: {rewards_earned}")
            
        return warnings


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
    proposals: List[ProposalSummary] = Field(
        ..., description="Top 3 summarized proposals"
    )


class TopOrganizationsResponse(BaseModel):
    """Response model for top organizations with proposals."""

    organizations: List[OrganizationWithProposals] = Field(
        ..., description="Top organizations with proposals"
    )
    processing_time: float = Field(..., description="Time taken to process in seconds")
    model_used: str = Field(..., description="AI model used for summarization")


class OrganizationOverviewResponse(BaseModel):
    """Response model for organization overview."""

    organization_id: str = Field(..., description="Organization unique identifier")
    organization_name: str = Field(..., description="Organization name")
    organization_slug: str = Field(..., description="Organization slug for URLs")
    description: Optional[str] = Field(None, description="Organization description")
    delegate_count: int = Field(..., ge=0, description="Number of delegates")
    token_holder_count: int = Field(..., ge=0, description="Number of token holders")
    total_proposals_count: int = Field(
        ..., ge=0, description="Total number of proposals"
    )
    proposal_counts_by_status: Dict[str, int] = Field(
        ..., description="Proposal counts grouped by status"
    )
    recent_activity_count: int = Field(
        ..., ge=0, description="Recent governance activity count"
    )
    governance_participation_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Governance participation rate"
    )


class ProposalVoter(BaseModel):
    """Individual voter information for a proposal.

    Represents a single voter's participation in a proposal vote,
    including their address, voting power, and vote choice.
    """

    address: str = Field(..., min_length=1, description="Voter's blockchain address")
    amount: str = Field(
        ..., description="Voting power as string to handle large numbers"
    )
    vote_type: VoteType = Field(..., description="Vote choice")

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate blockchain address format."""
        return ModelValidationHelper.validate_blockchain_address(v)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        """Validate voting amount is numeric and non-negative."""
        return ModelValidationHelper.validate_positive_amount(v, "voting amount")


class ProposalTopVoters(BaseModel):
    """Collection of top voters for a proposal.

    Contains a list of the most influential voters for a specific proposal,
    useful for displaying voting participation and influence distribution.
    """

    proposal_id: str = Field(..., description="Unique proposal identifier")
    voters: List[ProposalVoter] = Field(
        ..., description="List of top voters by voting power"
    )

    @field_validator("voters")
    @classmethod
    def validate_voters_list(cls, v: List[ProposalVoter]) -> List[ProposalVoter]:
        """Validate voters list constraints."""
        if not isinstance(v, list):
            raise ValueError("Voters must be a list")
        if len(v) > 100:
            raise ValueError("Voters list cannot exceed 100 entries")
        return v


class VoteDecision(BaseModel):
    """AI-generated voting decision for a proposal."""

    proposal_id: str = Field(..., description="The proposal ID being voted on")
    vote: VoteType = Field(
        ..., description="The voting decision: FOR, AGAINST, or ABSTAIN"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score in the decision (0.0 to 1.0)"
    )
    reasoning: str = Field(..., description="AI-generated explanation for the vote")
    risk_assessment: RiskLevel = Field(
        default=RiskLevel.MEDIUM, description="Risk level: LOW, MEDIUM, or HIGH"
    )
    estimated_gas_cost: float = Field(
        default=DEFAULT_ESTIMATED_GAS_COST, description="Estimated transaction cost in CELO"
    )
    strategy_used: VotingStrategy = Field(
        ..., description="The voting strategy used to make this decision"
    )

    @field_validator("proposal_id")
    @classmethod
    def validate_proposal_id(cls, v: str) -> str:
        """Validate proposal ID format and content."""
        # Runtime assertion: proposal_id must be meaningful
        assert isinstance(v, str), f"Proposal ID must be string, got {type(v)}"
        assert v.strip(), "Proposal ID cannot be empty or whitespace"
        assert len(v.strip()) >= 3, f"Proposal ID too short: {v}"
        
        return v.strip()

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        """Validate reasoning has sufficient content."""
        return ModelValidationHelper.validate_meaningful_text(v, min_length=10, field_name="reasoning")

    @field_validator("estimated_gas_cost")
    @classmethod
    def validate_gas_cost(cls, v: float) -> float:
        """Validate gas cost is reasonable."""
        # Runtime assertion: gas cost must be valid
        assert isinstance(v, (int, float)), f"Gas cost must be numeric, got {type(v)}"
        assert v >= 0.0, f"Gas cost cannot be negative: {v}"
        assert v <= 1000.0, f"Gas cost seems unreasonably high: {v}"
        
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within valid range and precision."""
        # Runtime assertion: confidence must be a valid number
        assert isinstance(v, (int, float)), f"Confidence must be numeric, got {type(v)}"
        assert not (v != v), "Confidence cannot be NaN"  # NaN check
        assert v != float('inf') and v != float('-inf'), "Confidence cannot be infinite"
        
        return cls._round_confidence_to_precision(v)
    
    @staticmethod
    def _round_confidence_to_precision(confidence: float) -> float:
        """Round confidence value to the specified decimal places."""
        # Runtime assertion: validate input assumptions
        assert isinstance(confidence, (int, float)), f"Expected numeric confidence, got {type(confidence)}"
        assert 0.0 <= confidence <= 1.0, f"Confidence must be between 0.0 and 1.0, got {confidence}"
        
        rounded_value = round(confidence, CONFIDENCE_DECIMAL_PLACES)
        
        # Runtime assertion: validate output assumptions
        assert 0.0 <= rounded_value <= 1.0, f"Rounded confidence out of range: {rounded_value}"
        
        return rounded_value


class AgentState(BaseModel):
    """Current state of the autonomous agent."""

    last_activity: datetime = Field(
        ..., description="Timestamp of last on-chain transaction"
    )
    votes_cast_today: int = Field(
        default=0, ge=0, description="Number of votes cast in current 24h period"
    )
    last_activity_tx_hash: Optional[str] = Field(
        None, description="Transaction hash of last activity"
    )

    is_staked: bool = Field(
        default=False, description="Whether agent is currently staked"
    )
    staking_rewards_earned: float = Field(
        default=0.0, ge=0.0, description="Total OLAS rewards earned"
    )
    stake_amount: float = Field(
        default=0.0, ge=0.0, description="Amount of OLAS staked"
    )

    current_round: FSMRoundType = Field(
        default=FSMRoundType.IDLE, description="Current FSM round for health monitoring"
    )
    rounds_completed: int = Field(
        default=0, ge=0, description="Total FSM rounds completed"
    )

    is_healthy: bool = Field(default=True, description="Overall agent health status")

    @field_validator("last_activity")
    @classmethod
    def validate_last_activity(cls, v: datetime) -> datetime:
        """Validate last activity timestamp is reasonable."""
        # Runtime assertion: timestamp must be valid
        assert isinstance(v, datetime), f"Last activity must be datetime, got {type(v)}"
        assert v <= datetime.now(), f"Last activity cannot be in the future: {v}"
        
        return v
    
    def get_staking_summary(self) -> Dict[str, Any]:
        """Get a summary of staking-related information with data consistency warnings."""
        # Validate staking state consistency and collect warnings
        warnings = ModelValidationHelper.validate_staking_consistency(
            self.is_staked, self.stake_amount, self.staking_rewards_earned
        )
        
        return {
            "is_staked": self.is_staked,
            "stake_amount": self.stake_amount,
            "rewards_earned": self.staking_rewards_earned,
            "data_consistency_warnings": warnings,
            "is_data_consistent": len(warnings) == 0,
        }
    
    def get_activity_summary(self) -> Dict[str, Any]:
        """Get a summary of activity-related information."""
        # Runtime assertion: validate activity data consistency
        assert isinstance(self.votes_cast_today, int), f"votes_cast_today must be int, got {type(self.votes_cast_today)}"
        assert self.votes_cast_today >= 0, f"votes_cast_today cannot be negative: {self.votes_cast_today}"
        assert self.votes_cast_today <= 1000, f"votes_cast_today seems unreasonably high: {self.votes_cast_today}"
        
        return {
            "last_activity": self.last_activity,
            "votes_cast_today": self.votes_cast_today,
            "last_tx_hash": self.last_activity_tx_hash,
        }
    
    def get_fsm_summary(self) -> Dict[str, Any]:
        """Get a summary of FSM-related information."""
        # Runtime assertion: validate FSM state consistency
        assert isinstance(self.current_round, FSMRoundType), f"current_round must be FSMRoundType, got {type(self.current_round)}"
        assert isinstance(self.rounds_completed, int), f"rounds_completed must be int, got {type(self.rounds_completed)}"
        assert self.rounds_completed >= 0, f"rounds_completed cannot be negative: {self.rounds_completed}"
        
        return {
            "current_round": self.current_round,
            "rounds_completed": self.rounds_completed,
            "is_healthy": self.is_healthy,
        }

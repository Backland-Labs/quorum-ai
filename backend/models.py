"""Pydantic models for DAO and proposal data structures."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator, HttpUrl


# Constants for VoteDecision model
DEFAULT_ESTIMATED_GAS_COST = 0.005  # CELO
CONFIDENCE_DECIMAL_PLACES = 3

# Validation thresholds
MIN_PROPOSAL_ID_LENGTH = 3
MIN_REASONING_LENGTH = 10
MIN_MEANINGFUL_TEXT_LENGTH = 10
MIN_BLOCKCHAIN_ADDRESS_LENGTH = 10
MAX_REASONABLE_GAS_COST = 1000.0
MAX_REASONABLE_VOTES_PER_DAY = 1000
MAX_VOTERS_LIST_SIZE = 100

# Constants for VoteDecision model
DEFAULT_RISK_ASSESSMENT = "MEDIUM"

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
    def _validate_string_type_and_content(value: str, field_name: str) -> str:
        """Common validation for string type and basic content."""
        assert isinstance(value, str), f"{field_name} must be string, got {type(value)}"
        assert value.strip(), f"{field_name} cannot be empty or whitespace"
        return value.strip()

    @staticmethod
    def validate_blockchain_address(address: str) -> str:
        """Validate blockchain address format."""
        cleaned_address = ModelValidationHelper._validate_string_type_and_content(
            address, "Address"
        )

        # Runtime assertion: validate address format
        assert (
            len(cleaned_address) >= MIN_BLOCKCHAIN_ADDRESS_LENGTH
        ), f"Address too short: {cleaned_address}"
        assert not cleaned_address.isspace(), "Address cannot be only whitespace"
        assert not cleaned_address.startswith(
            " "
        ), "Address cannot start with whitespace"
        assert not cleaned_address.endswith(" "), "Address cannot end with whitespace"

        return cleaned_address

    @staticmethod
    def validate_positive_amount(amount: str, field_name: str = "amount") -> str:
        """Validate that a string amount represents a positive number."""
        cleaned_amount = ModelValidationHelper._validate_string_type_and_content(
            amount, field_name
        )

        try:
            numeric_value = float(cleaned_amount)
            # Runtime assertion: validate numeric constraints
            assert (
                numeric_value >= 0
            ), f"{field_name} cannot be negative: {numeric_value}"
            assert numeric_value != float(
                "inf"
            ), f"{field_name} cannot be infinite: {numeric_value}"
            assert (
                numeric_value == numeric_value
            ), f"{field_name} cannot be NaN: {numeric_value}"  # NaN check
        except (ValueError, TypeError) as e:
            raise ValueError(f"{field_name} must be a valid number: {e}")

        return amount

    @staticmethod
    def validate_meaningful_text(
        text: str,
        min_length: int = MIN_MEANINGFUL_TEXT_LENGTH,
        field_name: str = "text",
    ) -> str:
        """Validate that text has meaningful content."""
        cleaned_text = ModelValidationHelper._validate_string_type_and_content(
            text, field_name
        )

        # Runtime assertion: validate text content quality
        assert (
            len(cleaned_text) >= min_length
        ), f"{field_name} too short, must be at least {min_length} chars: {len(cleaned_text)}"
        assert (
            not cleaned_text.isdigit()
        ), f"{field_name} cannot be only digits: {cleaned_text}"
        assert cleaned_text.count(" ") < len(
            cleaned_text
        ), f"{field_name} cannot be mostly spaces: {cleaned_text}"

        return cleaned_text

    @staticmethod
    def _validate_staking_types(
        is_staked: bool, stake_amount: float, rewards_earned: float
    ) -> None:
        """Validate staking parameter types."""
        assert isinstance(
            is_staked, bool
        ), f"is_staked must be bool, got {type(is_staked)}"
        assert isinstance(
            stake_amount, (int, float)
        ), f"stake_amount must be numeric, got {type(stake_amount)}"
        assert isinstance(
            rewards_earned, (int, float)
        ), f"rewards_earned must be numeric, got {type(rewards_earned)}"

    @staticmethod
    def _check_staking_business_rules(
        is_staked: bool, stake_amount: float, rewards_earned: float
    ) -> List[str]:
        """Check staking business rules and return warnings."""
        warnings = []

        if is_staked and stake_amount <= 0:
            warnings.append(
                f"Agent marked as staked but has zero/negative stake amount: {stake_amount}"
            )

        if rewards_earned < 0:
            warnings.append(f"Negative staking rewards detected: {rewards_earned}")

        return warnings

    @staticmethod
    def validate_staking_consistency(
        is_staked: bool, stake_amount: float, rewards_earned: float
    ) -> List[str]:
        """Validate staking state consistency and return list of warnings."""
        # Type validation (these are still critical errors)
        ModelValidationHelper._validate_staking_types(
            is_staked, stake_amount, rewards_earned
        )

        # Business rule validation (converted to warnings)
        return ModelValidationHelper._check_staking_business_rules(
            is_staked, stake_amount, rewards_earned
        )


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


class ProposalState(str, Enum):
    """Snapshot proposal state enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"


class VoteType(str, Enum):
    """Vote type enumeration."""

    FOR = "FOR"
    AGAINST = "AGAINST"
    ABSTAIN = "ABSTAIN"


class Vote(BaseModel):
    """Snapshot-based individual vote on a proposal."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    # Required fields
    id: str = Field(..., description="Unique vote identifier")
    voter: str = Field(..., description="Voter's wallet address")
    choice: Any = Field(
        ...,
        description="Vote choice (supports multiple types: int, List[int], Dict[str, float], str)",
    )
    created: int = Field(..., ge=0, description="Timestamp when vote was cast")
    vp: float = Field(..., ge=0.0, description="Total voting power")
    vp_by_strategy: List[float] = Field(
        ..., description="Voting power breakdown by strategy"
    )

    # Optional fields
    vp_state: Optional[str] = Field(None, description="Voting power calculation state")
    space: Optional[Dict[str, Any]] = Field(None, description="Associated space object")
    proposal: Optional[Dict[str, Any]] = Field(
        None, description="Associated proposal object"
    )
    reason: Optional[str] = Field(None, description="Vote reasoning/comment")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    ipfs: Optional[str] = Field(None, description="IPFS hash")
    app: Optional[str] = Field(None, description="App used to vote")

    @staticmethod
    def _validate_vote_string_field(value: str, field_name: str) -> str:
        """Validate string fields with vote-specific assertions."""
        # Runtime assertion: value must be valid string type
        assert isinstance(value, str), f"{field_name} must be string, got {type(value)}"
        assert value.strip(), f"{field_name} cannot be empty or whitespace"

        cleaned_value = value.strip()

        # Runtime assertion: cleaned value must have meaningful content
        assert len(cleaned_value) > 0, f"{field_name} must contain meaningful content"
        assert (
            cleaned_value != value
            or not value.startswith(" ")
            and not value.endswith(" ")
        ), f"{field_name} should not have leading/trailing whitespace"

        return cleaned_value

    @staticmethod
    def _validate_non_negative_integer(value: int, field_name: str) -> int:
        """Validate non-negative integer fields."""
        # Runtime assertion: value must be integer type
        assert isinstance(
            value, int
        ), f"{field_name} must be integer, got {type(value)}"
        assert not isinstance(
            value, bool
        ), f"{field_name} cannot be boolean disguised as int"

        # Runtime assertion: value must be non-negative
        assert value >= 0, f"{field_name} cannot be negative: {value}"

        return value

    @staticmethod
    def _validate_non_negative_float(value: float, field_name: str) -> float:
        """Validate non-negative float fields."""
        # Runtime assertion: value must be numeric type
        assert isinstance(
            value, (int, float)
        ), f"{field_name} must be numeric, got {type(value)}"
        assert value >= 0.0, f"{field_name} cannot be negative: {value}"

        # Runtime assertion: value must be valid number
        assert value == value, f"{field_name} cannot be NaN"  # NaN check
        assert value != float("inf"), f"{field_name} cannot be infinite"

        return float(value)

    @staticmethod
    def _validate_vp_by_strategy_list(vp_by_strategy: List[float]) -> List[float]:
        """Validate vp_by_strategy list with individual value validation."""
        # Runtime assertion: value must be list
        assert isinstance(
            vp_by_strategy, list
        ), f"vp_by_strategy must be list, got {type(vp_by_strategy)}"
        assert len(vp_by_strategy) > 0, "vp_by_strategy cannot be empty list"

        # Validate each value is non-negative
        validated_values = []
        for i, value in enumerate(vp_by_strategy):
            validated_value = Vote._validate_non_negative_float(
                value, f"vp_by_strategy[{i}]"
            )
            validated_values.append(validated_value)

        return validated_values

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate vote ID is non-empty string."""
        return cls._validate_vote_string_field(v, "id")

    @field_validator("voter")
    @classmethod
    def validate_voter(cls, v: str) -> str:
        """Validate voter address is valid blockchain address."""
        return ModelValidationHelper.validate_blockchain_address(v)

    @field_validator("created")
    @classmethod
    def validate_created(cls, v: int) -> int:
        """Validate created timestamp is non-negative integer."""
        return cls._validate_non_negative_integer(v, "created")

    @field_validator("vp")
    @classmethod
    def validate_vp(cls, v: float) -> float:
        """Validate voting power is non-negative float."""
        return cls._validate_non_negative_float(v, "vp")

    @field_validator("vp_by_strategy")
    @classmethod
    def validate_vp_by_strategy(cls, v: List[float]) -> List[float]:
        """Validate vp_by_strategy is non-empty list of non-negative floats."""
        return cls._validate_vp_by_strategy_list(v)

    @field_validator("choice")
    @classmethod
    def validate_choice(cls, v: Any) -> Any:
        """Validate choice field supports multiple types."""
        # Runtime assertion: choice cannot be None
        assert v is not None, "choice field is required and cannot be None"

        # Runtime assertion: choice cannot be boolean (probably invalid)
        if isinstance(v, bool):
            raise ValueError("choice field cannot be boolean type")

        # Allow int, list, dict, str types (common Snapshot choice types)
        valid_types = (int, list, dict, str)
        if not isinstance(v, valid_types):
            raise ValueError(f"choice must be one of {valid_types}, got {type(v)}")

        return v


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
    """Snapshot-based DAO proposal model."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    # Required fields
    id: str = Field(..., description="Unique proposal identifier")
    title: str = Field(..., description="Proposal title")
    choices: List[str] = Field(..., description="Array of voting options")
    start: int = Field(..., ge=0, description="Start timestamp")
    end: int = Field(..., ge=0, description="End timestamp")
    state: str = Field(..., description="Proposal state")
    author: str = Field(..., description="Author's wallet address")
    network: str = Field(..., description="Blockchain network")
    symbol: str = Field(..., description="Token symbol")
    scores: List[float] = Field(..., description="Vote scores per choice")
    scores_total: float = Field(..., ge=0.0, description="Total voting power")
    votes: int = Field(..., ge=0, description="Number of votes cast")
    created: int = Field(..., ge=0, description="Creation timestamp")
    quorum: float = Field(..., ge=0.0, description="Quorum threshold")

    # Optional fields
    body: Optional[str] = Field(None, description="Proposal description/content")
    snapshot: Optional[int] = Field(None, ge=0, description="Block number snapshot")
    space: Optional[Dict[str, Any]] = Field(None, description="Associated space object")
    scores_by_strategy: Optional[Dict[str, Any]] = Field(
        None, description="Breakdown by strategy"
    )
    updated: Optional[int] = Field(None, ge=0, description="Last update timestamp")
    type: Optional[str] = Field(None, description="Proposal type")
    strategies: List[Dict[str, Any]] = Field(
        default_factory=list, description="Voting strategies used"
    )
    plugins: Optional[Dict[str, Any]] = Field(None, description="Additional plugins")
    ipfs: Optional[str] = Field(None, description="IPFS hash")
    discussion: Optional[str] = Field(None, description="Discussion link")
    privacy: Optional[str] = Field(None, description="Privacy setting")

    @staticmethod
    def _validate_proposal_string_field(value: str, field_name: str) -> str:
        """Validate string fields with proposal-specific assertions."""
        # Runtime assertion: value must be valid string type
        assert isinstance(value, str), f"{field_name} must be string, got {type(value)}"
        assert value.strip(), f"{field_name} cannot be empty or whitespace"

        cleaned_value = value.strip()

        # Runtime assertion: cleaned value must have meaningful content
        assert len(cleaned_value) > 0, f"{field_name} must contain meaningful content"
        assert (
            cleaned_value != value
            or not value.startswith(" ")
            and not value.endswith(" ")
        ), f"{field_name} should not have leading/trailing whitespace"

        return cleaned_value

    @staticmethod
    def _validate_non_negative_integer(value: int, field_name: str) -> int:
        """Validate non-negative integer fields."""
        # Runtime assertion: value must be integer type
        assert isinstance(
            value, int
        ), f"{field_name} must be integer, got {type(value)}"
        assert not isinstance(
            value, bool
        ), f"{field_name} cannot be boolean disguised as int"

        # Runtime assertion: value must be non-negative
        assert value >= 0, f"{field_name} cannot be negative: {value}"

        return value

    @staticmethod
    def _validate_non_negative_float(value: float, field_name: str) -> float:
        """Validate non-negative float fields."""
        # Runtime assertion: value must be numeric type
        assert isinstance(
            value, (int, float)
        ), f"{field_name} must be numeric, got {type(value)}"
        assert value >= 0.0, f"{field_name} cannot be negative: {value}"

        # Runtime assertion: value must be valid number
        assert value == value, f"{field_name} cannot be NaN"  # NaN check
        assert value != float("inf"), f"{field_name} cannot be infinite"

        return float(value)

    @staticmethod
    def _validate_non_empty_list(value: List[Any], field_name: str) -> List[Any]:
        """Validate non-empty list fields."""
        # Runtime assertion: value must be list type
        assert isinstance(value, list), f"{field_name} must be list, got {type(value)}"
        assert len(value) > 0, f"{field_name} cannot be empty list"

        return value

    @staticmethod
    def _validate_optional_url(url: Optional[str], field_name: str) -> Optional[str]:
        """Validate optional URL fields with consistent error handling."""
        if url is None:
            return url

        # Runtime assertion: URL must be string if provided
        assert isinstance(
            url, str
        ), f"{field_name} must be string if provided, got {type(url)}"
        assert url.strip(), f"{field_name} cannot be empty string if provided"

        cleaned_url = url.strip()

        try:
            # Use HttpUrl for validation then return as string
            HttpUrl(cleaned_url)
            # Runtime assertion: URL validation succeeded
            assert "://" in cleaned_url, f"{field_name} must contain protocol scheme"
            return cleaned_url
        except Exception as e:
            raise ValueError(
                f"Invalid {field_name} URL format: {cleaned_url}. Error: {str(e)}"
            )

    @staticmethod
    def _validate_scores_list(scores: List[float]) -> List[float]:
        """Validate scores list with individual score validation."""
        # Runtime assertion: value must be list
        assert isinstance(scores, list), f"scores must be list, got {type(scores)}"

        # Validate each score is non-negative
        validated_scores = []
        for i, score in enumerate(scores):
            validated_score = Proposal._validate_non_negative_float(
                score, f"scores[{i}]"
            )
            validated_scores.append(validated_score)

        return validated_scores

    @staticmethod
    def _validate_optional_integer(
        value: Optional[int], field_name: str
    ) -> Optional[int]:
        """Validate optional integer fields."""
        if value is not None:
            return Proposal._validate_non_negative_integer(value, field_name)
        return value

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate proposal ID is non-empty string."""
        return cls._validate_proposal_string_field(v, "id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate proposal title is non-empty string."""
        return cls._validate_proposal_string_field(v, "title")

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        """Validate proposal state is non-empty string."""
        return cls._validate_proposal_string_field(v, "state")

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        """Validate author address is non-empty string."""
        return cls._validate_proposal_string_field(v, "author")

    @field_validator("network")
    @classmethod
    def validate_network(cls, v: str) -> str:
        """Validate network is non-empty string."""
        return cls._validate_proposal_string_field(v, "network")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol is non-empty string."""
        return cls._validate_proposal_string_field(v, "symbol")

    @field_validator("choices")
    @classmethod
    def validate_choices(cls, v: List[str]) -> List[str]:
        """Validate choices is non-empty list."""
        return cls._validate_non_empty_list(v, "choices")

    @field_validator("scores")
    @classmethod
    def validate_scores(cls, v: List[float]) -> List[float]:
        """Validate scores are non-negative floats."""
        return cls._validate_scores_list(v)

    @field_validator("scores_total")
    @classmethod
    def validate_scores_total(cls, v: float) -> float:
        """Validate scores_total is non-negative float."""
        return cls._validate_non_negative_float(v, "scores_total")

    @field_validator("votes")
    @classmethod
    def validate_votes(cls, v: int) -> int:
        """Validate votes is non-negative integer."""
        return cls._validate_non_negative_integer(v, "votes")

    @field_validator("created")
    @classmethod
    def validate_created(cls, v: int) -> int:
        """Validate created timestamp is non-negative integer."""
        return cls._validate_non_negative_integer(v, "created")

    @field_validator("quorum")
    @classmethod
    def validate_quorum(cls, v: float) -> float:
        """Validate quorum is non-negative float."""
        return cls._validate_non_negative_float(v, "quorum")

    @field_validator("start")
    @classmethod
    def validate_start(cls, v: int) -> int:
        """Validate start timestamp is non-negative integer."""
        return cls._validate_non_negative_integer(v, "start")

    @field_validator("end")
    @classmethod
    def validate_end(cls, v: int) -> int:
        """Validate end timestamp is non-negative integer."""
        return cls._validate_non_negative_integer(v, "end")

    @field_validator("snapshot")
    @classmethod
    def validate_snapshot(cls, v: Optional[int]) -> Optional[int]:
        """Validate snapshot block number is non-negative if provided."""
        return cls._validate_optional_integer(v, "snapshot")

    @field_validator("updated")
    @classmethod
    def validate_updated(cls, v: Optional[int]) -> Optional[int]:
        """Validate updated timestamp is non-negative if provided."""
        return cls._validate_optional_integer(v, "updated")

    @field_validator("discussion")
    @classmethod
    def validate_discussion_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate discussion URL format if provided."""
        return cls._validate_optional_url(v, "discussion")

    @staticmethod
    def _validate_scores_choices_consistency(
        scores: List[float], choices: List[str]
    ) -> None:
        """Validate scores and choices array consistency."""
        # Runtime assertion: arrays must have matching lengths
        assert (
            len(scores) == len(choices)
        ), f"scores array length ({len(scores)}) must match choices array length ({len(choices)})"
        assert len(scores) > 0, "Both scores and choices arrays must be non-empty"

    @model_validator(mode="after")
    def validate_proposal_consistency(self) -> "Proposal":
        """Validate cross-field consistency."""
        # Validate scores and choices arrays have consistent lengths
        self._validate_scores_choices_consistency(self.scores, self.choices)

        # Validate logical timestamp relationships
        self._validate_timestamp_logic()

        return self

    def _validate_timestamp_logic(self) -> None:
        """Validate logical relationships between timestamps."""
        # Runtime assertion: end must be after start
        if self.end <= self.start:
            raise ValueError(
                f"Proposal end timestamp ({self.end}) must be after start timestamp ({self.start})"
            )

        # Runtime assertion: created must be before or equal to start
        if self.created > self.start:
            raise ValueError(
                f"Proposal created timestamp ({self.created}) must be before or equal to start timestamp ({self.start})"
            )


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
        if len(v) > MAX_VOTERS_LIST_SIZE:
            raise ValueError(
                f"Voters list cannot exceed {MAX_VOTERS_LIST_SIZE} entries"
            )
        return v


class VoteDecision(BaseModel):
    """AI-generated voting decision for a proposal."""

    proposal_id: str = Field(..., description="The proposal ID being voted on")
    vote: VoteType = Field(
        ..., description="The voting decision: FOR, AGAINST, or ABSTAIN"
    )
    confidence: float = Field(
        ..., description="Confidence score in the decision (0.0 to 1.0)"
    )
    reasoning: str = Field(..., description="AI-generated explanation for the vote")
    risk_assessment: RiskLevel = Field(
        default=RiskLevel.MEDIUM, description="Risk level: LOW, MEDIUM, or HIGH"
    )
    estimated_gas_cost: float = Field(
        default=DEFAULT_ESTIMATED_GAS_COST,
        description="Estimated transaction cost in CELO",
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
        assert len(v.strip()) >= MIN_PROPOSAL_ID_LENGTH, f"Proposal ID too short: {v}"

        return v.strip()

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        """Validate reasoning has sufficient content."""
        return ModelValidationHelper.validate_meaningful_text(
            v, min_length=MIN_REASONING_LENGTH, field_name="reasoning"
        )

    @field_validator("estimated_gas_cost")
    @classmethod
    def validate_gas_cost(cls, v: float) -> float:
        """Validate gas cost is reasonable."""
        # Runtime assertion: gas cost must be valid
        assert isinstance(v, (int, float)), f"Gas cost must be numeric, got {type(v)}"
        assert v >= 0.0, f"Gas cost cannot be negative: {v}"
        assert v <= MAX_REASONABLE_GAS_COST, f"Gas cost seems unreasonably high: {v}"

        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is within valid range and precision."""
        # Runtime assertion: confidence must be a valid number
        assert isinstance(v, (int, float)), f"Confidence must be numeric, got {type(v)}"

        # Check for NaN
        if v != v:  # NaN check
            raise ValueError("Confidence cannot be NaN")

        # Check for infinite values
        if v == float("inf") or v == float("-inf"):
            raise ValueError("Confidence cannot be infinite")

        # Check range constraints
        if v < 0.0 or v > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")

        return cls._round_confidence_to_precision(v)

    @staticmethod
    def _round_confidence_to_precision(confidence: float) -> float:
        """Round confidence value to the specified decimal places."""
        # Runtime assertion: validate input assumptions
        assert isinstance(
            confidence, (int, float)
        ), f"Expected numeric confidence, got {type(confidence)}"
        assert (
            0.0 <= confidence <= 1.0
        ), f"Confidence must be between 0.0 and 1.0, got {confidence}"

        rounded_value = round(confidence, CONFIDENCE_DECIMAL_PLACES)

        # Runtime assertion: validate output assumptions
        assert (
            0.0 <= rounded_value <= 1.0
        ), f"Rounded confidence out of range: {rounded_value}"

        return rounded_value


class AiVoteResponse(BaseModel):
    vote: str = Field(description="Vote decision: FOR, AGAINST, or ABSTAIN")
    reasoning: str = Field(description="Reasoning for the vote decision")


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

    def _validate_activity_data(self) -> None:
        """Validate activity data consistency."""
        # Runtime assertion: validate votes_cast_today constraints
        assert isinstance(
            self.votes_cast_today, int
        ), f"votes_cast_today must be int, got {type(self.votes_cast_today)}"
        assert (
            self.votes_cast_today >= 0
        ), f"votes_cast_today cannot be negative: {self.votes_cast_today}"
        assert (
            self.votes_cast_today <= MAX_REASONABLE_VOTES_PER_DAY
        ), f"votes_cast_today seems unreasonably high: {self.votes_cast_today}"

        # Runtime assertion: validate transaction hash format if provided
        if self.last_activity_tx_hash is not None:
            assert isinstance(
                self.last_activity_tx_hash, str
            ), f"tx_hash must be string, got {type(self.last_activity_tx_hash)}"
            assert (
                len(self.last_activity_tx_hash.strip()) > 0
            ), "tx_hash cannot be empty"

    def _validate_fsm_data(self) -> None:
        """Validate FSM state consistency."""
        # Runtime assertion: validate FSM round state
        assert isinstance(
            self.current_round, FSMRoundType
        ), f"current_round must be FSMRoundType, got {type(self.current_round)}"
        assert isinstance(
            self.rounds_completed, int
        ), f"rounds_completed must be int, got {type(self.rounds_completed)}"
        assert (
            self.rounds_completed >= 0
        ), f"rounds_completed cannot be negative: {self.rounds_completed}"

        # Runtime assertion: validate health state consistency
        assert isinstance(
            self.is_healthy, bool
        ), f"is_healthy must be bool, got {type(self.is_healthy)}"

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
        self._validate_activity_data()

        return {
            "last_activity": self.last_activity,
            "votes_cast_today": self.votes_cast_today,
            "last_tx_hash": self.last_activity_tx_hash,
        }

    def get_fsm_summary(self) -> Dict[str, Any]:
        """Get a summary of FSM-related information."""
        self._validate_fsm_data()

        return {
            "current_round": self.current_round,
            "rounds_completed": self.rounds_completed,
            "is_healthy": self.is_healthy,
        }


class Space(BaseModel):
    """Snapshot Space model representing a DAO governance space."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    # Required fields
    id: str = Field(..., description="Unique space identifier")
    name: str = Field(..., description="Display name of the space")
    network: str = Field(..., description="Blockchain network identifier")
    symbol: str = Field(..., description="Token symbol for the space")
    strategies: List[Dict[str, Any]] = Field(
        default_factory=list, description="Array of voting strategies"
    )
    admins: List[str] = Field(
        default_factory=list, description="Array of admin addresses"
    )
    moderators: List[str] = Field(
        default_factory=list, description="Array of moderator addresses"
    )
    members: List[str] = Field(
        default_factory=list, description="Array of member addresses"
    )
    private: bool = Field(default=False, description="Whether space is private")
    verified: bool = Field(default=False, description="Verification status")
    created: int = Field(..., ge=0, description="Creation timestamp")
    proposalsCount: int = Field(default=0, ge=0, description="Total proposal count")
    followersCount: int = Field(default=0, ge=0, description="Follower count")
    votesCount: int = Field(default=0, ge=0, description="Total vote count")

    # Optional fields
    about: Optional[str] = Field(None, description="Description of the space")
    avatar: Optional[str] = Field(None, description="Avatar image URL")
    cover: Optional[str] = Field(None, description="Cover image URL")
    website: Optional[str] = Field(None, description="Website URL")
    twitter: Optional[str] = Field(None, description="Twitter handle")
    github: Optional[str] = Field(None, description="GitHub username")

    @staticmethod
    def _validate_space_string_field(value: str, field_name: str) -> str:
        """Validate string fields with space-specific assertions."""
        # Runtime assertion: value must be valid string type
        assert isinstance(value, str), f"{field_name} must be string, got {type(value)}"
        assert value.strip(), f"{field_name} cannot be empty or whitespace"

        cleaned_value = value.strip()

        # Runtime assertion: cleaned value must have meaningful content
        assert len(cleaned_value) > 0, f"{field_name} must contain meaningful content"
        assert (
            cleaned_value != value
            or not value.startswith(" ")
            and not value.endswith(" ")
        ), f"{field_name} should not have leading/trailing whitespace"

        return cleaned_value

    @staticmethod
    def _validate_optional_url(url: Optional[str], field_name: str) -> Optional[str]:
        """Validate optional URL fields with consistent error handling."""
        if url is None:
            return url

        # Runtime assertion: URL must be string if provided
        assert isinstance(
            url, str
        ), f"{field_name} must be string if provided, got {type(url)}"
        assert url.strip(), f"{field_name} cannot be empty string if provided"

        cleaned_url = url.strip()

        try:
            # Use HttpUrl for validation then return as string
            HttpUrl(cleaned_url)
            # Runtime assertion: URL validation succeeded
            assert "://" in cleaned_url, f"{field_name} must contain protocol scheme"
            return cleaned_url
        except Exception as e:
            raise ValueError(
                f"Invalid {field_name} URL format: {cleaned_url}. Error: {str(e)}"
            )

    @staticmethod
    def _validate_boolean_field(value, field_name: str) -> bool:
        """Validate boolean fields with runtime assertions."""
        # Runtime assertion: value must be boolean type
        assert isinstance(
            value, bool
        ), f"{field_name} must be boolean type, got {type(value)}"
        assert (
            value is True or value is False
        ), f"{field_name} must be exactly True or False, got {value}"

        return value

    @staticmethod
    def _validate_integer_field(value, field_name: str) -> int:
        """Validate integer fields with runtime assertions."""
        # Runtime assertion: value must be integer type
        assert isinstance(
            value, int
        ), f"{field_name} must be integer type, got {type(value)}"
        assert not isinstance(
            value, bool
        ), f"{field_name} cannot be boolean disguised as int"

        return value

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate space ID is non-empty string."""
        return cls._validate_space_string_field(v, "id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate space name is non-empty string."""
        return cls._validate_space_string_field(v, "name")

    @field_validator("network")
    @classmethod
    def validate_network(cls, v: str) -> str:
        """Validate network is non-empty string."""
        return cls._validate_space_string_field(v, "network")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol is non-empty string."""
        return cls._validate_space_string_field(v, "symbol")

    @field_validator("avatar")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate avatar URL format if provided."""
        return cls._validate_optional_url(v, "avatar")

    @field_validator("cover")
    @classmethod
    def validate_cover_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate cover URL format if provided."""
        return cls._validate_optional_url(v, "cover")

    @field_validator("website")
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format if provided."""
        return cls._validate_optional_url(v, "website")

    @field_validator("private", mode="before")
    @classmethod
    def validate_private_type(cls, v) -> bool:
        """Validate private field is boolean type."""
        return cls._validate_boolean_field(v, "private")

    @field_validator("verified", mode="before")
    @classmethod
    def validate_verified_type(cls, v) -> bool:
        """Validate verified field is boolean type."""
        return cls._validate_boolean_field(v, "verified")

    @field_validator("created", mode="before")
    @classmethod
    def validate_created_type(cls, v) -> int:
        """Validate created field is integer type."""
        return cls._validate_integer_field(v, "created")

    @field_validator("proposalsCount", mode="before")
    @classmethod
    def validate_proposals_count_type(cls, v) -> int:
        """Validate proposalsCount field is integer type."""
        return cls._validate_integer_field(v, "proposalsCount")

    @field_validator("followersCount", mode="before")
    @classmethod
    def validate_followers_count_type(cls, v) -> int:
        """Validate followersCount field is integer type."""
        return cls._validate_integer_field(v, "followersCount")

    @field_validator("votesCount", mode="before")
    @classmethod
    def validate_votes_count_type(cls, v) -> int:
        """Validate votesCount field is integer type."""
        return cls._validate_integer_field(v, "votesCount")


class AgentRunRequest(BaseModel):
    """Request model for agent run execution."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    space_id: str = Field(..., description="Snapshot space ID to monitor")
    dry_run: bool = Field(default=False, description="If true, simulate without voting")

    @field_validator("space_id")
    @classmethod
    def validate_space_id(cls, v: str) -> str:
        """Validate space_id is non-empty string."""
        # Runtime assertion: space_id must be meaningful
        assert isinstance(v, str), f"Space ID must be string, got {type(v)}"
        assert v.strip(), "Space ID cannot be empty or whitespace"

        cleaned_id = v.strip()

        # Runtime assertion: cleaned value must have meaningful content
        assert len(cleaned_id) > 0, "Space ID must contain meaningful content"

        return cleaned_id

    @field_validator("dry_run", mode="before")
    @classmethod
    def validate_dry_run(cls, v) -> bool:
        """Validate dry_run is boolean type."""
        # Runtime assertion: value must be boolean type
        assert isinstance(v, bool), f"Dry run must be boolean type, got {type(v)}"
        assert (
            v is True or v is False
        ), f"Dry run must be exactly True or False, got {v}"

        return v


class AgentRunResponse(BaseModel):
    """Response model for agent run execution."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    space_id: str = Field(..., description="Snapshot space ID that was monitored")
    proposals_analyzed: int = Field(
        ..., ge=0, description="Number of proposals analyzed"
    )
    votes_cast: List[VoteDecision] = Field(
        ..., description="List of vote decisions made"
    )
    user_preferences_applied: bool = Field(
        ..., description="Whether user preferences were applied"
    )
    execution_time: float = Field(..., ge=0.0, description="Execution time in seconds")
    errors: List[str] = Field(
        default_factory=list, description="List of errors encountered"
    )
    next_check_time: Optional[datetime] = Field(
        None, description="Next scheduled check time"
    )

    @field_validator("space_id")
    @classmethod
    def validate_space_id(cls, v: str) -> str:
        """Validate space_id is non-empty string."""
        # Runtime assertion: space_id must be meaningful
        assert isinstance(v, str), f"Space ID must be string, got {type(v)}"
        assert v.strip(), "Space ID cannot be empty or whitespace"

        cleaned_id = v.strip()

        # Runtime assertion: cleaned value must have meaningful content
        assert len(cleaned_id) > 0, "Space ID must contain meaningful content"

        return cleaned_id

    @field_validator("proposals_analyzed")
    @classmethod
    def validate_proposals_analyzed(cls, v: int) -> int:
        """Validate proposals_analyzed is non-negative integer."""
        # Runtime assertion: value must be integer type
        assert isinstance(v, int), f"Proposals analyzed must be integer, got {type(v)}"
        assert not isinstance(
            v, bool
        ), "Proposals analyzed cannot be boolean disguised as int"

        # Runtime assertion: value must be non-negative
        assert v >= 0, f"Proposals analyzed cannot be negative: {v}"

        return v

    @field_validator("execution_time")
    @classmethod
    def validate_execution_time(cls, v: float) -> float:
        """Validate execution_time is non-negative float."""
        # Runtime assertion: value must be numeric type
        assert isinstance(
            v, (int, float)
        ), f"Execution time must be numeric, got {type(v)}"
        assert v >= 0.0, f"Execution time cannot be negative: {v}"

        # Runtime assertion: value must be valid number
        assert v == v, "Execution time cannot be NaN"  # NaN check
        assert v != float("inf"), "Execution time cannot be infinite"

        return float(v)


class UserPreferences(BaseModel):
    """User preferences model for agent run configuration."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    voting_strategy: VotingStrategy = Field(
        default=VotingStrategy.BALANCED, description="Voting strategy to use"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for voting",
    )
    max_proposals_per_run: int = Field(
        default=3, ge=1, le=10, description="Maximum proposals to analyze per run"
    )
    blacklisted_proposers: List[str] = Field(
        default_factory=list, description="List of proposer addresses to avoid"
    )
    whitelisted_proposers: List[str] = Field(
        default_factory=list, description="List of trusted proposer addresses"
    )

    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence_threshold(cls, v: float) -> float:
        """Validate confidence_threshold is between 0.0 and 1.0."""
        # Runtime assertion: value must be numeric type
        assert isinstance(
            v, (int, float)
        ), f"Confidence threshold must be numeric, got {type(v)}"

        # Check for NaN
        if v != v:  # NaN check
            raise ValueError("Confidence threshold cannot be NaN")

        # Check for infinite values
        if v == float("inf") or v == float("-inf"):
            raise ValueError("Confidence threshold cannot be infinite")

        # Check range constraints
        if v < 0.0 or v > 1.0:
            raise ValueError(
                f"Confidence threshold must be between 0.0 and 1.0, got {v}"
            )

        return float(v)

    @field_validator("max_proposals_per_run")
    @classmethod
    def validate_max_proposals_per_run(cls, v: int) -> int:
        """Validate max_proposals_per_run is between 1 and 10."""
        # Runtime assertion: value must be integer type
        assert isinstance(
            v, int
        ), f"Max proposals per run must be integer, got {type(v)}"
        assert not isinstance(
            v, bool
        ), "Max proposals per run cannot be boolean disguised as int"

        # Runtime assertion: value must be within valid range
        assert 1 <= v <= 10, f"Max proposals per run must be between 1 and 10, got {v}"

        return v

    @field_validator("blacklisted_proposers")
    @classmethod
    def validate_blacklisted_proposers(cls, v: List[str]) -> List[str]:
        """Validate blacklisted_proposers is list of non-empty strings."""
        # Runtime assertion: value must be list
        assert isinstance(v, list), f"Blacklisted proposers must be list, got {type(v)}"

        # Validate each address is non-empty
        validated_addresses = []
        for i, address in enumerate(v):
            if not isinstance(address, str):
                raise ValueError(
                    f"Blacklisted proposer at index {i} must be string, got {type(address)}"
                )
            if not address.strip():
                raise ValueError(
                    f"Blacklisted proposer at index {i} cannot be empty or whitespace"
                )
            validated_addresses.append(address.strip())

        return validated_addresses

    @field_validator("whitelisted_proposers")
    @classmethod
    def validate_whitelisted_proposers(cls, v: List[str]) -> List[str]:
        """Validate whitelisted_proposers is list of non-empty strings."""
        # Runtime assertion: value must be list
        assert isinstance(v, list), f"Whitelisted proposers must be list, got {type(v)}"

        # Validate each address is non-empty
        validated_addresses = []
        for i, address in enumerate(v):
            if not isinstance(address, str):
                raise ValueError(
                    f"Whitelisted proposer at index {i} must be string, got {type(address)}"
                )
            if not address.strip():
                raise ValueError(
                    f"Whitelisted proposer at index {i} cannot be empty or whitespace"
                )
            validated_addresses.append(address.strip())

        return validated_addresses

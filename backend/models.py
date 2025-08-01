"""Pydantic models for DAO and proposal data structures."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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


# Risk assessment levels
class RiskLevel(str, Enum):
    """Risk assessment levels for proposals."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Voting strategy types
class VotingStrategy(str, Enum):
    """Voting strategies for autonomous agent decision making."""

    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


# Withdrawal status types
class WithdrawalStatus(str, Enum):
    """Status of withdrawal transactions."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelValidationHelper:
    """Centralized validation helper for model business rules."""

    @staticmethod
    def _validate_string_type_and_content(value: str, field_name: str) -> str:
        """Common validation for string type and basic content."""
        # Type validation
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string, got {type(value)}")

        # Strip whitespace for consistent validation
        stripped = value.strip()

        # Content validation
        if not stripped:
            raise ValueError(f"{field_name} cannot be empty or whitespace only")

        return stripped

    @staticmethod
    def validate_string_field(value: str, field_name: str) -> str:
        """Validate field is non-empty string."""
        return ModelValidationHelper._validate_string_type_and_content(
            value, field_name
        )

    @staticmethod
    def validate_meaningful_text(
        value: str, min_length: int = MIN_MEANINGFUL_TEXT_LENGTH, field_name: str = None
    ) -> str:
        """Validate text has meaningful content."""
        field_label = field_name or "Text"
        cleaned = ModelValidationHelper._validate_string_type_and_content(
            value, field_label
        )

        if len(cleaned) < min_length:
            raise ValueError(
                f"{field_label} must be at least {min_length} characters, got {len(cleaned)}"
            )

        return cleaned

    @staticmethod
    def validate_blockchain_address(value: str) -> str:
        """Validate blockchain address format."""
        cleaned = ModelValidationHelper._validate_string_type_and_content(
            value, "Address"
        )

        if len(cleaned) < MIN_BLOCKCHAIN_ADDRESS_LENGTH:
            raise ValueError(f"Invalid blockchain address format: {cleaned}")

        return cleaned

    @staticmethod
    def validate_positive_amount(value: str, field_name: str) -> str:
        """Validate string represents positive numeric amount."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a string, got {type(value)}")

        try:
            amount = float(value)
            if amount < 0:
                raise ValueError(f"{field_name} cannot be negative: {value}")
        except ValueError:
            raise ValueError(f"{field_name} must be numeric: {value}")

        return value

    @staticmethod
    def validate_optional_url(value: Optional[str], field_name: str) -> Optional[str]:
        """Validate optional URL format."""
        if value is None:
            return None

        cleaned = ModelValidationHelper._validate_string_type_and_content(
            value, field_name
        )

        # Basic URL validation
        if not (
            cleaned.startswith("http://")
            or cleaned.startswith("https://")
            or cleaned.startswith("ipfs://")
        ):
            raise ValueError(f"{field_name} must be a valid URL: {cleaned}")

        return cleaned

    @staticmethod
    def validate_boolean_field(value: Any, field_name: str) -> bool:
        """Convert and validate boolean field."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ["true", "1", "yes"]:
                return True
            elif value.lower() in ["false", "0", "no"]:
                return False
        if isinstance(value, (int, float)):
            return bool(value)

        raise ValueError(
            f"{field_name} must be convertible to boolean, got {type(value)}: {value}"
        )

    @staticmethod
    def validate_non_negative_integer(value: Any, field_name: str) -> int:
        """Validate and convert to non-negative integer."""
        if isinstance(value, bool):
            raise ValueError(
                f"{field_name} cannot be boolean disguised as int, got {value}"
            )

        try:
            int_value = int(value)
            if int_value < 0:
                raise ValueError(f"{field_name} cannot be negative: {value}")
            return int_value
        except (ValueError, TypeError):
            raise ValueError(
                f"{field_name} must be a non-negative integer, got {type(value)}: {value}"
            )


# Enum for vote types
class VoteType(str, Enum):
    """Vote types on proposals."""

    FOR = "FOR"
    AGAINST = "AGAINST"
    ABSTAIN = "ABSTAIN"


class ProposalState(str, Enum):
    """Proposal states from Snapshot."""

    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"


class VoteChoice(BaseModel):
    """Individual voting choice for proposals."""

    choice: int = Field(..., description="Numeric choice identifier")
    label: str = Field(..., description="Human-readable choice label")
    votes: float = Field(..., ge=0, description="Number of votes for this choice")
    percentage: float = Field(
        ..., ge=0, le=100, description="Percentage of total votes"
    )


class Proposal(BaseModel):
    """Snapshot proposal model representing a governance proposal."""

    # Required fields
    id: str = Field(..., description="Unique proposal identifier")
    title: str = Field(..., description="Proposal title")
    body: str = Field(..., description="Full proposal description")
    state: str = Field(..., description="Current state of the proposal")
    author: str = Field(..., description="Proposal author address")
    created: int = Field(..., description="Creation timestamp")
    start: int = Field(..., description="Voting start timestamp")
    end: int = Field(..., description="Voting end timestamp")
    votes: int = Field(default=0, description="Total number of votes")
    scores_total: float = Field(default=0.0, description="Total voting score")

    # Choice fields
    choices: List[str] = Field(
        default_factory=list, description="Voting choice options"
    )
    scores: List[float] = Field(default_factory=list, description="Scores per choice")

    # Optional fields
    snapshot: Optional[str] = Field(None, description="Blockchain snapshot identifier")
    discussion: Optional[str] = Field(None, description="Discussion forum link")
    ipfs: Optional[str] = Field(None, description="IPFS content hash")
    space_id: Optional[str] = Field(None, description="Parent space identifier")

    # Computed fields
    is_active: bool = Field(
        default=False, description="Whether voting is currently open"
    )
    time_remaining: Optional[str] = Field(
        None, description="Human-readable time remaining"
    )
    vote_choices: List[VoteChoice] = Field(
        default_factory=list, description="Processed voting choices with percentages"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate proposal ID format."""
        return ModelValidationHelper.validate_string_field(v, "id")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate proposal title."""
        return ModelValidationHelper.validate_string_field(v, "title")

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        """Validate author address."""
        return ModelValidationHelper.validate_blockchain_address(v)

    @field_validator("discussion")
    @classmethod
    def validate_discussion_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate discussion URL if provided."""
        return ModelValidationHelper.validate_optional_url(v, "discussion")

    @model_validator(mode="after")
    def compute_active_status(self) -> "Proposal":
        """Compute whether proposal is currently active for voting."""
        now = datetime.utcnow().timestamp()
        self.is_active = self.start <= now <= self.end
        return self

    @model_validator(mode="after")
    def compute_vote_choices(self) -> "Proposal":
        """Process choices and scores into VoteChoice objects."""
        if self.choices and self.scores:
            total_score = sum(self.scores) if self.scores else 1
            self.vote_choices = [
                VoteChoice(
                    choice=i + 1,
                    label=label,
                    votes=self.scores[i] if i < len(self.scores) else 0,
                    percentage=(
                        (self.scores[i] / total_score * 100)
                        if i < len(self.scores) and total_score > 0
                        else 0
                    ),
                )
                for i, label in enumerate(self.choices)
            ]
        return self


class ProposalSummary(BaseModel):
    """AI-generated summary of a proposal."""

    proposal_id: str = Field(..., description="The proposal ID being summarized")
    title: str = Field(..., description="Original proposal title")
    summary: str = Field(..., description="AI-generated concise summary")
    key_points: List[str] = Field(
        ..., description="List of key points from the proposal"
    )
    risk_assessment: Optional[RiskLevel] = Field(
        None, description="Risk level assessment"
    )
    recommendation: Optional[str] = Field(
        None, description="AI-generated voting recommendation"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the analysis"
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

    # Attestation tracking fields
    space_id: Optional[str] = Field(
        None, description="Snapshot space ID for attestation"
    )
    attestation_status: Optional[str] = Field(
        None, description="Status: pending, success, failed"
    )
    attestation_tx_hash: Optional[str] = Field(
        None, description="On-chain attestation transaction hash"
    )
    attestation_uid: Optional[str] = Field(
        None, description="EAS attestation unique identifier"
    )
    attestation_error: Optional[str] = Field(
        None, description="Error message if attestation failed"
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

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate space ID is non-empty string."""
        return ModelValidationHelper.validate_string_field(v, "id")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate space name is non-empty string."""
        return ModelValidationHelper.validate_string_field(v, "name")

    @field_validator("network")
    @classmethod
    def validate_network(cls, v: str) -> str:
        """Validate network is non-empty string."""
        return ModelValidationHelper.validate_string_field(v, "network")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate symbol is non-empty string."""
        return ModelValidationHelper.validate_string_field(v, "symbol")

    @field_validator("avatar")
    @classmethod
    def validate_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate avatar URL format if provided."""
        return ModelValidationHelper.validate_optional_url(v, "avatar")

    @field_validator("cover")
    @classmethod
    def validate_cover_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate cover URL format if provided."""
        return ModelValidationHelper.validate_optional_url(v, "cover")

    @field_validator("website")
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format if provided."""
        return ModelValidationHelper.validate_optional_url(v, "website")

    @field_validator("private", mode="before")
    @classmethod
    def validate_private_type(cls, v) -> bool:
        """Validate private field is boolean type."""
        return ModelValidationHelper.validate_boolean_field(v, "private")

    @field_validator("verified", mode="before")
    @classmethod
    def validate_verified_type(cls, v) -> bool:
        """Validate verified field is boolean type."""
        return ModelValidationHelper.validate_boolean_field(v, "verified")

    @field_validator("created", mode="before")
    @classmethod
    def validate_created_type(cls, v) -> int:
        """Validate created field is integer type."""
        return ModelValidationHelper.validate_non_negative_integer(v, "created")

    @field_validator("proposalsCount", mode="before")
    @classmethod
    def validate_proposals_count_type(cls, v) -> int:
        """Validate proposalsCount field is integer type."""
        return ModelValidationHelper.validate_non_negative_integer(v, "proposalsCount")

    @field_validator("followersCount", mode="before")
    @classmethod
    def validate_followers_count_type(cls, v) -> int:
        """Validate followersCount field is integer type."""
        return ModelValidationHelper.validate_non_negative_integer(v, "followersCount")

    @field_validator("votesCount", mode="before")
    @classmethod
    def validate_votes_count_type(cls, v) -> int:
        """Validate votesCount field is integer type."""
        return ModelValidationHelper.validate_non_negative_integer(v, "votesCount")


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


class AgentRunStatus(BaseModel):
    """Response model for agent run status endpoint."""

    current_state: str = Field(
        description="Current state of the agent (e.g., IDLE, FETCHING_PROPOSALS)"
    )
    last_run_timestamp: Optional[str] = Field(
        None, description="ISO timestamp of the last completed agent run"
    )
    is_active: bool = Field(description="Whether the agent is currently running")
    current_space_id: Optional[str] = Field(
        None, description="Space ID of the current or last run"
    )


class AgentDecisionResponse(BaseModel):
    """Response model for an individual agent decision with enriched data."""

    proposal_id: str = Field(..., description="The proposal ID that was voted on")
    vote: VoteType = Field(
        ..., description="The vote decision: FOR, AGAINST, or ABSTAIN"
    )
    confidence: float = Field(
        ..., description="Confidence score in the decision (0.0 to 1.0)"
    )
    reasoning: str = Field(..., description="AI-generated explanation for the vote")
    strategy_used: VotingStrategy = Field(..., description="The voting strategy used")
    timestamp: str = Field(..., description="ISO timestamp when the decision was made")
    proposal_title: str = Field(..., description="Title of the proposal from Snapshot")


class AgentDecisionsResponse(BaseModel):
    """Response model for the agent decisions endpoint."""

    decisions: List[AgentDecisionResponse] = Field(
        ..., description="List of recent voting decisions with enriched data"
    )


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


class Vote(BaseModel):
    """Snapshot vote model representing a vote on a proposal."""

    id: str = Field(..., description="Unique vote identifier")
    voter: str = Field(..., description="Voter's blockchain address")
    choice: int = Field(..., description="Vote choice")
    created: int = Field(..., ge=0, description="Creation timestamp")
    vp: float = Field(..., ge=0, description="Total voting power")
    vp_by_strategy: List[float] = Field(
        default_factory=list, description="Voting power by strategy"
    )
    reason: Optional[str] = Field(None, description="Vote reason/comment")
    ipfs: Optional[str] = Field(None, description="IPFS hash")
    vp_state: Optional[str] = Field(None, description="Voting power state")
    space: Optional[Dict[str, Any]] = Field(None, description="Space metadata")
    proposal: Optional[Dict[str, Any]] = Field(None, description="Proposal metadata")
    app: Optional[str] = Field(None, description="App used to vote")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate vote ID is non-empty string."""
        return ModelValidationHelper.validate_string_field(v, "id")

    @field_validator("voter")
    @classmethod
    def validate_voter(cls, v: str) -> str:
        """Validate voter address format."""
        return ModelValidationHelper.validate_blockchain_address(v)


class InvestedPosition(BaseModel):
    """Represents an invested position in a DeFi protocol."""

    protocol: str = Field(..., description="DeFi protocol name (e.g., Aave, Compound)")
    asset: str = Field(..., description="Asset symbol or identifier")
    amount: Decimal = Field(..., description="Amount invested")
    chain_id: int = Field(..., description="Blockchain chain ID")
    position_id: str = Field(..., description="Unique position identifier")
    timestamp: str = Field(..., description="Position creation timestamp")
    contract_address: Optional[str] = Field(
        None, description="Protocol contract address"
    )

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        """Validate protocol is non-empty string."""
        return ModelValidationHelper.validate_string_field(v, "protocol")

    @field_validator("asset")
    @classmethod
    def validate_asset(cls, v: str) -> str:
        """Validate asset is non-empty string."""
        return ModelValidationHelper.validate_string_field(v, "asset")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate amount is positive."""
        if v <= 0:
            raise ValueError(f"Amount must be positive, got {v}")
        return v

    @field_validator("chain_id")
    @classmethod
    def validate_chain_id(cls, v: int) -> int:
        """Validate chain_id is valid."""
        valid_chains = [
            1,
            10,
            100,
            8453,
            34443,
        ]  # Ethereum, Optimism, Gnosis, Base, Mode
        if v not in valid_chains:
            raise ValueError(f"Invalid chain_id: {v}")
        return v


class WithdrawalTransaction(BaseModel):
    """Represents a withdrawal transaction."""

    transaction_hash: str = Field(..., description="Blockchain transaction hash")
    safe_tx_hash: Optional[str] = Field(None, description="Safe transaction hash")
    status: WithdrawalStatus = Field(..., description="Transaction status")
    position_id: str = Field(..., description="Related position ID")
    amount: Decimal = Field(..., description="Withdrawal amount")
    chain_id: int = Field(..., description="Blockchain chain ID")
    timestamp: Optional[str] = Field(None, description="Transaction timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    @field_validator("transaction_hash")
    @classmethod
    def validate_transaction_hash(cls, v: str) -> str:
        """Validate transaction hash format."""
        if not v.startswith("0x"):
            raise ValueError("Transaction hash must start with 0x")
        if len(v) != 66:  # 0x + 64 hex chars
            raise ValueError("Transaction hash must be 66 characters")
        return v


class EASAttestationData(BaseModel):
    """Data model for EAS (Ethereum Attestation Service) attestations."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    # Required fields for attestation
    proposal_id: str = Field(..., description="Snapshot proposal ID being attested")
    space_id: str = Field(..., description="Snapshot space ID")
    voter_address: str = Field(..., description="Address of the voter")
    choice: int = Field(..., description="Vote choice value")
    vote_tx_hash: str = Field(..., description="Transaction hash of the Snapshot vote")
    timestamp: datetime = Field(..., description="Timestamp of the attestation")
    retry_count: int = Field(
        default=0, ge=0, le=3, description="Number of retry attempts"
    )

    # Optional fields for attestation results
    attestation_tx_hash: Optional[str] = Field(
        None, description="On-chain attestation transaction hash"
    )
    attestation_uid: Optional[str] = Field(
        None, description="EAS attestation unique identifier"
    )
    attestation_status: Optional[str] = Field(
        None, description="Status: pending, success, failed"
    )
    attestation_error: Optional[str] = Field(
        None, description="Error message if attestation failed"
    )

    @field_validator("voter_address")
    @classmethod
    def validate_voter_address(cls, v: str) -> str:
        """Validate Ethereum address format."""
        return ModelValidationHelper.validate_blockchain_address(v)

    @field_validator("vote_tx_hash", "attestation_tx_hash")
    @classmethod
    def validate_tx_hash(cls, v: Optional[str]) -> Optional[str]:
        """Validate transaction hash format."""
        if v is None:
            return v
        if not v.startswith("0x"):
            raise ValueError("Transaction hash must start with 0x")
        if len(v) != 66:  # 0x + 64 hex chars
            raise ValueError("Transaction hash must be 66 characters")
        return v

    @field_validator("attestation_status")
    @classmethod
    def validate_attestation_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate attestation status."""
        if v is None:
            return v
        valid_statuses = {"pending", "success", "failed"}
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid attestation status: {v}. Must be one of {valid_statuses}"
            )
        return v


class AgentRunStatistics(BaseModel):
    """Aggregated statistics about agent runs across all spaces."""

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    total_runs: int = Field(
        ..., ge=0, description="Total number of agent runs across all spaces"
    )
    total_proposals_evaluated: int = Field(
        ..., ge=0, description="Total number of proposals evaluated"
    )
    total_votes_cast: int = Field(..., ge=0, description="Total number of votes cast")
    average_confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Average confidence score across all votes"
    )
    success_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Percentage of runs completed without errors (0.0 to 1.0)",
    )
    average_runtime_seconds: float = Field(
        ..., ge=0.0, description="Average runtime per run in seconds"
    )


class StrategicBriefing(BaseModel):
    """Strategic briefing for agent decision making.

    Provides contextual information including user preferences, voting history
    analysis, and strategic recommendations to enhance AI decision-making.
    """

    model_config = {"str_strip_whitespace": True, "validate_assignment": True}

    summary: str = Field(
        ..., description="Comprehensive summary of the strategic context"
    )
    key_insights: List[str] = Field(
        ..., description="List of key insights from analysis"
    )
    historical_patterns: Dict[str, Any] = Field(
        ..., description="Analyzed patterns from voting history"
    )
    recommendations: List[str] = Field(
        ..., description="Strategic recommendations for voting decisions"
    )

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        """Validate summary is meaningful text."""
        return ModelValidationHelper.validate_meaningful_text(
            v, min_length=20, field_name="summary"
        )

    @field_validator("key_insights")
    @classmethod
    def validate_key_insights(cls, v: List[str]) -> List[str]:
        """Validate key insights list."""
        if not isinstance(v, list):
            raise ValueError("Key insights must be a list")
        if len(v) == 0:
            raise ValueError("Key insights cannot be empty")

        validated_insights = []
        for i, insight in enumerate(v):
            if not isinstance(insight, str):
                raise ValueError(
                    f"Key insight at index {i} must be string, got {type(insight)}"
                )
            cleaned = insight.strip()
            if len(cleaned) < MIN_MEANINGFUL_TEXT_LENGTH:
                raise ValueError(
                    f"Key insight at index {i} must be at least {MIN_MEANINGFUL_TEXT_LENGTH} characters"
                )
            validated_insights.append(cleaned)

        return validated_insights

    @field_validator("recommendations")
    @classmethod
    def validate_recommendations(cls, v: List[str]) -> List[str]:
        """Validate recommendations list."""
        if not isinstance(v, list):
            raise ValueError("Recommendations must be a list")
        if len(v) == 0:
            raise ValueError("Recommendations cannot be empty")

        validated_recommendations = []
        for i, recommendation in enumerate(v):
            if not isinstance(recommendation, str):
                raise ValueError(
                    f"Recommendation at index {i} must be string, got {type(recommendation)}"
                )
            cleaned = recommendation.strip()
            if len(cleaned) < MIN_MEANINGFUL_TEXT_LENGTH:
                raise ValueError(
                    f"Recommendation at index {i} must be at least {MIN_MEANINGFUL_TEXT_LENGTH} characters"
                )
            validated_recommendations.append(cleaned)

        return validated_recommendations

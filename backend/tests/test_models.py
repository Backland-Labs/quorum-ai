"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from typing import List
from pydantic import ValidationError

from models import (
    Proposal,
    ProposalSummary,
    ProposalFilters,
    ProposalListResponse,
    SummarizeRequest,
    SummarizeResponse,
    ProposalState,
    VoteType,
    Vote,
    SortCriteria,
    SortOrder,
    ProposalVoter,
    ProposalTopVoters,
    VoteDecision,
    RiskLevel,
    ModelValidationHelper,
    VotingStrategy,
)

# Test constants
TEST_GAS_COSTS = [0.001, 0.005, 0.01, 0.1]

# Test helper functions
def create_test_data_with_boundary_values(base_data: dict, field_name: str, 
                                        invalid_low: float, invalid_high: float,
                                        valid_low: float, valid_high: float) -> None:
    """Helper function to test boundary validation for numeric fields."""
    # Test invalid values
    test_data = base_data.copy()
    test_data[field_name] = invalid_high
    with pytest.raises(ValidationError):
        yield test_data, "high"
    
    test_data[field_name] = invalid_low
    with pytest.raises(ValidationError):
        yield test_data, "low"
    
    # Test valid boundary values
    test_data[field_name] = valid_low
    yield test_data, "valid_low"
    
    test_data[field_name] = valid_high
    yield test_data, "valid_high"

def assert_non_negative_field_validation(model_class, base_data: dict, field_name: str) -> None:
    """Helper function to validate non-negative numeric fields."""
    # Test negative value
    test_data = base_data.copy()
    test_data[field_name] = -1
    with pytest.raises(ValidationError):
        model_class(**test_data)
    
    # Test valid boundary values
    test_data[field_name] = 0
    instance = model_class(**test_data)
    assert getattr(instance, field_name) == 0


class TestProposalState:
    """Test cases for ProposalState enum."""

    def test_proposal_state_values_are_valid(self) -> None:
        """Test that all proposal state values are correctly defined."""
        expected_states = {
            "pending",
            "active", 
            "closed",
        }
        actual_states = {state.value for state in ProposalState}
        assert actual_states == expected_states

    def test_proposal_state_can_be_created_from_string(self) -> None:
        """Test that ProposalState can be created from string values."""
        state = ProposalState("active")
        assert state == ProposalState.ACTIVE


class TestVoteType:
    """Test cases for VoteType enum."""

    def test_vote_type_values_are_valid(self) -> None:
        """Test that all vote type values are correctly defined."""
        expected_types = {"FOR", "AGAINST", "ABSTAIN"}
        actual_types = {vote_type.value for vote_type in VoteType}
        assert actual_types == expected_types

    def test_vote_type_can_be_created_from_string(self) -> None:
        """Test that VoteType can be created from string values."""
        vote_type = VoteType("FOR")
        assert vote_type == VoteType.FOR


class TestVote:
    """Test cases for Vote model."""

    def test_vote_creation_with_all_fields(self) -> None:
        """Test successful Vote creation with all fields."""
        vote = Vote(
            id="vote-123",
            voter="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            choice=1,
            created=1698768000,
            vp=1000.0,
            vp_by_strategy=[1000.0],
            reason="Good proposal"
        )
        assert vote.id == "vote-123"
        assert vote.voter == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        assert vote.choice == 1
        assert vote.created == 1698768000
        assert vote.vp == 1000.0
        assert vote.vp_by_strategy == [1000.0]
        assert vote.reason == "Good proposal"

    def test_vote_creation_without_reason(self) -> None:
        """Test Vote creation without optional reason field."""
        vote = Vote(
            id="vote-456",
            voter="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            choice=2,
            created=1698768000,
            vp=500.0,
            vp_by_strategy=[500.0]
        )
        assert vote.reason is None

    def test_vote_creation_with_invalid_support_type(self) -> None:
        """Test that Vote creation fails with invalid choice type."""
        with pytest.raises(ValidationError):
            Vote(
                id="vote-invalid",
                voter="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
                choice=True,  # Boolean is not a valid choice type
                created=1698768000,
                vp=500.0,
                vp_by_strategy=[500.0]
            )  # type: ignore


class TestProposal:
    """Test cases for Proposal model."""

    def _create_valid_proposal_data(self) -> dict:
        """Create valid proposal data for testing (Snapshot structure)."""
        return {
            "id": "prop-123",
            "title": "Test Proposal",
            "choices": ["For", "Against"],
            "start": 1698768000,
            "end": 1699372800,
            "state": "active",
            "author": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "network": "1",
            "symbol": "TEST",
            "scores": [1000.0, 500.0],
            "scores_total": 1500.0,
            "votes": 25,
            "created": 1698681600,
            "quorum": 100.0,
        }

    def test_proposal_creation_with_required_fields(self) -> None:
        """Test Proposal creation with required fields."""
        proposal_data = self._create_valid_proposal_data()
        proposal = Proposal(**proposal_data)

        assert proposal.id == "prop-123"
        assert proposal.title == "Test Proposal"
        assert proposal.state == "active"
        assert proposal.choices == ["For", "Against"]
        assert proposal.scores == [1000.0, 500.0]
        assert proposal.scores_total == 1500.0
        assert proposal.votes == 25
        assert proposal.author == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"

    def test_proposal_creation_with_vote_counts(self) -> None:
        """Test Proposal creation with vote counts."""
        proposal_data = self._create_valid_proposal_data()
        proposal_data.update({
            "scores": [1000.0, 500.0, 100.0],
            "choices": ["For", "Against", "Abstain"],
            "votes": 50,
            "scores_total": 1600.0
        })

        proposal = Proposal(**proposal_data)
        assert proposal.scores == [1000.0, 500.0, 100.0]
        assert proposal.choices == ["For", "Against", "Abstain"]
        assert proposal.votes == 50
        assert proposal.scores_total == 1600.0

    def test_proposal_creation_with_url(self) -> None:
        """Test Proposal creation with discussion URL."""
        proposal_data = self._create_valid_proposal_data()
        proposal_data["discussion"] = "https://forum.example.com/proposal/123"

        proposal = Proposal(**proposal_data)
        assert proposal.discussion == "https://forum.example.com/proposal/123"


class TestProposalSummary:
    """Test cases for ProposalSummary model."""

    def _create_valid_summary_data(self) -> dict:
        """Create valid proposal summary data for testing."""
        return {
            "proposal_id": "prop-123",
            "title": "Test Proposal",
            "summary": "This is a summary",
            "key_points": ["Point 1", "Point 2"],
            "risk_level": "LOW",
            "recommendation": "Approve",
            "confidence_score": 0.85,
        }

    def test_proposal_summary_creation_with_valid_data(self) -> None:
        """Test ProposalSummary creation with valid data."""
        summary_data = self._create_valid_summary_data()
        summary = ProposalSummary(**summary_data)

        assert summary.proposal_id == "prop-123"
        assert summary.title == "Test Proposal"
        assert summary.summary == "This is a summary"
        assert summary.key_points == ["Point 1", "Point 2"]
        assert summary.risk_level == "LOW"
        assert summary.recommendation == "Approve"
        assert summary.confidence_score == 0.85

    def test_proposal_summary_confidence_score_validation(self) -> None:
        """Test that confidence score is validated to be between 0 and 1."""
        summary_data = self._create_valid_summary_data()

        # Test invalid confidence score > 1
        summary_data["confidence_score"] = 1.5
        with pytest.raises(ValidationError):
            ProposalSummary(**summary_data)

        # Test invalid confidence score < 0
        summary_data["confidence_score"] = -0.1
        with pytest.raises(ValidationError):
            ProposalSummary(**summary_data)

        # Test valid boundary values
        summary_data["confidence_score"] = 0.0
        summary = ProposalSummary(**summary_data)
        assert summary.confidence_score == 0.0

        summary_data["confidence_score"] = 1.0
        summary = ProposalSummary(**summary_data)
        assert summary.confidence_score == 1.0


class TestProposalFilters:
    """Test cases for ProposalFilters model."""

    def test_proposal_filters_with_defaults(self) -> None:
        """Test ProposalFilters creation with default values."""
        filters = ProposalFilters()

        assert filters.state is None
        assert filters.dao_id is None
        assert filters.limit == 20
        assert filters.after_cursor is None
        assert filters.sort_by == SortCriteria.CREATED_DATE
        assert filters.sort_order == SortOrder.DESC

    def test_proposal_filters_with_custom_values(self) -> None:
        """Test ProposalFilters creation with custom values."""
        filters = ProposalFilters(
            state=ProposalState.ACTIVE,
            dao_id="dao-123",
            limit=50,
            after_cursor="cursor_10",
            sort_by=SortCriteria.VOTE_COUNT,
            sort_order=SortOrder.ASC,
        )

        assert filters.state == ProposalState.ACTIVE
        assert filters.dao_id == "dao-123"
        assert filters.limit == 50
        assert filters.after_cursor == "cursor_10"
        assert filters.sort_by == SortCriteria.VOTE_COUNT
        assert filters.sort_order == SortOrder.ASC

    def test_proposal_filters_limit_validation(self) -> None:
        """Test that limit is validated to be within valid range."""
        # Test limit too low
        with pytest.raises(ValidationError):
            ProposalFilters(limit=0)

        # Test limit too high
        with pytest.raises(ValidationError):
            ProposalFilters(limit=101)

        # Test valid boundaries
        filters_min = ProposalFilters(limit=1)
        assert filters_min.limit == 1

        filters_max = ProposalFilters(limit=100)
        assert filters_max.limit == 100

    def test_proposal_filters_cursor_validation(self) -> None:
        """Test that after_cursor can be set to any string value."""
        filters = ProposalFilters(after_cursor="test_cursor")
        assert filters.after_cursor == "test_cursor"


class TestSummarizeRequest:
    """Test cases for SummarizeRequest model."""

    def test_summarize_request_with_valid_data(self) -> None:
        """Test SummarizeRequest creation with valid data."""
        request = SummarizeRequest(
            proposal_ids=["prop-1", "prop-2"],
            include_risk_assessment=True,
            include_recommendations=False,
        )

        assert request.proposal_ids == ["prop-1", "prop-2"]
        assert request.include_risk_assessment is True
        assert request.include_recommendations is False

    def test_summarize_request_with_defaults(self) -> None:
        """Test SummarizeRequest creation with default values."""
        request = SummarizeRequest(proposal_ids=["prop-1"])

        assert request.include_risk_assessment is True
        assert request.include_recommendations is True

    def test_summarize_request_proposal_ids_validation(self) -> None:
        """Test that proposal_ids list is validated for min/max items."""
        # Test empty list
        with pytest.raises(ValidationError):
            SummarizeRequest(proposal_ids=[])

        # Test too many items
        too_many_ids = [f"prop-{i}" for i in range(51)]
        with pytest.raises(ValidationError):
            SummarizeRequest(proposal_ids=too_many_ids)

        # Test valid boundaries
        min_request = SummarizeRequest(proposal_ids=["prop-1"])
        assert len(min_request.proposal_ids) == 1

        max_ids = [f"prop-{i}" for i in range(50)]
        max_request = SummarizeRequest(proposal_ids=max_ids)
        assert len(max_request.proposal_ids) == 50


class TestProposalListResponse:
    """Test cases for ProposalListResponse model."""

    def test_proposal_list_response_creation(self) -> None:
        """Test ProposalListResponse creation."""
        proposals = [
            Proposal(
                id="prop-1",
                title="Test 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=50.0,
            )
        ]

        response = ProposalListResponse(proposals=proposals, next_cursor="cursor_123")

        assert len(response.proposals) == 1
        assert response.next_cursor == "cursor_123"


class TestSummarizeResponse:
    """Test cases for SummarizeResponse model."""

    def test_summarize_response_creation(self) -> None:
        """Test SummarizeResponse creation."""
        summaries = [
            ProposalSummary(
                proposal_id="prop-1",
                title="Test",
                summary="Summary",
                key_points=["Point 1"],
                risk_level="LOW",
                recommendation="Approve",
                confidence_score=0.9,
            )
        ]

        response = SummarizeResponse(
            summaries=summaries, processing_time=1.5, model_used="gpt-4o-mini"
        )

        assert len(response.summaries) == 1
        assert response.processing_time == 1.5
        assert response.model_used == "gpt-4o-mini"


class TestProposalVoter:
    """Test cases for ProposalVoter model."""

    def test_proposal_voter_creation_with_valid_data(self) -> None:
        """Test ProposalVoter creation with valid data."""
        voter = ProposalVoter(
            address="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            amount="1000000000000000000",
            vote_type=VoteType.FOR,
        )

        assert voter.address == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        assert voter.amount == "1000000000000000000"
        assert voter.vote_type == VoteType.FOR

    def test_proposal_voter_creation_with_against_vote(self) -> None:
        """Test ProposalVoter creation with AGAINST vote."""
        voter = ProposalVoter(
            address="0x123abc456def789012345678901234567890abcd", amount="500000000000000000", vote_type=VoteType.AGAINST
        )

        assert voter.vote_type == VoteType.AGAINST

    def test_proposal_voter_creation_with_abstain_vote(self) -> None:
        """Test ProposalVoter creation with ABSTAIN vote."""
        voter = ProposalVoter(
            address="0xdef456789abc012345678901234567890abcdef", amount="250000000000000000", vote_type=VoteType.ABSTAIN
        )

        assert voter.vote_type == VoteType.ABSTAIN

    def test_proposal_voter_creation_with_invalid_vote_type_fails(self) -> None:
        """Test ProposalVoter creation fails with invalid vote type."""
        with pytest.raises(ValidationError):
            ProposalVoter(
                address="0x123abc456def789012345678901234567890abcd",
                amount="1000000000000000000",
                vote_type="INVALID",  # type: ignore
            )

    def test_proposal_voter_creation_with_missing_fields_fails(self) -> None:
        """Test ProposalVoter creation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            ProposalVoter(address="0x123abc456def789012345678901234567890abcd")  # type: ignore


class TestProposalTopVoters:
    """Test cases for ProposalTopVoters model."""

    def _create_sample_voters(self) -> List[ProposalVoter]:
        """Create sample voters for testing."""
        return [
            ProposalVoter(
                address="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
                amount="1000000000000000000",
                vote_type=VoteType.FOR,
            ),
            ProposalVoter(
                address="0x123abc456def789012345678901234567890abcd",
                amount="500000000000000000",
                vote_type=VoteType.AGAINST,
            ),
        ]

    def test_proposal_top_voters_creation_with_valid_data(self) -> None:
        """Test ProposalTopVoters creation with valid data."""
        voters = self._create_sample_voters()
        top_voters = ProposalTopVoters(proposal_id="proposal-123", voters=voters)

        assert top_voters.proposal_id == "proposal-123"
        assert len(top_voters.voters) == 2
        assert (
            top_voters.voters[0].address == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        )
        assert top_voters.voters[1].vote_type == VoteType.AGAINST

    def test_proposal_top_voters_creation_with_empty_voters_list(self) -> None:
        """Test ProposalTopVoters creation with empty voters list."""
        top_voters = ProposalTopVoters(proposal_id="proposal-456", voters=[])

        assert top_voters.proposal_id == "proposal-456"
        assert len(top_voters.voters) == 0

    def test_proposal_top_voters_creation_with_missing_fields_fails(self) -> None:
        """Test ProposalTopVoters creation fails when required fields are missing."""
        voters = self._create_sample_voters()

        with pytest.raises(ValidationError):
            ProposalTopVoters(voters=voters)  # type: ignore

    def test_proposal_voter_with_very_large_amount(self) -> None:
        """Test ProposalVoter can handle very large voting amounts."""
        large_amount = "999999999999999999999999999999999999"
        voter = ProposalVoter(
            address="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            amount=large_amount,
            vote_type=VoteType.FOR,
        )

        assert voter.amount == large_amount

    def test_proposal_voter_with_zero_amount(self) -> None:
        """Test ProposalVoter can handle zero voting amount."""
        voter = ProposalVoter(
            address="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            amount="0",
            vote_type=VoteType.ABSTAIN,
        )

        assert voter.amount == "0"

    def test_proposal_voter_with_empty_address_fails(self) -> None:
        """Test ProposalVoter creation fails with empty address."""
        with pytest.raises(ValidationError):
            ProposalVoter(
                address="", amount="1000000000000000000", vote_type=VoteType.FOR
            )

    def test_proposal_top_voters_with_single_voter(self) -> None:
        """Test ProposalTopVoters with a single voter."""
        voter = ProposalVoter(
            address="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            amount="1000000000000000000",
            vote_type=VoteType.FOR,
        )

        top_voters = ProposalTopVoters(proposal_id="proposal-789", voters=[voter])

        assert len(top_voters.voters) == 1
        assert top_voters.voters[0] == voter


class TestVoteDecision:
    """Test cases for VoteDecision model."""

    def _create_valid_vote_decision_data(self) -> dict:
        """Create valid vote decision data for testing."""
        return {
            "proposal_id": "prop-123",
            "vote": VoteType.FOR,
            "confidence": 0.85,
            "reasoning": "The proposal aligns with our governance strategy",
            "strategy_used": VotingStrategy.BALANCED,
        }

    def test_vote_decision_creation_with_required_fields(self) -> None:
        """Test VoteDecision creation with required fields."""
        decision_data = self._create_valid_vote_decision_data()
        decision = VoteDecision(**decision_data)

        assert decision.proposal_id == "prop-123"
        assert decision.vote == VoteType.FOR
        assert decision.confidence == 0.85
        assert decision.reasoning == "The proposal aligns with our governance strategy"
        assert decision.risk_assessment == RiskLevel.MEDIUM  # default value
        assert decision.estimated_gas_cost == 0.005  # default value

    def test_vote_decision_creation_with_all_fields(self) -> None:
        """Test VoteDecision creation with all fields."""
        decision_data = self._create_valid_vote_decision_data()
        decision_data.update({
            "risk_assessment": RiskLevel.HIGH,
            "estimated_gas_cost": 0.012,
        })

        decision = VoteDecision(**decision_data)
        assert decision.risk_assessment == RiskLevel.HIGH
        assert decision.estimated_gas_cost == 0.012

    def test_vote_decision_with_against_vote(self) -> None:
        """Test VoteDecision creation with AGAINST vote."""
        decision_data = self._create_valid_vote_decision_data()
        decision_data["vote"] = VoteType.AGAINST
        decision_data["reasoning"] = "The proposal has significant risks"

        decision = VoteDecision(**decision_data)
        assert decision.vote == VoteType.AGAINST
        assert decision.reasoning == "The proposal has significant risks"

    def test_vote_decision_with_abstain_vote(self) -> None:
        """Test VoteDecision creation with ABSTAIN vote."""
        decision_data = self._create_valid_vote_decision_data()
        decision_data["vote"] = VoteType.ABSTAIN
        decision_data["reasoning"] = "Insufficient information to make a decision"

        decision = VoteDecision(**decision_data)
        assert decision.vote == VoteType.ABSTAIN

    def test_vote_decision_confidence_validation(self) -> None:
        """Test that confidence is validated to be between 0 and 1."""
        decision_data = self._create_valid_vote_decision_data()

        # Test invalid confidence > 1
        decision_data["confidence"] = 1.5
        with pytest.raises(ValidationError):
            VoteDecision(**decision_data)

        # Test invalid confidence < 0
        decision_data["confidence"] = -0.1
        with pytest.raises(ValidationError):
            VoteDecision(**decision_data)

        # Test valid boundary values
        decision_data["confidence"] = 0.0
        decision = VoteDecision(**decision_data)
        assert decision.confidence == 0.0

        decision_data["confidence"] = 1.0
        decision = VoteDecision(**decision_data)
        assert decision.confidence == 1.0

    def test_vote_decision_confidence_rounding(self) -> None:
        """Test that confidence is rounded to 3 decimal places."""
        decision_data = self._create_valid_vote_decision_data()
        decision_data["confidence"] = 0.123456789

        decision = VoteDecision(**decision_data)
        assert decision.confidence == 0.123

    def test_vote_decision_creation_with_invalid_vote_type_fails(self) -> None:
        """Test VoteDecision creation fails with invalid vote type."""
        decision_data = self._create_valid_vote_decision_data()
        decision_data["vote"] = "INVALID"

        with pytest.raises(ValidationError):
            VoteDecision(**decision_data)

    def test_vote_decision_creation_fails_with_missing_required_fields(self) -> None:
        """Test that VoteDecision creation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            VoteDecision(proposal_id="prop-123")  # Missing other required fields

    def test_vote_decision_with_different_risk_assessments(self) -> None:
        """Test VoteDecision with different risk assessment values."""
        decision_data = self._create_valid_vote_decision_data()
        
        for risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]:
            decision_data["risk_assessment"] = risk_level
            decision = VoteDecision(**decision_data)
            assert decision.risk_assessment == risk_level

    def test_vote_decision_with_various_gas_costs(self) -> None:
        """Test VoteDecision with various gas cost values."""
        decision_data = self._create_valid_vote_decision_data()
        
        # Test different gas costs
        for gas_cost in TEST_GAS_COSTS:
            decision_data["estimated_gas_cost"] = gas_cost
            decision = VoteDecision(**decision_data)
            assert decision.estimated_gas_cost == gas_cost

    def test_vote_decision_proposal_id_validation_with_assertions(self) -> None:
        """Test VoteDecision proposal_id validation with runtime assertions."""
        decision_data = self._create_valid_vote_decision_data()
        
        # Test empty proposal_id
        decision_data["proposal_id"] = ""
        with pytest.raises(ValidationError, match="Proposal ID cannot be empty"):
            VoteDecision(**decision_data)
        
        # Test whitespace-only proposal_id
        decision_data["proposal_id"] = "   "
        with pytest.raises(ValidationError, match="Proposal ID cannot be empty"):
            VoteDecision(**decision_data)
        
        # Test too short proposal_id
        decision_data["proposal_id"] = "ab"
        with pytest.raises(ValidationError, match="Proposal ID too short"):
            VoteDecision(**decision_data)

    def test_vote_decision_reasoning_validation_with_assertions(self) -> None:
        """Test VoteDecision reasoning validation with runtime assertions."""
        decision_data = self._create_valid_vote_decision_data()
        
        # Test empty reasoning
        decision_data["reasoning"] = ""
        with pytest.raises(ValidationError, match="reasoning cannot be empty"):
            VoteDecision(**decision_data)
        
        # Test too short reasoning
        decision_data["reasoning"] = "short"
        with pytest.raises(ValidationError, match="reasoning too short"):
            VoteDecision(**decision_data)

    def test_vote_decision_gas_cost_validation_with_assertions(self) -> None:
        """Test VoteDecision gas cost validation with runtime assertions."""
        decision_data = self._create_valid_vote_decision_data()
        
        # Test negative gas cost
        decision_data["estimated_gas_cost"] = -0.1
        with pytest.raises(ValidationError, match="Gas cost cannot be negative"):
            VoteDecision(**decision_data)
        
        # Test unreasonably high gas cost
        decision_data["estimated_gas_cost"] = 1001.0
        with pytest.raises(ValidationError, match="Gas cost seems unreasonably high"):
            VoteDecision(**decision_data)


class TestModelValidationHelper:
    """Test cases for ModelValidationHelper utility class."""

    def test_validate_staking_consistency_with_consistent_data(self) -> None:
        """Test staking consistency validation with consistent data."""
        # Test consistent staking state
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=1000.0, rewards_earned=50.0
        )
        assert len(warnings) == 0

        # Test consistent non-staking state
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=False, stake_amount=0.0, rewards_earned=0.0
        )
        assert len(warnings) == 0

    def test_validate_staking_consistency_with_inconsistent_staking(self) -> None:
        """Test staking consistency validation with inconsistent staking state."""
        # Test inconsistent state: marked as staked but no stake amount
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=0.0, rewards_earned=0.0
        )
        assert len(warnings) == 1
        assert "marked as staked but has zero" in warnings[0]

    def test_validate_staking_consistency_with_negative_rewards(self) -> None:
        """Test staking consistency validation with negative rewards."""
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=False, stake_amount=0.0, rewards_earned=-10.0
        )
        assert len(warnings) == 1
        assert "Negative staking rewards" in warnings[0]

    def test_validate_staking_consistency_with_multiple_issues(self) -> None:
        """Test staking consistency validation with multiple issues."""
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=0.0, rewards_earned=-5.0
        )
        assert len(warnings) == 2

    def test_validate_staking_consistency_type_assertions_still_work(self) -> None:
        """Test that type assertions still work in staking consistency validation."""
        # Type errors should still be assertion errors, not warnings
        with pytest.raises(AssertionError, match="is_staked must be bool"):
            ModelValidationHelper.validate_staking_consistency(
                is_staked="true",  # type: ignore
                stake_amount=100.0,
                rewards_earned=10.0
            )

        with pytest.raises(AssertionError, match="stake_amount must be numeric"):
            ModelValidationHelper.validate_staking_consistency(
                is_staked=True,
                stake_amount="100",  # type: ignore
                rewards_earned=10.0
            )

    def test_validate_blockchain_address_with_valid_addresses(self) -> None:
        """Test blockchain address validation with valid addresses."""
        valid_addresses = [
            "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "0x123abc456def789012345678901234567890abcd",
            "some_long_enough_address_format",
        ]
        
        for address in valid_addresses:
            result = ModelValidationHelper.validate_blockchain_address(address)
            assert result == address

    def test_validate_blockchain_address_with_invalid_addresses(self) -> None:
        """Test blockchain address validation with invalid addresses."""
        invalid_addresses = [
            "",  # empty
            "   ",  # whitespace only
            "short",  # too short
        ]
        
        for address in invalid_addresses:
            with pytest.raises(AssertionError):
                ModelValidationHelper.validate_blockchain_address(address)
                
        # Test that addresses with leading/trailing spaces are correctly cleaned
        leading_space = " 0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        result = ModelValidationHelper.validate_blockchain_address(leading_space)
        assert result == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        
        trailing_space = "0x742d35cc6835c0532021efc598c51ddc1d8b4b21 "
        result = ModelValidationHelper.validate_blockchain_address(trailing_space)
        assert result == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"

    def test_validate_positive_amount_with_valid_amounts(self) -> None:
        """Test positive amount validation with valid amounts."""
        valid_amounts = ["0", "1", "100.5", "999999999999999999999"]
        
        for amount in valid_amounts:
            result = ModelValidationHelper.validate_positive_amount(amount)
            assert result == amount

    def test_validate_positive_amount_with_invalid_amounts(self) -> None:
        """Test positive amount validation with invalid amounts."""
        invalid_amounts = [
            "",  # empty
            "   ",  # whitespace only
            "-1",  # negative
            "abc",  # non-numeric
            "inf",  # infinite
        ]
        
        for amount in invalid_amounts:
            with pytest.raises((AssertionError, ValueError)):
                ModelValidationHelper.validate_positive_amount(amount)

    def test_validate_meaningful_text_with_valid_text(self) -> None:
        """Test meaningful text validation with valid text."""
        valid_texts = ["This is meaningful text", "Short but ok"]
        
        for text in valid_texts:
            result = ModelValidationHelper.validate_meaningful_text(text)
            assert result == text

    def test_validate_meaningful_text_with_invalid_text(self) -> None:
        """Test meaningful text validation with invalid text."""
        invalid_texts = [
            "",  # empty
            "   ",  # whitespace only
            "short",  # too short (< 10 chars by default)
            "1234567890",  # only digits
            "                    ",  # mostly spaces
        ]
        
        for text in invalid_texts:
            with pytest.raises(AssertionError):
                ModelValidationHelper.validate_meaningful_text(text)

    def test_validate_staking_consistency_with_valid_states(self) -> None:
        """Test staking consistency validation with various valid states."""
        valid_states = [
            (True, 100.0, 10.0),  # Staked with positive amounts
            (False, 0.0, 0.0),    # Not staked with zero amounts
            (True, 500.0, 0.0),   # Staked but no rewards yet
        ]
        
        for is_staked, stake_amount, rewards_earned in valid_states:
            warnings = ModelValidationHelper.validate_staking_consistency(
                is_staked, stake_amount, rewards_earned
            )
            assert len(warnings) == 0

    def test_validate_staking_consistency_with_invalid_states(self) -> None:
        """Test staking consistency validation with various invalid states."""
        # Test business rule violations that should return warnings
        business_rule_violations = [
            (True, 0.0, 10.0),   # Staked but no stake amount
            (False, 100.0, -5.0), # Not staked with negative rewards
        ]
        
        for is_staked, stake_amount, rewards_earned in business_rule_violations:
            warnings = ModelValidationHelper.validate_staking_consistency(
                is_staked, stake_amount, rewards_earned
            )
            assert len(warnings) > 0
            
        # Test type validation failure (should raise AssertionError)
        with pytest.raises(AssertionError, match="stake_amount must be numeric"):
            ModelValidationHelper.validate_staking_consistency(
                True, "invalid", 5.0  # type: ignore
            )
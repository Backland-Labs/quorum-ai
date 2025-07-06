"""Tests for Pydantic models."""

import pytest
from datetime import datetime
from typing import List
from pydantic import ValidationError

from models import (
    DAO,
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
    AgentState,
    RiskLevel,
    FSMRoundType,
    ModelValidationHelper,
    VotingStrategy,
)

# Test constants
TEST_GAS_COSTS = [0.001, 0.005, 0.01, 0.1]
TEST_FSM_ROUNDS = [
    FSMRoundType.IDLE,
    FSMRoundType.VOTING,
    FSMRoundType.EXECUTION,
    FSMRoundType.HEALTH_CHECK,
]

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
            "ACTIVE",
            "CANCELED",
            "CROSSCHAINEXECUTED",
            "DEFEATED",
            "EXECUTED",
            "EXPIRED",
            "PENDING",
            "QUEUED",
            "SUCCEEDED",
        }
        actual_states = {state.value for state in ProposalState}
        assert actual_states == expected_states

    def test_proposal_state_can_be_created_from_string(self) -> None:
        """Test that ProposalState can be created from string values."""
        state = ProposalState("ACTIVE")
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
            voter="0x123", support=VoteType.FOR, weight="1000", reason="Good proposal"
        )
        assert vote.voter == "0x123"
        assert vote.support == VoteType.FOR
        assert vote.weight == "1000"
        assert vote.reason == "Good proposal"

    def test_vote_creation_without_reason(self) -> None:
        """Test Vote creation without optional reason field."""
        vote = Vote(voter="0x123", support=VoteType.AGAINST, weight="500")
        assert vote.reason is None

    def test_vote_creation_with_invalid_support_type(self) -> None:
        """Test that Vote creation fails with invalid support type."""
        with pytest.raises(ValidationError):
            Vote(voter="0x123", support="INVALID", weight="1000")  # type: ignore


class TestDAO:
    """Test cases for DAO model."""

    def _create_valid_dao_data(self) -> dict:
        """Create valid DAO data for testing."""
        return {
            "id": "dao-123",
            "name": "Test DAO",
            "slug": "test-dao",
            "organization_id": "org-456",
        }

    def test_dao_creation_with_required_fields(self) -> None:
        """Test DAO creation with only required fields."""
        dao_data = self._create_valid_dao_data()
        dao = DAO(**dao_data)

        assert dao.id == "dao-123"
        assert dao.name == "Test DAO"
        assert dao.slug == "test-dao"
        assert dao.organization_id == "org-456"
        assert dao.description is None
        assert dao.active_proposals_count == 0
        assert dao.total_proposals_count == 0

    def test_dao_creation_with_all_fields(self) -> None:
        """Test DAO creation with all fields."""
        dao_data = self._create_valid_dao_data()
        dao_data.update(
            {
                "description": "A test DAO",
                "active_proposals_count": 5,
                "total_proposals_count": 20,
            }
        )

        dao = DAO(**dao_data)
        assert dao.description == "A test DAO"
        assert dao.active_proposals_count == 5
        assert dao.total_proposals_count == 20

    def test_dao_creation_fails_with_missing_required_fields(self) -> None:
        """Test that DAO creation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            DAO(name="Test DAO")  # Missing other required fields


class TestProposal:
    """Test cases for Proposal model."""

    def _create_valid_proposal_data(self) -> dict:
        """Create valid proposal data for testing."""
        return {
            "id": "prop-123",
            "title": "Test Proposal",
            "description": "A test proposal description",
            "state": ProposalState.ACTIVE,
            "created_at": datetime.now(),
            "start_block": 1000,
            "end_block": 2000,
            "dao_id": "dao-123",
            "dao_name": "Test DAO",
        }

    def test_proposal_creation_with_required_fields(self) -> None:
        """Test Proposal creation with required fields."""
        proposal_data = self._create_valid_proposal_data()
        proposal = Proposal(**proposal_data)

        assert proposal.id == "prop-123"
        assert proposal.title == "Test Proposal"
        assert proposal.state == ProposalState.ACTIVE
        assert proposal.votes_for == "0"
        assert proposal.votes_against == "0"
        assert proposal.votes_abstain == "0"
        assert proposal.url is None

    def test_proposal_creation_with_vote_counts(self) -> None:
        """Test Proposal creation with vote counts."""
        proposal_data = self._create_valid_proposal_data()
        proposal_data.update(
            {"votes_for": "1000", "votes_against": "500", "votes_abstain": "100"}
        )

        proposal = Proposal(**proposal_data)
        assert proposal.votes_for == "1000"
        assert proposal.votes_against == "500"
        assert proposal.votes_abstain == "100"

    def test_proposal_creation_with_url(self) -> None:
        """Test Proposal creation with URL."""
        proposal_data = self._create_valid_proposal_data()
        proposal_data["url"] = "https://tally.xyz/proposal/123"

        proposal = Proposal(**proposal_data)
        assert proposal.url == "https://tally.xyz/proposal/123"


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
                description="Desc 1",
                state=ProposalState.ACTIVE,
                created_at=datetime.now(),
                start_block=1000,
                end_block=2000,
                dao_id="dao-1",
                dao_name="DAO 1",
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


class TestOrganizationOverviewResponse:
    """Test cases for OrganizationOverviewResponse model."""

    def _create_valid_overview_data(self) -> dict:
        """Create valid organization overview data for testing."""
        return {
            "organization_id": "org-123",
            "organization_name": "Test DAO",
            "organization_slug": "test-dao",
            "description": "A test DAO organization",
            "delegate_count": 150,
            "token_holder_count": 1000,
            "total_proposals_count": 50,
            "proposal_counts_by_status": {
                "ACTIVE": 5,
                "SUCCEEDED": 25,
                "DEFEATED": 10,
                "PENDING": 3,
                "EXECUTED": 7,
            },
            "recent_activity_count": 15,
            "governance_participation_rate": 0.75,
        }

    def test_organization_overview_response_creation_with_all_fields(self) -> None:
        """Test OrganizationOverviewResponse creation with all fields."""
        from models import OrganizationOverviewResponse

        overview_data = self._create_valid_overview_data()
        response = OrganizationOverviewResponse(**overview_data)

        assert response.organization_id == "org-123"
        assert response.organization_name == "Test DAO"
        assert response.organization_slug == "test-dao"
        assert response.description == "A test DAO organization"
        assert response.delegate_count == 150
        assert response.token_holder_count == 1000
        assert response.total_proposals_count == 50
        assert response.proposal_counts_by_status["ACTIVE"] == 5
        assert response.recent_activity_count == 15
        assert response.governance_participation_rate == 0.75

    def test_organization_overview_response_creation_with_required_fields_only(
        self,
    ) -> None:
        """Test OrganizationOverviewResponse creation with only required fields."""
        from models import OrganizationOverviewResponse

        minimal_data = {
            "organization_id": "org-123",
            "organization_name": "Test DAO",
            "organization_slug": "test-dao",
            "delegate_count": 150,
            "token_holder_count": 1000,
            "total_proposals_count": 50,
            "proposal_counts_by_status": {},
            "recent_activity_count": 15,
            "governance_participation_rate": 0.75,
        }

        response = OrganizationOverviewResponse(**minimal_data)
        assert response.organization_id == "org-123"
        assert response.description is None
        assert response.proposal_counts_by_status == {}

    def test_organization_overview_response_participation_rate_validation(self) -> None:
        """Test that governance_participation_rate is validated to be between 0 and 1."""
        from models import OrganizationOverviewResponse

        overview_data = self._create_valid_overview_data()

        # Test invalid participation rate > 1
        overview_data["governance_participation_rate"] = 1.5
        with pytest.raises(ValidationError):
            OrganizationOverviewResponse(**overview_data)

        # Test invalid participation rate < 0
        overview_data["governance_participation_rate"] = -0.1
        with pytest.raises(ValidationError):
            OrganizationOverviewResponse(**overview_data)

        # Test valid boundary values
        overview_data["governance_participation_rate"] = 0.0
        response = OrganizationOverviewResponse(**overview_data)
        assert response.governance_participation_rate == 0.0

        overview_data["governance_participation_rate"] = 1.0
        response = OrganizationOverviewResponse(**overview_data)
        assert response.governance_participation_rate == 1.0

    def test_organization_overview_response_negative_counts_validation(self) -> None:
        """Test that count fields are validated to be non-negative."""
        from models import OrganizationOverviewResponse

        overview_data = self._create_valid_overview_data()

        # Test negative delegate_count
        overview_data["delegate_count"] = -1
        with pytest.raises(ValidationError):
            OrganizationOverviewResponse(**overview_data)

        overview_data = self._create_valid_overview_data()
        # Test negative token_holder_count
        overview_data["token_holder_count"] = -5
        with pytest.raises(ValidationError):
            OrganizationOverviewResponse(**overview_data)

        overview_data = self._create_valid_overview_data()
        # Test negative total_proposals_count
        overview_data["total_proposals_count"] = -10
        with pytest.raises(ValidationError):
            OrganizationOverviewResponse(**overview_data)

    def test_organization_overview_response_creation_fails_with_missing_required_fields(
        self,
    ) -> None:
        """Test that OrganizationOverviewResponse creation fails when required fields are missing."""
        from models import OrganizationOverviewResponse

        with pytest.raises(ValidationError):
            OrganizationOverviewResponse(organization_name="Test DAO")


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


class TestAgentState:
    """Test cases for AgentState model."""

    def _create_valid_agent_state_data(self) -> dict:
        """Create valid agent state data for testing."""
        return {
            "last_activity": datetime.now(),
        }

    def test_agent_state_creation_with_required_fields(self) -> None:
        """Test AgentState creation with required fields."""
        state_data = self._create_valid_agent_state_data()
        state = AgentState(**state_data)

        assert isinstance(state.last_activity, datetime)
        assert state.votes_cast_today == 0  # default value
        assert state.last_activity_tx_hash is None  # default value
        assert state.is_staked is False  # default value
        assert state.staking_rewards_earned == 0.0  # default value
        assert state.stake_amount == 0.0  # default value
        assert state.current_round == FSMRoundType.IDLE  # default value
        assert state.rounds_completed == 0  # default value
        assert state.is_healthy is True  # default value

    def test_agent_state_creation_with_all_fields(self) -> None:
        """Test AgentState creation with all fields."""
        state_data = self._create_valid_agent_state_data()
        state_data.update({
            "votes_cast_today": 5,
            "last_activity_tx_hash": "0x123abc456def789",
            "is_staked": True,
            "staking_rewards_earned": 12.5,
            "stake_amount": 1000.0,
            "current_round": FSMRoundType.VOTING,
            "rounds_completed": 100,
            "is_healthy": False,
        })

        state = AgentState(**state_data)
        assert state.votes_cast_today == 5
        assert state.last_activity_tx_hash == "0x123abc456def789"
        assert state.is_staked is True
        assert state.staking_rewards_earned == 12.5
        assert state.stake_amount == 1000.0
        assert state.current_round == FSMRoundType.VOTING
        assert state.rounds_completed == 100
        assert state.is_healthy is False

    def test_agent_state_votes_cast_today_validation(self) -> None:
        """Test that votes_cast_today is validated to be non-negative."""
        state_data = self._create_valid_agent_state_data()
        assert_non_negative_field_validation(AgentState, state_data, "votes_cast_today")
        
        # Test additional valid value
        state_data["votes_cast_today"] = 10
        state = AgentState(**state_data)
        assert state.votes_cast_today == 10

    def test_agent_state_staking_rewards_validation(self) -> None:
        """Test that staking_rewards_earned is validated to be non-negative."""
        state_data = self._create_valid_agent_state_data()
        assert_non_negative_field_validation(AgentState, state_data, "staking_rewards_earned")
        
        # Test additional valid value
        state_data["staking_rewards_earned"] = 100.5
        state = AgentState(**state_data)
        assert state.staking_rewards_earned == 100.5

    def test_agent_state_stake_amount_validation(self) -> None:
        """Test that stake_amount is validated to be non-negative."""
        state_data = self._create_valid_agent_state_data()
        assert_non_negative_field_validation(AgentState, state_data, "stake_amount")
        
        # Test additional valid value
        state_data["stake_amount"] = 5000.0
        state = AgentState(**state_data)
        assert state.stake_amount == 5000.0

    def test_agent_state_rounds_completed_validation(self) -> None:
        """Test that rounds_completed is validated to be non-negative."""
        state_data = self._create_valid_agent_state_data()
        assert_non_negative_field_validation(AgentState, state_data, "rounds_completed")
        
        # Test additional valid value
        state_data["rounds_completed"] = 1000
        state = AgentState(**state_data)
        assert state.rounds_completed == 1000

    def test_agent_state_creation_fails_with_missing_required_fields(self) -> None:
        """Test that AgentState creation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            AgentState()  # Missing required last_activity field

    def test_agent_state_with_different_round_types(self) -> None:
        """Test AgentState with different FSM round types."""
        state_data = self._create_valid_agent_state_data()
        
        for round_type in TEST_FSM_ROUNDS:
            state_data["current_round"] = round_type
            state = AgentState(**state_data)
            assert state.current_round == round_type

    def test_agent_state_with_optional_tx_hash(self) -> None:
        """Test AgentState with and without transaction hash."""
        state_data = self._create_valid_agent_state_data()
        
        # Test with None (default)
        state = AgentState(**state_data)
        assert state.last_activity_tx_hash is None

        # Test with actual tx hash
        state_data["last_activity_tx_hash"] = "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        state = AgentState(**state_data)
        assert state.last_activity_tx_hash == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"

    def test_agent_state_staking_status_combinations(self) -> None:
        """Test different combinations of staking-related fields."""
        state_data = self._create_valid_agent_state_data()
        
        # Test not staked scenario
        state_data.update({
            "is_staked": False,
            "stake_amount": 0.0,
            "staking_rewards_earned": 0.0,
        })
        state = AgentState(**state_data)
        assert state.is_staked is False
        assert state.stake_amount == 0.0
        assert state.staking_rewards_earned == 0.0

        # Test staked scenario
        state_data.update({
            "is_staked": True,
            "stake_amount": 1000.0,
            "staking_rewards_earned": 25.75,
        })
        state = AgentState(**state_data)
        assert state.is_staked is True
        assert state.stake_amount == 1000.0
        assert state.staking_rewards_earned == 25.75

    def test_agent_state_summary_methods(self) -> None:
        """Test AgentState summary methods return correct information."""
        state_data = self._create_valid_agent_state_data()
        state_data.update({
            "votes_cast_today": 5,
            "last_activity_tx_hash": "0x123abc",
            "is_staked": True,
            "staking_rewards_earned": 12.5,
            "stake_amount": 1000.0,
            "current_round": FSMRoundType.VOTING,
            "rounds_completed": 100,
            "is_healthy": False,
        })
        
        state = AgentState(**state_data)
        
        # Test staking summary
        staking_summary = state.get_staking_summary()
        expected_staking = {
            "is_staked": True,
            "stake_amount": 1000.0,
            "rewards_earned": 12.5,
            "data_consistency_warnings": [],
            "is_data_consistent": True,
        }
        assert staking_summary == expected_staking
        
        # Test activity summary
        activity_summary = state.get_activity_summary()
        expected_activity = {
            "last_activity": state.last_activity,
            "votes_cast_today": 5,
            "last_tx_hash": "0x123abc",
        }
        assert activity_summary == expected_activity
        
        # Test FSM summary
        fsm_summary = state.get_fsm_summary()
        expected_fsm = {
            "current_round": FSMRoundType.VOTING,
            "rounds_completed": 100,
            "is_healthy": False,
        }
        assert fsm_summary == expected_fsm

    def test_agent_state_last_activity_validation_with_assertions(self) -> None:
        """Test AgentState last_activity validation with runtime assertions."""
        from datetime import datetime, timedelta
        
        # Test future timestamp
        future_time = datetime.now() + timedelta(hours=1)
        with pytest.raises(ValidationError, match="Last activity cannot be in the future"):
            AgentState(last_activity=future_time)

    def test_agent_state_staking_summary_with_warnings(self) -> None:
        """Test AgentState staking summary with data consistency warnings."""
        state_data = self._create_valid_agent_state_data()
        
        # Test inconsistent staking state (staked but zero stake amount)
        state_data.update({
            "is_staked": True,
            "stake_amount": 0.0,
            "staking_rewards_earned": 0.0,
        })
        
        state = AgentState(**state_data)
        summary = state.get_staking_summary()
        
        # Should return warnings instead of crashing
        assert summary["is_staked"] is True
        assert summary["stake_amount"] == 0.0
        assert summary["rewards_earned"] == 0.0
        assert summary["is_data_consistent"] is False
        assert len(summary["data_consistency_warnings"]) == 1
        assert "zero/negative stake amount" in summary["data_consistency_warnings"][0]

    def test_agent_state_staking_summary_with_negative_rewards(self) -> None:
        """Test AgentState staking summary with negative rewards warning."""
        state_data = self._create_valid_agent_state_data()
        
        # Test negative rewards (should be caught at Pydantic level, but test helper directly)
        from models import ModelValidationHelper
        
        warnings = ModelValidationHelper.validate_staking_consistency(
            False, 0.0, -5.0
        )
        
        assert len(warnings) == 1
        assert "Negative staking rewards detected" in warnings[0]

    def test_agent_state_staking_summary_consistent_data(self) -> None:
        """Test AgentState staking summary with consistent data."""
        state_data = self._create_valid_agent_state_data()
        
        # Test consistent staking state
        state_data.update({
            "is_staked": True,
            "stake_amount": 1000.0,
            "staking_rewards_earned": 25.0,
        })
        
        state = AgentState(**state_data)
        summary = state.get_staking_summary()
        
        # Should have no warnings
        assert summary["is_staked"] is True
        assert summary["stake_amount"] == 1000.0
        assert summary["rewards_earned"] == 25.0
        assert summary["is_data_consistent"] is True
        assert len(summary["data_consistency_warnings"]) == 0

    def test_agent_state_activity_summary_assertions(self) -> None:
        """Test AgentState activity summary runtime assertions."""
        state_data = self._create_valid_agent_state_data()
        
        # Test unreasonably high votes cast today
        state_data["votes_cast_today"] = 1001
        state = AgentState(**state_data)
        with pytest.raises(AssertionError, match="votes_cast_today seems unreasonably high"):
            state.get_activity_summary()

    def test_agent_state_fsm_summary_assertions(self) -> None:
        """Test AgentState FSM summary runtime assertions."""
        state_data = self._create_valid_agent_state_data()
        
        # Test negative rounds completed (should be prevented by field validation)
        state_data["rounds_completed"] = -1
        with pytest.raises(ValidationError):
            AgentState(**state_data)

    def test_agent_state_staking_consistency_validation(self) -> None:
        """Test AgentState staking consistency validation."""
        state_data = self._create_valid_agent_state_data()
        
        # Test valid staked state
        state_data.update({
            "is_staked": True,
            "stake_amount": 1000.0,
            "staking_rewards_earned": 25.0,
        })
        
        state = AgentState(**state_data)
        summary = state.get_staking_summary()  # Should not raise
        assert summary["is_staked"] is True
        assert summary["stake_amount"] == 1000.0
        
        # Test valid non-staked state
        state_data.update({
            "is_staked": False,
            "stake_amount": 0.0,
            "staking_rewards_earned": 0.0,
        })
        
        state = AgentState(**state_data)
        summary = state.get_staking_summary()  # Should not raise
        assert summary["is_staked"] is False


class TestModelValidationHelper:
    """Test cases for ModelValidationHelper class."""
    
    def test_validate_staking_consistency_with_consistent_data(self) -> None:
        """Test staking consistency validation with valid data."""
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=1000.0, rewards_earned=50.0
        )
        assert len(warnings) == 0
        
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=False, stake_amount=0.0, rewards_earned=0.0
        )
        assert len(warnings) == 0

    def test_validate_staking_consistency_with_inconsistent_staking(self) -> None:
        """Test staking consistency validation with inconsistent staking state."""
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=0.0, rewards_earned=0.0
        )
        assert len(warnings) == 1
        assert "zero/negative stake amount" in warnings[0]
        
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=-100.0, rewards_earned=0.0
        )
        assert len(warnings) == 1
        assert "zero/negative stake amount" in warnings[0]

    def test_validate_staking_consistency_with_negative_rewards(self) -> None:
        """Test staking consistency validation with negative rewards."""
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=False, stake_amount=0.0, rewards_earned=-10.0
        )
        assert len(warnings) == 1
        assert "Negative staking rewards detected" in warnings[0]

    def test_validate_staking_consistency_with_multiple_issues(self) -> None:
        """Test staking consistency validation with multiple issues."""
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=0.0, rewards_earned=-5.0
        )
        assert len(warnings) == 2
        assert any("zero/negative stake amount" in w for w in warnings)
        assert any("Negative staking rewards detected" in w for w in warnings)

    def test_validate_staking_consistency_type_assertions_still_work(self) -> None:
        """Test that type validation still throws assertions for invalid types."""
        with pytest.raises(AssertionError, match="is_staked must be bool"):
            ModelValidationHelper.validate_staking_consistency(
                is_staked="true", stake_amount=100.0, rewards_earned=0.0  # type: ignore
            )
        
        with pytest.raises(AssertionError, match="stake_amount must be numeric"):
            ModelValidationHelper.validate_staking_consistency(
                is_staked=True, stake_amount="100", rewards_earned=0.0  # type: ignore
            )
        
        with pytest.raises(AssertionError, match="rewards_earned must be numeric"):
            ModelValidationHelper.validate_staking_consistency(
                is_staked=True, stake_amount=100.0, rewards_earned="0"  # type: ignore
            )

    def test_validate_blockchain_address_with_valid_addresses(self) -> None:
        """Test validate_blockchain_address with valid addresses."""
        valid_addresses = [
            "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "0x123abc456def789012345678901234567890abcd",
            "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        ]
        
        for address in valid_addresses:
            result = ModelValidationHelper.validate_blockchain_address(address)
            assert result == address

    def test_validate_blockchain_address_with_invalid_addresses(self) -> None:
        """Test validate_blockchain_address with invalid addresses."""
        # Test empty address
        with pytest.raises(AssertionError, match="Address cannot be empty"):
            ModelValidationHelper.validate_blockchain_address("")
        
        # Test whitespace-only address
        with pytest.raises(AssertionError, match="Address cannot be empty"):
            ModelValidationHelper.validate_blockchain_address("   ")
        
        # Test too short address
        with pytest.raises(AssertionError, match="Address too short"):
            ModelValidationHelper.validate_blockchain_address("0x123")
        
        # Test non-string address
        with pytest.raises(AssertionError, match="Address must be string"):
            ModelValidationHelper.validate_blockchain_address(123)  # type: ignore

    def test_validate_positive_amount_with_valid_amounts(self) -> None:
        """Test validate_positive_amount with valid amounts."""
        valid_amounts = ["0", "1000", "1000.5", "999999999999999999999999"]
        
        for amount in valid_amounts:
            result = ModelValidationHelper.validate_positive_amount(amount)
            assert result == amount

    def test_validate_positive_amount_with_invalid_amounts(self) -> None:
        """Test validate_positive_amount with invalid amounts."""
        # Test negative amount
        with pytest.raises(AssertionError, match="amount cannot be negative"):
            ModelValidationHelper.validate_positive_amount("-1")
        
        # Test empty amount
        with pytest.raises(AssertionError, match="amount cannot be empty"):
            ModelValidationHelper.validate_positive_amount("")
        
        # Test non-numeric amount
        with pytest.raises(ValueError, match="amount must be a valid number"):
            ModelValidationHelper.validate_positive_amount("not_a_number")
        
        # Test non-string amount
        with pytest.raises(AssertionError, match="amount must be string"):
            ModelValidationHelper.validate_positive_amount(123)  # type: ignore

    def test_validate_meaningful_text_with_valid_text(self) -> None:
        """Test validate_meaningful_text with valid text."""
        valid_text = "This is a meaningful text with sufficient length"
        result = ModelValidationHelper.validate_meaningful_text(valid_text)
        assert result == valid_text

    def test_validate_meaningful_text_with_invalid_text(self) -> None:
        """Test validate_meaningful_text with invalid text."""
        # Test empty text
        with pytest.raises(AssertionError, match="text cannot be empty"):
            ModelValidationHelper.validate_meaningful_text("")
        
        # Test too short text
        with pytest.raises(AssertionError, match="text too short"):
            ModelValidationHelper.validate_meaningful_text("short")
        
        # Test custom field name and min length
        with pytest.raises(AssertionError, match="description too short"):
            ModelValidationHelper.validate_meaningful_text("short", min_length=20, field_name="description")

    def test_validate_staking_consistency_with_valid_states(self) -> None:
        """Test validate_staking_consistency with valid staking states."""
        # Test valid staked state
        ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=1000.0, rewards_earned=25.0
        )
        
        # Test valid non-staked state
        ModelValidationHelper.validate_staking_consistency(
            is_staked=False, stake_amount=0.0, rewards_earned=0.0
        )

    def test_validate_staking_consistency_with_invalid_states(self) -> None:
        """Test validate_staking_consistency with invalid staking states returns warnings."""
        # Test staked but zero stake amount (should return warning, not throw)
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=True, stake_amount=0.0, rewards_earned=0.0
        )
        assert len(warnings) == 1
        assert "zero/negative stake amount" in warnings[0]
        
        # Test negative rewards (should return warning, not throw)
        warnings = ModelValidationHelper.validate_staking_consistency(
            is_staked=False, stake_amount=0.0, rewards_earned=-5.0
        )
        assert len(warnings) == 1
        assert "Negative staking rewards detected" in warnings[0]
        
        # Test invalid types (these should still throw assertions)
        with pytest.raises(AssertionError, match="is_staked must be bool"):
            ModelValidationHelper.validate_staking_consistency(
                is_staked="true", stake_amount=0.0, rewards_earned=0.0  # type: ignore
            )

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
)


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
            address="0x123abc", amount="500000000000000000", vote_type=VoteType.AGAINST
        )

        assert voter.vote_type == VoteType.AGAINST

    def test_proposal_voter_creation_with_abstain_vote(self) -> None:
        """Test ProposalVoter creation with ABSTAIN vote."""
        voter = ProposalVoter(
            address="0xdef456", amount="250000000000000000", vote_type=VoteType.ABSTAIN
        )

        assert voter.vote_type == VoteType.ABSTAIN

    def test_proposal_voter_creation_with_invalid_vote_type_fails(self) -> None:
        """Test ProposalVoter creation fails with invalid vote type."""
        with pytest.raises(ValidationError):
            ProposalVoter(
                address="0x123abc",
                amount="1000000000000000000",
                vote_type="INVALID",  # type: ignore
            )

    def test_proposal_voter_creation_with_missing_fields_fails(self) -> None:
        """Test ProposalVoter creation fails when required fields are missing."""
        with pytest.raises(ValidationError):
            ProposalVoter(address="0x123abc")  # type: ignore


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
                address="0x123abc456def789",
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

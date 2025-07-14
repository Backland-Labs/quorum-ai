"""Tests for updated ProposalState enum to match Snapshot states."""

import pytest
from pydantic import ValidationError

from models import ProposalState


class TestProposalStateEnum:
    """Test class for updated ProposalState enum with Snapshot states."""

    def test_proposal_state_supports_snapshot_pending_state(self):
        """Test ProposalState supports 'pending' state from Snapshot."""
        # Arrange & Act
        state = ProposalState("pending")
        
        # Assert
        assert state == "pending"
        assert isinstance(state, ProposalState)

    def test_proposal_state_supports_snapshot_active_state(self):
        """Test ProposalState supports 'active' state from Snapshot."""
        # Arrange & Act
        state = ProposalState("active")
        
        # Assert
        assert state == "active"
        assert isinstance(state, ProposalState)

    def test_proposal_state_supports_snapshot_closed_state(self):
        """Test ProposalState supports 'closed' state from Snapshot."""
        # Arrange & Act
        state = ProposalState("closed")
        
        # Assert
        assert state == "closed"
        assert isinstance(state, ProposalState)

    def test_proposal_state_all_snapshot_states_available(self):
        """Test all Snapshot states are available in ProposalState enum."""
        # Arrange
        expected_states = ["pending", "active", "closed"]
        
        # Act & Assert
        for expected_state in expected_states:
            state = ProposalState(expected_state)
            assert state == expected_state
            assert isinstance(state, ProposalState)

    def test_proposal_state_invalid_state_raises_validation_error(self):
        """Test invalid state values raise ValidationError."""
        # Arrange
        invalid_states = ["invalid", "unknown", "ACTIVE", "PENDING", "CLOSED", ""]
        
        # Act & Assert
        for invalid_state in invalid_states:
            with pytest.raises(ValueError, match="is not a valid ProposalState"):
                ProposalState(invalid_state)

    def test_proposal_state_case_sensitive_validation(self):
        """Test ProposalState is case sensitive for Snapshot states."""
        # Arrange
        uppercase_states = ["PENDING", "ACTIVE", "CLOSED"]
        
        # Act & Assert
        for uppercase_state in uppercase_states:
            with pytest.raises(ValueError):
                ProposalState(uppercase_state)

    def test_proposal_state_enum_values_match_snapshot_exactly(self):
        """Test ProposalState enum values match Snapshot states exactly."""
        # Arrange
        expected_snapshot_states = {"pending", "active", "closed"}
        
        # Act
        actual_states = {state.value for state in ProposalState}
        
        # Assert
        assert actual_states == expected_snapshot_states
        assert len(actual_states) == 3

    def test_proposal_state_no_tally_states_present(self):
        """Test ProposalState does not contain old Tally states."""
        # Arrange
        old_tally_states = {"ACTIVE", "DEFEATED", "EXECUTED", "PENDING", "SUCCEEDED"}
        
        # Act
        actual_states = {state.value for state in ProposalState}
        
        # Assert
        # None of the old Tally states should be present
        assert not any(tally_state in actual_states for tally_state in old_tally_states)

    def test_proposal_state_string_representation(self):
        """Test ProposalState string representation and value access."""
        # Arrange & Act
        pending_state = ProposalState("pending")
        active_state = ProposalState("active")
        closed_state = ProposalState("closed")
        
        # Assert
        assert pending_state.value == "pending"
        assert active_state.value == "active"
        assert closed_state.value == "closed"

    def test_proposal_state_equality_comparison(self):
        """Test ProposalState equality comparison works correctly."""
        # Arrange & Act
        state1 = ProposalState("pending")
        state2 = ProposalState("pending")
        state3 = ProposalState("active")
        
        # Assert
        assert state1 == state2
        assert state1 != state3
        assert state1 == "pending"
        assert state1 != "active"
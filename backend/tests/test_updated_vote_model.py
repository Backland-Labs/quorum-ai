"""Tests for updated Snapshot-based Vote model.

These tests are designed to validate the new Vote model structure that will replace
the current Tally-based Vote model. The tests are written to fail initially since
the Vote model has not been updated yet.

The new Vote model should support Snapshot's data structure with fields like:
- id, voter, choice, created, vp, vp_by_strategy, etc.
"""

import pytest
from typing import Any, Dict, List, Optional
from pydantic import ValidationError

from models import Vote


class TestUpdatedVoteModelBasicInstantiation:
    """Test basic Vote model instantiation with required fields."""

    def _create_valid_vote_data(self) -> Dict[str, Any]:
        """Create valid vote data for the updated Snapshot-based Vote model."""
        return {
            "id": "vote-123-abc",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": 1,
            "created": 1698768000,
            "vp": 1000.5,
            "vp_by_strategy": [500.25, 300.75, 199.5],
        }

    def test_vote_creation_with_required_fields_succeeds(self) -> None:
        """Test Vote creation with only required fields succeeds."""
        vote_data = self._create_valid_vote_data()
        vote = Vote(**vote_data)

        # Runtime assertion: required fields are properly set
        assert vote.id == "vote-123-abc"
        assert vote.voter == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        assert vote.choice == 1
        assert vote.created == 1698768000
        assert vote.vp == 1000.5
        assert vote.vp_by_strategy == [500.25, 300.75, 199.5]

    def test_vote_creation_with_all_fields_succeeds(self) -> None:
        """Test Vote creation with all optional fields included."""
        vote_data = self._create_valid_vote_data()
        vote_data.update({
            "vp_state": "validated",
            "space": {
                "id": "space-123",
                "name": "Test Space",
                "network": "1"
            },
            "proposal": {
                "id": "proposal-456",
                "title": "Test Proposal",
                "state": "active"
            },
            "reason": "I support this proposal because it aligns with our values",
            "metadata": {
                "app": "snapshot-web",
                "source": "ui"
            },
            "ipfs": "QmX7Y8Z9A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S",
            "app": "snapshot"
        })

        vote = Vote(**vote_data)

        # Runtime assertion: all fields are properly set
        assert vote.vp_state == "validated"
        assert vote.space["id"] == "space-123"
        assert vote.proposal["id"] == "proposal-456"
        assert vote.reason == "I support this proposal because it aligns with our values"
        assert vote.metadata["app"] == "snapshot-web"
        assert vote.ipfs == "QmX7Y8Z9A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S"
        assert vote.app == "snapshot"


class TestUpdatedVoteModelFieldValidation:
    """Test field validation for the updated Vote model."""

    def _create_valid_vote_data(self) -> Dict[str, Any]:
        """Create valid vote data for testing."""
        return {
            "id": "vote-123-abc",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": 1,
            "created": 1698768000,
            "vp": 1000.5,
            "vp_by_strategy": [500.25, 300.75, 199.5],
        }

    def test_vote_id_validation_succeeds_with_valid_id(self) -> None:
        """Test that id field accepts valid string values."""
        vote_data = self._create_valid_vote_data()
        
        valid_ids = [
            "vote-123",
            "0x123abc456def",
            "simple-vote-id",
            "vote_with_underscores",
            "VOTE-WITH-CAPS-123"
        ]
        
        for vote_id in valid_ids:
            vote_data["id"] = vote_id
            vote = Vote(**vote_data)
            # Runtime assertion: id is properly set
            assert vote.id == vote_id

    def test_vote_id_validation_fails_with_invalid_id(self) -> None:
        """Test that id field validation fails for invalid values."""
        vote_data = self._create_valid_vote_data()

        # Test empty string
        vote_data["id"] = ""
        with pytest.raises(ValidationError, match="id.*empty"):
            Vote(**vote_data)

        # Test whitespace only
        vote_data["id"] = "   "
        with pytest.raises(ValidationError, match="id.*empty|whitespace"):
            Vote(**vote_data)

    def test_vote_voter_validation_succeeds_with_valid_address(self) -> None:
        """Test that voter field accepts valid blockchain addresses."""
        vote_data = self._create_valid_vote_data()
        
        valid_addresses = [
            "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "0x123abc456def789012345678901234567890abcd",
            "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # vitalik.eth
        ]
        
        for address in valid_addresses:
            vote_data["voter"] = address
            vote = Vote(**vote_data)
            # Runtime assertion: voter address is properly set
            assert vote.voter == address

    def test_vote_voter_validation_fails_with_invalid_address(self) -> None:
        """Test that voter field validation fails for invalid addresses."""
        vote_data = self._create_valid_vote_data()

        # Test empty string
        vote_data["voter"] = ""
        with pytest.raises(ValidationError, match="Address cannot be empty or whitespace"):
            Vote(**vote_data)

        # Test too short address
        vote_data["voter"] = "0x123"
        with pytest.raises(ValidationError, match="voter.*too short|Address too short"):
            Vote(**vote_data)

    def test_vote_created_validation_succeeds_with_valid_timestamps(self) -> None:
        """Test that created field accepts valid timestamp values."""
        vote_data = self._create_valid_vote_data()
        
        valid_timestamps = [0, 1, 1698768000, 2147483647]  # Various valid Unix timestamps
        
        for timestamp in valid_timestamps:
            vote_data["created"] = timestamp
            vote = Vote(**vote_data)
            # Runtime assertion: timestamp is properly set
            assert vote.created == timestamp

    def test_vote_created_validation_fails_with_invalid_timestamps(self) -> None:
        """Test that created field validation fails for invalid timestamps."""
        vote_data = self._create_valid_vote_data()

        # Test negative timestamp
        vote_data["created"] = -1
        with pytest.raises(ValidationError, match="created.*negative|greater than or equal"):
            Vote(**vote_data)

        # Test non-integer timestamp
        vote_data["created"] = 1698768000.5
        with pytest.raises(ValidationError, match="Input should be a valid integer"):
            Vote(**vote_data)

    def test_vote_vp_validation_succeeds_with_valid_values(self) -> None:
        """Test that vp (voting power) field accepts valid numeric values."""
        vote_data = self._create_valid_vote_data()
        
        valid_vp_values = [0.0, 1.0, 1000.5, 999999999.99]
        
        for vp_value in valid_vp_values:
            vote_data["vp"] = vp_value
            vote = Vote(**vote_data)
            # Runtime assertion: vp is properly set
            assert vote.vp == vp_value

    def test_vote_vp_validation_fails_with_invalid_values(self) -> None:
        """Test that vp field validation fails for invalid values."""
        vote_data = self._create_valid_vote_data()

        # Test negative voting power
        vote_data["vp"] = -1.0
        with pytest.raises(ValidationError, match="vp.*negative|greater than or equal"):
            Vote(**vote_data)

        # Test non-numeric voting power
        vote_data["vp"] = "not_a_number"
        with pytest.raises(ValidationError, match="Input should be a valid number"):
            Vote(**vote_data)

    def test_vote_vp_by_strategy_validation_succeeds_with_valid_arrays(self) -> None:
        """Test that vp_by_strategy field accepts valid float arrays."""
        vote_data = self._create_valid_vote_data()
        
        valid_arrays = [
            [100.0],
            [50.5, 25.25, 24.25],
            [0.0, 0.0, 0.0],
            [999999.99, 0.01]
        ]
        
        for array in valid_arrays:
            vote_data["vp_by_strategy"] = array
            vote = Vote(**vote_data)
            # Runtime assertion: vp_by_strategy is properly set
            assert vote.vp_by_strategy == array

    def test_vote_vp_by_strategy_validation_fails_with_invalid_arrays(self) -> None:
        """Test that vp_by_strategy field validation fails for invalid arrays."""
        vote_data = self._create_valid_vote_data()

        # Test empty array
        vote_data["vp_by_strategy"] = []
        with pytest.raises(ValidationError, match="vp_by_strategy.*empty"):
            Vote(**vote_data)

        # Test array with negative values
        vote_data["vp_by_strategy"] = [100.0, -50.0]
        with pytest.raises(ValidationError, match="vp_by_strategy.*negative"):
            Vote(**vote_data)

        # Test non-array value
        vote_data["vp_by_strategy"] = "not_an_array"
        with pytest.raises(ValidationError, match="vp_by_strategy.*list|array"):
            Vote(**vote_data)


class TestUpdatedVoteModelChoiceFieldHandling:
    """Test choice field handling for different vote types."""

    def _create_base_vote_data(self) -> Dict[str, Any]:
        """Create base vote data without choice field."""
        return {
            "id": "vote-123-abc",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "created": 1698768000,
            "vp": 1000.5,
            "vp_by_strategy": [500.25, 300.75, 199.5],
        }

    def test_choice_field_handles_single_choice_vote(self) -> None:
        """Test choice field supports single choice (integer) voting."""
        vote_data = self._create_base_vote_data()
        
        # Test various single choice values
        single_choices = [1, 2, 3, 0]  # 0-based or 1-based indexing
        
        for choice in single_choices:
            vote_data["choice"] = choice
            vote = Vote(**vote_data)
            # Runtime assertion: choice is properly set as integer
            assert vote.choice == choice
            assert isinstance(vote.choice, int)

    def test_choice_field_handles_multiple_choice_vote(self) -> None:
        """Test choice field supports multiple choice (array) voting."""
        vote_data = self._create_base_vote_data()
        
        # Test various multiple choice arrays
        multiple_choices = [
            [1, 2],
            [1, 2, 3],
            [0, 1, 2, 3, 4]
        ]
        
        for choice in multiple_choices:
            vote_data["choice"] = choice
            vote = Vote(**vote_data)
            # Runtime assertion: choice is properly set as list
            assert vote.choice == choice
            assert isinstance(vote.choice, list)

    def test_choice_field_handles_weighted_choice_vote(self) -> None:
        """Test choice field supports weighted choice (object) voting."""
        vote_data = self._create_base_vote_data()
        
        # Test various weighted choice objects
        weighted_choices = [
            {"1": 60.0, "2": 40.0},
            {"1": 100.0},
            {"1": 33.33, "2": 33.33, "3": 33.34}
        ]
        
        for choice in weighted_choices:
            vote_data["choice"] = choice
            vote = Vote(**vote_data)
            # Runtime assertion: choice is properly set as dict
            assert vote.choice == choice
            assert isinstance(vote.choice, dict)

    def test_choice_field_handles_string_choice_values(self) -> None:
        """Test choice field supports string-based choices."""
        vote_data = self._create_base_vote_data()
        
        # Test string choices (for some voting systems)
        string_choices = ["yes", "no", "abstain", "for", "against"]
        
        for choice in string_choices:
            vote_data["choice"] = choice
            vote = Vote(**vote_data)
            # Runtime assertion: choice is properly set as string
            assert vote.choice == choice
            assert isinstance(vote.choice, str)

    def test_choice_field_validation_fails_with_invalid_types(self) -> None:
        """Test that choice field validation fails for completely invalid types."""
        vote_data = self._create_base_vote_data()

        # Test None (should fail if choice is required)
        vote_data["choice"] = None
        with pytest.raises(ValidationError, match="choice.*required|none"):
            Vote(**vote_data)

        # Test boolean (probably not a valid choice type)
        vote_data["choice"] = True
        with pytest.raises(ValidationError, match="choice.*type|boolean"):
            Vote(**vote_data)


class TestUpdatedVoteModelOptionalFieldHandling:
    """Test handling of optional fields in the updated Vote model."""

    def _create_minimal_vote_data(self) -> Dict[str, Any]:
        """Create minimal vote data with only required fields."""
        return {
            "id": "vote-123-abc",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": 1,
            "created": 1698768000,
            "vp": 1000.5,
            "vp_by_strategy": [500.25, 300.75, 199.5],
        }

    def test_optional_vp_state_field_handling(self) -> None:
        """Test vp_state optional field is handled correctly."""
        vote_data = self._create_minimal_vote_data()
        
        # Test without vp_state (should default to None)
        vote = Vote(**vote_data)
        assert vote.vp_state is None
        
        # Test with vp_state
        vote_data["vp_state"] = "validated"
        vote = Vote(**vote_data)
        # Runtime assertion: vp_state is properly set
        assert vote.vp_state == "validated"

    def test_optional_space_field_handling(self) -> None:
        """Test space optional field accepts space objects."""
        vote_data = self._create_minimal_vote_data()
        
        # Test without space (should default to None)
        vote = Vote(**vote_data)
        assert vote.space is None
        
        # Test with space object
        space_object = {
            "id": "space-123",
            "name": "Test Space",
            "network": "1",
            "symbol": "TEST"
        }
        vote_data["space"] = space_object
        vote = Vote(**vote_data)
        # Runtime assertion: space is properly set
        assert vote.space == space_object
        assert vote.space["id"] == "space-123"

    def test_optional_proposal_field_handling(self) -> None:
        """Test proposal optional field accepts proposal objects."""
        vote_data = self._create_minimal_vote_data()
        
        # Test without proposal (should default to None)
        vote = Vote(**vote_data)
        assert vote.proposal is None
        
        # Test with proposal object
        proposal_object = {
            "id": "proposal-456",
            "title": "Test Proposal",
            "state": "active",
            "author": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        }
        vote_data["proposal"] = proposal_object
        vote = Vote(**vote_data)
        # Runtime assertion: proposal is properly set
        assert vote.proposal == proposal_object
        assert vote.proposal["id"] == "proposal-456"

    def test_optional_reason_field_handling(self) -> None:
        """Test reason optional field accepts string explanations."""
        vote_data = self._create_minimal_vote_data()
        
        # Test without reason (should default to None)
        vote = Vote(**vote_data)
        assert vote.reason is None
        
        # Test with reason
        reason_text = "I support this proposal because it improves governance"
        vote_data["reason"] = reason_text
        vote = Vote(**vote_data)
        # Runtime assertion: reason is properly set
        assert vote.reason == reason_text

    def test_optional_metadata_field_handling(self) -> None:
        """Test metadata optional field accepts arbitrary objects."""
        vote_data = self._create_minimal_vote_data()
        
        # Test without metadata (should default to None)
        vote = Vote(**vote_data)
        assert vote.metadata is None
        
        # Test with metadata object
        metadata_object = {
            "app": "snapshot-web",
            "version": "1.2.3",
            "source": "ui",
            "client_version": "desktop"
        }
        vote_data["metadata"] = metadata_object
        vote = Vote(**vote_data)
        # Runtime assertion: metadata is properly set
        assert vote.metadata == metadata_object
        assert vote.metadata["app"] == "snapshot-web"

    def test_optional_ipfs_field_handling(self) -> None:
        """Test ipfs optional field accepts IPFS hash strings."""
        vote_data = self._create_minimal_vote_data()
        
        # Test without ipfs (should default to None)
        vote = Vote(**vote_data)
        assert vote.ipfs is None
        
        # Test with ipfs hash
        ipfs_hash = "QmX7Y8Z9A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S"
        vote_data["ipfs"] = ipfs_hash
        vote = Vote(**vote_data)
        # Runtime assertion: ipfs is properly set
        assert vote.ipfs == ipfs_hash

    def test_optional_app_field_handling(self) -> None:
        """Test app optional field accepts application name strings."""
        vote_data = self._create_minimal_vote_data()
        
        # Test without app (should default to None)
        vote = Vote(**vote_data)
        assert vote.app is None
        
        # Test with app name
        app_names = ["snapshot", "snapshot-web", "boardroom", "tally"]
        
        for app_name in app_names:
            vote_data["app"] = app_name
            vote = Vote(**vote_data)
            # Runtime assertion: app is properly set
            assert vote.app == app_name


class TestUpdatedVoteModelEdgeCasesAndErrorConditions:
    """Test edge cases and error conditions for the updated Vote model."""

    def test_vote_creation_fails_with_missing_required_fields(self) -> None:
        """Test that Vote creation fails when required fields are missing."""
        
        # Test missing id
        with pytest.raises(ValidationError, match="Field required"):
            Vote(
                voter="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
                choice=1,
                created=1698768000,
                vp=1000.5,
                vp_by_strategy=[500.25, 499.75]
            )
        
        # Test missing voter
        with pytest.raises(ValidationError, match="Field required"):
            Vote(
                id="vote-123",
                choice=1,
                created=1698768000,
                vp=1000.5,
                vp_by_strategy=[500.25, 499.75]
            )
        
        # Test missing choice
        with pytest.raises(ValidationError, match="Field required"):
            Vote(
                id="vote-123",
                voter="0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
                created=1698768000,
                vp=1000.5,
                vp_by_strategy=[500.25, 499.75]
            )

    def test_vote_creation_with_extreme_vp_values(self) -> None:
        """Test Vote creation with extreme but valid voting power values."""
        base_data = {
            "id": "vote-123",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": 1,
            "created": 1698768000,
        }
        
        # Test very large voting power
        extreme_vp_data = base_data.copy()
        extreme_vp_data.update({
            "vp": 999999999999.99,
            "vp_by_strategy": [999999999999.99]
        })
        vote = Vote(**extreme_vp_data)
        # Runtime assertion: extreme values are handled correctly
        assert vote.vp == 999999999999.99
        assert vote.vp_by_strategy[0] == 999999999999.99
        
        # Test zero voting power
        zero_vp_data = base_data.copy()
        zero_vp_data.update({
            "vp": 0.0,
            "vp_by_strategy": [0.0]
        })
        vote = Vote(**zero_vp_data)
        # Runtime assertion: zero values are handled correctly
        assert vote.vp == 0.0
        assert vote.vp_by_strategy[0] == 0.0

    def test_vote_creation_with_complex_nested_objects(self) -> None:
        """Test Vote creation with complex nested space and proposal objects."""
        vote_data = {
            "id": "vote-complex-123",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": {"1": 60.0, "2": 40.0},
            "created": 1698768000,
            "vp": 1000.5,
            "vp_by_strategy": [500.25, 300.75, 199.5],
            "space": {
                "id": "space-complex",
                "name": "Complex Space",
                "network": "1",
                "symbol": "COMPLEX",
                "strategies": [
                    {"name": "erc20-balance-of", "params": {"symbol": "COMP"}},
                    {"name": "delegation", "params": {"symbol": "COMP"}}
                ],
                "admins": ["0x123", "0x456"],
                "private": False,
                "verified": True
            },
            "proposal": {
                "id": "proposal-complex",
                "title": "Complex Proposal with Many Fields",
                "state": "active",
                "choices": ["For", "Against", "Abstain"],
                "scores": [1000.0, 500.0, 100.0],
                "scores_total": 1600.0,
                "votes": 50,
                "author": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
            },
            "metadata": {
                "app": "snapshot",
                "version": "1.0.0",
                "features": ["weighted_voting", "delegation"],
                "client_info": {
                    "browser": "chrome",
                    "version": "120.0.0"
                }
            }
        }
        
        vote = Vote(**vote_data)
        
        # Runtime assertion: complex nested objects are handled correctly
        assert vote.space["strategies"][0]["name"] == "erc20-balance-of"
        assert vote.proposal["scores_total"] == 1600.0
        assert vote.metadata["client_info"]["browser"] == "chrome"

    def test_vote_creation_with_invalid_nested_object_types(self) -> None:
        """Test that Vote creation fails with invalid nested object types."""
        base_data = {
            "id": "vote-123",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": 1,
            "created": 1698768000,
            "vp": 1000.5,
            "vp_by_strategy": [500.25, 499.75],
        }
        
        # Test invalid space type (string instead of object)
        invalid_space_data = base_data.copy()
        invalid_space_data["space"] = "not_an_object"
        with pytest.raises(ValidationError, match="space.*object|dict"):
            Vote(**invalid_space_data)
        
        # Test invalid proposal type (list instead of object)
        invalid_proposal_data = base_data.copy()
        invalid_proposal_data["proposal"] = ["not", "an", "object"]
        with pytest.raises(ValidationError, match="proposal.*object|dict"):
            Vote(**invalid_proposal_data)
        
        # Test invalid metadata type (integer instead of object)
        invalid_metadata_data = base_data.copy()
        invalid_metadata_data["metadata"] = 12345
        with pytest.raises(ValidationError, match="metadata.*object|dict"):
            Vote(**invalid_metadata_data)


class TestUpdatedVoteModelSerializationDeserialization:
    """Test serialization and deserialization of the updated Vote model."""

    def _create_comprehensive_vote_data(self) -> Dict[str, Any]:
        """Create comprehensive vote data for serialization testing."""
        return {
            "id": "vote-serialize-123",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": {"1": 70.0, "2": 30.0},
            "created": 1698768000,
            "vp": 2500.75,
            "vp_by_strategy": [1500.5, 700.25, 300.0],
            "vp_state": "final",
            "space": {
                "id": "test-space",
                "name": "Test Governance Space"
            },
            "proposal": {
                "id": "test-proposal",
                "title": "Test Governance Proposal"
            },
            "reason": "This proposal will improve our governance process",
            "metadata": {
                "app_version": "2.0.0",
                "voting_method": "weighted"
            },
            "ipfs": "QmTestHashForVoteData123456789ABCDEF",
            "app": "snapshot-interface"
        }

    def test_vote_model_serializes_to_dict_correctly(self) -> None:
        """Test that Vote model serializes to dictionary correctly."""
        vote_data = self._create_comprehensive_vote_data()
        vote = Vote(**vote_data)
        
        # Serialize to dict
        serialized = vote.model_dump()
        
        # Runtime assertion: all fields are present in serialized output
        assert serialized["id"] == vote_data["id"]
        assert serialized["voter"] == vote_data["voter"]
        assert serialized["choice"] == vote_data["choice"]
        assert serialized["created"] == vote_data["created"]
        assert serialized["vp"] == vote_data["vp"]
        assert serialized["vp_by_strategy"] == vote_data["vp_by_strategy"]
        assert serialized["vp_state"] == vote_data["vp_state"]
        assert serialized["space"] == vote_data["space"]
        assert serialized["proposal"] == vote_data["proposal"]
        assert serialized["reason"] == vote_data["reason"]
        assert serialized["metadata"] == vote_data["metadata"]
        assert serialized["ipfs"] == vote_data["ipfs"]
        assert serialized["app"] == vote_data["app"]

    def test_vote_model_serializes_to_json_correctly(self) -> None:
        """Test that Vote model serializes to JSON correctly."""
        import json
        
        vote_data = self._create_comprehensive_vote_data()
        vote = Vote(**vote_data)
        
        # Serialize to JSON
        json_str = vote.model_dump_json()
        
        # Parse back to verify structure
        parsed = json.loads(json_str)
        
        # Runtime assertion: JSON serialization preserves data integrity
        assert parsed["id"] == vote_data["id"]
        assert parsed["choice"] == vote_data["choice"]
        assert parsed["vp"] == vote_data["vp"]

    def test_vote_model_deserializes_from_dict_correctly(self) -> None:
        """Test that Vote model can be created from dictionary data."""
        vote_data = self._create_comprehensive_vote_data()
        
        # Create vote from dict
        vote = Vote(**vote_data)
        
        # Serialize and deserialize
        serialized = vote.model_dump()
        reconstructed_vote = Vote(**serialized)
        
        # Runtime assertion: deserialization preserves all data
        assert reconstructed_vote.id == vote.id
        assert reconstructed_vote.voter == vote.voter
        assert reconstructed_vote.choice == vote.choice
        assert reconstructed_vote.created == vote.created
        assert reconstructed_vote.vp == vote.vp
        assert reconstructed_vote.vp_by_strategy == vote.vp_by_strategy

    def test_vote_model_handles_partial_serialization(self) -> None:
        """Test that Vote model handles serialization with only required fields."""
        minimal_data = {
            "id": "vote-minimal-123",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": 1,
            "created": 1698768000,
            "vp": 1000.0,
            "vp_by_strategy": [1000.0],
        }
        
        vote = Vote(**minimal_data)
        serialized = vote.model_dump()
        
        # Runtime assertion: optional fields are properly handled in serialization
        assert serialized["id"] == minimal_data["id"]
        assert serialized["vp_state"] is None
        assert serialized["space"] is None
        assert serialized["proposal"] is None
        assert serialized["reason"] is None
        assert serialized["metadata"] is None
        assert serialized["ipfs"] is None
        assert serialized["app"] is None

    def test_vote_model_serialization_excludes_none_values_when_requested(self) -> None:
        """Test that Vote model can exclude None values from serialization."""
        minimal_data = {
            "id": "vote-exclude-none-123",
            "voter": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "choice": 1,
            "created": 1698768000,
            "vp": 1000.0,
            "vp_by_strategy": [1000.0],
        }
        
        vote = Vote(**minimal_data)
        
        # Serialize excluding None values
        serialized = vote.model_dump(exclude_none=True)
        
        # Runtime assertion: None values are excluded from serialized output
        assert "vp_state" not in serialized
        assert "space" not in serialized
        assert "proposal" not in serialized
        assert "reason" not in serialized
        assert "metadata" not in serialized
        assert "ipfs" not in serialized
        assert "app" not in serialized
        
        # But required fields are still present
        assert "id" in serialized
        assert "voter" in serialized
        assert "choice" in serialized
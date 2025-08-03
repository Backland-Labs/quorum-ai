"""Tests for the updated Snapshot-based Proposal model.

These tests are designed to validate the NEW Proposal model structure
based on Snapshot's data structure.
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from pydantic import ValidationError

from models import Proposal


class TestUpdatedSnapshotProposal:
    """Test cases for the updated Snapshot-based Proposal model."""

    def _create_valid_snapshot_proposal_data(self) -> dict:
        """Create valid Snapshot proposal data for testing."""
        return {
            "id": "0x123abc456def789012345678901234567890abcdef123456789012345678901234",
            "title": "Improve governance token distribution mechanism",
            "body": "This proposal aims to improve the current governance token distribution...",
            "choices": ["For", "Against", "Abstain"],
            "start": 1698768000,  # Unix timestamp
            "end": 1699372800,    # Unix timestamp
            "snapshot": 18500000,  # Block number
            "state": "active",
            "author": "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "space": {
                "id": "yam.eth",
                "name": "Yam Finance",
                "network": "1",
                "symbol": "YAM"
            },
            "network": "1",
            "symbol": "YAM",
            "scores": [1250.75, 850.25, 150.0],
            "scores_total": 2251.0,
            "scores_by_strategy": {
                "erc20-balance-of": [1000.0, 750.0, 100.0],
                "balancer": [250.75, 100.25, 50.0]
            },
            "votes": 125,
            "created": 1698681600,
            "updated": 1698768000,
            "type": "single-choice",
            "strategies": [
                {
                    "name": "erc20-balance-of",
                    "params": {
                        "symbol": "YAM",
                        "address": "0x0AaCfbeC6a24756c20D41914F2caba817C0d8521",
                        "decimals": 18
                    }
                }
            ],
            "plugins": {
                "hal": {},
                "aragon": {"network": "1"}
            },
            "ipfs": "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
            "discussion": "https://forum.yam.finance/t/proposal-discussion/123",
            "quorum": 1000.0,
            "privacy": "none"
        }

    def _create_minimal_snapshot_proposal_data(self) -> dict:
        """Create minimal valid Snapshot proposal data with only required fields."""
        return {
            "id": "0x456def789abc012345678901234567890abcdef456789abc012345678901234",
            "title": "Update treasury management strategy",
            "body": None,
            "choices": ["Yes", "No"],
            "start": 1698768000,
            "end": 1699372800,
            "snapshot": None,
            "state": "pending",
            "author": "0x123abc456def789012345678901234567890abcd",
            "space": None,
            "network": "1",
            "symbol": "GOV",
            "scores": [0.0, 0.0],
            "scores_total": 0.0,
            "scores_by_strategy": None,
            "votes": 0,
            "created": 1698681600,
            "updated": None,
            "type": None,
            "strategies": [],
            "plugins": None,
            "ipfs": None,
            "discussion": None,
            "quorum": 0.0,
            "privacy": None
        }

    def test_proposal_creation_with_required_fields_only(self) -> None:
        """Test Proposal creation with only required fields."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert proposal.id == "0x456def789abc012345678901234567890abcdef456789abc012345678901234"
        assert proposal.title == "Update treasury management strategy"
        assert proposal.body is None
        assert proposal.choices == ["Yes", "No"]
        assert proposal.start == 1698768000
        assert proposal.end == 1699372800
        assert proposal.snapshot is None
        assert proposal.state == "pending"
        assert proposal.author == "0x123abc456def789012345678901234567890abcd"
        assert proposal.space is None
        assert proposal.network == "1"
        assert proposal.symbol == "GOV"
        assert proposal.scores == [0.0, 0.0]
        assert proposal.scores_total == 0.0
        assert proposal.scores_by_strategy is None
        assert proposal.votes == 0
        assert proposal.created == 1698681600
        assert proposal.updated is None
        assert proposal.type is None
        assert proposal.strategies == []
        assert proposal.plugins is None
        assert proposal.ipfs is None
        assert proposal.discussion is None
        assert proposal.quorum == 0.0
        assert proposal.privacy is None

    def test_proposal_creation_with_all_fields(self) -> None:
        """Test Proposal creation with all fields including optional ones."""
        # Arrange
        proposal_data = self._create_valid_snapshot_proposal_data()

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert proposal.id == "0x123abc456def789012345678901234567890abcdef123456789012345678901234"
        assert proposal.title == "Improve governance token distribution mechanism"
        assert proposal.body == "This proposal aims to improve the current governance token distribution..."
        assert proposal.choices == ["For", "Against", "Abstain"]
        assert proposal.start == 1698768000
        assert proposal.end == 1699372800
        assert proposal.snapshot == 18500000
        assert proposal.state == "active"
        assert proposal.author == "0x742d35cc6835c0532021efc598c51ddc1d8b4b21"
        assert proposal.space["id"] == "yam.eth"
        assert proposal.space["name"] == "Yam Finance"
        assert proposal.network == "1"
        assert proposal.symbol == "YAM"
        assert proposal.scores == [1250.75, 850.25, 150.0]
        assert proposal.scores_total == 2251.0
        assert "erc20-balance-of" in proposal.scores_by_strategy
        assert proposal.votes == 125
        assert proposal.created == 1698681600
        assert proposal.updated == 1698768000
        assert proposal.type == "single-choice"
        assert len(proposal.strategies) == 1
        assert proposal.strategies[0]["name"] == "erc20-balance-of"
        assert "hal" in proposal.plugins
        assert proposal.ipfs == "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco"
        assert proposal.discussion == "https://forum.yam.finance/t/proposal-discussion/123"
        assert proposal.quorum == 1000.0
        assert proposal.privacy == "none"

    def test_proposal_creation_fails_with_missing_required_id(self) -> None:
        """Test that Proposal creation fails when id field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["id"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_title(self) -> None:
        """Test that Proposal creation fails when title field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["title"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_choices(self) -> None:
        """Test that Proposal creation fails when choices field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["choices"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_start(self) -> None:
        """Test that Proposal creation fails when start field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["start"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_end(self) -> None:
        """Test that Proposal creation fails when end field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["end"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_state(self) -> None:
        """Test that Proposal creation fails when state field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["state"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_author(self) -> None:
        """Test that Proposal creation fails when author field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["author"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_network(self) -> None:
        """Test that Proposal creation fails when network field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["network"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_creation_fails_with_missing_required_symbol(self) -> None:
        """Test that Proposal creation fails when symbol field is missing."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        del proposal_data["symbol"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_id_validation_empty_string_fails(self) -> None:
        """Test that Proposal creation fails with empty id string."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["id"] = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_id_validation_whitespace_only_fails(self) -> None:
        """Test that Proposal creation fails with whitespace-only id."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["id"] = "   "

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_title_validation_empty_string_fails(self) -> None:
        """Test that Proposal creation fails with empty title string."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["title"] = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_title_validation_whitespace_only_fails(self) -> None:
        """Test that Proposal creation fails with whitespace-only title."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["title"] = "   "

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_choices_validation_empty_list_fails(self) -> None:
        """Test that Proposal creation fails with empty choices list."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["choices"] = []

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_choices_validation_with_multiple_choices(self) -> None:
        """Test Proposal creation with various choice configurations."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        
        # Test binary choice (scores already match with 2 items)
        proposal_data["choices"] = ["Yes", "No"]
        proposal_data["scores"] = [0.0, 0.0]  # Ensure scores match choices
        proposal = Proposal(**proposal_data)
        assert proposal.choices == ["Yes", "No"]

        # Test multiple choice
        proposal_data["choices"] = ["Option A", "Option B", "Option C", "Abstain"]
        proposal_data["scores"] = [0.0, 0.0, 0.0, 0.0]  # Update scores to match 4 choices
        proposal = Proposal(**proposal_data)
        assert len(proposal.choices) == 4
        assert proposal.choices[0] == "Option A"

        # Test single option (should still be valid)
        proposal_data["choices"] = ["Approve"]
        proposal_data["scores"] = [0.0]  # Update scores to match 1 choice
        proposal = Proposal(**proposal_data)
        assert proposal.choices == ["Approve"]

    def test_proposal_timestamp_validation_with_valid_timestamps(self) -> None:
        """Test Proposal timestamp fields validation with valid values."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_timestamps = [0, 1000000000, 1698768000, 1699372800, 2000000000]

        for timestamp in valid_timestamps:
            # Test start timestamp (ensure created <= start <= end)
            proposal_data["created"] = timestamp
            proposal_data["start"] = timestamp
            proposal_data["end"] = timestamp + 86400
            proposal = Proposal(**proposal_data)
            assert proposal.start == timestamp

            # Test end timestamp (ensure start <= end)
            proposal_data["end"] = timestamp + 86400  # Add one day
            proposal = Proposal(**proposal_data)
            assert proposal.end == timestamp + 86400

            # Test created timestamp (ensure created <= start)
            proposal_data["created"] = timestamp
            proposal_data["start"] = timestamp  # Ensure start >= created
            proposal = Proposal(**proposal_data)
            assert proposal.created == timestamp

    def test_proposal_timestamp_validation_negative_values_fail(self) -> None:
        """Test that Proposal creation fails with negative timestamp values."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()

        # Test negative start
        proposal_data["start"] = -1
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test negative end
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["end"] = -1
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test negative created
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["created"] = -1
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_author_validation_with_valid_addresses(self) -> None:
        """Test Proposal author field validation with valid blockchain addresses."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_addresses = [
            "0x742d35cc6835c0532021efc598c51ddc1d8b4b21",
            "0x123abc456def789012345678901234567890abcd",
            "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            "0x0000000000000000000000000000000000000001"
        ]

        for address in valid_addresses:
            # Arrange
            proposal_data["author"] = address

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.author == address

    def test_proposal_author_validation_empty_address_fails(self) -> None:
        """Test that Proposal creation fails with empty author address."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["author"] = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_network_validation_with_various_networks(self) -> None:
        """Test Proposal network field validation with various network IDs."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_networks = ["1", "137", "42161", "10", "100", "56", "43114"]

        for network in valid_networks:
            # Arrange
            proposal_data["network"] = network

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.network == network

    def test_proposal_symbol_validation_with_valid_symbols(self) -> None:
        """Test Proposal symbol field validation with valid token symbols."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_symbols = ["YAM", "BAL", "UNI", "COMP", "AAVE", "MKR", "CRV", "SUSHI"]

        for symbol in valid_symbols:
            # Arrange
            proposal_data["symbol"] = symbol

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.symbol == symbol

    def test_proposal_state_validation_with_snapshot_states(self) -> None:
        """Test Proposal state field validation with Snapshot-specific states."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_states = ["pending", "active", "closed", "canceled"]

        for state in valid_states:
            # Arrange
            proposal_data["state"] = state

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.state == state

    def test_proposal_scores_validation_with_valid_arrays(self) -> None:
        """Test Proposal scores field validation with valid score arrays."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        
        # Test with matching scores and choices
        proposal_data["choices"] = ["For", "Against", "Abstain"]
        proposal_data["scores"] = [1250.75, 850.25, 150.0]
        proposal = Proposal(**proposal_data)
        assert len(proposal.scores) == len(proposal.choices)
        assert proposal.scores[0] == 1250.75

        # Test with zero scores
        proposal_data["scores"] = [0.0, 0.0, 0.0]
        proposal = Proposal(**proposal_data)
        assert all(score == 0.0 for score in proposal.scores)

        # Test with decimal scores
        proposal_data["scores"] = [123.456, 789.012, 345.678]
        proposal = Proposal(**proposal_data)
        assert proposal.scores[1] == 789.012

    def test_proposal_scores_total_validation_with_valid_values(self) -> None:
        """Test Proposal scores_total field validation with valid values."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_totals = [0.0, 100.5, 1000.0, 9999999.99]

        for total in valid_totals:
            # Arrange
            proposal_data["scores_total"] = total

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.scores_total == total

    def test_proposal_scores_total_validation_negative_fails(self) -> None:
        """Test that Proposal creation fails with negative scores_total."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["scores_total"] = -100.0

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_votes_validation_with_valid_counts(self) -> None:
        """Test Proposal votes field validation with valid vote counts."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_counts = [0, 1, 50, 1000, 999999]

        for count in valid_counts:
            # Arrange
            proposal_data["votes"] = count

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.votes == count

    def test_proposal_votes_validation_negative_fails(self) -> None:
        """Test that Proposal creation fails with negative votes count."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["votes"] = -1

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_quorum_validation_with_valid_values(self) -> None:
        """Test Proposal quorum field validation with valid values."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_quorums = [0.0, 100.0, 1000.5, 999999.99]

        for quorum in valid_quorums:
            # Arrange
            proposal_data["quorum"] = quorum

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.quorum == quorum

    def test_proposal_quorum_validation_negative_fails(self) -> None:
        """Test that Proposal creation fails with negative quorum value."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["quorum"] = -50.0

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_space_validation_with_nested_object(self) -> None:
        """Test Proposal space field validation with nested space object."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        space_object = {
            "id": "compound.eth",
            "name": "Compound",
            "network": "1",
            "symbol": "COMP",
            "verified": True,
            "private": False
        }
        proposal_data["space"] = space_object

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert isinstance(proposal.space, dict)
        assert proposal.space["id"] == "compound.eth"
        assert proposal.space["name"] == "Compound"
        assert proposal.space["network"] == "1"

    def test_proposal_strategies_validation_with_complex_objects(self) -> None:
        """Test Proposal strategies field validation with complex strategy objects."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        strategies = [
            {
                "name": "erc20-balance-of",
                "params": {
                    "symbol": "YAM",
                    "address": "0x0AaCfbeC6a24756c20D41914F2caba817C0d8521",
                    "decimals": 18
                }
            },
            {
                "name": "balancer",
                "params": {
                    "symbol": "BAL BPT",
                    "address": "0x5c6Ee304399DBdB9C8Ef030aB642B10820DB8F56"
                }
            }
        ]
        proposal_data["strategies"] = strategies

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert isinstance(proposal.strategies, list)
        assert len(proposal.strategies) == 2
        assert proposal.strategies[0]["name"] == "erc20-balance-of"
        assert proposal.strategies[1]["name"] == "balancer"

    def test_proposal_scores_by_strategy_validation_with_nested_dict(self) -> None:
        """Test Proposal scores_by_strategy field validation with nested dictionary."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        scores_by_strategy = {
            "erc20-balance-of": [1000.0, 750.0, 100.0],
            "balancer": [250.75, 100.25, 50.0],
            "delegation": [100.0, 200.0, 25.0]
        }
        proposal_data["scores_by_strategy"] = scores_by_strategy

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert isinstance(proposal.scores_by_strategy, dict)
        assert "erc20-balance-of" in proposal.scores_by_strategy
        assert isinstance(proposal.scores_by_strategy["erc20-balance-of"], list)
        assert proposal.scores_by_strategy["balancer"][0] == 250.75

    def test_proposal_plugins_validation_with_nested_dict(self) -> None:
        """Test Proposal plugins field validation with nested plugin configuration."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        plugins = {
            "hal": {},
            "aragon": {"network": "1"},
            "gnosis": {
                "safe": "0x123abc456def789012345678901234567890abcd",
                "network": "1"
            }
        }
        proposal_data["plugins"] = plugins

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert isinstance(proposal.plugins, dict)
        assert "hal" in proposal.plugins
        assert "aragon" in proposal.plugins
        assert proposal.plugins["gnosis"]["safe"] == "0x123abc456def789012345678901234567890abcd"

    def test_proposal_optional_fields_validation_with_none_values(self) -> None:
        """Test Proposal optional fields validation when set to None."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data.update({
            "body": None,
            "snapshot": None,
            "space": None,
            "scores_by_strategy": None,
            "updated": None,
            "type": None,
            "plugins": None,
            "ipfs": None,
            "discussion": None,
            "privacy": None
        })

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert proposal.body is None
        assert proposal.snapshot is None
        assert proposal.space is None
        assert proposal.scores_by_strategy is None
        assert proposal.updated is None
        assert proposal.type is None
        assert proposal.plugins is None
        assert proposal.ipfs is None
        assert proposal.discussion is None
        assert proposal.privacy is None

    def test_proposal_ipfs_validation_with_valid_hashes(self) -> None:
        """Test Proposal IPFS field validation with valid IPFS hashes."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_ipfs_hashes = [
            "QmXoypizjW3WknFiJnKLwHCnL72vedxjQkDDP1mXWo6uco",
            "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
            "QmZfSNqM7nM7K8VUtYJhFYMFq5Vn5YLn4VQPPLhCQ7a8Nr"
        ]

        for ipfs_hash in valid_ipfs_hashes:
            # Arrange
            proposal_data["ipfs"] = ipfs_hash

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.ipfs == ipfs_hash

    def test_proposal_discussion_validation_with_valid_urls(self) -> None:
        """Test Proposal discussion field validation with valid URLs."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_urls = [
            "https://forum.yam.finance/t/proposal-discussion/123",
            "https://governance.compound.finance/proposals/45",
            "https://discuss.ens.domains/t/proposal-xyz/789"
        ]

        for url in valid_urls:
            # Arrange
            proposal_data["discussion"] = url

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.discussion == url

    def test_proposal_discussion_validation_invalid_url_fails(self) -> None:
        """Test that Proposal creation fails with invalid discussion URL."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        invalid_urls = ["not-a-url", "ftp://invalid", "http://"]

        for invalid_url in invalid_urls:
            # Arrange
            proposal_data["discussion"] = invalid_url

            # Act & Assert
            with pytest.raises(ValidationError):
                Proposal(**proposal_data)

    def test_proposal_privacy_validation_with_valid_values(self) -> None:
        """Test Proposal privacy field validation with valid privacy settings."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_privacy_values = ["none", "single", "ranked"]

        for privacy_value in valid_privacy_values:
            # Arrange
            proposal_data["privacy"] = privacy_value

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.privacy == privacy_value

    def test_proposal_type_validation_with_valid_types(self) -> None:
        """Test Proposal type field validation with valid proposal types."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        valid_types = ["single-choice", "approval", "ranked-choice", "quadratic", "weighted"]

        for proposal_type in valid_types:
            # Arrange
            proposal_data["type"] = proposal_type

            # Act
            proposal = Proposal(**proposal_data)

            # Assert
            assert proposal.type == proposal_type

    def test_proposal_field_types_validation_fails_with_wrong_types(self) -> None:
        """Test Proposal field type validation fails with incorrect types."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()

        # Test invalid id type
        proposal_data["id"] = 123
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid title type
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["title"] = ["invalid", "type"]
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid choices type
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["choices"] = "not-a-list"
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid start type (non-numeric string)
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["start"] = "not-a-number"
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid end type (non-numeric string)
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["end"] = "not-a-number"
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid scores type
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["scores"] = "not-a-list"
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid scores_total type (non-numeric string)
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["scores_total"] = "not-a-number"
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid votes type (non-numeric string)
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["votes"] = "not-a-number"
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

        # Test invalid strategies type
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["strategies"] = "not-a-list"
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_serialization_to_dict(self) -> None:
        """Test Proposal model serialization to dictionary."""
        # Arrange
        proposal_data = self._create_valid_snapshot_proposal_data()
        proposal = Proposal(**proposal_data)

        # Act
        serialized = proposal.model_dump()

        # Assert
        assert isinstance(serialized, dict)
        assert serialized["id"] == "0x123abc456def789012345678901234567890abcdef123456789012345678901234"
        assert serialized["title"] == "Improve governance token distribution mechanism"
        assert serialized["state"] == "active"
        assert isinstance(serialized["choices"], list)
        assert isinstance(serialized["scores"], list)
        assert isinstance(serialized["strategies"], list)

    def test_proposal_serialization_to_json(self) -> None:
        """Test Proposal model serialization to JSON string."""
        # Arrange
        proposal_data = self._create_valid_snapshot_proposal_data()
        proposal = Proposal(**proposal_data)

        # Act
        json_str = proposal.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        assert "0x123abc456def789012345678901234567890abcdef123456789012345678901234" in json_str
        assert "Improve governance token distribution mechanism" in json_str
        assert "active" in json_str

    def test_proposal_deserialization_from_dict(self) -> None:
        """Test Proposal model deserialization from dictionary."""
        # Arrange
        proposal_data = self._create_valid_snapshot_proposal_data()

        # Act
        proposal = Proposal.model_validate(proposal_data)

        # Assert
        assert proposal.id == "0x123abc456def789012345678901234567890abcdef123456789012345678901234"
        assert proposal.title == "Improve governance token distribution mechanism"
        assert proposal.state == "active"

    def test_proposal_edge_case_large_numbers(self) -> None:
        """Test Proposal with very large numeric values."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        
        # Test large snapshot block number
        proposal_data["snapshot"] = 99999999999
        proposal = Proposal(**proposal_data)
        assert proposal.snapshot == 99999999999

        # Test large vote count
        proposal_data["votes"] = 9999999
        proposal = Proposal(**proposal_data)
        assert proposal.votes == 9999999

        # Test large quorum
        proposal_data["quorum"] = 999999999.99
        proposal = Proposal(**proposal_data)
        assert proposal.quorum == 999999999.99

    def test_proposal_edge_case_empty_optional_objects(self) -> None:
        """Test Proposal with empty objects for optional fields."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data.update({
            "space": {},
            "scores_by_strategy": {},
            "plugins": {},
            "strategies": []
        })

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert proposal.space == {}
        assert proposal.scores_by_strategy == {}
        assert proposal.plugins == {}
        assert proposal.strategies == []

    def test_proposal_edge_case_special_characters_in_strings(self) -> None:
        """Test Proposal with special characters in string fields."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data.update({
            "title": "Proposal with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "body": "Content with unicode: 🚀 ⚡ 💰 and emojis",
            "type": "single-choice",
            "privacy": "none"
        })

        # Act
        proposal = Proposal(**proposal_data)

        # Assert
        assert "!@#$%^&*()_+-=" in proposal.title
        assert "🚀" in proposal.body
        assert "⚡" in proposal.body
        assert proposal.type == "single-choice"

    def test_proposal_consistency_validation_scores_choices_mismatch(self) -> None:
        """Test Proposal validation when scores and choices arrays have different lengths."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["choices"] = ["For", "Against"]  # 2 choices
        proposal_data["scores"] = [100.0, 50.0, 25.0]  # 3 scores

        # Act & Assert
        # Should either adjust automatically or validate consistency
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_logical_validation_end_before_start_fails(self) -> None:
        """Test that Proposal creation fails when end timestamp is before start."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["start"] = 1699372800
        proposal_data["end"] = 1698768000  # End before start

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)

    def test_proposal_logical_validation_created_after_start_fails(self) -> None:
        """Test that Proposal creation fails when created timestamp is after start."""
        # Arrange
        proposal_data = self._create_minimal_snapshot_proposal_data()
        proposal_data["created"] = 1699372800
        proposal_data["start"] = 1698768000  # Start before created

        # Act & Assert
        with pytest.raises(ValidationError):
            Proposal(**proposal_data)
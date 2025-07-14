"""Tests for Snapshot Space Pydantic model."""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from pydantic import ValidationError

from models import Space  # This import will fail until Space model is implemented


class TestSpace:
    """Test cases for Snapshot Space model."""

    def _create_valid_space_data(self) -> dict:
        """Create valid Snapshot Space data for testing."""
        return {
            "id": "yam.eth",
            "name": "Yam Finance",
            "network": "1",
            "symbol": "YAM",
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
            "admins": ["0x683A78bA1f6b25E29fbBC9Cd1BFA29A51520De84"],
            "moderators": [],
            "members": [],
            "private": False,
            "verified": True,
            "created": 1598460000,
            "proposalsCount": 150,
            "followersCount": 5420,
            "votesCount": 8934
        }

    def _create_minimal_space_data(self) -> dict:
        """Create minimal valid space data with only required fields."""
        return {
            "id": "balancer.eth",
            "name": "Balancer",
            "network": "1",
            "symbol": "BAL",
            "strategies": [],
            "admins": [],
            "moderators": [],
            "members": [],
            "private": False,
            "verified": False,
            "created": 1600000000,
            "proposalsCount": 0,
            "followersCount": 0,
            "votesCount": 0
        }

    def test_space_creation_with_required_fields_only(self) -> None:
        """Test Space creation with only required fields."""
        # Arrange
        space_data = self._create_minimal_space_data()

        # Act
        space = Space(**space_data)

        # Assert
        assert space.id == "balancer.eth"
        assert space.name == "Balancer"
        assert space.network == "1"
        assert space.symbol == "BAL"
        assert space.strategies == []
        assert space.admins == []
        assert space.moderators == []
        assert space.members == []
        assert space.private is False
        assert space.verified is False
        assert space.created == 1600000000
        assert space.proposalsCount == 0
        assert space.followersCount == 0
        assert space.votesCount == 0

    def test_space_creation_with_all_fields(self) -> None:
        """Test Space creation with all fields including optional ones."""
        # Arrange
        space_data = self._create_valid_space_data()
        space_data.update({
            "about": "Yam is an elastic supply cryptocurrency",
            "avatar": "https://cdn.stamp.fyi/space/yam.eth?s=164",
            "cover": "https://cdn.stamp.fyi/space/yam.eth?s=400",
            "website": "https://yam.finance",
            "twitter": "YamFinance",
            "github": "yam-finance"
        })

        # Act
        space = Space(**space_data)

        # Assert
        assert space.id == "yam.eth"
        assert space.name == "Yam Finance"
        assert space.about == "Yam is an elastic supply cryptocurrency"
        assert space.network == "1"
        assert space.symbol == "YAM"
        assert len(space.strategies) == 1
        assert space.strategies[0]["name"] == "erc20-balance-of"
        assert space.admins == ["0x683A78bA1f6b25E29fbBC9Cd1BFA29A51520De84"]
        assert space.moderators == []
        assert space.members == []
        assert space.private is False
        assert space.avatar == "https://cdn.stamp.fyi/space/yam.eth?s=164"
        assert space.cover == "https://cdn.stamp.fyi/space/yam.eth?s=400"
        assert space.website == "https://yam.finance"
        assert space.twitter == "YamFinance"
        assert space.github == "yam-finance"
        assert space.verified is True
        assert space.created == 1598460000
        assert space.proposalsCount == 150
        assert space.followersCount == 5420
        assert space.votesCount == 8934

    def test_space_creation_with_optional_fields_as_none(self) -> None:
        """Test Space creation with optional fields explicitly set to None."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data.update({
            "about": None,
            "avatar": None,
            "cover": None,
            "website": None,
            "twitter": None,
            "github": None
        })

        # Act
        space = Space(**space_data)

        # Assert
        assert space.about is None
        assert space.avatar is None
        assert space.cover is None
        assert space.website is None
        assert space.twitter is None
        assert space.github is None

    def test_space_creation_fails_with_missing_required_id(self) -> None:
        """Test that Space creation fails when id field is missing."""
        # Arrange
        space_data = self._create_minimal_space_data()
        del space_data["id"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_creation_fails_with_missing_required_name(self) -> None:
        """Test that Space creation fails when name field is missing."""
        # Arrange
        space_data = self._create_minimal_space_data()
        del space_data["name"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_creation_fails_with_missing_required_network(self) -> None:
        """Test that Space creation fails when network field is missing."""
        # Arrange
        space_data = self._create_minimal_space_data()
        del space_data["network"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_creation_fails_with_missing_required_symbol(self) -> None:
        """Test that Space creation fails when symbol field is missing."""
        # Arrange
        space_data = self._create_minimal_space_data()
        del space_data["symbol"]

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_id_validation_empty_string_fails(self) -> None:
        """Test that Space creation fails with empty id string."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["id"] = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_id_validation_whitespace_only_fails(self) -> None:
        """Test that Space creation fails with whitespace-only id."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["id"] = "   "

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_name_validation_empty_string_fails(self) -> None:
        """Test that Space creation fails with empty name string."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["name"] = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_name_validation_whitespace_only_fails(self) -> None:
        """Test that Space creation fails with whitespace-only name."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["name"] = "   "

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_symbol_validation_empty_string_fails(self) -> None:
        """Test that Space creation fails with empty symbol string."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["symbol"] = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_symbol_validation_whitespace_only_fails(self) -> None:
        """Test that Space creation fails with whitespace-only symbol."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["symbol"] = "   "

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_network_validation_empty_string_fails(self) -> None:
        """Test that Space creation fails with empty network string."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["network"] = ""

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_network_validation_accepts_various_network_ids(self) -> None:
        """Test that Space accepts various valid network IDs."""
        # Arrange
        space_data = self._create_minimal_space_data()
        valid_networks = ["1", "137", "42161", "10", "100"]

        for network in valid_networks:
            # Arrange
            space_data["network"] = network

            # Act
            space = Space(**space_data)

            # Assert
            assert space.network == network

    def test_space_strategies_validation_with_complex_strategies(self) -> None:
        """Test Space creation with complex voting strategies."""
        # Arrange
        space_data = self._create_minimal_space_data()
        complex_strategies = [
            {
                "name": "erc20-balance-of",
                "params": {
                    "symbol": "BAL",
                    "address": "0xba100000625a3754423978a60c9317c58a424e3D",
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
        space_data["strategies"] = complex_strategies

        # Act
        space = Space(**space_data)

        # Assert
        assert len(space.strategies) == 2
        assert space.strategies[0]["name"] == "erc20-balance-of"
        assert space.strategies[1]["name"] == "balancer"

    def test_space_admins_validation_with_multiple_addresses(self) -> None:
        """Test Space creation with multiple admin addresses."""
        # Arrange
        space_data = self._create_minimal_space_data()
        admin_addresses = [
            "0x683A78bA1f6b25E29fbBC9Cd1BFA29A51520De84",
            "0x742d35Cc6835C0532021EFC598C51DdC1d8b4b21",
            "0x123abc456def789012345678901234567890abcd"
        ]
        space_data["admins"] = admin_addresses

        # Act
        space = Space(**space_data)

        # Assert
        assert len(space.admins) == 3
        assert space.admins == admin_addresses

    def test_space_moderators_validation_with_multiple_addresses(self) -> None:
        """Test Space creation with multiple moderator addresses."""
        # Arrange
        space_data = self._create_minimal_space_data()
        moderator_addresses = [
            "0x456def789abc012345678901234567890abcdef1",
            "0x789abc012def345678901234567890abcdef234"
        ]
        space_data["moderators"] = moderator_addresses

        # Act
        space = Space(**space_data)

        # Assert
        assert len(space.moderators) == 2
        assert space.moderators == moderator_addresses

    def test_space_members_validation_with_multiple_addresses(self) -> None:
        """Test Space creation with multiple member addresses."""
        # Arrange
        space_data = self._create_minimal_space_data()
        member_addresses = [
            "0xabc123def456789012345678901234567890abcd",
            "0xdef456abc789012345678901234567890abcdef",
            "0x012345678901234567890123456789012345abcd",
            "0x567890123456789012345678901234567890def1"
        ]
        space_data["members"] = member_addresses

        # Act
        space = Space(**space_data)

        # Assert
        assert len(space.members) == 4
        assert space.members == member_addresses

    def test_space_private_validation_with_boolean_values(self) -> None:
        """Test Space private field validation with boolean values."""
        # Arrange
        space_data = self._create_minimal_space_data()

        # Test private = True
        space_data["private"] = True
        space = Space(**space_data)
        assert space.private is True

        # Test private = False
        space_data["private"] = False
        space = Space(**space_data)
        assert space.private is False

    def test_space_verified_validation_with_boolean_values(self) -> None:
        """Test Space verified field validation with boolean values."""
        # Arrange
        space_data = self._create_minimal_space_data()

        # Test verified = True
        space_data["verified"] = True
        space = Space(**space_data)
        assert space.verified is True

        # Test verified = False
        space_data["verified"] = False
        space = Space(**space_data)
        assert space.verified is False

    def test_space_created_validation_with_valid_timestamps(self) -> None:
        """Test Space created field validation with valid timestamps."""
        # Arrange
        space_data = self._create_minimal_space_data()
        valid_timestamps = [0, 1000000000, 1600000000, 1700000000, 2000000000]

        for timestamp in valid_timestamps:
            # Arrange
            space_data["created"] = timestamp

            # Act
            space = Space(**space_data)

            # Assert
            assert space.created == timestamp

    def test_space_created_validation_negative_timestamp_fails(self) -> None:
        """Test that Space creation fails with negative timestamp."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["created"] = -1

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_proposals_count_validation_non_negative(self) -> None:
        """Test Space proposalsCount validation with non-negative values."""
        # Arrange
        space_data = self._create_minimal_space_data()
        valid_counts = [0, 1, 100, 1000, 10000]

        for count in valid_counts:
            # Arrange
            space_data["proposalsCount"] = count

            # Act
            space = Space(**space_data)

            # Assert
            assert space.proposalsCount == count

    def test_space_proposals_count_validation_negative_fails(self) -> None:
        """Test that Space creation fails with negative proposalsCount."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["proposalsCount"] = -1

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_followers_count_validation_non_negative(self) -> None:
        """Test Space followersCount validation with non-negative values."""
        # Arrange
        space_data = self._create_minimal_space_data()
        valid_counts = [0, 10, 1000, 50000, 100000]

        for count in valid_counts:
            # Arrange
            space_data["followersCount"] = count

            # Act
            space = Space(**space_data)

            # Assert
            assert space.followersCount == count

    def test_space_followers_count_validation_negative_fails(self) -> None:
        """Test that Space creation fails with negative followersCount."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["followersCount"] = -5

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_votes_count_validation_non_negative(self) -> None:
        """Test Space votesCount validation with non-negative values."""
        # Arrange
        space_data = self._create_minimal_space_data()
        valid_counts = [0, 25, 5000, 75000, 200000]

        for count in valid_counts:
            # Arrange
            space_data["votesCount"] = count

            # Act
            space = Space(**space_data)

            # Assert
            assert space.votesCount == count

    def test_space_votes_count_validation_negative_fails(self) -> None:
        """Test that Space creation fails with negative votesCount."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data["votesCount"] = -10

        # Act & Assert
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_url_validation_with_valid_urls(self) -> None:
        """Test Space URL fields validation with valid URLs."""
        # Arrange
        space_data = self._create_minimal_space_data()
        valid_urls = {
            "avatar": "https://cdn.stamp.fyi/space/test.eth?s=164",
            "cover": "https://cdn.stamp.fyi/space/test.eth?s=400",
            "website": "https://example.com"
        }

        for field, url in valid_urls.items():
            # Arrange
            space_data[field] = url

            # Act
            space = Space(**space_data)

            # Assert
            assert getattr(space, field) == url

    def test_space_url_validation_with_invalid_urls_fails(self) -> None:
        """Test that Space creation fails with invalid URLs."""
        # Arrange
        space_data = self._create_minimal_space_data()
        invalid_urls = ["not-a-url", "ftp://invalid", "http://", "https://"]

        for invalid_url in invalid_urls:
            # Test avatar
            space_data["avatar"] = invalid_url
            with pytest.raises(ValidationError):
                Space(**space_data)

            # Test cover
            space_data = self._create_minimal_space_data()
            space_data["cover"] = invalid_url
            with pytest.raises(ValidationError):
                Space(**space_data)

            # Test website
            space_data = self._create_minimal_space_data()
            space_data["website"] = invalid_url
            with pytest.raises(ValidationError):
                Space(**space_data)

    def test_space_social_fields_validation_with_valid_handles(self) -> None:
        """Test Space social media fields validation with valid handles."""
        # Arrange
        space_data = self._create_minimal_space_data()
        
        # Test Twitter handle
        space_data["twitter"] = "YamFinance"
        space = Space(**space_data)
        assert space.twitter == "YamFinance"

        # Test GitHub username
        space_data["github"] = "yam-finance"
        space = Space(**space_data)
        assert space.github == "yam-finance"

    def test_space_about_field_validation_with_long_text(self) -> None:
        """Test Space about field validation with long descriptive text."""
        # Arrange
        space_data = self._create_minimal_space_data()
        long_about = (
            "Yam Finance is a decentralized protocol that aims to provide "
            "elastic supply cryptocurrency backed by a treasury of "
            "DeFi assets. The protocol uses rebasing mechanisms to "
            "maintain price stability while generating yield for "
            "stakeholders through various DeFi strategies."
        )
        space_data["about"] = long_about

        # Act
        space = Space(**space_data)

        # Assert
        assert space.about == long_about
        assert len(space.about) > 100

    def test_space_serialization_to_dict(self) -> None:
        """Test Space model serialization to dictionary."""
        # Arrange
        space_data = self._create_valid_space_data()
        space = Space(**space_data)

        # Act
        serialized = space.model_dump()

        # Assert
        assert isinstance(serialized, dict)
        assert serialized["id"] == "yam.eth"
        assert serialized["name"] == "Yam Finance"
        assert serialized["network"] == "1"
        assert serialized["symbol"] == "YAM"
        assert isinstance(serialized["strategies"], list)
        assert isinstance(serialized["admins"], list)

    def test_space_serialization_to_json(self) -> None:
        """Test Space model serialization to JSON string."""
        # Arrange
        space_data = self._create_valid_space_data()
        space = Space(**space_data)

        # Act
        json_str = space.model_dump_json()

        # Assert
        assert isinstance(json_str, str)
        assert "yam.eth" in json_str
        assert "Yam Finance" in json_str

    def test_space_deserialization_from_dict(self) -> None:
        """Test Space model deserialization from dictionary."""
        # Arrange
        space_data = self._create_valid_space_data()

        # Act
        space = Space.model_validate(space_data)

        # Assert
        assert space.id == "yam.eth"
        assert space.name == "Yam Finance"

    def test_space_field_types_validation(self) -> None:
        """Test Space field type validation fails with wrong types."""
        # Arrange
        space_data = self._create_minimal_space_data()

        # Test invalid id type
        space_data["id"] = 123
        with pytest.raises(ValidationError):
            Space(**space_data)

        # Test invalid name type
        space_data = self._create_minimal_space_data()
        space_data["name"] = ["invalid", "type"]
        with pytest.raises(ValidationError):
            Space(**space_data)

        # Test invalid strategies type
        space_data = self._create_minimal_space_data()
        space_data["strategies"] = "not-a-list"
        with pytest.raises(ValidationError):
            Space(**space_data)

        # Test invalid admins type
        space_data = self._create_minimal_space_data()
        space_data["admins"] = "not-a-list"
        with pytest.raises(ValidationError):
            Space(**space_data)

        # Test invalid private type
        space_data = self._create_minimal_space_data()
        space_data["private"] = "true"
        with pytest.raises(ValidationError):
            Space(**space_data)

        # Test invalid verified type
        space_data = self._create_minimal_space_data()
        space_data["verified"] = 1
        with pytest.raises(ValidationError):
            Space(**space_data)

        # Test invalid created type
        space_data = self._create_minimal_space_data()
        space_data["created"] = "1600000000"
        with pytest.raises(ValidationError):
            Space(**space_data)

        # Test invalid proposalsCount type
        space_data = self._create_minimal_space_data()
        space_data["proposalsCount"] = "100"
        with pytest.raises(ValidationError):
            Space(**space_data)

    def test_space_edge_case_large_counts(self) -> None:
        """Test Space with very large count values."""
        # Arrange
        space_data = self._create_minimal_space_data()
        large_count = 9999999999

        # Test large proposalsCount
        space_data["proposalsCount"] = large_count
        space = Space(**space_data)
        assert space.proposalsCount == large_count

        # Test large followersCount
        space_data["followersCount"] = large_count
        space = Space(**space_data)
        assert space.followersCount == large_count

        # Test large votesCount
        space_data["votesCount"] = large_count
        space = Space(**space_data)
        assert space.votesCount == large_count

    def test_space_edge_case_empty_lists(self) -> None:
        """Test Space with empty lists for array fields."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data.update({
            "strategies": [],
            "admins": [],
            "moderators": [],
            "members": []
        })

        # Act
        space = Space(**space_data)

        # Assert
        assert space.strategies == []
        assert space.admins == []
        assert space.moderators == []
        assert space.members == []

    def test_space_edge_case_special_characters_in_strings(self) -> None:
        """Test Space with special characters in string fields."""
        # Arrange
        space_data = self._create_minimal_space_data()
        space_data.update({
            "id": "test-dao.eth",
            "name": "Test DAO & Co. (2024)",
            "symbol": "TEST-TOKEN",
            "about": "A test DAO with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        })

        # Act
        space = Space(**space_data)

        # Assert
        assert space.id == "test-dao.eth"
        assert space.name == "Test DAO & Co. (2024)"
        assert space.symbol == "TEST-TOKEN"
        assert "!@#$%^&*()_+-=" in space.about
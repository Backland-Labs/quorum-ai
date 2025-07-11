"""Tests for Governor ABI system - TDD RED PHASE (failing tests)."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any, List

# These imports will fail initially as the classes don't exist yet
# This is intentional for TDD RED phase
try:
    from services.governor_abi import GovernorABI, GovernorBravoABI, CompoundGovernorABI
    from models import GovernorFunction, GovernorContractType, ABILoadError
except ImportError:
    # Expected during RED phase - classes don't exist yet
    pass


class TestGovernorABIInitialization:
    """Test GovernorABI base class initialization and setup."""

    def test_governor_abi_initialization_with_valid_abi_path(self) -> None:
        """Test that GovernorABI initializes correctly with valid ABI file path."""
        # This test will fail because GovernorABI doesn't exist yet
        mock_abi_data = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                assert abi is not None
                assert abi.abi_path == "/path/to/abi.json"
                assert len(abi.functions) > 0

    def test_governor_abi_initialization_with_nonexistent_file_raises_error(self) -> None:
        """Test that GovernorABI raises ABILoadError when ABI file doesn't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(ABILoadError, match="ABI file not found"):
                GovernorABI("/nonexistent/path.json")

    def test_governor_abi_initialization_with_invalid_json_raises_error(self) -> None:
        """Test that GovernorABI raises ABILoadError when ABI file contains invalid JSON."""
        invalid_json = "{ invalid json content"
        
        with patch("builtins.open", mock_open(read_data=invalid_json)):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Invalid JSON in ABI file"):
                    GovernorABI("/path/to/invalid.json")

    def test_governor_abi_initialization_validates_required_functions(self) -> None:
        """Test that GovernorABI validates presence of required governor functions."""
        incomplete_abi = {
            "abi": [
                {
                    "name": "someOtherFunction",
                    "type": "function",
                    "inputs": []
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(incomplete_abi))):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Missing required governor functions"):
                    GovernorABI("/path/to/incomplete.json")


class TestGovernorABIFunctionValidation:
    """Test GovernorABI function signature validation and extraction."""

    def test_governor_abi_extracts_cast_vote_function(self) -> None:
        """Test that GovernorABI correctly extracts castVote function signature."""
        mock_abi_data = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                },
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                },
                {
                    "name": "proposalVotes",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "state",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "hasVoted",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "voter", "type": "address"}
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                cast_vote_func = abi.get_function("castVote")
                assert cast_vote_func is not None
                assert cast_vote_func.name == "castVote"
                assert len(cast_vote_func.inputs) == 2
                assert cast_vote_func.inputs[0]["name"] == "proposalId"
                assert cast_vote_func.inputs[0]["type"] == "uint256"

    def test_governor_abi_extracts_cast_vote_with_reason_function(self) -> None:
        """Test that GovernorABI correctly extracts castVoteWithReason function signature."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                cast_vote_with_reason_func = abi.get_function("castVoteWithReason")
                assert cast_vote_with_reason_func is not None
                assert cast_vote_with_reason_func.name == "castVoteWithReason"
                assert len(cast_vote_with_reason_func.inputs) == 3
                assert cast_vote_with_reason_func.inputs[2]["name"] == "reason"
                assert cast_vote_with_reason_func.inputs[2]["type"] == "string"

    def test_governor_abi_extracts_proposal_votes_function(self) -> None:
        """Test that GovernorABI correctly extracts proposalVotes function signature."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                proposal_votes_func = abi.get_function("proposalVotes")
                assert proposal_votes_func is not None
                assert proposal_votes_func.name == "proposalVotes"
                assert len(proposal_votes_func.inputs) == 1
                assert proposal_votes_func.inputs[0]["name"] == "proposalId"

    def test_governor_abi_extracts_state_function(self) -> None:
        """Test that GovernorABI correctly extracts state function signature."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                state_func = abi.get_function("state")
                assert state_func is not None
                assert state_func.name == "state"
                assert len(state_func.inputs) == 1

    def test_governor_abi_extracts_has_voted_function(self) -> None:
        """Test that GovernorABI correctly extracts hasVoted function signature."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                has_voted_func = abi.get_function("hasVoted")
                assert has_voted_func is not None
                assert has_voted_func.name == "hasVoted"
                assert len(has_voted_func.inputs) == 2
                assert has_voted_func.inputs[1]["name"] == "voter"
                assert has_voted_func.inputs[1]["type"] == "address"

    def test_governor_abi_get_function_returns_none_for_missing_function(self) -> None:
        """Test that get_function returns None for functions that don't exist."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                missing_func = abi.get_function("nonExistentFunction")
                assert missing_func is None

    def _create_complete_governor_abi(self) -> Dict[str, Any]:
        """Helper method to create a complete governor ABI for testing."""
        return {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                },
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                },
                {
                    "name": "proposalVotes",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "state",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "hasVoted",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "voter", "type": "address"}
                    ]
                }
            ]
        }


class TestGovernorABIRequiredFunctions:
    """Test GovernorABI validation of required governor functions."""

    def test_governor_abi_validates_all_required_functions_present(self) -> None:
        """Test that GovernorABI validates all required functions are present."""
        complete_abi = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                },
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                },
                {
                    "name": "proposalVotes",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "state",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "hasVoted",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "voter", "type": "address"}
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(complete_abi))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/complete.json")
                
                assert abi.has_required_functions() is True
                required_functions = abi.get_required_functions()
                assert len(required_functions) == 5

    def test_governor_abi_fails_validation_when_cast_vote_missing(self) -> None:
        """Test that GovernorABI fails validation when castVote function is missing."""
        incomplete_abi = {
            "abi": [
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(incomplete_abi))):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Missing required function: castVote"):
                    GovernorABI("/path/to/incomplete.json")

    def test_governor_abi_fails_validation_when_proposal_votes_missing(self) -> None:
        """Test that GovernorABI fails validation when proposalVotes function is missing."""
        incomplete_abi = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                },
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(incomplete_abi))):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Missing required function: proposalVotes"):
                    GovernorABI("/path/to/incomplete.json")

    def test_governor_abi_list_required_functions(self) -> None:
        """Test that GovernorABI can list all required function names."""
        expected_required_functions = [
            "castVote",
            "castVoteWithReason", 
            "proposalVotes",
            "state",
            "hasVoted"
        ]
        
        required_functions = GovernorABI.get_required_function_names()
        assert len(required_functions) == 5
        for func_name in expected_required_functions:
            assert func_name in required_functions


class TestGovernorABIFunctionSignatures:
    """Test GovernorABI function signature validation."""

    def test_governor_abi_validates_cast_vote_signature(self) -> None:
        """Test that GovernorABI validates castVote function signature."""
        abi_with_wrong_signature = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"}
                        # Missing support parameter
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(abi_with_wrong_signature))):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Invalid signature for function: castVote"):
                    GovernorABI("/path/to/wrong_signature.json")

    def test_governor_abi_validates_cast_vote_with_reason_signature(self) -> None:
        """Test that GovernorABI validates castVoteWithReason function signature."""
        abi_with_wrong_signature = {
            "abi": [
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                        # Missing reason parameter
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(abi_with_wrong_signature))):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Invalid signature for function: castVoteWithReason"):
                    GovernorABI("/path/to/wrong_signature.json")

    def test_governor_abi_validates_has_voted_signature(self) -> None:
        """Test that GovernorABI validates hasVoted function signature."""
        abi_with_wrong_signature = {
            "abi": [
                {
                    "name": "hasVoted",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"}
                        # Missing voter parameter
                    ]
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(abi_with_wrong_signature))):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Invalid signature for function: hasVoted"):
                    GovernorABI("/path/to/wrong_signature.json")


class TestGovernorABIVoteEncoding:
    """Test GovernorABI vote encoding functionality."""

    def test_governor_abi_encodes_cast_vote_data(self) -> None:
        """Test that GovernorABI can encode castVote function call data."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                proposal_id = 12345
                support = 1  # FOR vote
                
                encoded_data = abi.encode_cast_vote(proposal_id, support)
                assert encoded_data is not None
                assert isinstance(encoded_data, str)
                assert encoded_data.startswith("0x")

    def test_governor_abi_encodes_cast_vote_with_reason_data(self) -> None:
        """Test that GovernorABI can encode castVoteWithReason function call data."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                proposal_id = 12345
                support = 1  # FOR vote
                reason = "This proposal benefits the community"
                
                encoded_data = abi.encode_cast_vote_with_reason(proposal_id, support, reason)
                assert encoded_data is not None
                assert isinstance(encoded_data, str)
                assert encoded_data.startswith("0x")

    def test_governor_abi_validates_vote_encoding_parameters(self) -> None:
        """Test that GovernorABI validates parameters for vote encoding."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                # Test invalid support value
                with pytest.raises(ValueError, match="support must be 0, 1, or 2"):
                    abi.encode_cast_vote(12345, 5)
                
                # Test invalid proposal ID
                with pytest.raises(ValueError, match="proposal_id must be positive"):
                    abi.encode_cast_vote(-1, 1)

    def test_governor_abi_validates_reason_parameter(self) -> None:
        """Test that GovernorABI validates reason parameter for castVoteWithReason."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                # Test empty reason
                with pytest.raises(ValueError, match="reason cannot be empty"):
                    abi.encode_cast_vote_with_reason(12345, 1, "")
                
                # Test None reason
                with pytest.raises(ValueError, match="reason cannot be None"):
                    abi.encode_cast_vote_with_reason(12345, 1, None)

    def _create_complete_governor_abi(self) -> Dict[str, Any]:
        """Helper method to create a complete governor ABI for testing."""
        return {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                },
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                },
                {
                    "name": "proposalVotes",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "state",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "hasVoted",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "voter", "type": "address"}
                    ]
                }
            ]
        }


class TestGovernorABIErrorHandling:
    """Test GovernorABI error handling scenarios."""

    def test_governor_abi_handles_empty_abi_file(self) -> None:
        """Test that GovernorABI handles empty ABI files gracefully."""
        empty_abi = "{}"
        
        with patch("builtins.open", mock_open(read_data=empty_abi)):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="ABI file is empty or missing 'abi' key"):
                    GovernorABI("/path/to/empty.json")

    def test_governor_abi_handles_malformed_function_definitions(self) -> None:
        """Test that GovernorABI handles malformed function definitions."""
        malformed_abi = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function"
                    # Missing inputs field
                }
            ]
        }
        
        with patch("builtins.open", mock_open(read_data=json.dumps(malformed_abi))):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Malformed function definition"):
                    GovernorABI("/path/to/malformed.json")

    def test_governor_abi_handles_read_permission_error(self) -> None:
        """Test that GovernorABI handles file permission errors."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(ABILoadError, match="Permission denied reading ABI file"):
                    GovernorABI("/path/to/protected.json")

    def test_governor_abi_handles_encoding_error_gracefully(self) -> None:
        """Test that GovernorABI handles encoding errors gracefully."""
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                abi = GovernorABI("/path/to/abi.json")
                
                # Mock encoding failure
                with patch.object(abi, "_encode_function_call", side_effect=Exception("Encoding failed")):
                    with pytest.raises(ValueError, match="Failed to encode function call"):
                        abi.encode_cast_vote(12345, 1)

    def _create_complete_governor_abi(self) -> Dict[str, Any]:
        """Helper method to create a complete governor ABI for testing."""
        return {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                },
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                },
                {
                    "name": "proposalVotes",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "state",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "hasVoted",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "voter", "type": "address"}
                    ]
                }
            ]
        }


class TestGovernorABISpecificImplementations:
    """Test specific governor ABI implementations (Compound, Bravo, etc.)."""

    def test_compound_governor_abi_initialization(self) -> None:
        """Test that CompoundGovernorABI initializes with correct ABI path."""
        # This test will fail because CompoundGovernorABI doesn't exist yet
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="{\"abi\": []}")):
                compound_abi = CompoundGovernorABI()
                
                assert compound_abi is not None
                assert compound_abi.contract_type == GovernorContractType.COMPOUND
                assert "compound" in compound_abi.abi_path.lower()

    def test_governor_bravo_abi_initialization(self) -> None:
        """Test that GovernorBravoABI initializes with correct ABI path."""
        # This test will fail because GovernorBravoABI doesn't exist yet
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="{\"abi\": []}")):
                bravo_abi = GovernorBravoABI()
                
                assert bravo_abi is not None
                assert bravo_abi.contract_type == GovernorContractType.GOVERNOR_BRAVO
                assert "bravo" in bravo_abi.abi_path.lower()

    def test_compound_governor_has_specific_functions(self) -> None:
        """Test that CompoundGovernorABI has Compound-specific functions."""
        mock_compound_abi = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                },
                {
                    "name": "castVoteWithReason",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"},
                        {"name": "reason", "type": "string"}
                    ]
                },
                {
                    "name": "proposalVotes",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "state",
                    "type": "function",
                    "inputs": [{"name": "proposalId", "type": "uint256"}]
                },
                {
                    "name": "hasVoted",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "voter", "type": "address"}
                    ]
                },
                {
                    "name": "quorumVotes",
                    "type": "function",
                    "inputs": []
                }
            ]
        }
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(mock_compound_abi))):
                compound_abi = CompoundGovernorABI()
                
                # Should have standard governor functions
                assert compound_abi.get_function("castVote") is not None
                assert compound_abi.get_function("proposalVotes") is not None
                
                # Should also have Compound-specific functions
                assert compound_abi.get_function("quorumVotes") is not None

    def test_governor_abi_factory_creates_correct_type(self) -> None:
        """Test that GovernorABI factory creates correct governor type."""
        # This test will fail because the factory doesn't exist yet
        from services.governor_abi import GovernorABIFactory
        
        compound_abi = GovernorABIFactory.create(GovernorContractType.COMPOUND)
        assert isinstance(compound_abi, CompoundGovernorABI)
        
        bravo_abi = GovernorABIFactory.create(GovernorContractType.GOVERNOR_BRAVO)
        assert isinstance(bravo_abi, GovernorBravoABI)


class TestGovernorABIAsyncOperations:
    """Test GovernorABI async operations for future extensibility."""

    @pytest.mark.asyncio
    async def test_governor_abi_async_load_from_url(self) -> None:
        """Test that GovernorABI can asynchronously load ABI from URL."""
        # This test will fail because async loading doesn't exist yet
        mock_abi_data = {
            "abi": [
                {
                    "name": "castVote",
                    "type": "function",
                    "inputs": [
                        {"name": "proposalId", "type": "uint256"},
                        {"name": "support", "type": "uint8"}
                    ]
                }
            ]
        }
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_abi_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            abi = await GovernorABI.load_from_url("https://example.com/abi.json")
            assert abi is not None
            assert abi.get_function("castVote") is not None

    @pytest.mark.asyncio
    async def test_governor_abi_async_validation_fails_gracefully(self) -> None:
        """Test that async ABI loading fails gracefully with network errors."""
        # This test will fail because async loading doesn't exist yet
        with patch("httpx.AsyncClient.get", side_effect=Exception("Network error")):
            with pytest.raises(ABILoadError, match="Failed to load ABI from URL"):
                await GovernorABI.load_from_url("https://example.com/invalid.json")


class TestGovernorFunction:
    """Test GovernorFunction model for representing ABI functions."""

    def test_governor_function_creation_with_valid_data(self) -> None:
        """Test GovernorFunction creation with valid function data."""
        # This test will fail because GovernorFunction doesn't exist yet
        function_data = {
            "name": "castVote",
            "type": "function",
            "inputs": [
                {"name": "proposalId", "type": "uint256"},
                {"name": "support", "type": "uint8"}
            ]
        }
        
        gov_function = GovernorFunction(**function_data)
        assert gov_function.name == "castVote"
        assert gov_function.type == "function"
        assert len(gov_function.inputs) == 2
        assert gov_function.inputs[0]["name"] == "proposalId"

    def test_governor_function_validates_required_fields(self) -> None:
        """Test that GovernorFunction validates required fields are present."""
        # This test will fail because GovernorFunction doesn't exist yet
        with pytest.raises(ValueError, match="Function name is required"):
            GovernorFunction(type="function", inputs=[])

    def test_governor_function_validates_input_parameters(self) -> None:
        """Test that GovernorFunction validates input parameter structure."""
        # This test will fail because GovernorFunction doesn't exist yet
        invalid_function_data = {
            "name": "castVote",
            "type": "function",
            "inputs": [
                {"name": "proposalId"}  # Missing type field
            ]
        }
        
        with pytest.raises(ValueError, match="Input parameter missing required fields"):
            GovernorFunction(**invalid_function_data)


class TestGovernorContractType:
    """Test GovernorContractType enum for different governor implementations."""

    def test_governor_contract_type_has_required_values(self) -> None:
        """Test that GovernorContractType enum has all required values."""
        # This test will fail because GovernorContractType doesn't exist yet
        expected_types = {
            "COMPOUND",
            "GOVERNOR_BRAVO", 
            "AAVE",
            "UNISWAP",
            "GENERIC"
        }
        
        actual_types = {contract_type.value for contract_type in GovernorContractType}
        assert actual_types >= expected_types  # Should have at least these types

    def test_governor_contract_type_can_be_created_from_string(self) -> None:
        """Test that GovernorContractType can be created from string values."""
        # This test will fail because GovernorContractType doesn't exist yet
        contract_type = GovernorContractType("COMPOUND")
        assert contract_type == GovernorContractType.COMPOUND


class TestABILoadError:
    """Test ABILoadError exception for ABI loading failures."""

    def test_abi_load_error_creation_with_message(self) -> None:
        """Test ABILoadError creation with error message."""
        # This test will fail because ABILoadError doesn't exist yet
        error_message = "Failed to load ABI file"
        error = ABILoadError(error_message)
        
        assert str(error) == error_message
        assert isinstance(error, Exception)

    def test_abi_load_error_creation_with_nested_exception(self) -> None:
        """Test ABILoadError creation with nested exception."""
        # This test will fail because ABILoadError doesn't exist yet
        original_error = FileNotFoundError("File not found")
        error = ABILoadError("ABI load failed", original_error)
        
        assert "ABI load failed" in str(error)
        assert error.__cause__ == original_error
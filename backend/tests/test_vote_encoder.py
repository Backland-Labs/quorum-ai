"""Tests for VoteEncoder system - TDD RED PHASE (failing tests).

This test file defines the expected behavior for the VoteEncoder class, which provides
a high-level interface for encoding votes across different governor types. The tests
follow the AAA pattern and include comprehensive validation, error handling, and
edge case coverage.

The VoteEncoder class is designed to:
1. Provide a unified interface for vote encoding across governor types
2. Handle governor type detection and ABI selection automatically
3. Support both single vote and batch vote operations
4. Include comprehensive parameter validation
5. Support async operations for loading ABIs from URLs
6. Implement caching for performance optimization
7. Provide clear error messages and recovery mechanisms
"""

import pytest
import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import patch, MagicMock, mock_open

# These imports will fail initially as the classes don't exist yet
# This is intentional for TDD RED phase
try:
    from services.vote_encoder import (
        VoteEncoder,
        VoteEncodingError,
        BatchVoteEncodingError,
        VoteEncodingResult,
        BatchVoteEncodingResult,
        GovernorTypeDetector,
        VoteEncodingCache
    )
    from services.governor_abi import GovernorABI, CompoundGovernorABI, GovernorBravoABI
    from models import GovernorContractType, VoteType
except ImportError:
    # Expected during RED phase - classes don't exist yet
    pass


class TestVoteEncoderInitialization:
    """Test VoteEncoder initialization and basic setup."""

    def test_vote_encoder_initialization_with_governor_type(self) -> None:
        """Test that VoteEncoder initializes correctly with specific governor type."""
        # This test will fail because VoteEncoder doesn't exist yet
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        assert encoder is not None
        assert encoder.governor_type == GovernorContractType.COMPOUND
        assert encoder.abi is not None
        assert isinstance(encoder.abi, CompoundGovernorABI)

    def test_vote_encoder_initialization_with_custom_abi_path(self) -> None:
        """Test that VoteEncoder initializes correctly with custom ABI path."""
        custom_abi_path = "/path/to/custom/governor.json"
        mock_abi_data = self._create_complete_governor_abi()
        
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_abi_data))):
            with patch("pathlib.Path.exists", return_value=True):
                encoder = VoteEncoder(abi_path=custom_abi_path)
                
                assert encoder is not None
                assert encoder.abi_path == custom_abi_path
                assert encoder.governor_type == GovernorContractType.GENERIC

    def test_vote_encoder_initialization_with_governor_bravo_type(self) -> None:
        """Test that VoteEncoder initializes correctly with Governor Bravo type."""
        encoder = VoteEncoder(governor_type=GovernorContractType.GOVERNOR_BRAVO)
        
        assert encoder is not None
        assert encoder.governor_type == GovernorContractType.GOVERNOR_BRAVO
        assert isinstance(encoder.abi, GovernorBravoABI)

    def test_vote_encoder_initialization_fails_with_invalid_parameters(self) -> None:
        """Test that VoteEncoder initialization fails with invalid parameters."""
        # Test with both governor_type and abi_path (conflicting parameters)
        with pytest.raises(ValueError, match="Cannot specify both governor_type and abi_path"):
            VoteEncoder(
                governor_type=GovernorContractType.COMPOUND,
                abi_path="/path/to/abi.json"
            )

    def test_vote_encoder_initialization_fails_without_parameters(self) -> None:
        """Test that VoteEncoder initialization fails without required parameters."""
        with pytest.raises(ValueError, match="Must specify either governor_type or abi_path"):
            VoteEncoder()

    def test_vote_encoder_enables_caching_by_default(self) -> None:
        """Test that VoteEncoder enables caching by default."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        assert encoder.caching_enabled is True
        assert encoder.cache is not None
        assert isinstance(encoder.cache, VoteEncodingCache)

    def test_vote_encoder_can_disable_caching(self) -> None:
        """Test that VoteEncoder can disable caching when requested."""
        encoder = VoteEncoder(
            governor_type=GovernorContractType.COMPOUND,
            enable_caching=False
        )
        
        assert encoder.caching_enabled is False
        assert encoder.cache is None

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


class TestVoteEncoderSingleVoteEncoding:
    """Test VoteEncoder single vote encoding functionality."""

    def test_encode_cast_vote_returns_valid_result(self) -> None:
        """Test that encode_cast_vote returns valid encoding result."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        proposal_id = 12345
        support = VoteType.FOR
        
        result = encoder.encode_cast_vote(proposal_id, support)
        
        assert result is not None
        assert isinstance(result, VoteEncodingResult)
        assert result.proposal_id == proposal_id
        assert result.support == support
        assert result.encoded_data.startswith("0x")
        assert result.function_name == "castVote"
        assert result.governor_type == GovernorContractType.COMPOUND
        assert result.encoding_timestamp is not None

    def test_encode_cast_vote_with_reason_returns_valid_result(self) -> None:
        """Test that encode_cast_vote_with_reason returns valid encoding result."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        proposal_id = 12345
        support = VoteType.FOR
        reason = "This proposal benefits the community and aligns with our values"
        
        result = encoder.encode_cast_vote_with_reason(proposal_id, support, reason)
        
        assert result is not None
        assert isinstance(result, VoteEncodingResult)
        assert result.proposal_id == proposal_id
        assert result.support == support
        assert result.reason == reason
        assert result.encoded_data.startswith("0x")
        assert result.function_name == "castVoteWithReason"
        assert result.governor_type == GovernorContractType.COMPOUND

    def test_encode_cast_vote_against_vote(self) -> None:
        """Test encoding AGAINST vote works correctly."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        proposal_id = 67890
        support = VoteType.AGAINST
        
        result = encoder.encode_cast_vote(proposal_id, support)
        
        assert result.proposal_id == proposal_id
        assert result.support == VoteType.AGAINST
        assert result.encoded_data.startswith("0x")
        assert len(result.encoded_data) > 10  # Should have meaningful length

    def test_encode_cast_vote_abstain_vote(self) -> None:
        """Test encoding ABSTAIN vote works correctly."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        proposal_id = 11111
        support = VoteType.ABSTAIN
        
        result = encoder.encode_cast_vote(proposal_id, support)
        
        assert result.proposal_id == proposal_id
        assert result.support == VoteType.ABSTAIN
        assert result.encoded_data.startswith("0x")

    def test_encode_cast_vote_validates_proposal_id(self) -> None:
        """Test that encode_cast_vote validates proposal ID parameter."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Test negative proposal ID
        with pytest.raises(VoteEncodingError, match="Proposal ID must be positive"):
            encoder.encode_cast_vote(-1, VoteType.FOR)
            
        # Test zero proposal ID
        with pytest.raises(VoteEncodingError, match="Proposal ID must be positive"):
            encoder.encode_cast_vote(0, VoteType.FOR)

    def test_encode_cast_vote_validates_support_type(self) -> None:
        """Test that encode_cast_vote validates support parameter type."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Test invalid support type (int instead of VoteType)
        with pytest.raises(VoteEncodingError, match="Support must be VoteType enum"):
            encoder.encode_cast_vote(12345, 1)  # Should use VoteType.FOR instead
            
        # Test None support
        with pytest.raises(VoteEncodingError, match="Support cannot be None"):
            encoder.encode_cast_vote(12345, None)

    def test_encode_cast_vote_with_reason_validates_reason(self) -> None:
        """Test that encode_cast_vote_with_reason validates reason parameter."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        proposal_id = 12345
        support = VoteType.FOR
        
        # Test empty reason
        with pytest.raises(VoteEncodingError, match="Reason cannot be empty"):
            encoder.encode_cast_vote_with_reason(proposal_id, support, "")
            
        # Test None reason
        with pytest.raises(VoteEncodingError, match="Reason cannot be None"):
            encoder.encode_cast_vote_with_reason(proposal_id, support, None)
            
        # Test reason that's too short
        with pytest.raises(VoteEncodingError, match="Reason must be at least 10 characters"):
            encoder.encode_cast_vote_with_reason(proposal_id, support, "Too short")

    def test_encode_cast_vote_with_reason_validates_reason_length(self) -> None:
        """Test that encode_cast_vote_with_reason validates reason length limits."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        proposal_id = 12345
        support = VoteType.FOR
        
        # Test reason that's too long (over 1000 characters)
        long_reason = "x" * 1001
        with pytest.raises(VoteEncodingError, match="Reason cannot exceed 1000 characters"):
            encoder.encode_cast_vote_with_reason(proposal_id, support, long_reason)

    def test_encode_cast_vote_caches_results_when_enabled(self) -> None:
        """Test that vote encoding results are cached when caching is enabled."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND, enable_caching=True)
        proposal_id = 12345
        support = VoteType.FOR
        
        # First encoding should miss cache
        result1 = encoder.encode_cast_vote(proposal_id, support)
        assert result1.from_cache is False
        
        # Second encoding should hit cache
        result2 = encoder.encode_cast_vote(proposal_id, support)
        assert result2.from_cache is True
        assert result2.encoded_data == result1.encoded_data

    def test_encode_cast_vote_bypasses_cache_when_disabled(self) -> None:
        """Test that vote encoding bypasses cache when caching is disabled."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND, enable_caching=False)
        proposal_id = 12345
        support = VoteType.FOR
        
        # Both encodings should bypass cache
        result1 = encoder.encode_cast_vote(proposal_id, support)
        result2 = encoder.encode_cast_vote(proposal_id, support)
        
        assert result1.from_cache is False
        assert result2.from_cache is False
        assert result2.encoded_data == result1.encoded_data  # Same data, not cached


class TestVoteEncoderBatchOperations:
    """Test VoteEncoder batch vote encoding functionality."""

    def test_encode_batch_votes_returns_valid_results(self) -> None:
        """Test that encode_batch_votes returns valid batch encoding results."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        vote_requests = [
            {"proposal_id": 12345, "support": VoteType.FOR},
            {"proposal_id": 67890, "support": VoteType.AGAINST},
            {"proposal_id": 11111, "support": VoteType.ABSTAIN}
        ]
        
        result = encoder.encode_batch_votes(vote_requests)
        
        assert result is not None
        assert isinstance(result, BatchVoteEncodingResult)
        assert len(result.vote_encodings) == 3
        assert result.successful_count == 3
        assert result.failed_count == 0
        assert result.total_count == 3
        assert result.batch_timestamp is not None

    def test_encode_batch_votes_with_reasons_returns_valid_results(self) -> None:
        """Test that encode_batch_votes with reasons returns valid results."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        vote_requests = [
            {
                "proposal_id": 12345,
                "support": VoteType.FOR,
                "reason": "Excellent proposal that benefits the community"
            },
            {
                "proposal_id": 67890,
                "support": VoteType.AGAINST,
                "reason": "Proposal lacks sufficient detail and oversight"
            }
        ]
        
        result = encoder.encode_batch_votes_with_reasons(vote_requests)
        
        assert result is not None
        assert len(result.vote_encodings) == 2
        assert all(encoding.reason is not None for encoding in result.vote_encodings)
        assert all(encoding.function_name == "castVoteWithReason" for encoding in result.vote_encodings)

    def test_encode_batch_votes_handles_mixed_success_failure(self) -> None:
        """Test that encode_batch_votes handles mixed success and failure scenarios."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        vote_requests = [
            {"proposal_id": 12345, "support": VoteType.FOR},  # Valid
            {"proposal_id": -1, "support": VoteType.FOR},     # Invalid proposal ID
            {"proposal_id": 67890, "support": VoteType.AGAINST}  # Valid
        ]
        
        result = encoder.encode_batch_votes(vote_requests)
        
        assert result.total_count == 3
        assert result.successful_count == 2
        assert result.failed_count == 1
        assert len(result.vote_encodings) == 2  # Only successful encodings
        assert len(result.errors) == 1  # One error for invalid proposal ID

    def test_encode_batch_votes_validates_input_list(self) -> None:
        """Test that encode_batch_votes validates input list parameters."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Test empty list
        with pytest.raises(BatchVoteEncodingError, match="Vote requests list cannot be empty"):
            encoder.encode_batch_votes([])
            
        # Test None list
        with pytest.raises(BatchVoteEncodingError, match="Vote requests cannot be None"):
            encoder.encode_batch_votes(None)

    def test_encode_batch_votes_validates_batch_size_limit(self) -> None:
        """Test that encode_batch_votes validates batch size limits."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Create a batch that exceeds the limit (assume max 100 votes per batch)
        large_batch = [
            {"proposal_id": i, "support": VoteType.FOR}
            for i in range(1, 102)  # 101 votes
        ]
        
        with pytest.raises(BatchVoteEncodingError, match="Batch size cannot exceed 100 votes"):
            encoder.encode_batch_votes(large_batch)

    def test_encode_batch_votes_validates_request_structure(self) -> None:
        """Test that encode_batch_votes validates individual request structure."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Test missing required fields
        invalid_requests = [
            {"proposal_id": 12345},  # Missing support
            {"support": VoteType.FOR}  # Missing proposal_id
        ]
        
        result = encoder.encode_batch_votes(invalid_requests)
        
        # Should handle validation errors gracefully
        assert result.successful_count == 0
        assert result.failed_count == 2
        assert len(result.errors) == 2

    def test_encode_batch_votes_optimizes_with_caching(self) -> None:
        """Test that encode_batch_votes optimizes performance with caching."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND, enable_caching=True)
        
        # First batch
        vote_requests = [
            {"proposal_id": 12345, "support": VoteType.FOR},
            {"proposal_id": 67890, "support": VoteType.AGAINST}
        ]
        
        result1 = encoder.encode_batch_votes(vote_requests)
        
        # Second batch with same votes
        result2 = encoder.encode_batch_votes(vote_requests)
        
        # Second batch should use cached results
        assert all(encoding.from_cache for encoding in result2.vote_encodings)
        assert result2.cache_hit_count == 2
        assert result2.cache_miss_count == 0

    def test_encode_batch_votes_tracks_timing_metrics(self) -> None:
        """Test that encode_batch_votes tracks timing and performance metrics."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        vote_requests = [
            {"proposal_id": 12345, "support": VoteType.FOR},
            {"proposal_id": 67890, "support": VoteType.AGAINST}
        ]
        
        result = encoder.encode_batch_votes(vote_requests)
        
        assert result.processing_time_ms > 0
        assert result.average_encoding_time_ms > 0
        assert isinstance(result.processing_time_ms, float)
        assert isinstance(result.average_encoding_time_ms, float)


class TestVoteEncoderGovernorTypeDetection:
    """Test VoteEncoder governor type detection and ABI selection."""

    def test_vote_encoder_detects_compound_governor_type(self) -> None:
        """Test that VoteEncoder detects Compound governor type from contract address."""
        # Mock governor type detector
        with patch.object(GovernorTypeDetector, 'detect_governor_type') as mock_detect:
            mock_detect.return_value = GovernorContractType.COMPOUND
            
            encoder = VoteEncoder.from_contract_address("0x1234567890abcdef")
            
            assert encoder.governor_type == GovernorContractType.COMPOUND
            assert isinstance(encoder.abi, CompoundGovernorABI)
            mock_detect.assert_called_once_with("0x1234567890abcdef")

    def test_vote_encoder_detects_governor_bravo_type(self) -> None:
        """Test that VoteEncoder detects Governor Bravo type from contract address."""
        with patch.object(GovernorTypeDetector, 'detect_governor_type') as mock_detect:
            mock_detect.return_value = GovernorContractType.GOVERNOR_BRAVO
            
            encoder = VoteEncoder.from_contract_address("0xabcdef1234567890")
            
            assert encoder.governor_type == GovernorContractType.GOVERNOR_BRAVO
            assert isinstance(encoder.abi, GovernorBravoABI)

    def test_vote_encoder_handles_unknown_governor_type(self) -> None:
        """Test that VoteEncoder handles unknown governor types gracefully."""
        with patch.object(GovernorTypeDetector, 'detect_governor_type') as mock_detect:
            mock_detect.return_value = GovernorContractType.GENERIC
            
            encoder = VoteEncoder.from_contract_address("0xunknowncontract")
            
            assert encoder.governor_type == GovernorContractType.GENERIC
            assert isinstance(encoder.abi, GovernorABI)  # Falls back to generic ABI

    def test_vote_encoder_caches_governor_type_detection(self) -> None:
        """Test that VoteEncoder caches governor type detection results."""
        # Use an address that's not in the known_addresses list to test detection caching
        contract_address = "0xunknownaddress12345"
        
        # Clear cache before testing to ensure clean state
        GovernorTypeDetector.clear_cache()
        
        # Mock the internal detection method that actually does the work
        with patch.object(GovernorTypeDetector, '_detect_by_function_signatures') as mock_detect:
            mock_detect.return_value = GovernorContractType.COMPOUND
            
            # First detection
            encoder1 = VoteEncoder.from_contract_address(contract_address)
            
            # Second detection for same address
            encoder2 = VoteEncoder.from_contract_address(contract_address)
            
            # Should only call detection once due to caching
            assert mock_detect.call_count == 1
            assert encoder1.governor_type == encoder2.governor_type
            assert encoder1.governor_type == GovernorContractType.COMPOUND

    def test_vote_encoder_validates_contract_address_format(self) -> None:
        """Test that VoteEncoder validates contract address format."""
        # Test invalid address format
        with pytest.raises(ValueError, match="Invalid contract address format"):
            VoteEncoder.from_contract_address("invalid_address")
            
        # Test empty address
        with pytest.raises(ValueError, match="Contract address cannot be empty"):
            VoteEncoder.from_contract_address("")
            
        # Test None address
        with pytest.raises(ValueError, match="Contract address cannot be None"):
            VoteEncoder.from_contract_address(None)

    def test_governor_type_detector_uses_multiple_strategies(self) -> None:
        """Test that GovernorTypeDetector uses multiple detection strategies."""
        # This test will fail because GovernorTypeDetector doesn't exist yet
        detector = GovernorTypeDetector()
        contract_address = "0x1234567890abcdef"
        
        with patch.object(detector, '_detect_by_contract_signature') as mock_signature:
            with patch.object(detector, '_detect_by_function_signatures') as mock_functions:
                with patch.object(detector, '_detect_by_known_addresses') as mock_addresses:
                    mock_addresses.return_value = None
                    mock_signature.return_value = None
                    mock_functions.return_value = GovernorContractType.COMPOUND
                    
                    result = detector.detect_governor_type(contract_address)
                    
                    assert result == GovernorContractType.COMPOUND
                    # Should try multiple strategies in order
                    mock_addresses.assert_called_once()
                    mock_signature.assert_called_once()
                    mock_functions.assert_called_once()


class TestVoteEncoderAsyncOperations:
    """Test VoteEncoder async operations for loading ABIs from URLs."""

    @pytest.mark.asyncio
    async def test_vote_encoder_loads_abi_from_url_async(self) -> None:
        """Test that VoteEncoder can load ABI from URL asynchronously."""
        abi_url = "https://example.com/governor-abi-load-test.json"
        mock_abi_data = self._create_complete_governor_abi()
        
        # Clear URL cache to ensure clean test state
        VoteEncoder.clear_url_cache()
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_abi_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            encoder = await VoteEncoder.from_url_async(abi_url)
            
            assert encoder is not None
            assert encoder.abi_url == abi_url
            assert encoder.governor_type == GovernorContractType.GENERIC

    @pytest.mark.asyncio
    async def test_vote_encoder_handles_network_errors_gracefully(self) -> None:
        """Test that async ABI loading handles network errors gracefully."""
        abi_url = "https://example.com/network-error-test.json"
        
        # Clear URL cache to ensure clean test state
        VoteEncoder.clear_url_cache()
        
        with patch("httpx.AsyncClient.get", side_effect=Exception("Network error")):
            with pytest.raises(VoteEncodingError, match="Failed to load ABI from URL"):
                await VoteEncoder.from_url_async(abi_url)

    @pytest.mark.asyncio
    async def test_vote_encoder_validates_abi_content_from_url(self) -> None:
        """Test that VoteEncoder validates ABI content loaded from URL."""
        abi_url = "https://example.com/invalid-abi.json"
        invalid_abi_data = {"invalid": "abi structure"}
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = invalid_abi_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            with pytest.raises(VoteEncodingError, match="Invalid ABI structure from URL"):
                await VoteEncoder.from_url_async(abi_url)

    @pytest.mark.asyncio
    async def test_vote_encoder_caches_abi_loaded_from_url(self) -> None:
        """Test that VoteEncoder caches ABI loaded from URL."""
        abi_url = "https://example.com/cache-test-abi.json"
        mock_abi_data = self._create_complete_governor_abi()
        
        # Clear URL cache to ensure clean test state
        VoteEncoder.clear_url_cache()
        
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_abi_data
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            # First load
            encoder1 = await VoteEncoder.from_url_async(abi_url)
            
            # Second load should use cache
            encoder2 = await VoteEncoder.from_url_async(abi_url)
            
            # Should only make one HTTP request due to caching
            assert mock_get.call_count == 1
            assert encoder1.abi_url == encoder2.abi_url

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


class TestVoteEncoderErrorHandling:
    """Test VoteEncoder error handling and recovery mechanisms."""

    def test_vote_encoding_error_creation_with_details(self) -> None:
        """Test VoteEncodingError creation with detailed error information."""
        # This test will fail because VoteEncodingError doesn't exist yet
        proposal_id = 12345
        support = VoteType.FOR
        original_error = ValueError("Invalid parameter")
        
        error = VoteEncodingError(
            message="Failed to encode vote",
            proposal_id=proposal_id,
            support=support,
            governor_type=GovernorContractType.COMPOUND,
            original_error=original_error
        )
        
        assert str(error) == "Failed to encode vote"
        assert error.proposal_id == proposal_id
        assert error.support == support
        assert error.governor_type == GovernorContractType.COMPOUND
        assert error.original_error == original_error

    def test_batch_vote_encoding_error_tracks_multiple_failures(self) -> None:
        """Test BatchVoteEncodingError tracks multiple encoding failures."""
        # This test will fail because BatchVoteEncodingError doesn't exist yet
        individual_errors = [
            VoteEncodingError("Error 1", proposal_id=123),
            VoteEncodingError("Error 2", proposal_id=456)
        ]
        
        batch_error = BatchVoteEncodingError(
            message="Batch encoding failed",
            total_requests=5,
            successful_count=3,
            failed_count=2,
            individual_errors=individual_errors
        )
        
        assert batch_error.total_requests == 5
        assert batch_error.successful_count == 3
        assert batch_error.failed_count == 2
        assert len(batch_error.individual_errors) == 2

    def test_vote_encoder_handles_abi_loading_failures(self) -> None:
        """Test that VoteEncoder handles ABI loading failures gracefully."""
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(VoteEncodingError, match="ABI file not found"):
                VoteEncoder(abi_path="/nonexistent/abi.json")

    def test_vote_encoder_handles_corrupted_abi_data(self) -> None:
        """Test that VoteEncoder handles corrupted ABI data gracefully."""
        corrupted_abi = "{ invalid json content"
        
        with patch("builtins.open", mock_open(read_data=corrupted_abi)):
            with patch("pathlib.Path.exists", return_value=True):
                with pytest.raises(VoteEncodingError, match="Invalid ABI file format"):
                    VoteEncoder(abi_path="/path/to/corrupted.json")

    def test_vote_encoder_handles_encoding_failures_gracefully(self) -> None:
        """Test that VoteEncoder handles individual encoding failures gracefully."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Mock encoding failure
        with patch.object(encoder.abi, 'encode_cast_vote', side_effect=Exception("Encoding failed")):
            with pytest.raises(VoteEncodingError, match="Failed to encode vote"):
                encoder.encode_cast_vote(12345, VoteType.FOR)

    def test_vote_encoder_provides_detailed_error_context(self) -> None:
        """Test that VoteEncoder provides detailed error context for debugging."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        try:
            encoder.encode_cast_vote(-1, VoteType.FOR)  # Invalid proposal ID
        except VoteEncodingError as e:
            assert e.proposal_id == -1
            assert e.support == VoteType.FOR
            assert e.governor_type == GovernorContractType.COMPOUND
            assert "Proposal ID must be positive" in str(e)


class TestVoteEncodingResultModels:
    """Test VoteEncodingResult and BatchVoteEncodingResult models."""

    def test_vote_encoding_result_contains_all_required_fields(self) -> None:
        """Test that VoteEncodingResult contains all required fields."""
        # This test will fail because VoteEncodingResult doesn't exist yet
        result = VoteEncodingResult(
            proposal_id=12345,
            support=VoteType.FOR,
            encoded_data="0x1234567890abcdef",
            function_name="castVote",
            governor_type=GovernorContractType.COMPOUND,
            encoding_timestamp=datetime.now(),
            from_cache=False
        )
        
        assert result.proposal_id == 12345
        assert result.support == VoteType.FOR
        assert result.encoded_data == "0x1234567890abcdef"
        assert result.function_name == "castVote"
        assert result.governor_type == GovernorContractType.COMPOUND
        assert result.from_cache is False
        assert result.encoding_timestamp is not None

    def test_vote_encoding_result_with_reason_contains_reason_field(self) -> None:
        """Test that VoteEncodingResult with reason contains reason field."""
        reason = "This proposal benefits the community"
        result = VoteEncodingResult(
            proposal_id=12345,
            support=VoteType.FOR,
            reason=reason,
            encoded_data="0x1234567890abcdef",
            function_name="castVoteWithReason",
            governor_type=GovernorContractType.COMPOUND,
            encoding_timestamp=datetime.now(),
            from_cache=False
        )
        
        assert result.reason == reason
        assert result.function_name == "castVoteWithReason"

    def test_batch_vote_encoding_result_aggregates_individual_results(self) -> None:
        """Test that BatchVoteEncodingResult aggregates individual encoding results."""
        # This test will fail because BatchVoteEncodingResult doesn't exist yet
        individual_results = [
            VoteEncodingResult(
                proposal_id=12345,
                support=VoteType.FOR,
                encoded_data="0x1111",
                function_name="castVote",
                governor_type=GovernorContractType.COMPOUND,
                encoding_timestamp=datetime.now(),
                from_cache=False
            ),
            VoteEncodingResult(
                proposal_id=67890,
                support=VoteType.AGAINST,
                encoded_data="0x2222",
                function_name="castVote",
                governor_type=GovernorContractType.COMPOUND,
                encoding_timestamp=datetime.now(),
                from_cache=True
            )
        ]
        
        batch_result = BatchVoteEncodingResult(
            vote_encodings=individual_results,
            successful_count=2,
            failed_count=0,
            total_count=2,
            errors=[],
            processing_time_ms=150.5,
            average_encoding_time_ms=75.25,
            cache_hit_count=1,
            cache_miss_count=1,
            batch_timestamp=datetime.now()
        )
        
        assert len(batch_result.vote_encodings) == 2
        assert batch_result.successful_count == 2
        assert batch_result.failed_count == 0
        assert batch_result.cache_hit_count == 1
        assert batch_result.cache_miss_count == 1

    def test_vote_encoding_result_validates_encoded_data_format(self) -> None:
        """Test that VoteEncodingResult validates encoded data format."""
        # Test invalid hex format
        with pytest.raises(ValueError, match="Encoded data must be valid hex string"):
            VoteEncodingResult(
                proposal_id=12345,
                support=VoteType.FOR,
                encoded_data="invalid_hex",  # Not hex format
                function_name="castVote",
                governor_type=GovernorContractType.COMPOUND,
                encoding_timestamp=datetime.now(),
                from_cache=False
            )

    def test_batch_vote_encoding_result_validates_count_consistency(self) -> None:
        """Test that BatchVoteEncodingResult validates count consistency."""
        individual_results = [
            VoteEncodingResult(
                proposal_id=12345,
                support=VoteType.FOR,
                encoded_data="0x1111",
                function_name="castVote",
                governor_type=GovernorContractType.COMPOUND,
                encoding_timestamp=datetime.now(),
                from_cache=False
            )
        ]
        
        # Test inconsistent counts
        with pytest.raises(ValueError, match="Count fields are inconsistent"):
            BatchVoteEncodingResult(
                vote_encodings=individual_results,
                successful_count=2,  # Should be 1
                failed_count=0,
                total_count=1,
                errors=[],
                processing_time_ms=100.0,
                average_encoding_time_ms=100.0,
                cache_hit_count=0,
                cache_miss_count=1,
                batch_timestamp=datetime.now()
            )


class TestVoteEncodingCache:
    """Test VoteEncodingCache functionality."""

    def test_vote_encoding_cache_stores_and_retrieves_results(self) -> None:
        """Test that VoteEncodingCache stores and retrieves encoding results."""
        # This test will fail because VoteEncodingCache doesn't exist yet
        cache = VoteEncodingCache()
        
        cache_key = cache.generate_key(
            proposal_id=12345,
            support=VoteType.FOR,
            governor_type=GovernorContractType.COMPOUND
        )
        
        encoded_data = "0x1234567890abcdef"
        cache.store(cache_key, encoded_data)
        
        retrieved_data = cache.get(cache_key)
        assert retrieved_data == encoded_data

    def test_vote_encoding_cache_handles_cache_misses(self) -> None:
        """Test that VoteEncodingCache handles cache misses gracefully."""
        cache = VoteEncodingCache()
        
        non_existent_key = "non_existent_key"
        result = cache.get(non_existent_key)
        
        assert result is None

    def test_vote_encoding_cache_respects_ttl_expiration(self) -> None:
        """Test that VoteEncodingCache respects TTL expiration."""
        cache = VoteEncodingCache(default_ttl_seconds=1)  # 1 second TTL
        
        cache_key = "test_key"
        encoded_data = "0x1234567890abcdef"
        
        cache.store(cache_key, encoded_data)
        
        # Should be available immediately
        assert cache.get(cache_key) == encoded_data
        
        # Should expire after TTL
        import time
        time.sleep(1.1)  # Wait longer than TTL
        assert cache.get(cache_key) is None

    def test_vote_encoding_cache_generates_consistent_keys(self) -> None:
        """Test that VoteEncodingCache generates consistent cache keys."""
        cache = VoteEncodingCache()
        
        key1 = cache.generate_key(
            proposal_id=12345,
            support=VoteType.FOR,
            governor_type=GovernorContractType.COMPOUND
        )
        
        key2 = cache.generate_key(
            proposal_id=12345,
            support=VoteType.FOR,
            governor_type=GovernorContractType.COMPOUND
        )
        
        assert key1 == key2

    def test_vote_encoding_cache_generates_different_keys_for_different_params(self) -> None:
        """Test that VoteEncodingCache generates different keys for different parameters."""
        cache = VoteEncodingCache()
        
        key1 = cache.generate_key(
            proposal_id=12345,
            support=VoteType.FOR,
            governor_type=GovernorContractType.COMPOUND
        )
        
        key2 = cache.generate_key(
            proposal_id=12345,
            support=VoteType.AGAINST,  # Different support
            governor_type=GovernorContractType.COMPOUND
        )
        
        assert key1 != key2

    def test_vote_encoding_cache_tracks_hit_miss_statistics(self) -> None:
        """Test that VoteEncodingCache tracks hit and miss statistics."""
        cache = VoteEncodingCache()
        
        # Initially should have no hits or misses
        assert cache.hit_count == 0
        assert cache.miss_count == 0
        
        # Cache miss
        cache.get("non_existent_key")
        assert cache.miss_count == 1
        
        # Cache store and hit
        cache.store("test_key", "test_data")
        cache.get("test_key")
        assert cache.hit_count == 1

    def test_vote_encoding_cache_can_be_cleared(self) -> None:
        """Test that VoteEncodingCache can be cleared."""
        cache = VoteEncodingCache()
        
        cache.store("key1", "data1")
        cache.store("key2", "data2")
        
        assert cache.get("key1") == "data1"
        assert cache.get("key2") == "data2"
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestVoteEncoderPerformanceOptimizations:
    """Test VoteEncoder performance optimizations and metrics."""

    def test_vote_encoder_batch_encoding_is_faster_than_individual(self) -> None:
        """Test that batch encoding is faster than individual encoding operations."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND, enable_caching=False)
        
        vote_requests = [
            {"proposal_id": i, "support": VoteType.FOR}
            for i in range(1, 11)  # 10 votes
        ]
        
        # Time individual encodings
        import time
        start_time = time.time()
        for request in vote_requests:
            encoder.encode_cast_vote(request["proposal_id"], request["support"])
        individual_time = time.time() - start_time
        
        # Time batch encoding
        start_time = time.time()
        batch_result = encoder.encode_batch_votes(vote_requests)
        batch_time = time.time() - start_time
        
        # Batch should be faster (or at least not significantly slower)
        assert batch_time <= individual_time * 1.5  # Allow some overhead tolerance
        assert batch_result.processing_time_ms > 0

    def test_vote_encoder_caching_improves_performance(self) -> None:
        """Test that caching improves encoding performance for repeated operations."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND, enable_caching=True)
        
        proposal_id = 12345
        support = VoteType.FOR
        
        # First encoding (cache miss)
        import time
        start_time = time.time()
        result1 = encoder.encode_cast_vote(proposal_id, support)
        first_time = time.time() - start_time
        
        # Second encoding (cache hit)
        start_time = time.time()
        result2 = encoder.encode_cast_vote(proposal_id, support)
        second_time = time.time() - start_time
        
        # Cached result should be faster
        assert second_time < first_time
        assert result1.from_cache is False
        assert result2.from_cache is True
        assert result1.encoded_data == result2.encoded_data

    def test_vote_encoder_tracks_performance_metrics(self) -> None:
        """Test that VoteEncoder tracks detailed performance metrics."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Perform some encodings
        encoder.encode_cast_vote(12345, VoteType.FOR)
        encoder.encode_cast_vote(67890, VoteType.AGAINST)
        
        metrics = encoder.get_performance_metrics()
        
        assert metrics is not None
        assert "total_encodings" in metrics
        assert "cache_hit_rate" in metrics
        assert "average_encoding_time_ms" in metrics
        assert metrics["total_encodings"] >= 2

    def test_vote_encoder_handles_concurrent_encoding_requests(self) -> None:
        """Test that VoteEncoder handles concurrent encoding requests safely."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        import concurrent.futures
        
        def encode_vote(proposal_id: int) -> VoteEncodingResult:
            return encoder.encode_cast_vote(proposal_id, VoteType.FOR)
        
        # Submit concurrent encoding requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(encode_vote, proposal_id)
                for proposal_id in range(1, 11)
            ]
            
            results = [future.result() for future in futures]
        
        # All encodings should succeed
        assert len(results) == 10
        assert all(isinstance(result, VoteEncodingResult) for result in results)
        assert all(result.encoded_data.startswith("0x") for result in results)


class TestVoteEncoderEdgeCases:
    """Test VoteEncoder edge cases and boundary conditions."""

    def test_vote_encoder_handles_maximum_proposal_id(self) -> None:
        """Test that VoteEncoder handles maximum proposal ID values."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Test with maximum uint256 value
        max_proposal_id = 2**256 - 1
        result = encoder.encode_cast_vote(max_proposal_id, VoteType.FOR)
        
        assert result.proposal_id == max_proposal_id
        assert result.encoded_data.startswith("0x")

    def test_vote_encoder_handles_unicode_reasons(self) -> None:
        """Test that VoteEncoder handles Unicode characters in vote reasons."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        unicode_reason = "This proposal benefits the community 🚀 with émojis and spëcial chars"
        result = encoder.encode_cast_vote_with_reason(12345, VoteType.FOR, unicode_reason)
        
        assert result.reason == unicode_reason
        assert result.encoded_data.startswith("0x")

    def test_vote_encoder_handles_empty_batch_gracefully(self) -> None:
        """Test that VoteEncoder handles empty batch requests gracefully."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        with pytest.raises(BatchVoteEncodingError, match="Vote requests list cannot be empty"):
            encoder.encode_batch_votes([])

    def test_vote_encoder_handles_memory_pressure_with_large_batches(self) -> None:
        """Test that VoteEncoder handles memory pressure with large batch operations."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Create a large but valid batch (within limits)
        large_batch = [
            {"proposal_id": i, "support": VoteType.FOR}
            for i in range(1, 101)  # 100 votes (at limit)
        ]
        
        result = encoder.encode_batch_votes(large_batch)
        
        assert result.total_count == 100
        assert result.successful_count == 100
        assert len(result.vote_encodings) == 100

    def test_vote_encoder_handles_network_timeouts_gracefully(self) -> None:
        """Test that VoteEncoder handles network timeouts when loading ABIs."""
        
        @pytest.mark.asyncio
        async def test_timeout():
            with patch("httpx.AsyncClient.get", side_effect=asyncio.TimeoutError("Request timeout")):
                with pytest.raises(VoteEncodingError, match="Request timeout"):
                    await VoteEncoder.from_url_async("https://slow-server.com/abi.json")
        
        # Run the async test
        asyncio.run(test_timeout())

    def test_vote_encoder_validates_reason_special_characters(self) -> None:
        """Test that VoteEncoder validates reason strings with special characters."""
        encoder = VoteEncoder(governor_type=GovernorContractType.COMPOUND)
        
        # Test reason with only special characters (should fail)
        special_chars_only = "!@#$%^&*()"
        with pytest.raises(VoteEncodingError, match="Reason must contain meaningful text"):
            encoder.encode_cast_vote_with_reason(12345, VoteType.FOR, special_chars_only)
        
        # Test valid reason with mixed content
        valid_reason = "This proposal is beneficial! It will improve governance by 25%."
        result = encoder.encode_cast_vote_with_reason(12345, VoteType.FOR, valid_reason)
        assert result.reason == valid_reason
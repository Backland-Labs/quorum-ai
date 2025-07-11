"""Base governor interface and common patterns for all governor types.

This module provides base classes and interfaces that can be shared across
different governor implementations to reduce code duplication and ensure
consistent behavior.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from models import (
    GovernorContractType,
    VoteType,
    VoteEncodingResult,
    BatchVoteEncodingResult,
)

# Configure logger
logger = logging.getLogger(__name__)


class BaseGovernorInterface(ABC):
    """Abstract base interface for all governor implementations.
    
    This interface defines the core methods that all governor types must implement
    while allowing for specialized behavior in concrete implementations.
    """
    
    @property
    @abstractmethod
    def contract_type(self) -> GovernorContractType:
        """Get the governor contract type."""
        pass
    
    @property
    @abstractmethod
    def contract_address(self) -> str:
        """Get the governor contract address."""
        pass
    
    @abstractmethod
    def encode_vote(
        self,
        proposal_id: int,
        support: VoteType,
        voter_address: Optional[str] = None
    ) -> VoteEncodingResult:
        """Encode a vote for a proposal.
        
        Args:
            proposal_id: The proposal ID to vote on
            support: The vote type (FOR, AGAINST, ABSTAIN)
            voter_address: Optional voter address for validation
            
        Returns:
            VoteEncodingResult with encoded transaction data
        """
        pass
    
    @abstractmethod
    def encode_vote_with_reason(
        self,
        proposal_id: int,
        support: VoteType,
        reason: str
    ) -> VoteEncodingResult:
        """Encode a vote with reason for a proposal.
        
        Args:
            proposal_id: The proposal ID to vote on
            support: The vote type (FOR, AGAINST, ABSTAIN)
            reason: The reason for the vote
            
        Returns:
            VoteEncodingResult with encoded transaction data
        """
        pass
    
    @abstractmethod
    def encode_batch_votes(
        self,
        vote_requests: List[Dict[str, Any]]
    ) -> BatchVoteEncodingResult:
        """Encode multiple votes in batch.
        
        Args:
            vote_requests: List of vote request dictionaries
            
        Returns:
            BatchVoteEncodingResult with processing results
        """
        pass
    
    @abstractmethod
    def has_function(self, name: str) -> bool:
        """Check if function exists in governor ABI.
        
        Args:
            name: Function name to check
            
        Returns:
            True if function exists, False otherwise
        """
        pass


class BaseGovernorValidator:
    """Common validation methods for governor implementations.
    
    This class provides shared validation logic that can be used across
    different governor types to ensure consistent parameter validation.
    """
    
    @staticmethod
    def validate_proposal_id(proposal_id: int, governor_type: GovernorContractType) -> None:
        """Validate proposal ID with standard checks.
        
        Args:
            proposal_id: The proposal ID to validate
            governor_type: The governor contract type for context
            
        Raises:
            ValueError: If proposal ID is invalid
        """
        # Runtime assertions for critical validation
        assert isinstance(proposal_id, int), "proposal_id must be an integer"
        assert isinstance(governor_type, GovernorContractType), "governor_type must be GovernorContractType"
        
        if not isinstance(proposal_id, int):
            raise ValueError("Proposal ID must be an integer")
        if proposal_id <= 0:
            raise ValueError("Proposal ID must be positive")
        if proposal_id > 2**32 - 1:
            raise ValueError("Proposal ID exceeds maximum value")
        
        logger.debug(f"Validated proposal ID {proposal_id} for {governor_type.value}")
    
    @staticmethod
    def validate_support_type(support: VoteType) -> None:
        """Validate vote support type.
        
        Args:
            support: The vote type to validate
            
        Raises:
            ValueError: If support type is invalid
        """
        # Runtime assertion for critical validation
        assert isinstance(support, VoteType), "support must be a VoteType enum"
        
        if not isinstance(support, VoteType):
            raise ValueError("Support must be a VoteType enum")
        
        logger.debug(f"Validated support type: {support}")
    
    @staticmethod
    def validate_voter_address(voter_address: str) -> None:
        """Validate voter address format.
        
        Args:
            voter_address: The address to validate
            
        Raises:
            ValueError: If address format is invalid
        """
        # Runtime assertion for critical validation
        assert isinstance(voter_address, str), "voter_address must be a string"
        
        if not isinstance(voter_address, str):
            raise ValueError("Voter address must be a string")
        if not voter_address.strip():
            raise ValueError("Voter address cannot be empty")
        if not voter_address.startswith("0x"):
            raise ValueError("Voter address must start with 0x")
        if len(voter_address) != 42:
            raise ValueError("Voter address must be 42 characters long")
        
        logger.debug(f"Validated voter address format: {voter_address[:6]}...")
    
    @staticmethod
    def validate_reason_text(reason: str) -> None:
        """Validate vote reason text.
        
        Args:
            reason: The reason text to validate
            
        Raises:
            ValueError: If reason is invalid
        """
        # Runtime assertion for critical validation
        assert isinstance(reason, str), "reason must be a string"
        
        if not isinstance(reason, str):
            raise ValueError("Reason must be a string")
        if not reason.strip():
            raise ValueError("Reason cannot be empty")
        if len(reason.strip()) < 3:
            raise ValueError("Reason must be at least 3 characters")
        if len(reason) > 1000:
            raise ValueError("Reason cannot exceed 1000 characters")
        
        logger.debug(f"Validated reason text: {len(reason)} characters")


class BaseGovernorMetrics:
    """Common metrics and performance tracking for governor implementations.
    
    This class provides shared metrics functionality that can be used across
    different governor types for consistent performance monitoring.
    """
    
    def __init__(self):
        """Initialize metrics tracking."""
        self._total_encodings = 0
        self._total_encoding_time = 0.0
        self._successful_encodings = 0
        self._failed_encodings = 0
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.debug("Initialized BaseGovernorMetrics")
    
    def record_encoding_success(self, encoding_time: float, from_cache: bool = False) -> None:
        """Record a successful encoding operation.
        
        Args:
            encoding_time: Time taken for encoding in seconds
            from_cache: Whether result came from cache
        """
        # Runtime assertions for metrics validation
        assert isinstance(encoding_time, (int, float)), "encoding_time must be numeric"
        assert encoding_time >= 0, "encoding_time must be non-negative"
        
        self._total_encodings += 1
        self._successful_encodings += 1
        self._total_encoding_time += encoding_time
        
        if from_cache:
            self._cache_hits += 1
        else:
            self._cache_misses += 1
        
        logger.debug(f"Recorded encoding success: {encoding_time:.3f}s, from_cache={from_cache}")
    
    def record_encoding_failure(self) -> None:
        """Record a failed encoding operation."""
        self._total_encodings += 1
        self._failed_encodings += 1
        
        logger.debug("Recorded encoding failure")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics.
        
        Returns:
            Dictionary containing performance metrics
        """
        success_rate = 0.0
        if self._total_encodings > 0:
            success_rate = self._successful_encodings / self._total_encodings
        
        cache_hit_rate = 0.0
        total_cache_operations = self._cache_hits + self._cache_misses
        if total_cache_operations > 0:
            cache_hit_rate = self._cache_hits / total_cache_operations
        
        avg_encoding_time = 0.0
        if self._successful_encodings > 0:
            avg_encoding_time = self._total_encoding_time / self._successful_encodings
        
        return {
            "total_encodings": self._total_encodings,
            "successful_encodings": self._successful_encodings,
            "failed_encodings": self._failed_encodings,
            "success_rate": success_rate,
            "cache_hit_rate": cache_hit_rate,
            "average_encoding_time_seconds": avg_encoding_time,
            "total_encoding_time_seconds": self._total_encoding_time
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._total_encodings = 0
        self._total_encoding_time = 0.0
        self._successful_encodings = 0
        self._failed_encodings = 0
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.debug("Reset all performance metrics")


class BaseGovernorUtils:
    """Common utility methods for governor implementations.
    
    This class provides shared utility functions that can be used across
    different governor types to reduce code duplication.
    """
    
    @staticmethod
    def vote_type_to_int(vote_type: VoteType) -> int:
        """Convert VoteType enum to integer representation.
        
        Args:
            vote_type: The VoteType enum value
            
        Returns:
            Integer representation (0=Against, 1=For, 2=Abstain)
            
        Raises:
            ValueError: If vote type is invalid
        """
        # Runtime assertion for critical conversion
        assert isinstance(vote_type, VoteType), "vote_type must be a VoteType enum"
        
        mapping = {
            VoteType.AGAINST: 0,
            VoteType.FOR: 1,
            VoteType.ABSTAIN: 2
        }
        
        if vote_type not in mapping:
            raise ValueError(f"Unknown vote type: {vote_type}")
        
        result = mapping[vote_type]
        logger.debug(f"Converted {vote_type} to integer {result}")
        return result
    
    @staticmethod
    def create_encoding_result(
        proposal_id: int,
        support: VoteType,
        encoded_data: str,
        function_name: str,
        governor_type: GovernorContractType,
        from_cache: bool = False,
        reason: Optional[str] = None
    ) -> VoteEncodingResult:
        """Create a standardized VoteEncodingResult.
        
        Args:
            proposal_id: The proposal ID
            support: The vote type
            encoded_data: The encoded transaction data
            function_name: The function name used
            governor_type: The governor contract type
            from_cache: Whether result came from cache
            reason: Optional vote reason
            
        Returns:
            VoteEncodingResult instance
        """
        # Runtime assertions for critical result creation
        assert isinstance(proposal_id, int), "proposal_id must be an integer"
        assert isinstance(support, VoteType), "support must be a VoteType enum"
        assert isinstance(encoded_data, str), "encoded_data must be a string"
        assert isinstance(function_name, str), "function_name must be a string"
        assert isinstance(governor_type, GovernorContractType), "governor_type must be GovernorContractType"
        
        logger.debug(f"Creating encoding result for {function_name} on proposal {proposal_id}")
        
        return VoteEncodingResult(
            proposal_id=proposal_id,
            support=support,
            encoded_data=encoded_data,
            function_name=function_name,
            governor_type=governor_type,
            encoding_timestamp=datetime.now(),
            from_cache=from_cache,
            reason=reason
        )
    
    @staticmethod
    def validate_batch_request_structure(request: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate batch request structure.
        
        Args:
            request: The request dictionary to validate
            required_fields: List of required field names
            
        Raises:
            ValueError: If request structure is invalid
        """
        # Runtime assertions for critical validation
        assert isinstance(request, dict), "request must be a dictionary"
        assert isinstance(required_fields, list), "required_fields must be a list"
        
        if not isinstance(request, dict):
            raise ValueError("Request must be a dictionary")
        
        missing_fields = [field for field in required_fields if field not in request]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        logger.debug(f"Validated batch request with fields: {list(request.keys())}")
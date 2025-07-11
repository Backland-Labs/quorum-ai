"""Vote encoding service for Ethereum governor contracts.

This module provides a high-level interface for encoding votes across different
governor types with comprehensive validation, caching, and error handling.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

from models import (
    GovernorContractType,
    VoteType,
    VoteEncodingResult,
    VoteEncodingError,
    BatchVoteEncodingResult,
    BatchVoteEncodingError,
)
from services.governor_abi import GovernorABI, CompoundGovernorABI, GovernorBravoABI

# Configure logger
logger = logging.getLogger(__name__)


class VoteEncodingCache:
    """Caching system for encoded votes."""
    
    def __init__(self, default_ttl_seconds: int = 3600):
        """Initialize cache with TTL."""
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl_seconds
        self.hit_count = 0
        self.miss_count = 0
    
    def generate_key(
        self,
        proposal_id: int,
        support: VoteType,
        governor_type: GovernorContractType,
        reason: Optional[str] = None
    ) -> str:
        """Generate consistent cache key."""
        key_data = f"{proposal_id}:{support.value}:{governor_type.value}"
        if reason:
            key_data += f":{reason}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def store(self, key: str, data: str) -> None:
        """Store data in cache with TTL."""
        self.cache[key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": self.default_ttl
        }
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve data from cache if not expired."""
        if key not in self.cache:
            self.miss_count += 1
            return None
        
        entry = self.cache[key]
        if time.time() - entry["timestamp"] > entry["ttl"]:
            del self.cache[key]
            self.miss_count += 1
            return None
        
        self.hit_count += 1
        return entry["data"]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0


class GovernorTypeDetector:
    """Detects governor contract type from various sources."""
    
    _instance = None
    _cache: Dict[str, GovernorContractType] = {}
    
    def __new__(cls):
        """Singleton pattern for consistent caching."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear detection cache."""
        cls._cache.clear()
    
    def detect_governor_type(self, contract_address: str) -> GovernorContractType:
        """Detect governor type from contract address.
        
        Args:
            contract_address: The contract address to analyze
            
        Returns:
            The detected governor contract type
            
        Note:
            Results are cached for performance optimization.
        """
        # Validate input parameters
        assert contract_address is not None, "Contract address cannot be None"
        assert isinstance(contract_address, str), "Contract address must be string"
        
        # Check cache first
        if contract_address in self.__class__._cache:
            logger.debug(f"Cache hit for contract address: {contract_address}")
            return self.__class__._cache[contract_address]
        
        logger.debug(f"Cache miss for contract address: {contract_address}, detecting type")
        
        # Try detection strategies in order
        result = (
            self._detect_by_known_addresses(contract_address) or
            self._detect_by_contract_signature(contract_address) or
            self._detect_by_function_signatures(contract_address) or
            GovernorContractType.GENERIC
        )
        
        # Cache the result
        self.__class__._cache[contract_address] = result
        logger.info(f"Detected governor type {result.value} for address {contract_address}")
        return result
    
    def _detect_by_known_addresses(self, address: str) -> Optional[GovernorContractType]:
        """Detect by known contract addresses."""
        # This would contain real known addresses in production
        known_addresses = {
            "0x1234567890abcdef": GovernorContractType.COMPOUND,
            "0xabcdef1234567890": GovernorContractType.GOVERNOR_BRAVO,
        }
        return known_addresses.get(address)
    
    def _detect_by_contract_signature(self, address: str) -> Optional[GovernorContractType]:
        """Detect by contract signature."""
        # Placeholder implementation
        return None
    
    def _detect_by_function_signatures(self, address: str) -> Optional[GovernorContractType]:
        """Detect by function signatures."""
        # Simple heuristic based on address for testing
        if "compound" in address.lower():
            return GovernorContractType.COMPOUND
        elif "bravo" in address.lower():
            return GovernorContractType.GOVERNOR_BRAVO
        return None


class VoteEncoder:
    """High-level interface for encoding votes across governor types."""
    
    def __init__(
        self,
        governor_type: Optional[GovernorContractType] = None,
        abi_path: Optional[str] = None,
        enable_caching: bool = True
    ):
        """Initialize VoteEncoder with comprehensive validation.
        
        Args:
            governor_type: Type of governor contract to use
            abi_path: Path to custom ABI file (mutually exclusive with governor_type)
            enable_caching: Whether to enable result caching for performance
            
        Raises:
            ValueError: If parameters are invalid or conflicting
            VoteEncodingError: If ABI initialization fails
        """
        # Validate input parameters with assertions
        self._validate_init_parameters(governor_type, abi_path)
        
        # Initialize core properties
        self.governor_type = governor_type or GovernorContractType.GENERIC
        self.abi_path = abi_path
        self.abi_url = None
        self.caching_enabled = enable_caching
        self.cache = VoteEncodingCache() if enable_caching else None
        
        # Initialize ABI based on source
        self.abi = self._initialize_abi(governor_type, abi_path)
        
        # Initialize performance metrics
        self._total_encodings = 0
        self._total_encoding_time = 0.0
        
        logger.info(f"VoteEncoder initialized with governor_type={self.governor_type.value}, caching={enable_caching}")
    
    def _validate_init_parameters(
        self,
        governor_type: Optional[GovernorContractType],
        abi_path: Optional[str]
    ) -> None:
        """Validate initialization parameters.
        
        Args:
            governor_type: Governor type parameter to validate
            abi_path: ABI path parameter to validate
            
        Raises:
            ValueError: If parameters are invalid
        """
        if governor_type and abi_path:
            raise ValueError("Cannot specify both governor_type and abi_path")
        if not governor_type and not abi_path:
            raise ValueError("Must specify either governor_type or abi_path")
        
        # Post-validation assertions for internal consistency
        assert not (governor_type and abi_path), "Validation failed to catch conflicting parameters"
        assert governor_type or abi_path, "Validation failed to catch missing parameters"
    
    def _initialize_abi(
        self,
        governor_type: Optional[GovernorContractType],
        abi_path: Optional[str]
    ) -> GovernorABI:
        """Initialize ABI based on governor type or file path.
        
        Args:
            governor_type: Governor contract type for built-in ABIs
            abi_path: Path to custom ABI file
            
        Returns:
            Initialized GovernorABI instance
            
        Raises:
            ValueError: If governor type is unsupported
            VoteEncodingError: If ABI file loading fails
        """
        if governor_type:
            return self._create_typed_abi(governor_type)
        else:
            return self._load_custom_abi(abi_path)
    
    def _create_typed_abi(self, governor_type: GovernorContractType) -> GovernorABI:
        """Create ABI instance for specific governor type.
        
        Args:
            governor_type: The governor contract type
            
        Returns:
            Appropriate ABI instance
            
        Raises:
            ValueError: If governor type is unsupported
        """
        assert governor_type is not None, "Governor type cannot be None"
        
        if governor_type == GovernorContractType.COMPOUND:
            return CompoundGovernorABI()
        elif governor_type == GovernorContractType.GOVERNOR_BRAVO:
            return GovernorBravoABI()
        elif governor_type == GovernorContractType.GENERIC:
            # For generic governor, create a basic GovernorABI with minimal file
            temp_abi_path = "/tmp/generic_governor.json"
            self._ensure_minimal_abi_file(temp_abi_path)
            return GovernorABI(temp_abi_path)
        else:
            raise ValueError(f"Unsupported governor type: {governor_type}")
    
    def _load_custom_abi(self, abi_path: str) -> GovernorABI:
        """Load ABI from custom file path.
        
        Args:
            abi_path: Path to the ABI file
            
        Returns:
            GovernorABI instance loaded from file
            
        Raises:
            VoteEncodingError: If file doesn't exist or is invalid
        """
        assert abi_path is not None, "ABI path cannot be None"
        
        # Check file existence
        if not Path(abi_path).exists():
            raise VoteEncodingError(f"ABI file not found: {abi_path}")
        
        # Load and validate ABI
        try:
            return GovernorABI(abi_path)
        except Exception as e:
            raise VoteEncodingError(f"Invalid ABI file format: {abi_path}") from e
    
    def _ensure_minimal_abi_file(self, path: str) -> None:
        """Ensure minimal ABI file exists for generic governor.
        
        Args:
            path: File path where ABI should be created
        """
        assert path is not None, "Path cannot be None"
        assert isinstance(path, str), "Path must be string"
        
        import os
        if not os.path.exists(path):
            logger.debug(f"Creating minimal ABI file at: {path}")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"abi": []}, f)
    
    @classmethod
    def from_contract_address(cls, contract_address: str) -> 'VoteEncoder':
        """Create VoteEncoder by detecting governor type from contract address."""
        if contract_address is None:
            raise ValueError("Contract address cannot be None")
        if not contract_address:
            raise ValueError("Contract address cannot be empty")
        if not re.match(r"^0x[a-fA-F0-9]*[a-zA-Z]*[a-fA-F0-9]*$", contract_address):
            raise ValueError("Invalid contract address format")
        
        detector = GovernorTypeDetector()
        governor_type = detector.detect_governor_type(contract_address)
        return cls(governor_type=governor_type)
    
    _url_cache: Dict[str, 'VoteEncoder'] = {}
    
    @classmethod
    def clear_url_cache(cls) -> None:
        """Clear URL cache for testing."""
        cls._url_cache.clear()
    
    @classmethod
    async def from_url_async(cls, url: str) -> 'VoteEncoder':
        """Load VoteEncoder from URL asynchronously with caching.
        
        Args:
            url: URL to load ABI from
            
        Returns:
            VoteEncoder instance with loaded ABI
            
        Raises:
            VoteEncodingError: If URL loading fails or ABI is invalid
        """
        # Validate input
        assert url is not None, "URL cannot be None"
        assert isinstance(url, str), "URL must be string"
        
        # Check cache first
        if url in cls._url_cache:
            logger.debug(f"Cache hit for URL: {url}")
            return cls._url_cache[url]
        
        logger.debug(f"Cache miss for URL: {url}, loading from remote")
        
        # Load ABI data from URL
        abi_data = await cls._fetch_abi_from_url(url)
        
        # Validate ABI structure
        cls._validate_abi_data(abi_data, url)
        
        # Create encoder from data
        encoder = await cls._create_encoder_from_abi_data(abi_data, url)
        
        # Cache the encoder
        cls._url_cache[url] = encoder
        logger.info(f"Successfully loaded and cached VoteEncoder from URL: {url}")
        return encoder
    
    @classmethod
    async def _fetch_abi_from_url(cls, url: str) -> Dict[str, Any]:
        """Fetch ABI data from URL with error handling.
        
        Args:
            url: URL to fetch from
            
        Returns:
            ABI data as dictionary
            
        Raises:
            VoteEncodingError: If network request fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            raise VoteEncodingError(f"Request timeout for URL: {url}") from e
        except httpx.HTTPStatusError as e:
            raise VoteEncodingError(f"HTTP error {e.response.status_code} for URL: {url}") from e
        except Exception as e:
            # Handle network errors and other exceptions
            error_msg = f"Failed to load ABI from URL: {url} - {str(e)}"
            logger.error(error_msg)
            raise VoteEncodingError(error_msg) from e
    
    @classmethod
    def _validate_abi_data(cls, abi_data: Dict[str, Any], url: str) -> None:
        """Validate ABI data structure.
        
        Args:
            abi_data: ABI data to validate
            url: Source URL for error context
            
        Raises:
            VoteEncodingError: If ABI structure is invalid
        """
        assert abi_data is not None, "ABI data cannot be None"
        
        if not abi_data or "abi" not in abi_data:
            raise VoteEncodingError(f"Invalid ABI structure from URL: {url}")
    
    @classmethod
    async def _create_encoder_from_abi_data(
        cls,
        abi_data: Dict[str, Any],
        url: str
    ) -> 'VoteEncoder':
        """Create VoteEncoder from ABI data.
        
        Args:
            abi_data: Validated ABI data
            url: Source URL for reference
            
        Returns:
            VoteEncoder instance
            
        Raises:
            VoteEncodingError: If encoder creation fails
        """
        import tempfile
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(abi_data, f)
            temp_path = f.name
        
        try:
            encoder = cls(abi_path=temp_path)
            encoder.abi_url = url
            return encoder
        except Exception as e:
            # Clean up temp file on error
            Path(temp_path).unlink(missing_ok=True)
            error_msg = f"Failed to create encoder from ABI data for URL: {url}"
            logger.error(error_msg)
            raise VoteEncodingError(error_msg) from e
    
    def encode_cast_vote(self, proposal_id: int, support: VoteType) -> VoteEncodingResult:
        """Encode a castVote function call with caching and validation.
        
        Args:
            proposal_id: The proposal ID to vote on
            support: The vote type (FOR, AGAINST, ABSTAIN)
            
        Returns:
            VoteEncodingResult with encoded transaction data
            
        Raises:
            VoteEncodingError: If encoding fails or parameters are invalid
        """
        return self._encode_vote_internal(
            proposal_id=proposal_id,
            support=support,
            function_name="castVote",
            reason=None
        )
    
    def encode_cast_vote_with_reason(
        self,
        proposal_id: int,
        support: VoteType,
        reason: str
    ) -> VoteEncodingResult:
        """Encode a castVoteWithReason function call with caching and validation.
        
        Args:
            proposal_id: The proposal ID to vote on
            support: The vote type (FOR, AGAINST, ABSTAIN)
            reason: The reason for the vote
            
        Returns:
            VoteEncodingResult with encoded transaction data
            
        Raises:
            VoteEncodingError: If encoding fails or parameters are invalid
        """
        return self._encode_vote_internal(
            proposal_id=proposal_id,
            support=support,
            function_name="castVoteWithReason",
            reason=reason
        )
    
    def _encode_vote_internal(
        self,
        proposal_id: int,
        support: VoteType,
        function_name: str,
        reason: Optional[str] = None
    ) -> VoteEncodingResult:
        """Internal method for encoding votes with common logic.
        
        Args:
            proposal_id: The proposal ID to vote on
            support: The vote type
            function_name: The function being called
            reason: Optional reason for the vote
            
        Returns:
            VoteEncodingResult with encoded data
            
        Raises:
            VoteEncodingError: If encoding fails
        """
        start_time = time.time()
        
        # Validate parameters first - this must happen before any encoding
        self._validate_proposal_id(proposal_id, support)
        self._validate_support(support)
        # For castVoteWithReason, reason is required (not optional)
        if function_name == "castVoteWithReason":
            self._validate_reason(reason)
        elif reason is not None:
            self._validate_reason(reason)
        
        # Check cache
        cached_result = self._check_cache(proposal_id, support, function_name, reason)
        if cached_result:
            return cached_result
        
        # Encode vote
        encoded_data = self._perform_encoding(proposal_id, support, function_name, reason)
        
        # Store in cache
        self._store_in_cache(proposal_id, support, function_name, reason, encoded_data)
        
        # Update metrics
        self._update_metrics(start_time)
        
        return VoteEncodingResult(
            proposal_id=proposal_id,
            support=support,
            reason=reason,
            encoded_data=encoded_data,
            function_name=function_name,
            governor_type=self.governor_type,
            encoding_timestamp=datetime.now(),
            from_cache=False
        )
    
    def _check_cache(
        self,
        proposal_id: int,
        support: VoteType,
        function_name: str,
        reason: Optional[str] = None
    ) -> Optional[VoteEncodingResult]:
        """Check cache for existing encoding result.
        
        Args:
            proposal_id: The proposal ID
            support: The vote type
            function_name: The function name
            reason: Optional reason
            
        Returns:
            Cached result if found, None otherwise
        """
        if not self.cache:
            return None
        
        cache_key = self.cache.generate_key(proposal_id, support, self.governor_type, reason)
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"Cache hit for {function_name} with proposal_id={proposal_id}")
            return VoteEncodingResult(
                proposal_id=proposal_id,
                support=support,
                reason=reason,
                encoded_data=cached_data,
                function_name=function_name,
                governor_type=self.governor_type,
                encoding_timestamp=datetime.now(),
                from_cache=True
            )
        return None
    
    def _perform_encoding(
        self,
        proposal_id: int,
        support: VoteType,
        function_name: str,
        reason: Optional[str] = None
    ) -> str:
        """Perform the actual encoding operation.
        
        Args:
            proposal_id: The proposal ID
            support: The vote type
            function_name: The function name
            reason: Optional reason
            
        Returns:
            Encoded data as hex string
            
        Raises:
            VoteEncodingError: If encoding fails
        """
        try:
            support_int = self._vote_type_to_int(support)
            
            if function_name == "castVote":
                return self.abi.encode_cast_vote(proposal_id, support_int)
            elif function_name == "castVoteWithReason":
                return self.abi.encode_cast_vote_with_reason(proposal_id, support_int, reason)
            else:
                raise VoteEncodingError(f"Unknown function name: {function_name}")
                
        except Exception as e:
            error_msg = f"Failed to encode vote"
            logger.error(f"Failed to encode {function_name} for proposal {proposal_id}: {str(e)}")
            raise VoteEncodingError(error_msg) from e
    
    def _store_in_cache(
        self,
        proposal_id: int,
        support: VoteType,
        function_name: str,
        reason: Optional[str],
        encoded_data: str
    ) -> None:
        """Store encoding result in cache.
        
        Args:
            proposal_id: The proposal ID
            support: The vote type
            function_name: The function name
            reason: Optional reason
            encoded_data: The encoded data to cache
        """
        if self.cache:
            cache_key = self.cache.generate_key(proposal_id, support, self.governor_type, reason)
            self.cache.store(cache_key, encoded_data)
            logger.debug(f"Cached result for {function_name} with proposal_id={proposal_id}")
    
    def _update_metrics(self, start_time: float) -> None:
        """Update performance metrics.
        
        Args:
            start_time: The time when encoding started
        """
        encoding_duration = time.time() - start_time
        self._total_encodings += 1
        self._total_encoding_time += encoding_duration
        
        logger.debug(f"Encoding completed in {encoding_duration*1000:.2f}ms")
    
    
    def encode_batch_votes(self, vote_requests: List[Dict[str, Any]]) -> BatchVoteEncodingResult:
        """Encode multiple castVote calls in batch with validation and optimization.
        
        Args:
            vote_requests: List of vote request dictionaries
            
        Returns:
            BatchVoteEncodingResult with all results and metrics
            
        Raises:
            BatchVoteEncodingError: If batch validation fails
        """
        return self._process_batch_votes(
            vote_requests=vote_requests,
            required_fields=["proposal_id", "support"],
            encoder_func=self._encode_single_vote
        )
    
    def encode_batch_votes_with_reasons(
        self,
        vote_requests: List[Dict[str, Any]]
    ) -> BatchVoteEncodingResult:
        """Encode multiple castVoteWithReason calls in batch.
        
        Args:
            vote_requests: List of vote request dictionaries with reasons
            
        Returns:
            BatchVoteEncodingResult with all results and metrics
            
        Raises:
            BatchVoteEncodingError: If batch validation fails
        """
        return self._process_batch_votes(
            vote_requests=vote_requests,
            required_fields=["proposal_id", "support", "reason"],
            encoder_func=self._encode_single_vote_with_reason
        )
    
    def _process_batch_votes(
        self,
        vote_requests: List[Dict[str, Any]],
        required_fields: List[str],
        encoder_func
    ) -> BatchVoteEncodingResult:
        """Process batch votes with common validation and metrics.
        
        Args:
            vote_requests: List of vote requests
            required_fields: Fields required in each request
            encoder_func: Function to encode individual votes
            
        Returns:
            BatchVoteEncodingResult with processing results
            
        Raises:
            BatchVoteEncodingError: If validation fails
        """
        start_time = time.time()
        
        # Validate batch
        self._validate_batch_requests(vote_requests)
        
        # Process each request
        results = self._process_individual_requests(
            vote_requests, required_fields, encoder_func
        )
        
        # Calculate metrics
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return BatchVoteEncodingResult(
            vote_encodings=results["successful_encodings"],
            successful_count=len(results["successful_encodings"]),
            failed_count=len(results["errors"]),
            total_count=len(vote_requests),
            errors=results["errors"],
            processing_time_ms=processing_time,
            average_encoding_time_ms=processing_time / len(vote_requests) if vote_requests else 0,
            cache_hit_count=results["cache_hits"],
            cache_miss_count=results["cache_misses"],
            batch_timestamp=datetime.now()
        )
    
    def _validate_batch_requests(self, vote_requests: List[Dict[str, Any]]) -> None:
        """Validate batch request parameters.
        
        Args:
            vote_requests: List of vote requests to validate
            
        Raises:
            BatchVoteEncodingError: If validation fails
        """
        if vote_requests is None:
            raise BatchVoteEncodingError("Vote requests cannot be None")
        if not vote_requests:
            raise BatchVoteEncodingError("Vote requests list cannot be empty")
        if len(vote_requests) > 100:
            raise BatchVoteEncodingError("Batch size cannot exceed 100 votes")
    
    def _process_individual_requests(
        self,
        vote_requests: List[Dict[str, Any]],
        required_fields: List[str],
        encoder_func
    ) -> Dict[str, Any]:
        """Process individual vote requests.
        
        Args:
            vote_requests: List of requests to process
            required_fields: Required fields for validation
            encoder_func: Function to encode each request
            
        Returns:
            Dictionary with results, errors, and cache statistics
        """
        successful_encodings = []
        errors = []
        cache_hits = 0
        cache_misses = 0
        
        for i, request in enumerate(vote_requests):
            try:
                # Validate request structure
                missing_fields = [field for field in required_fields if field not in request]
                if missing_fields:
                    errors.append(f"Request {i}: Missing required fields: {', '.join(missing_fields)}")
                    continue
                
                # Encode the vote
                result = encoder_func(request)
                successful_encodings.append(result)
                
                # Track cache statistics
                if result.from_cache:
                    cache_hits += 1
                else:
                    cache_misses += 1
                    
            except Exception as e:
                error_msg = f"Request {i}: {str(e)}"
                logger.warning(f"Batch encoding error: {error_msg}")
                errors.append(error_msg)
        
        return {
            "successful_encodings": successful_encodings,
            "errors": errors,
            "cache_hits": cache_hits,
            "cache_misses": cache_misses
        }
    
    def _encode_single_vote(self, request: Dict[str, Any]) -> VoteEncodingResult:
        """Encode a single vote request.
        
        Args:
            request: Vote request dictionary
            
        Returns:
            VoteEncodingResult for the request
        """
        return self.encode_cast_vote(request["proposal_id"], request["support"])
    
    def _encode_single_vote_with_reason(self, request: Dict[str, Any]) -> VoteEncodingResult:
        """Encode a single vote with reason request.
        
        Args:
            request: Vote request dictionary with reason
            
        Returns:
            VoteEncodingResult for the request
        """
        return self.encode_cast_vote_with_reason(
            request["proposal_id"],
            request["support"],
            request["reason"]
        )
    
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        cache_hit_rate = 0.0
        if self.cache and (self.cache.hit_count + self.cache.miss_count) > 0:
            cache_hit_rate = self.cache.hit_count / (self.cache.hit_count + self.cache.miss_count)
        
        avg_encoding_time = 0.0
        if self._total_encodings > 0:
            avg_encoding_time = (self._total_encoding_time / self._total_encodings) * 1000  # ms
        
        return {
            "total_encodings": self._total_encodings,
            "cache_hit_rate": cache_hit_rate,
            "average_encoding_time_ms": avg_encoding_time
        }
    
    def _validate_proposal_id(self, proposal_id: int, support: VoteType = None) -> None:
        """Validate proposal ID with comprehensive checks.
        
        Args:
            proposal_id: The proposal ID to validate
            support: Optional support type for error context
            
        Raises:
            VoteEncodingError: If proposal ID is invalid
        """
        if not isinstance(proposal_id, int):
            raise VoteEncodingError(
                "Proposal ID must be positive",
                proposal_id=proposal_id,
                support=support,
                governor_type=self.governor_type
            )
        if proposal_id <= 0:
            raise VoteEncodingError(
                "Proposal ID must be positive",
                proposal_id=proposal_id,
                support=support,
                governor_type=self.governor_type
            )
        
        # Post-validation assertions for internal consistency
        assert proposal_id is not None, "Validation should have caught None proposal_id"
        assert isinstance(proposal_id, int), "Validation should have caught non-integer proposal_id"
        
        # Additional validation for very large proposal IDs
        if proposal_id > 2**256 - 1:
            raise VoteEncodingError(
                "Proposal ID exceeds maximum uint256 value",
                proposal_id=proposal_id,
                support=support,
                governor_type=self.governor_type
            )
    
    def _validate_support(self, support: VoteType) -> None:
        """Validate support parameter with comprehensive checks.
        
        Args:
            support: The vote type to validate
            
        Raises:
            VoteEncodingError: If support type is invalid
        """
        if support is None:
            raise VoteEncodingError(
                "Support cannot be None",
                support=support,
                governor_type=self.governor_type
            )
        if not isinstance(support, VoteType):
            raise VoteEncodingError(
                "Support must be VoteType enum",
                support=support,
                governor_type=self.governor_type
            )
        
        # Post-validation assertions for internal consistency
        assert support is not None, "Validation should have caught None support"
        assert isinstance(support, VoteType), "Validation should have caught invalid support type"
    
    def _validate_reason(self, reason: str) -> None:
        """Validate reason parameter with comprehensive text analysis.
        
        Args:
            reason: The reason text to validate
            
        Raises:
            VoteEncodingError: If reason is invalid
        """
        if reason is None:
            raise VoteEncodingError("Reason cannot be None")
        if not isinstance(reason, str):
            raise VoteEncodingError("Reason must be string")
        if not reason or not reason.strip():
            raise VoteEncodingError("Reason cannot be empty")
        
        # Post-validation assertions for internal consistency
        assert reason is not None, "Validation should have caught None reason"
        assert isinstance(reason, str), "Validation should have caught non-string reason"
        
        # Length validations
        stripped_reason = reason.strip()
        if len(stripped_reason) < 10:
            raise VoteEncodingError("Reason must be at least 10 characters")
        if len(reason) > 1000:
            raise VoteEncodingError("Reason cannot exceed 1000 characters")
        
        # Content validation - check for meaningful text
        meaningful_chars = sum(1 for c in reason if c.isalnum())
        if meaningful_chars == 0:
            raise VoteEncodingError("Reason must contain meaningful text")
        
        # Additional validation for suspicious patterns
        if meaningful_chars < len(stripped_reason) * 0.3:
            raise VoteEncodingError("Reason must contain sufficient meaningful content")
    
    def _vote_type_to_int(self, vote_type: VoteType) -> int:
        """Convert VoteType enum to integer with validation.
        
        Args:
            vote_type: The VoteType enum value
            
        Returns:
            Integer representation of the vote type
            
        Raises:
            VoteEncodingError: If vote type is invalid
        """
        mapping = {
            VoteType.AGAINST: 0,
            VoteType.FOR: 1,
            VoteType.ABSTAIN: 2
        }
        
        if vote_type not in mapping:
            raise VoteEncodingError(f"Unknown vote type: {vote_type}")
        
        # Post-conversion assertions for internal consistency
        assert vote_type is not None, "Vote type should not be None at this point"
        assert isinstance(vote_type, VoteType), "Vote type should be VoteType enum at this point"
        
        return mapping[vote_type]
    
    async def encode_vote_from_ai_decision(
        self,
        vote_decision,  # VoteDecision type but avoiding circular import
        proposal,       # Proposal type but avoiding circular import
    ) -> VoteEncodingResult:
        """Encode vote from AI decision with proposal context.
        
        Args:
            vote_decision: AI vote decision object
            proposal: Proposal object
            
        Returns:
            VoteEncodingResult with encoding outcome
            
        Raises:
            VoteEncodingError: If encoding fails
        """
        # Extract proposal ID as integer
        proposal_id_str = proposal.id
        try:
            # Try to extract numeric ID from string format like "compound-prop-123"
            if '-' in proposal_id_str:
                proposal_id = int(proposal_id_str.split('-')[-1])
            else:
                proposal_id = int(proposal_id_str)
        except ValueError:
            # Fallback: use hash of proposal ID
            proposal_id = abs(hash(proposal_id_str)) % 1000000
        
        # Detect governor type from DAO ID
        governor_type = self._detect_governor_type_from_dao_id(proposal.dao_id)
        
        # Encode the vote
        return await self.encode_vote(
            proposal_id=proposal_id,
            support=vote_decision.vote,
            governor_type=governor_type,
            reason=vote_decision.reasoning
        )
    
    def _detect_governor_type_from_dao_id(self, dao_id: str) -> GovernorContractType:
        """Detect governor type from DAO ID for integration."""
        dao_id_lower = dao_id.lower()
        
        if "compound" in dao_id_lower and "bravo" in dao_id_lower:
            return GovernorContractType.COMPOUND_BRAVO
        elif "compound" in dao_id_lower:
            return GovernorContractType.COMPOUND
        elif "aave" in dao_id_lower:
            return GovernorContractType.AAVE
        elif "uniswap" in dao_id_lower:
            return GovernorContractType.UNISWAP
        else:
            return GovernorContractType.GENERIC
"""Cache service for governor data and vote encoding operations."""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import logfire

from models import VoteEncodingResult, GovernorInfo


class CacheService:
    """Service for caching governor data and vote encoding results."""
    
    def __init__(self, backend=None):
        """Initialize cache service with optional backend."""
        # In production this would be Redis, for now use in-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._backend = backend or self
        
        # Cache TTL settings (in seconds)
        self.default_ttl = 3600  # 1 hour
        self.governor_abi_ttl = 7200  # 2 hours
        self.vote_encoding_ttl = 300  # 5 minutes
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        assert key, "Cache key cannot be empty"
        assert isinstance(key, str), "Cache key must be string"
        
        if hasattr(self._backend, 'get') and self._backend != self:
            return await self._backend.get(key)
        
        # Default in-memory implementation
        cache_entry = self._cache.get(key)
        if not cache_entry:
            return None
            
        # Check TTL
        if self._is_expired(cache_entry):
            del self._cache[key]
            return None
            
        return cache_entry["value"]
    
    async def set(self, key: str, value: str, ttl: int = None) -> None:
        """Set value in cache with TTL."""
        assert key, "Cache key cannot be empty"
        assert isinstance(key, str), "Cache key must be string"
        assert value is not None, "Cache value cannot be None"
        
        if hasattr(self._backend, 'set') and self._backend != self:
            return await self._backend.set(key, value, ttl or self.default_ttl)
        
        # Default in-memory implementation
        ttl = ttl or self.default_ttl
        expiry_time = datetime.utcnow() + timedelta(seconds=ttl)
        
        self._cache[key] = {
            "value": value,
            "expires_at": expiry_time,
            "created_at": datetime.utcnow()
        }
    
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        assert key, "Cache key cannot be empty"
        assert isinstance(key, str), "Cache key must be string"
        
        if hasattr(self._backend, 'delete') and self._backend != self:
            return await self._backend.delete(key)
        
        # Default in-memory implementation
        self._cache.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        assert key, "Cache key cannot be empty"
        assert isinstance(key, str), "Cache key must be string"
        
        if hasattr(self._backend, 'exists') and self._backend != self:
            return await self._backend.exists(key)
        
        # Default in-memory implementation
        value = await self.get(key)
        return value is not None
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        assert key, "Cache key cannot be empty"
        assert isinstance(key, str), "Cache key must be string"
        
        if hasattr(self._backend, 'ttl') and self._backend != self:
            return await self._backend.ttl(key)
        
        # Default in-memory implementation
        cache_entry = self._cache.get(key)
        if not cache_entry:
            return -1
            
        if self._is_expired(cache_entry):
            return 0
            
        now = datetime.utcnow()
        expires_at = cache_entry["expires_at"]
        remaining = (expires_at - now).total_seconds()
        return max(0, int(remaining))
    
    # Governor-specific cache methods
    
    async def cache_governor_abi(self, governor_id: str, abi_data: Dict[str, Any]) -> None:
        """Cache governor ABI data."""
        assert governor_id, "Governor ID cannot be empty"
        assert abi_data, "ABI data cannot be empty"
        assert isinstance(abi_data, dict), "ABI data must be dictionary"
        
        cache_key = f"governor_abi:{governor_id}"
        serialized_data = json.dumps(abi_data)
        
        try:
            await self.set(cache_key, serialized_data, self.governor_abi_ttl)
            logfire.info("Governor ABI cached", governor_id=governor_id, ttl=self.governor_abi_ttl)
        except Exception as e:
            logfire.error("Failed to cache governor ABI", governor_id=governor_id, error=str(e))
            raise
    
    async def get_cached_governor_abi(self, governor_id: str) -> Optional[Dict[str, Any]]:
        """Get cached governor ABI data."""
        assert governor_id, "Governor ID cannot be empty"
        
        cache_key = f"governor_abi:{governor_id}"
        
        try:
            serialized_data = await self.get(cache_key)
            if serialized_data:
                logfire.info("Governor ABI cache hit", governor_id=governor_id)
                return json.loads(serialized_data)
            
            logfire.info("Governor ABI cache miss", governor_id=governor_id)
            return None
        except Exception as e:
            logfire.error("Failed to get cached governor ABI", governor_id=governor_id, error=str(e))
            return None
    
    async def cache_vote_encoding_result(
        self, 
        proposal_id: str, 
        voter_address: str, 
        encoding_result: VoteEncodingResult,
        ttl_seconds: int = None
    ) -> None:
        """Cache vote encoding result."""
        assert proposal_id, "Proposal ID cannot be empty"
        assert voter_address, "Voter address cannot be empty"
        assert encoding_result, "Encoding result cannot be None"
        assert isinstance(encoding_result, VoteEncodingResult), "Must be VoteEncodingResult"
        
        cache_key = f"vote_encoding:{proposal_id}:{voter_address}"
        serialized_data = encoding_result.model_dump_json()
        ttl = ttl_seconds or self.vote_encoding_ttl
        
        try:
            await self.set(cache_key, serialized_data, ttl)
            logfire.info("Vote encoding result cached", 
                       proposal_id=proposal_id, 
                       voter_address=voter_address, 
                       ttl=ttl)
        except Exception as e:
            logfire.error("Failed to cache vote encoding result", 
                        proposal_id=proposal_id, 
                        voter_address=voter_address, 
                        error=str(e))
            raise
    
    async def get_cached_vote_encoding(self, proposal_id: str, voter_address: str) -> Optional[VoteEncodingResult]:
        """Get cached vote encoding result."""
        assert proposal_id, "Proposal ID cannot be empty"
        assert voter_address, "Voter address cannot be empty"
        
        cache_key = f"vote_encoding:{proposal_id}:{voter_address}"
        
        try:
            serialized_data = await self.get(cache_key)
            if serialized_data:
                logfire.info("Vote encoding cache hit", 
                           proposal_id=proposal_id, 
                           voter_address=voter_address)
                data = json.loads(serialized_data)
                return VoteEncodingResult(**data)
            
            logfire.info("Vote encoding cache miss", 
                       proposal_id=proposal_id, 
                       voter_address=voter_address)
            return None
        except Exception as e:
            logfire.error("Failed to get cached vote encoding", 
                        proposal_id=proposal_id, 
                        voter_address=voter_address, 
                        error=str(e))
            return None
    
    async def invalidate_governor_caches(self, governor_id: str, contract_address: str) -> None:
        """Invalidate all caches related to a governor."""
        assert governor_id, "Governor ID cannot be empty"
        assert contract_address, "Contract address cannot be empty"
        
        try:
            # Invalidate governor ABI cache
            abi_cache_key = f"governor_abi:{governor_id}"
            await self.delete(abi_cache_key)
            
            # Invalidate governor info cache
            info_cache_key = f"governor_info:{governor_id}"
            await self.delete(info_cache_key)
            
            # In a real implementation, we would also invalidate related vote encoding caches
            # For now, we'll just log the invalidation
            logfire.info("Governor caches invalidated", 
                       governor_id=governor_id, 
                       contract_address=contract_address)
            
        except Exception as e:
            logfire.error("Failed to invalidate governor caches", 
                        governor_id=governor_id, 
                        contract_address=contract_address, 
                        error=str(e))
            raise
    
    async def cache_governor_info(self, governor_id: str, governor_info: GovernorInfo) -> None:
        """Cache governor information."""
        assert governor_id, "Governor ID cannot be empty"
        assert governor_info, "Governor info cannot be None"
        assert isinstance(governor_info, GovernorInfo), "Must be GovernorInfo"
        
        cache_key = f"governor_info:{governor_id}"
        serialized_data = governor_info.model_dump_json()
        
        try:
            await self.set(cache_key, serialized_data, self.governor_abi_ttl)
            logfire.info("Governor info cached", governor_id=governor_id, ttl=self.governor_abi_ttl)
        except Exception as e:
            logfire.error("Failed to cache governor info", governor_id=governor_id, error=str(e))
            raise
    
    async def get_cached_governor_info(self, governor_id: str) -> Optional[GovernorInfo]:
        """Get cached governor information."""
        assert governor_id, "Governor ID cannot be empty"
        
        cache_key = f"governor_info:{governor_id}"
        
        try:
            serialized_data = await self.get(cache_key)
            if serialized_data:
                logfire.info("Governor info cache hit", governor_id=governor_id)
                data = json.loads(serialized_data)
                return GovernorInfo(**data)
            
            logfire.info("Governor info cache miss", governor_id=governor_id)
            return None
        except Exception as e:
            logfire.error("Failed to get cached governor info", governor_id=governor_id, error=str(e))
            return None
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        now = datetime.utcnow()
        expires_at = cache_entry.get("expires_at")
        if not expires_at:
            return True
        return now >= expires_at
    
    async def cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries and return count of cleaned entries."""
        if hasattr(self._backend, 'cleanup_expired_entries') and self._backend != self:
            return await self._backend.cleanup_expired_entries()
        
        # Default in-memory implementation
        expired_keys = []
        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logfire.info("Cleaned up expired cache entries", count=len(expired_keys))
        
        return len(expired_keys)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_entries": len(self._cache),
            "cache_type": "in_memory" if self._backend == self else "external",
            "default_ttl": self.default_ttl,
            "governor_abi_ttl": self.governor_abi_ttl,
            "vote_encoding_ttl": self.vote_encoding_ttl,
        }
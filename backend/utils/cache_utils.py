"""Cache utility functions for generating cache keys and handling serialization."""

import hashlib
import json
import logging
from typing import Any, Dict, List, Tuple, Union
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def generate_cache_key(
    method_name: str, 
    args: Tuple[Any, ...], 
    kwargs: Dict[str, Any]
) -> str:
    """Generate a deterministic cache key from method name and parameters.
    
    Args:
        method_name: Name of the method being cached
        args: Positional arguments passed to the method
        kwargs: Keyword arguments passed to the method
        
    Returns:
        Deterministic cache key string
    """
    key_parts = [method_name]
    readable_parts = []
    
    # Process positional arguments
    for arg in args:
        if arg is None:
            key_parts.append("None")
            readable_parts.append("None")
        elif isinstance(arg, BaseModel):
            # For Pydantic models, use their JSON representation for hashing
            key_parts.append(arg.model_dump_json())
            # But include ID for readability if available
            if hasattr(arg, 'id'):
                readable_parts.append(str(arg.id))
            else:
                readable_parts.append(arg.__class__.__name__)
        else:
            arg_str = str(arg)
            key_parts.append(arg_str)
            readable_parts.append(arg_str)
    
    # Process keyword arguments in sorted order for deterministic output
    sorted_kwargs = sorted(kwargs.items())
    for key, value in sorted_kwargs:
        if value is None:
            key_parts.append(f"{key}:None")
            readable_parts.append(f"{key}:None")
        elif isinstance(value, BaseModel):
            key_parts.append(f"{key}:{value.model_dump_json()}")
            if hasattr(value, 'id'):
                readable_parts.append(f"{key}:{value.id}")
            else:
                readable_parts.append(f"{key}:{value.__class__.__name__}")
        else:
            value_str = str(value)
            key_parts.append(f"{key}:{value_str}")
            readable_parts.append(f"{key}:{value_str}")
    
    # Create a hash of the combined key parts for consistency
    key_string = ":".join(key_parts)
    key_hash = hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:8]
    
    # Combine readable parts with hash for debugging and uniqueness
    readable_part = ":".join(readable_parts) if readable_parts else "noargs"
    return f"cache:{method_name}:{readable_part}:{key_hash}"


def serialize_for_cache(data: Any) -> str:
    """Serialize data for storage in cache, handling Pydantic models.
    
    Args:
        data: Data to serialize (can be simple types, Pydantic models, lists, dicts)
        
    Returns:
        JSON string representation of the data
        
    Raises:
        TypeError: If data contains non-serializable objects
    """
    def convert_for_json(obj: Any) -> Any:
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        elif isinstance(obj, list):
            return [convert_for_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: convert_for_json(value) for key, value in obj.items()}
        elif callable(obj) and not isinstance(obj, type):
            # Reject callable objects like functions/lambdas
            raise TypeError(f"Cannot serialize callable object: {obj}")
        elif hasattr(obj, '__dict__'):
            # Handle objects with attributes by checking for problematic types
            converted_attrs = {}
            for key, value in obj.__dict__.items():
                if callable(value) and not isinstance(value, type):
                    raise TypeError(f"Cannot serialize object with callable attribute '{key}': {value}")
                converted_attrs[key] = convert_for_json(value)
            return converted_attrs
        else:
            return obj
    
    try:
        converted_data = convert_for_json(data)
        # Try to serialize the converted data
        return json.dumps(converted_data, ensure_ascii=False)
    except TypeError as e:
        # Re-raise conversion errors as-is, but handle JSON serialization errors
        if "Cannot serialize" in str(e):
            raise e
        # For other JSON serialization errors, try with string conversion
        try:
            return json.dumps(converted_data, default=str, ensure_ascii=False)
        except (TypeError, NameError) as json_e:
            raise TypeError(f"Unable to serialize data for cache: {json_e}")


def deserialize_from_cache(serialized_data: str) -> Any:
    """Deserialize data from cache storage.
    
    Args:
        serialized_data: JSON string to deserialize
        
    Returns:
        Deserialized Python object (Pydantic models become dictionaries)
        
    Raises:
        ValueError: If the serialized data is not valid JSON
    """
    try:
        return json.loads(serialized_data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Unable to deserialize cached data: {e}")


# Cache invalidation utilities

async def invalidate_cache_pattern(pattern: str) -> int:
    """Invalidate all cache keys matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "cache:get_dao:*")
        
    Returns:
        Number of keys deleted
    """
    from services.cache_service import cache_service
    
    if not cache_service.is_available:
        logger.warning(f"Cache service unavailable for pattern invalidation: {pattern}")
        return 0
    
    try:
        # Find all keys matching the pattern
        keys = await cache_service._redis_client.keys(pattern)
        
        if not keys:
            logger.debug(f"No keys found for pattern: {pattern}")
            return 0
        
        # Delete all matching keys
        deleted_count = await cache_service._redis_client.delete(*keys)
        logger.info(f"Invalidated {deleted_count} cache keys for pattern: {pattern}")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")
        return 0


async def invalidate_dao_cache(dao_id: str) -> int:
    """Invalidate all cache entries related to a specific DAO.
    
    Args:
        dao_id: The DAO identifier
        
    Returns:
        Total number of keys deleted
    """
    patterns = [
        f"cache:*{dao_id}*",
        f"cache:get_dao_proposals:{dao_id}:*",
        f"cache:get_proposals:*dao_id:{dao_id}*",
        f"cache:get_dao:{dao_id}:*"
    ]
    
    total_deleted = 0
    for pattern in patterns:
        deleted = await invalidate_cache_pattern(pattern)
        total_deleted += deleted
    
    logger.info(f"Invalidated total {total_deleted} cache keys for DAO: {dao_id}")
    return total_deleted


async def invalidate_proposal_cache(proposal_id: str) -> int:
    """Invalidate all cache entries related to a specific proposal.
    
    Args:
        proposal_id: The proposal identifier
        
    Returns:
        Total number of keys deleted
    """
    patterns = [
        f"cache:*{proposal_id}*",
        f"cache:get_proposal:{proposal_id}:*",
        f"cache:process_proposal:{proposal_id}:*",
        f"cache:analyze_proposal:{proposal_id}:*"
    ]
    
    total_deleted = 0
    for pattern in patterns:
        deleted = await invalidate_cache_pattern(pattern)
        total_deleted += deleted
    
    logger.info(f"Invalidated total {total_deleted} cache keys for proposal: {proposal_id}")
    return total_deleted


async def bulk_invalidate_cache(patterns: List[str]) -> int:
    """Invalidate cache keys for multiple patterns in bulk.
    
    Args:
        patterns: List of Redis key patterns
        
    Returns:
        Total number of keys deleted across all patterns
    """
    total_deleted = 0
    
    for pattern in patterns:
        deleted = await invalidate_cache_pattern(pattern)
        total_deleted += deleted
    
    logger.info(f"Bulk invalidation completed: {total_deleted} keys deleted for {len(patterns)} patterns")
    return total_deleted
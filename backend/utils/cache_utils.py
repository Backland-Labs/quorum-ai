"""Cache utility functions for generating cache keys and handling serialization."""

import hashlib
import json
from typing import Any, Dict, Tuple
from pydantic import BaseModel


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
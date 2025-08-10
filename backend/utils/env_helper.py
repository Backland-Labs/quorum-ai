"""Environment variable helper functions for Pearl integration."""

import os
from typing import Optional


def get_env_with_prefix(
    key: str, default: Optional[str] = None, prefix: str = "CONNECTION_CONFIGS_CONFIG_"
) -> Optional[str]:
    """Get environment variable with prefix fallback.

    This function implements the Pearl environment variable prefixing convention.
    It checks for the prefixed version first, then falls back to the non-prefixed
    version for backward compatibility.

    Args:
        key: Environment variable name
        default: Default value if neither prefixed nor non-prefixed exists
        prefix: Prefix to check first (defaults to CONNECTION_CONFIGS_CONFIG_)

    Returns:
        Environment variable value or default

    Examples:
        >>> # If CONNECTION_CONFIGS_CONFIG_API_KEY=prefixed and API_KEY=fallback exist
        >>> get_env_with_prefix("API_KEY")
        'prefixed'

        >>> # If only API_KEY=fallback exists
        >>> get_env_with_prefix("API_KEY")
        'fallback'

        >>> # If neither exists
        >>> get_env_with_prefix("MISSING_KEY", "default")
        'default'
    """
    prefixed_key = f"{prefix}{key}"
    prefixed_value = os.getenv(prefixed_key)
    if prefixed_value is not None:
        return prefixed_value
    return os.getenv(key, default)

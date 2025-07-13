"""Service for interacting with the Snapshot API."""

import asyncio
from typing import Optional

import httpx

from config import settings

# Constants for better code clarity
DEFAULT_SEMAPHORE_LIMIT = 5  # Default semaphore limit for parallel requests


class SnapshotService:
    """Service for interacting with the Snapshot API."""

    def __init__(self) -> None:
        """Initialize SnapshotService with required configuration."""
        # Runtime assertions for critical method
        assert hasattr(settings, 'request_timeout'), "Settings must have request_timeout attribute"
        assert settings.request_timeout > 0, "Request timeout must be positive"
        
        self.base_url = "https://hub.snapshot.org/graphql"
        self.timeout = settings.request_timeout
        self.semaphore = asyncio.Semaphore(DEFAULT_SEMAPHORE_LIMIT)
        self.client = httpx.AsyncClient(timeout=self.timeout)
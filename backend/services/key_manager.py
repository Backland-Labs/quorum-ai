"""Secure private key management service for Pearl platform integration.

This module provides centralized management of Ethereum private keys with
security features including permission validation, secure memory handling,
and caching with expiration.
"""

import os
import re
import stat
from datetime import datetime, timedelta
from pathlib import Path

from config import settings
from logging_config import setup_pearl_logger

logger = setup_pearl_logger(__name__, store_path=settings.store_path)

# Constants
KEY_FILE_NAME = "ethereum_private_key.txt"
CACHE_TIMEOUT_MINUTES = 5
REQUIRED_PERMISSIONS = 0o600  # Read by owner only
# Ethereum private key regex: 64 hex characters, optionally prefixed with 0x
PRIVATE_KEY_PATTERN = re.compile(r"^(0x)?[a-fA-F0-9]{64}$")


class KeyManagerError(Exception):
    """Base exception for KeyManager errors."""


class KeyManager:
    """Manages secure access to Ethereum private keys.

    This service provides:
    - Secure file reading with permission validation
    - Key format validation
    - Memory caching with expiration
    - Secure error handling without exposing sensitive data
    """

    def __init__(self, working_directory: str | None = None):
        """Initialize the KeyManager.

        Args:
            working_directory: Directory containing the key file. Defaults to current directory.
        """
        self.working_directory = Path(working_directory or os.getcwd())
        self.key_file_path = self.working_directory / KEY_FILE_NAME
        self._cached_key: str | None = None
        self._cache_timestamp: datetime | None = None
        logger.info(
            "KeyManager initialized",
            extra={"working_directory": str(self.working_directory)},
        )

    def get_private_key(self) -> str:
        """Get the Ethereum private key.

        Returns:
            The private key as a hex string (with 0x prefix).

        Raises:
            KeyManagerError: If the key cannot be read or is invalid.
        """
        # Check cache first
        if self._is_cache_valid():
            logger.debug("Using cached private key")
            return self._cached_key

        # Read and validate key
        key = self._read_key_file()
        key = self._validate_key_format(key)

        # Update cache
        self._cached_key = key
        self._cache_timestamp = datetime.now()
        logger.info("Private key loaded and cached")

        return key

    def clear_cache(self) -> None:
        """Clear the cached private key from memory."""
        self._cached_key = None
        self._cache_timestamp = None
        logger.info("Private key cache cleared")

    def _is_cache_valid(self) -> bool:
        """Check if the cached key is still valid.

        Returns:
            True if cache is valid, False otherwise.
        """
        if self._cached_key is None or self._cache_timestamp is None:
            return False

        cache_age = datetime.now() - self._cache_timestamp
        max_age = timedelta(minutes=CACHE_TIMEOUT_MINUTES)

        return cache_age < max_age

    def _read_key_file(self) -> str:
        """Read the private key from file with security checks.

        Returns:
            The raw key content.

        Raises:
            KeyManagerError: If file doesn't exist or has insecure permissions.
        """
        # Validate file exists
        self._ensure_file_exists()

        # Validate file permissions
        self._validate_file_permissions()

        # Read the key
        return self._read_file_content()

    def _ensure_file_exists(self) -> None:
        """Ensure the key file exists.

        Raises:
            KeyManagerError: If file doesn't exist.
        """
        if not self.key_file_path.exists():
            logger.error("Key file not found")
            msg = "Key file not found. Ensure the key file exists in the working directory."
            raise KeyManagerError(msg)

    def _read_file_content(self) -> str:
        """Read and return the file content.

        Returns:
            The file content, stripped of whitespace.

        Raises:
            KeyManagerError: If file cannot be read.
        """
        try:
            key_content = self.key_file_path.read_text().strip()
            logger.debug("Key file read successfully")
            return key_content
        except Exception as e:
            logger.exception(f"Failed to read key file: {type(e).__name__}")
            msg = "Failed to read key file. Check file accessibility."
            raise KeyManagerError(msg)

    def _validate_file_permissions(self) -> None:
        """Validate that the key file has secure permissions.

        Raises:
            KeyManagerError: If permissions are not 600 (read by owner only).
        """
        try:
            file_stat = self.key_file_path.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)

            if file_mode != REQUIRED_PERMISSIONS:
                logger.error("Key file has insecure permissions")
                msg = (
                    "Key file has insecure permissions. "
                    "File must have 600 permissions (read by owner only)."
                )
                raise KeyManagerError(msg)

            logger.debug("Key file permissions validated")
        except KeyManagerError:
            raise
        except Exception as e:
            logger.exception(f"Failed to check file permissions: {type(e).__name__}")
            msg = "Failed to validate key file permissions."
            raise KeyManagerError(msg)

    def _validate_key_format(self, key: str) -> str:
        """Validate and normalize the private key format.

        Args:
            key: The raw key string.

        Returns:
            The normalized key with 0x prefix.

        Raises:
            KeyManagerError: If the key format is invalid.
        """
        # Check if key matches the expected format
        if not PRIVATE_KEY_PATTERN.match(key):
            logger.error("Invalid key format detected")
            msg = "Invalid key format. Expected 64 hexadecimal characters."
            raise KeyManagerError(msg)

        # Normalize to include 0x prefix
        if not key.startswith("0x"):
            key = "0x" + key

        logger.debug("Key format validated")
        return key

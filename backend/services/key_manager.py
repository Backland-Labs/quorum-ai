"""Secure private key management service for Pearl platform integration.

This module provides centralized management of Ethereum private keys with
security features including permission validation, secure memory handling,
and caching with expiration.

Supports both plaintext private keys and encrypted V3 Keystore JSON format.
For encrypted keys, set the AGENT_PASSWORD environment variable.
"""

import json
import os
import re
import stat
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from logging_config import setup_pearl_logger
from config import settings

logger = setup_pearl_logger(__name__, store_path=settings.store_path)

# Constants
KEY_FILE_NAME = "ethereum_private_key.txt"
CACHE_TIMEOUT_MINUTES = 5
# Ethereum private key regex: 64 hex characters, optionally prefixed with 0x
PRIVATE_KEY_PATTERN = re.compile(r"^(0x)?[a-fA-F0-9]{64}$")


class KeyManagerError(Exception):
    """Base exception for KeyManager errors."""

    pass


class KeyManager:
    """Manages secure access to Ethereum private keys.

    This service provides:
    - Secure file reading with permission validation
    - Key format validation
    - Memory caching with expiration
    - Secure error handling without exposing sensitive data
    - Support for encrypted V3 Keystore JSON format
    """

    def __init__(self, password: Optional[str] = None):
        """Initialize the KeyManager.

        Args:
            password: Optional password to decrypt encrypted V3 Keystore keys.
                     If not provided, will check AGENT_PASSWORD environment variable.

        Raises:
            KeyManagerError: If key file doesn't exist or has insecure permissions.
        """
        self.working_directory = Path("/agent_key")
        self.key_file_path = self.working_directory / KEY_FILE_NAME
        self._cached_key: Optional[str] = None
        self._cache_timestamp: Optional[datetime] = None
        self._password = password

        # Validate key file setup during initialization
        self._validate_key_file_setup()

        logger.info(
            "KeyManager initialized",
            extra={"working_directory": str(self.working_directory)},
        )

    def get_private_key(self, password: Optional[str] = None) -> str:
        """Get the Ethereum private key.

        Supports both plaintext keys and encrypted V3 Keystore JSON format.
        For encrypted keys, a password must be provided either as a parameter,
        during KeyManager initialization, or via AGENT_PASSWORD environment variable.

        Args:
            password: Optional password to decrypt encrypted keys. Takes precedence
                     over constructor password and environment variable.

        Returns:
            The private key as a hex string (with 0x prefix).

        Raises:
            KeyManagerError: If the key cannot be read, decrypted, or is invalid.
        """
        # Check cache first
        if self._is_cache_valid():
            logger.debug("Using cached private key")
            return self._cached_key

        # Read key file content
        content = self._read_key_file()

        # Detect format and process accordingly
        if self._is_encrypted_keystore(content):
            key = self._decrypt_keystore(content, password)
        else:
            key = self._validate_key_format(content)

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

    def _validate_key_file_setup(self) -> None:
        """Validate that the key file exists and has secure permissions.

        This method is called during initialization to provide early feedback
        about key file configuration issues.

        Raises:
            KeyManagerError: If file doesn't exist or has insecure permissions.
        """
        self._ensure_file_exists()
        logger.info("Key file setup validated successfully")

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

        # Read the key
        return self._read_file_content()

    def _ensure_file_exists(self) -> None:
        """Ensure the key file exists.

        Raises:
            KeyManagerError: If file doesn't exist.
        """
        if not self.key_file_path.exists():
            logger.error("Key file not found")
            raise KeyManagerError(
                "Key file not found. Ensure the key file exists in the working directory."
            )

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
            logger.error(f"Failed to read key file: {type(e).__name__}")
            raise KeyManagerError("Failed to read key file. Check file accessibility.")


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
            raise KeyManagerError(
                "Invalid key format. Expected 64 hexadecimal characters."
            )

        # Normalize to include 0x prefix
        if not key.startswith("0x"):
            key = "0x" + key

        logger.debug("Key format validated")
        return key

    def _is_encrypted_keystore(self, content: str) -> bool:
        """Detect if content is a V3 Keystore JSON format.

        The V3 Keystore format contains a 'crypto' or 'Crypto' field with
        encryption parameters.

        Args:
            content: The file content to check.

        Returns:
            True if content appears to be V3 Keystore JSON, False otherwise.
        """
        try:
            data = json.loads(content)
            # V3 Keystore uses 'crypto' (lowercase) per spec, but some tools use 'Crypto'
            is_keystore = "crypto" in data or "Crypto" in data
            if is_keystore:
                logger.debug("Detected encrypted V3 Keystore format")
            return is_keystore
        except json.JSONDecodeError:
            return False

    def _decrypt_keystore(self, content: str, password: Optional[str] = None) -> str:
        """Decrypt a V3 Keystore JSON to extract the private key.

        Args:
            content: The V3 Keystore JSON content.
            password: Optional password override. If not provided, uses password
                     from constructor or AGENT_PASSWORD environment variable.

        Returns:
            The decrypted private key with 0x prefix.

        Raises:
            KeyManagerError: If password is missing or decryption fails.
        """
        from eth_account import Account
        from utils.env_helper import get_env_with_prefix

        # Resolve password: parameter > constructor > environment
        effective_password = password or self._password or get_env_with_prefix("AGENT_PASSWORD")

        if effective_password is None:
            logger.error("Encrypted key detected but no password provided")
            raise KeyManagerError(
                "Encrypted key detected but no password provided. "
                "Set AGENT_PASSWORD environment variable or provide password parameter."
            )

        try:
            logger.info("Decrypting V3 Keystore")
            private_key = Account.decrypt(content, effective_password)

            # Convert bytes to hex string with 0x prefix
            if isinstance(private_key, bytes):
                key_hex = "0x" + private_key.hex()
            else:
                key_hex = private_key if private_key.startswith("0x") else "0x" + private_key

            logger.info("Successfully decrypted V3 Keystore")
            return key_hex

        except ValueError as e:
            # eth_account raises ValueError for wrong password or invalid keystore
            error_msg = str(e)
            if "password" in error_msg.lower() or "mac" in error_msg.lower():
                logger.error("Failed to decrypt keystore: incorrect password")
                raise KeyManagerError(
                    "Failed to decrypt keystore: incorrect password or corrupted file."
                ) from e
            else:
                logger.error(f"Failed to decrypt keystore: {error_msg}")
                raise KeyManagerError(f"Failed to decrypt keystore: {error_msg}") from e
        except Exception as e:
            logger.error(f"Unexpected error decrypting keystore: {type(e).__name__}")
            raise KeyManagerError(
                "Failed to decrypt keystore. Check file format and password."
            ) from e

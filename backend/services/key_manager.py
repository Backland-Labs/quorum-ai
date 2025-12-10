"""Secure private key management service for Pearl platform integration.

This module provides centralized management of Ethereum private keys with
security features including permission validation, secure memory handling,
and caching with expiration.
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from eth_account import Account

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
    """

    def __init__(self, password: Optional[str] = None):
        """Initialize the KeyManager.

        Args:
            password: Optional password for decrypting V3 Keystore encrypted keys.

        Raises:
            KeyManagerError: If key file doesn't exist or has insecure permissions.
        """
        # Get key directory from environment or use default
        key_dir_env = os.environ.get("AGENT_KEY_DIR")
        if key_dir_env:
            self.working_directory = Path(key_dir_env)
        else:
            # Use /agent_key as default (Docker-friendly)
            self.working_directory = Path("/agent_key")
        self.key_file_path = self.working_directory / KEY_FILE_NAME
        self._cached_key: Optional[str] = None
        self._cache_timestamp: Optional[datetime] = None
        self._password = password

        # Validate key file setup during initialization
        self._validate_key_file_setup()

        logger.info(
            "KeyManager initialized",
            extra={
                "working_directory": str(self.working_directory),
                "password_provided": password is not None,
            },
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

    def _is_v3_keystore(self, content: str) -> bool:
        """Check if the content is a V3 Keystore JSON format.

        Args:
            content: The file content to check.

        Returns:
            True if content is a valid V3 keystore, False otherwise.
        """
        try:
            keystore = json.loads(content)
            return isinstance(keystore, dict) and keystore.get("version") == 3
        except json.JSONDecodeError:
            return False

    def _decrypt_v3_keystore(self, keystore_json: str) -> str:
        """Decrypt a V3 Keystore JSON and return the private key.

        Args:
            keystore_json: The V3 keystore JSON string.

        Returns:
            The decrypted private key as a hex string with 0x prefix.

        Raises:
            KeyManagerError: If decryption fails or password is incorrect.
        """
        try:
            keystore = json.loads(keystore_json)
            private_key_bytes = Account.decrypt(keystore, self._password)
            private_key = "0x" + private_key_bytes.hex()
            logger.debug("V3 keystore decrypted successfully")
            return private_key
        except ValueError as e:
            # eth_account raises ValueError for incorrect password
            logger.error("V3 keystore decryption failed: incorrect password")
            raise KeyManagerError(
                "Failed to decrypt V3 keystore: incorrect password provided"
            ) from e
        except Exception as e:
            logger.error(f"V3 keystore decryption failed: {type(e).__name__}")
            raise KeyManagerError(
                f"Failed to decrypt V3 keystore: {type(e).__name__}"
            ) from e

    def _read_file_content(self) -> str:
        """Read and return the file content.

        If the content is a V3 Keystore JSON, it will be decrypted using the
        provided password. Otherwise, the plaintext content is returned.

        Returns:
            The private key (decrypted if V3 keystore, plaintext otherwise).

        Raises:
            KeyManagerError: If file cannot be read or V3 keystore requires password.
        """
        try:
            key_content = self.key_file_path.read_text().strip()
            logger.debug("Key file read successfully")

            # Check if content is V3 keystore format
            if self._is_v3_keystore(key_content):
                logger.info("Detected V3 Keystore format")
                if not self._password:
                    logger.error("V3 keystore detected but no password provided")
                    raise KeyManagerError(
                        "V3 Keystore encrypted key file detected but no password provided. "
                        "Please provide password via --password argument or KEY_PASSWORD environment variable."
                    )
                # Decrypt V3 keystore
                return self._decrypt_v3_keystore(key_content)

            # Return plaintext content
            return key_content
        except KeyManagerError:
            # Re-raise KeyManagerError as-is
            raise
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

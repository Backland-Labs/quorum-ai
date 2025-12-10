"""Comprehensive unit tests for KeyManager V3 keystore support.

This test suite covers:
1. Plaintext key loading (backwards compatibility)
2. V3 keystore detection
3. V3 keystore decryption
4. Caching behavior
5. File error handling
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from eth_account import Account

from services.key_manager import KeyManager, KeyManagerError


# Test constants
TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
TEST_PASSWORD = "test_password"


@pytest.fixture
def test_keystore():
    """Generate a V3 keystore JSON encrypted with the test password."""
    keystore = Account.encrypt(TEST_PRIVATE_KEY, TEST_PASSWORD)
    return keystore


@pytest.fixture
def test_keystore_json(test_keystore):
    """Return the V3 keystore as a JSON string."""
    return json.dumps(test_keystore)


@pytest.fixture
def temp_key_dir(tmp_path):
    """Create a temporary directory for key files and set AGENT_KEY_DIR."""
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    return key_dir


@pytest.fixture
def plaintext_key_file(temp_key_dir):
    """Create a plaintext key file with 0x prefix."""
    key_file = temp_key_dir / "ethereum_private_key.txt"
    key_file.write_text(TEST_PRIVATE_KEY)
    return key_file


@pytest.fixture
def plaintext_key_file_no_prefix(temp_key_dir):
    """Create a plaintext key file without 0x prefix."""
    key_file = temp_key_dir / "ethereum_private_key.txt"
    key_file.write_text(TEST_PRIVATE_KEY[2:])  # Remove 0x prefix
    return key_file


@pytest.fixture
def v3_keystore_file(temp_key_dir, test_keystore_json):
    """Create a V3 keystore file."""
    key_file = temp_key_dir / "ethereum_private_key.txt"
    key_file.write_text(test_keystore_json)
    return key_file


# ====================
# Test Plaintext Key Loading (Backwards Compatibility)
# ====================


class TestPlaintextKeyLoading:
    """Test plaintext key loading to ensure backwards compatibility."""

    def test_plaintext_key_with_0x_prefix(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that a plaintext key with 0x prefix loads correctly."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager()
        private_key = key_manager.get_private_key()

        assert private_key == TEST_PRIVATE_KEY
        assert private_key.startswith("0x")

    def test_plaintext_key_without_0x_prefix(self, temp_key_dir, plaintext_key_file_no_prefix, monkeypatch):
        """Test that a plaintext key without 0x prefix is normalized correctly."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager()
        private_key = key_manager.get_private_key()

        assert private_key == TEST_PRIVATE_KEY
        assert private_key.startswith("0x")

    def test_plaintext_key_invalid_format(self, temp_key_dir, monkeypatch):
        """Test that an invalid plaintext key format raises KeyManagerError."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create file with invalid key format
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text("invalid_key_format")

        key_manager = KeyManager()

        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()

        assert "Invalid key format" in str(exc_info.value)

    def test_plaintext_key_too_short(self, temp_key_dir, monkeypatch):
        """Test that a key that's too short raises KeyManagerError."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create file with key that's too short
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text("0x1234567890abcdef")

        key_manager = KeyManager()

        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()

        assert "Invalid key format" in str(exc_info.value)

    def test_plaintext_key_with_whitespace(self, temp_key_dir, monkeypatch):
        """Test that a plaintext key with surrounding whitespace is handled correctly."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create file with whitespace around key
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text(f"  {TEST_PRIVATE_KEY}  \n")

        key_manager = KeyManager()
        private_key = key_manager.get_private_key()

        assert private_key == TEST_PRIVATE_KEY
        assert private_key.startswith("0x")


# ====================
# Test V3 Keystore Detection
# ====================


class TestV3KeystoreDetection:
    """Test V3 keystore format detection logic."""

    def test_is_v3_keystore_valid(self, temp_key_dir, plaintext_key_file, test_keystore_json, monkeypatch):
        """Test that a valid V3 keystore JSON is detected correctly."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))
        key_manager = KeyManager(password=TEST_PASSWORD)

        assert key_manager._is_v3_keystore(test_keystore_json) is True

    def test_is_v3_keystore_invalid_json(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that invalid JSON returns False."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))
        key_manager = KeyManager(password=TEST_PASSWORD)

        assert key_manager._is_v3_keystore("not valid json {[}]") is False

    def test_is_v3_keystore_wrong_version(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that JSON with version != 3 returns False."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))
        key_manager = KeyManager(password=TEST_PASSWORD)

        # Create keystore with wrong version
        wrong_version_keystore = {"version": 2, "crypto": {}}
        wrong_version_json = json.dumps(wrong_version_keystore)

        assert key_manager._is_v3_keystore(wrong_version_json) is False

    def test_is_v3_keystore_missing_version(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that JSON without version field returns False."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))
        key_manager = KeyManager(password=TEST_PASSWORD)

        # Create keystore without version
        no_version_keystore = {"crypto": {}, "address": "test"}
        no_version_json = json.dumps(no_version_keystore)

        assert key_manager._is_v3_keystore(no_version_json) is False

    def test_is_v3_keystore_version_as_string(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that version as string '3' is not detected (must be int)."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))
        key_manager = KeyManager(password=TEST_PASSWORD)

        # Create keystore with version as string
        string_version_keystore = {"version": "3", "crypto": {}}
        string_version_json = json.dumps(string_version_keystore)

        # Should return False because version must be int 3, not string "3"
        assert key_manager._is_v3_keystore(string_version_json) is False

    def test_is_v3_keystore_not_dict(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that JSON array or other non-dict types return False."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))
        key_manager = KeyManager(password=TEST_PASSWORD)

        # JSON array
        assert key_manager._is_v3_keystore("[]") is False

        # JSON string
        assert key_manager._is_v3_keystore('"test"') is False

        # JSON number
        assert key_manager._is_v3_keystore("123") is False


# ====================
# Test V3 Keystore Decryption
# ====================


class TestV3KeystoreDecryption:
    """Test V3 keystore decryption functionality."""

    def test_v3_keystore_decryption_with_correct_password(
        self, temp_key_dir, v3_keystore_file, monkeypatch
    ):
        """Test that V3 keystore decrypts successfully with correct password."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager(password=TEST_PASSWORD)
        private_key = key_manager.get_private_key()

        assert private_key == TEST_PRIVATE_KEY
        assert private_key.startswith("0x")

    def test_v3_keystore_decryption_with_wrong_password(
        self, temp_key_dir, v3_keystore_file, monkeypatch
    ):
        """Test that V3 keystore decryption fails with wrong password."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager(password="wrong_password")

        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()

        assert "incorrect password" in str(exc_info.value).lower()

    def test_v3_keystore_without_password(
        self, temp_key_dir, v3_keystore_file, monkeypatch
    ):
        """Test that V3 keystore without password raises clear error."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create KeyManager without password
        key_manager = KeyManager()

        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()

        error_message = str(exc_info.value)
        assert "V3 Keystore" in error_message
        assert "no password provided" in error_message
        assert "--password" in error_message or "KEY_PASSWORD" in error_message

    def test_v3_keystore_with_empty_password(
        self, temp_key_dir, v3_keystore_file, monkeypatch
    ):
        """Test that V3 keystore with empty string password fails appropriately."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Empty password should still trigger decryption attempt
        key_manager = KeyManager(password="")

        with pytest.raises(KeyManagerError):
            key_manager.get_private_key()

    def test_v3_keystore_decryption_preserves_0x_prefix(
        self, temp_key_dir, v3_keystore_file, monkeypatch
    ):
        """Test that decrypted key has 0x prefix."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager(password=TEST_PASSWORD)
        private_key = key_manager.get_private_key()

        assert private_key.startswith("0x")
        assert len(private_key) == 66  # 0x + 64 hex chars

    def test_v3_keystore_malformed_json_in_file(
        self, temp_key_dir, monkeypatch
    ):
        """Test handling of malformed V3 keystore JSON."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create file with malformed JSON (has version:3 but invalid structure)
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text('{"version": 3, "crypto": "invalid"}')

        key_manager = KeyManager(password=TEST_PASSWORD)

        with pytest.raises(KeyManagerError):
            key_manager.get_private_key()


# ====================
# Test Caching Behavior
# ====================


class TestCachingBehavior:
    """Test KeyManager caching functionality."""

    def test_key_is_cached_after_first_load(
        self, temp_key_dir, plaintext_key_file, monkeypatch
    ):
        """Test that the key is cached after first load."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager()

        # First load
        key1 = key_manager.get_private_key()

        # Delete the file to prove cache is used
        plaintext_key_file.unlink()

        # Second load should use cache
        key2 = key_manager.get_private_key()

        assert key1 == key2 == TEST_PRIVATE_KEY

    def test_cache_clear(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that clear_cache() clears the cached key."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager()

        # Load and cache key
        key_manager.get_private_key()
        assert key_manager._cached_key is not None
        assert key_manager._cache_timestamp is not None

        # Clear cache
        key_manager.clear_cache()

        assert key_manager._cached_key is None
        assert key_manager._cache_timestamp is None

    def test_cache_expiration(
        self, temp_key_dir, plaintext_key_file, monkeypatch
    ):
        """Test that cache expires after timeout."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager()

        # Load and cache key
        key_manager.get_private_key()

        # Manually expire the cache by setting old timestamp
        from datetime import datetime, timedelta
        key_manager._cache_timestamp = datetime.now() - timedelta(minutes=10)

        # Cache should be invalid now
        assert key_manager._is_cache_valid() is False

    def test_cache_works_with_v3_keystore(
        self, temp_key_dir, v3_keystore_file, monkeypatch
    ):
        """Test that caching works correctly with V3 keystore."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager(password=TEST_PASSWORD)

        # First load (requires decryption)
        key1 = key_manager.get_private_key()

        # Delete file to prove cache is used
        v3_keystore_file.unlink()

        # Second load should use cache (no file read or decryption)
        key2 = key_manager.get_private_key()

        assert key1 == key2 == TEST_PRIVATE_KEY


# ====================
# Test File Errors
# ====================


class TestFileErrors:
    """Test file-related error handling."""

    def test_file_not_found_error(self, temp_key_dir, monkeypatch):
        """Test that missing file raises KeyManagerError during initialization."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # KeyManager should validate file exists during __init__
        with pytest.raises(KeyManagerError) as exc_info:
            KeyManager()

        assert "Key file not found" in str(exc_info.value)

    def test_empty_key_file(self, temp_key_dir, monkeypatch):
        """Test that an empty key file raises appropriate error."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create empty file
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text("")

        key_manager = KeyManager()

        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()

        assert "Invalid key format" in str(exc_info.value)

    def test_file_with_only_whitespace(self, temp_key_dir, monkeypatch):
        """Test that a file with only whitespace raises appropriate error."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create file with only whitespace
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text("   \n\t  \n")

        key_manager = KeyManager()

        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()

        assert "Invalid key format" in str(exc_info.value)


# ====================
# Test Backwards Compatibility
# ====================


class TestBackwardsCompatibility:
    """Test that plaintext keys work without password parameter."""

    def test_plaintext_key_works_without_password_param(
        self, temp_key_dir, plaintext_key_file, monkeypatch
    ):
        """Test that plaintext key works without password parameter."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create KeyManager without password
        key_manager = KeyManager()
        private_key = key_manager.get_private_key()

        assert private_key == TEST_PRIVATE_KEY

    def test_password_param_ignored_for_plaintext_keys(
        self, temp_key_dir, plaintext_key_file, monkeypatch
    ):
        """Test that password parameter is ignored for plaintext keys."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        # Create KeyManager with password (should be ignored for plaintext)
        key_manager = KeyManager(password="ignored_password")
        private_key = key_manager.get_private_key()

        assert private_key == TEST_PRIVATE_KEY


# ====================
# Test Initialization and Configuration
# ====================


class TestKeyManagerInitialization:
    """Test KeyManager initialization and configuration."""

    def test_default_key_directory(self, plaintext_key_file, monkeypatch):
        """Test that default key directory is /agent_key when env var not set."""
        # Remove AGENT_KEY_DIR from environment
        monkeypatch.delenv("AGENT_KEY_DIR", raising=False)

        # Mock the file existence check for default directory
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'read_text', return_value=TEST_PRIVATE_KEY):
                key_manager = KeyManager()
                assert key_manager.working_directory == Path("/agent_key")

    def test_custom_key_directory_from_env(
        self, temp_key_dir, plaintext_key_file, monkeypatch
    ):
        """Test that custom key directory is used when AGENT_KEY_DIR is set."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager()

        assert key_manager.working_directory == temp_key_dir
        assert key_manager.key_file_path == temp_key_dir / "ethereum_private_key.txt"

    def test_password_stored_securely(self, temp_key_dir, plaintext_key_file, monkeypatch):
        """Test that password is stored as instance variable."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        password = "secret_password"
        key_manager = KeyManager(password=password)

        assert key_manager._password == password

    def test_initialization_without_password(
        self, temp_key_dir, plaintext_key_file, monkeypatch
    ):
        """Test that KeyManager can be initialized without password."""
        monkeypatch.setenv("AGENT_KEY_DIR", str(temp_key_dir))

        key_manager = KeyManager()

        assert key_manager._password is None

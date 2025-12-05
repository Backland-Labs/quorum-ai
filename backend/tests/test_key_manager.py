"""Tests for KeyManager service with encrypted V3 Keystore support."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from eth_account import Account

# Set required environment variables before importing modules that need them
os.environ.setdefault("BASE_RPC_URL", "http://localhost:8545")
os.environ.setdefault("MOCK_MODE", "1")

# Import directly from the module file to avoid import chain issues
sys.path.insert(0, str(Path(__file__).parent.parent))
from services.key_manager import KeyManager, KeyManagerError


# Sample plaintext private key (test key - not for production use!)
TEST_PLAINTEXT_KEY = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
TEST_PLAINTEXT_KEY_WITH_PREFIX = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Password for encrypted keystore tests
TEST_PASSWORD = "test_password_123"


@pytest.fixture
def temp_key_dir():
    """Create a temporary directory for key file tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def plaintext_key_file(temp_key_dir):
    """Create a temporary plaintext key file."""
    key_file = temp_key_dir / "ethereum_private_key.txt"
    key_file.write_text(TEST_PLAINTEXT_KEY)
    return key_file


@pytest.fixture
def plaintext_key_file_with_prefix(temp_key_dir):
    """Create a temporary plaintext key file with 0x prefix."""
    key_file = temp_key_dir / "ethereum_private_key.txt"
    key_file.write_text(TEST_PLAINTEXT_KEY_WITH_PREFIX)
    return key_file


@pytest.fixture
def encrypted_keystore_file(temp_key_dir):
    """Create a temporary encrypted V3 Keystore file."""
    # Generate a keystore using eth_account
    key_file = temp_key_dir / "ethereum_private_key.txt"

    # Create encrypted keystore from test key
    keystore = Account.encrypt(TEST_PLAINTEXT_KEY_WITH_PREFIX, TEST_PASSWORD)
    key_file.write_text(json.dumps(keystore))

    return key_file


@pytest.fixture
def encrypted_keystore_uppercase_crypto(temp_key_dir):
    """Create a V3 Keystore with uppercase 'Crypto' field."""
    key_file = temp_key_dir / "ethereum_private_key.txt"

    # Create encrypted keystore and modify to use uppercase Crypto
    keystore = Account.encrypt(TEST_PLAINTEXT_KEY_WITH_PREFIX, TEST_PASSWORD)
    if "crypto" in keystore:
        keystore["Crypto"] = keystore.pop("crypto")

    key_file.write_text(json.dumps(keystore))
    return key_file


class TestKeyManagerPlaintext:
    """Tests for plaintext private key loading."""

    def test_load_plaintext_key_without_prefix(self, temp_key_dir, plaintext_key_file):
        """Test loading a plaintext key without 0x prefix."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = plaintext_key_file

            key = manager.get_private_key()

            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX
            assert key.startswith("0x")

    def test_load_plaintext_key_with_prefix(self, temp_key_dir, plaintext_key_file_with_prefix):
        """Test loading a plaintext key with 0x prefix."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = plaintext_key_file_with_prefix

            key = manager.get_private_key()

            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX

    def test_plaintext_key_caching(self, temp_key_dir, plaintext_key_file):
        """Test that plaintext keys are cached properly."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = plaintext_key_file

            # First call - reads from file
            key1 = manager.get_private_key()

            # Second call - should use cache
            key2 = manager.get_private_key()

            assert key1 == key2
            assert manager._cached_key is not None

    def test_invalid_plaintext_key_format(self, temp_key_dir):
        """Test that invalid key formats raise an error."""
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text("invalid_key_format")

        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = key_file

            with pytest.raises(KeyManagerError, match="Invalid key format"):
                manager.get_private_key()


class TestKeyManagerEncrypted:
    """Tests for encrypted V3 Keystore loading."""

    def test_load_encrypted_key_with_password(self, temp_key_dir, encrypted_keystore_file):
        """Test loading an encrypted keystore with correct password."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager(password=TEST_PASSWORD)
            manager.key_file_path = encrypted_keystore_file

            key = manager.get_private_key()

            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX

    def test_load_encrypted_key_with_method_password(self, temp_key_dir, encrypted_keystore_file):
        """Test loading an encrypted keystore with password passed to method."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = encrypted_keystore_file

            key = manager.get_private_key(password=TEST_PASSWORD)

            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX

    def test_load_encrypted_key_with_env_password(self, temp_key_dir, encrypted_keystore_file):
        """Test loading an encrypted keystore with AGENT_PASSWORD environment variable."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            with patch.dict(os.environ, {"AGENT_PASSWORD": TEST_PASSWORD}):
                manager = KeyManager()
                manager.key_file_path = encrypted_keystore_file

                key = manager.get_private_key()

                assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX

    def test_encrypted_key_without_password_raises_error(self, temp_key_dir, encrypted_keystore_file):
        """Test that encrypted key without password raises an error."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            # Patch get_env_with_prefix in the utils module where it's imported from
            with patch("utils.env_helper.get_env_with_prefix", return_value=None):
                manager = KeyManager()
                manager.key_file_path = encrypted_keystore_file

                with pytest.raises(KeyManagerError, match="no password provided"):
                    manager.get_private_key()

    def test_encrypted_key_with_wrong_password(self, temp_key_dir, encrypted_keystore_file):
        """Test that wrong password raises an error."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager(password="wrong_password")
            manager.key_file_path = encrypted_keystore_file

            with pytest.raises(KeyManagerError, match="incorrect password|Failed to decrypt"):
                manager.get_private_key()

    def test_load_encrypted_key_uppercase_crypto(self, temp_key_dir, encrypted_keystore_uppercase_crypto):
        """Test loading keystore with uppercase 'Crypto' field."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager(password=TEST_PASSWORD)
            manager.key_file_path = encrypted_keystore_uppercase_crypto

            key = manager.get_private_key()

            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX


class TestKeyManagerDetection:
    """Tests for encrypted key detection."""

    def test_detect_encrypted_keystore_lowercase(self):
        """Test detection of keystore with lowercase 'crypto' field."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()

            keystore_json = json.dumps({"crypto": {"cipher": "aes-128-ctr"}})
            assert manager._is_encrypted_keystore(keystore_json) is True

    def test_detect_encrypted_keystore_uppercase(self):
        """Test detection of keystore with uppercase 'Crypto' field."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()

            keystore_json = json.dumps({"Crypto": {"cipher": "aes-128-ctr"}})
            assert manager._is_encrypted_keystore(keystore_json) is True

    def test_detect_plaintext_key(self):
        """Test that plaintext keys are not detected as encrypted."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()

            assert manager._is_encrypted_keystore(TEST_PLAINTEXT_KEY) is False
            assert manager._is_encrypted_keystore(TEST_PLAINTEXT_KEY_WITH_PREFIX) is False

    def test_detect_invalid_json(self):
        """Test that invalid JSON is not detected as encrypted."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()

            assert manager._is_encrypted_keystore("not json at all") is False
            assert manager._is_encrypted_keystore("{invalid json}") is False

    def test_detect_json_without_crypto(self):
        """Test that JSON without crypto field is not detected as encrypted."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()

            json_without_crypto = json.dumps({"address": "0x123", "id": "abc"})
            assert manager._is_encrypted_keystore(json_without_crypto) is False


class TestKeyManagerPasswordPriority:
    """Tests for password resolution priority."""

    def test_method_password_takes_priority(self, temp_key_dir, encrypted_keystore_file):
        """Test that method password takes priority over constructor and env."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            with patch.dict(os.environ, {"AGENT_PASSWORD": "wrong_env_password"}):
                # Constructor has wrong password
                manager = KeyManager(password="wrong_constructor_password")
                manager.key_file_path = encrypted_keystore_file

                # Method password is correct - should succeed
                key = manager.get_private_key(password=TEST_PASSWORD)

                assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX

    def test_constructor_password_takes_priority_over_env(self, temp_key_dir, encrypted_keystore_file):
        """Test that constructor password takes priority over environment."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            with patch.dict(os.environ, {"AGENT_PASSWORD": "wrong_env_password"}):
                # Constructor has correct password
                manager = KeyManager(password=TEST_PASSWORD)
                manager.key_file_path = encrypted_keystore_file

                key = manager.get_private_key()

                assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX


class TestKeyManagerBackwardsCompatibility:
    """Tests for backwards compatibility with existing deployments."""

    def test_plaintext_key_works_without_password(self, temp_key_dir, plaintext_key_file):
        """Test that plaintext keys work without any password configuration."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            # No password set anywhere
            manager = KeyManager()
            manager.key_file_path = plaintext_key_file

            key = manager.get_private_key()

            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX

    def test_default_constructor_works(self, temp_key_dir, plaintext_key_file):
        """Test that default constructor still works."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = plaintext_key_file

            assert manager._password is None

            key = manager.get_private_key()
            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX


class TestKeyManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_malformed_keystore_json(self, temp_key_dir):
        """Test handling of malformed keystore JSON."""
        key_file = temp_key_dir / "ethereum_private_key.txt"
        # Valid JSON with crypto field but missing required fields
        malformed_keystore = json.dumps({"crypto": {}})
        key_file.write_text(malformed_keystore)

        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager(password=TEST_PASSWORD)
            manager.key_file_path = key_file

            with pytest.raises(KeyManagerError):
                manager.get_private_key()

    def test_empty_file(self, temp_key_dir):
        """Test handling of empty key file."""
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text("")

        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = key_file

            with pytest.raises(KeyManagerError, match="Invalid key format"):
                manager.get_private_key()

    def test_whitespace_only_file(self, temp_key_dir):
        """Test handling of whitespace-only key file."""
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text("   \n\t  ")

        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = key_file

            with pytest.raises(KeyManagerError, match="Invalid key format"):
                manager.get_private_key()

    def test_key_with_extra_whitespace(self, temp_key_dir):
        """Test that keys with extra whitespace are handled correctly."""
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text(f"  {TEST_PLAINTEXT_KEY}  \n")

        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = key_file

            key = manager.get_private_key()

            assert key == TEST_PLAINTEXT_KEY_WITH_PREFIX

    def test_clear_cache_works(self, temp_key_dir, plaintext_key_file):
        """Test that cache clearing works properly."""
        with patch.object(KeyManager, "_validate_key_file_setup"):
            manager = KeyManager()
            manager.key_file_path = plaintext_key_file

            # Load key to cache it
            manager.get_private_key()
            assert manager._cached_key is not None

            # Clear cache
            manager.clear_cache()

            assert manager._cached_key is None
            assert manager._cache_timestamp is None

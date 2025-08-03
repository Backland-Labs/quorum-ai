"""Test suite for the KeyManager service.

This module tests the secure private key management functionality required
for Pearl platform integration. It ensures that private keys are read securely,
permissions are validated, and keys are handled safely in memory.
"""

import os
import stat
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from eth_account import Account

from services.key_manager import KeyManager, KeyManagerError


class TestKeyManager:
    """Test cases for the KeyManager service."""

    @pytest.fixture
    def temp_key_dir(self):
        """Create a temporary directory for key files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def valid_private_key(self):
        """Generate a valid Ethereum private key."""
        account = Account.create()
        # Return key without 0x prefix as it would be stored in file
        return account.key.hex()[2:] if account.key.hex().startswith('0x') else account.key.hex()

    @pytest.fixture
    def key_file_path(self, temp_key_dir):
        """Return the path to the key file."""
        return temp_key_dir / "ethereum_private_key.txt"

    @pytest.fixture
    def key_manager(self, temp_key_dir):
        """Create a KeyManager instance with a temporary directory."""
        return KeyManager(working_directory=str(temp_key_dir))

    def test_locate_key_file_correctly(self, key_manager, key_file_path, valid_private_key):
        """Test that KeyManager can locate the ethereum_private_key.txt file correctly.
        
        This test is important because the KeyManager must be able to find the key file
        in the agent's working directory, which is a critical requirement for Pearl platform
        deployment where agents manage their own keys.
        """
        # Create key file with proper permissions
        key_file_path.write_text(valid_private_key)
        os.chmod(key_file_path, 0o600)
        
        # Should successfully read the key
        key = key_manager.get_private_key()
        # KeyManager normalizes to include 0x prefix
        assert key == '0x' + valid_private_key

    def test_reject_files_with_insecure_permissions(self, key_manager, key_file_path, valid_private_key):
        """Test that KeyManager rejects key files with insecure permissions.
        
        This test is critical for security. The KeyManager must ensure that private key
        files have restrictive permissions (600 - read by owner only) to prevent
        unauthorized access in multi-user environments.
        """
        # Create key file with insecure permissions
        key_file_path.write_text(valid_private_key)
        
        # Test various insecure permission modes
        insecure_modes = [0o644, 0o664, 0o666, 0o777, 0o640, 0o660]
        
        for mode in insecure_modes:
            os.chmod(key_file_path, mode)
            with pytest.raises(KeyManagerError) as exc_info:
                key_manager.get_private_key()
            assert "insecure permissions" in str(exc_info.value).lower()
            assert str(oct(mode)) not in str(exc_info.value)  # Should not expose actual permissions

    def test_validate_key_format(self, key_manager, key_file_path):
        """Test that KeyManager validates the private key format.
        
        This test ensures that the KeyManager properly validates Ethereum private keys
        to prevent invalid keys from being used in blockchain operations, which could
        cause transaction failures or loss of funds.
        """
        # Test invalid key formats
        invalid_keys = [
            "not-a-hex-key",
            "0x",  # Empty hex
            "0xGHIJKL",  # Invalid hex characters
            "0x" + "a" * 63,  # Too short (31 bytes)
            "0x" + "a" * 65,  # Too long (33 bytes)
            "",  # Empty string
            " ",  # Whitespace only
        ]
        
        for invalid_key in invalid_keys:
            key_file_path.write_text(invalid_key)
            os.chmod(key_file_path, 0o600)
            with pytest.raises(KeyManagerError) as exc_info:
                key_manager.get_private_key()
            assert "invalid key format" in str(exc_info.value).lower()

    def test_no_sensitive_data_in_error_messages(self, key_manager, key_file_path):
        """Test that error messages do not expose sensitive information.
        
        This test is important for security. Error messages should be helpful but must
        not leak sensitive information like file paths, key contents, or system details
        that could aid an attacker.
        """
        # Test missing file error
        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()
        error_msg = str(exc_info.value)
        assert "ethereum_private_key.txt" not in error_msg
        assert str(key_file_path.parent) not in error_msg
        assert "key file not found" in error_msg.lower()
        
        # Test permission error with actual path
        key_file_path.write_text("test")
        os.chmod(key_file_path, 0o777)
        with pytest.raises(KeyManagerError) as exc_info:
            key_manager.get_private_key()
        error_msg = str(exc_info.value)
        assert str(key_file_path) not in error_msg
        assert "0o777" not in error_msg
        assert "insecure permissions" in error_msg.lower()

    def test_lazy_loading_of_private_key(self, key_manager, key_file_path, valid_private_key):
        """Test that KeyManager implements lazy loading of private keys.
        
        This test ensures that private keys are only loaded when needed, not at
        initialization. This is important for performance and security, as keys
        should only be in memory when actively being used.
        """
        # Key file doesn't exist at initialization - should not raise
        assert key_manager._cached_key is None
        assert key_manager._cache_timestamp is None
        
        # Create key file
        key_file_path.write_text(valid_private_key)
        os.chmod(key_file_path, 0o600)
        
        # First call should load the key
        with patch.object(Path, 'read_text') as mock_read:
            mock_read.return_value = valid_private_key
            key1 = key_manager.get_private_key()
            assert mock_read.call_count == 1
            assert key1 == '0x' + valid_private_key

    def test_key_caching_with_timeout(self, key_manager, key_file_path, valid_private_key):
        """Test that KeyManager caches keys with a 5-minute timeout.
        
        This test verifies the caching mechanism that balances performance (avoiding
        repeated file reads) with security (keys don't stay in memory indefinitely).
        The 5-minute timeout is a security requirement.
        """
        key_file_path.write_text(valid_private_key)
        os.chmod(key_file_path, 0o600)
        
        # First call should read from file
        with patch.object(Path, 'read_text', return_value=valid_private_key) as mock_read:
            key1 = key_manager.get_private_key()
            assert mock_read.call_count == 1
        
        # Immediate second call should use cache
        with patch.object(Path, 'read_text') as mock_read:
            key2 = key_manager.get_private_key()
            assert mock_read.call_count == 0
            assert key2 == key1
        
        # Simulate time passing (4 minutes - still within cache)
        key_manager._cache_timestamp = datetime.now() - timedelta(minutes=4)
        with patch.object(Path, 'read_text') as mock_read:
            key3 = key_manager.get_private_key()
            assert mock_read.call_count == 0
            assert key3 == key1
        
        # Simulate time passing (6 minutes - cache expired)
        key_manager._cache_timestamp = datetime.now() - timedelta(minutes=6)
        with patch.object(Path, 'read_text', return_value=valid_private_key) as mock_read:
            key4 = key_manager.get_private_key()
            assert mock_read.call_count == 1
            assert key4 == '0x' + valid_private_key

    def test_memory_clearing_after_use(self, key_manager, key_file_path, valid_private_key):
        """Test that KeyManager can clear keys from memory.
        
        This test ensures that sensitive key data can be explicitly cleared from memory
        when no longer needed. This is a critical security feature to minimize the
        window of exposure for private keys in memory.
        """
        key_file_path.write_text(valid_private_key)
        os.chmod(key_file_path, 0o600)
        
        # Load key into cache
        key = key_manager.get_private_key()
        assert key_manager._cached_key is not None
        assert key_manager._cache_timestamp is not None
        
        # Clear cache
        key_manager.clear_cache()
        
        # Verify cache is cleared
        assert key_manager._cached_key is None
        assert key_manager._cache_timestamp is None
        
        # Next call should read from file again
        with patch.object(Path, 'read_text', return_value=valid_private_key) as mock_read:
            key2 = key_manager.get_private_key()
            assert mock_read.call_count == 1

    def test_handle_whitespace_in_key_file(self, key_manager, key_file_path, valid_private_key):
        """Test that KeyManager properly handles whitespace in key files.
        
        This test ensures robustness when reading key files that may have been
        manually edited or generated with different tools. Trailing whitespace
        is a common issue that should be handled gracefully.
        """
        # Test key with various whitespace
        key_with_whitespace = f"  {valid_private_key}  \n\t"
        key_file_path.write_text(key_with_whitespace)
        os.chmod(key_file_path, 0o600)
        
        key = key_manager.get_private_key()
        assert key == '0x' + valid_private_key  # Should strip whitespace and add 0x prefix
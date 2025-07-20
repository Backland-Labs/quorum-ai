"""Integration tests for VotingService with KeyManager.

This module tests the integration between VotingService and KeyManager,
ensuring that the VotingService properly uses KeyManager for secure
private key access.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from eth_account import Account

from services.key_manager import KeyManager, KeyManagerError
from services.voting_service import VotingService


class TestVotingServiceKeyManagerIntegration:
    """Test cases for VotingService and KeyManager integration."""

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
    def key_file_with_valid_key(self, temp_key_dir, valid_private_key):
        """Create a key file with proper permissions and valid key."""
        key_file = temp_key_dir / "ethereum_private_key.txt"
        key_file.write_text(valid_private_key)
        os.chmod(key_file, 0o600)
        return key_file

    def test_voting_service_uses_key_manager(self, temp_key_dir, key_file_with_valid_key, valid_private_key):
        """Test that VotingService properly uses KeyManager to load private keys.
        
        This test verifies that the VotingService uses the centralized KeyManager
        instead of directly reading the key file, ensuring consistent security
        practices across the application.
        """
        # Create KeyManager and VotingService
        key_manager = KeyManager(working_directory=str(temp_key_dir))
        voting_service = VotingService(key_manager=key_manager)
        
        # Access the account property (should trigger lazy loading)
        account = voting_service.account
        
        # Verify account is loaded correctly
        assert account is not None
        # Compare keys ensuring both have the same format
        account_key = account.key.hex()
        if account_key.startswith('0x'):
            account_key = account_key[2:]
        assert account_key == valid_private_key
        assert voting_service._account is not None  # Should be cached

    def test_voting_service_lazy_loads_account(self, temp_key_dir, key_file_with_valid_key):
        """Test that VotingService loads the account lazily.
        
        This test ensures that the private key is only loaded when needed,
        not at initialization time, improving security and performance.
        """
        # Create KeyManager and VotingService
        key_manager = KeyManager(working_directory=str(temp_key_dir))
        
        # Mock the get_private_key method to track calls
        with patch.object(key_manager, 'get_private_key') as mock_get_key:
            mock_get_key.return_value = '0x' + '1' * 64
            
            # Create VotingService - should not load key yet
            voting_service = VotingService(key_manager=key_manager)
            assert mock_get_key.call_count == 0
            assert voting_service._account is None
            
            # Access account - should load key now
            account = voting_service.account
            assert mock_get_key.call_count == 1
            assert voting_service._account is not None
            
            # Access account again - should use cached value
            account2 = voting_service.account
            assert mock_get_key.call_count == 1  # No additional calls
            assert account2 is account  # Same instance

    def test_voting_service_handles_key_manager_errors(self, temp_key_dir):
        """Test that VotingService properly handles KeyManager errors.
        
        This test ensures that errors from KeyManager are properly propagated
        and that the VotingService doesn't mask security-related errors.
        """
        # Create KeyManager without key file
        key_manager = KeyManager(working_directory=str(temp_key_dir))
        voting_service = VotingService(key_manager=key_manager)
        
        # Accessing account should raise KeyManagerError
        with pytest.raises(KeyManagerError) as exc_info:
            _ = voting_service.account
        
        assert "key file not found" in str(exc_info.value).lower()

    def test_voting_service_creates_default_key_manager(self):
        """Test that VotingService creates a default KeyManager if none provided.
        
        This test ensures backward compatibility - VotingService should work
        even if no KeyManager is explicitly provided, by creating one internally.
        """
        # Create VotingService without providing KeyManager
        voting_service = VotingService()
        
        # Should have created a KeyManager internally
        assert voting_service.key_manager is not None
        assert isinstance(voting_service.key_manager, KeyManager)

    def test_voting_service_respects_key_caching(self, temp_key_dir, key_file_with_valid_key, valid_private_key):
        """Test that VotingService benefits from KeyManager's caching.
        
        This test verifies that the key caching mechanism in KeyManager
        is properly utilized by VotingService for performance benefits.
        """
        key_manager = KeyManager(working_directory=str(temp_key_dir))
        voting_service = VotingService(key_manager=key_manager)
        
        # Track file reads using a counter
        read_count = 0
        original_read_content = key_manager._read_file_content
        
        def mock_read_content():
            nonlocal read_count
            read_count += 1
            return original_read_content()
        
        # Patch the _read_file_content method
        key_manager._read_file_content = mock_read_content
        
        # First access should load and cache
        account1 = voting_service.account
        assert read_count == 1
        
        # Clear VotingService's account cache to force reload
        voting_service._account = None
        
        # Second access should use KeyManager's cache
        account2 = voting_service.account
        assert read_count == 1  # Should still be 1 due to cache
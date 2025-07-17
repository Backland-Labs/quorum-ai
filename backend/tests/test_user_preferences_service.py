"""Tests for UserPreferencesService."""

import pytest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from models import UserPreferences, VotingStrategy


class TestUserPreferencesServiceInitialization:
    """Test UserPreferencesService initialization."""

    def test_user_preferences_service_initialization_default_file(self):
        """Test UserPreferencesService initialization with default file."""
        from services.user_preferences_service import UserPreferencesService
        
        service = UserPreferencesService()
        
        assert service.preferences_file == "user_preferences.txt"

    def test_user_preferences_service_initialization_custom_file(self):
        """Test UserPreferencesService initialization with custom file."""
        from services.user_preferences_service import UserPreferencesService
        
        service = UserPreferencesService(preferences_file="custom_preferences.json")
        
        assert service.preferences_file == "custom_preferences.json"


class TestUserPreferencesServiceLoadPreferences:
    """Test UserPreferencesService load_preferences method."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "conservative", "confidence_threshold": 0.8, "max_proposals_per_run": 5, "blacklisted_proposers": ["0x123"], "whitelisted_proposers": ["0x456"]}')
    @patch("os.path.exists")
    async def test_load_preferences_success(self, mock_exists, mock_file):
        """Test successful preferences loading from file."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        preferences = await service.load_preferences()
        
        assert preferences.voting_strategy == VotingStrategy.CONSERVATIVE
        assert preferences.confidence_threshold == 0.8
        assert preferences.max_proposals_per_run == 5
        assert preferences.blacklisted_proposers == ["0x123"]
        assert preferences.whitelisted_proposers == ["0x456"]

    @patch("os.path.exists")
    async def test_load_preferences_file_not_found(self, mock_exists):
        """Test loading preferences when file doesn't exist returns defaults."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = False
        service = UserPreferencesService("nonexistent.txt")
        
        preferences = await service.load_preferences()
        
        # Should return default preferences
        assert preferences.voting_strategy == VotingStrategy.BALANCED
        assert preferences.confidence_threshold == 0.7
        assert preferences.max_proposals_per_run == 3
        assert preferences.blacklisted_proposers == []
        assert preferences.whitelisted_proposers == []

    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": "json", "missing": "required_fields"}')
    @patch("os.path.exists")
    async def test_load_preferences_invalid_json_structure(self, mock_exists, mock_file):
        """Test loading preferences with invalid JSON structure returns defaults."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("invalid_preferences.txt")
        
        preferences = await service.load_preferences()
        
        # Should return default preferences on invalid JSON structure
        assert preferences.voting_strategy == VotingStrategy.BALANCED
        assert preferences.confidence_threshold == 0.7
        assert preferences.max_proposals_per_run == 3

    @patch("builtins.open", new_callable=mock_open, read_data='invalid json content')
    @patch("os.path.exists")
    async def test_load_preferences_invalid_json_syntax(self, mock_exists, mock_file):
        """Test loading preferences with invalid JSON syntax returns defaults."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("corrupt_preferences.txt")
        
        preferences = await service.load_preferences()
        
        # Should return default preferences on JSON parse error
        assert preferences.voting_strategy == VotingStrategy.BALANCED
        assert preferences.confidence_threshold == 0.7

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    @patch("os.path.exists")
    async def test_load_preferences_permission_error(self, mock_exists, mock_file):
        """Test loading preferences with permission error returns defaults."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("permission_denied.txt")
        
        preferences = await service.load_preferences()
        
        # Should return default preferences on permission error
        assert preferences.voting_strategy == VotingStrategy.BALANCED
        assert preferences.confidence_threshold == 0.7

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "invalid_strategy"}')
    @patch("os.path.exists")
    async def test_load_preferences_invalid_field_values(self, mock_exists, mock_file):
        """Test loading preferences with invalid field values returns defaults."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("invalid_values.txt")
        
        preferences = await service.load_preferences()
        
        # Should return default preferences on validation error
        assert preferences.voting_strategy == VotingStrategy.BALANCED

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "aggressive", "confidence_threshold": 0.9}')
    @patch("os.path.exists")
    async def test_load_preferences_partial_data(self, mock_exists, mock_file):
        """Test loading preferences with partial data fills in defaults."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("partial_preferences.txt")
        
        preferences = await service.load_preferences()
        
        # Should use provided values and fill in defaults for missing fields
        assert preferences.voting_strategy == VotingStrategy.AGGRESSIVE
        assert preferences.confidence_threshold == 0.9
        assert preferences.max_proposals_per_run == 3  # default
        assert preferences.blacklisted_proposers == []  # default
        assert preferences.whitelisted_proposers == []  # default


class TestUserPreferencesServiceSavePreferences:
    """Test UserPreferencesService save_preferences method."""

    @patch("os.rename")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.makedirs")
    async def test_save_preferences_success(self, mock_makedirs, mock_temp_file, mock_rename):
        """Test successful preferences saving to file."""
        from services.user_preferences_service import UserPreferencesService
        
        # Mock temporary file
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "temp_file.tmp"
        mock_temp_file_obj.__enter__.return_value = mock_temp_file_obj
        mock_temp_file_obj.__exit__.return_value = None
        mock_temp_file.return_value = mock_temp_file_obj
        
        service = UserPreferencesService("test_preferences.txt")
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.CONSERVATIVE,
            confidence_threshold=0.8,
            max_proposals_per_run=5,
            blacklisted_proposers=["0x123"],
            whitelisted_proposers=["0x456"]
        )
        
        await service.save_preferences(preferences)
        
        # Check that atomic write was used
        mock_temp_file.assert_called_once()
        mock_rename.assert_called_once_with("temp_file.tmp", "test_preferences.txt")
        
        # Check that JSON was written to temp file
        mock_temp_file_obj.write.assert_called()

    @patch("os.rename")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.makedirs")
    async def test_save_preferences_creates_directory(self, mock_makedirs, mock_temp_file, mock_rename):
        """Test that save_preferences creates directory if it doesn't exist."""
        from services.user_preferences_service import UserPreferencesService
        
        # Mock temporary file
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "temp_file.tmp"
        mock_temp_file_obj.__enter__.return_value = mock_temp_file_obj
        mock_temp_file_obj.__exit__.return_value = None
        mock_temp_file.return_value = mock_temp_file_obj
        
        service = UserPreferencesService("subdir/test_preferences.txt")
        preferences = UserPreferences()
        
        await service.save_preferences(preferences)
        
        # Check that directory was created
        mock_makedirs.assert_called_once_with("subdir", exist_ok=True)

    @patch("tempfile.NamedTemporaryFile", side_effect=PermissionError("Permission denied"))
    @patch("os.makedirs")
    async def test_save_preferences_permission_error(self, mock_makedirs, mock_temp_file):
        """Test save_preferences handles permission error gracefully."""
        from services.user_preferences_service import UserPreferencesService
        
        service = UserPreferencesService("readonly_preferences.txt")
        preferences = UserPreferences()
        
        # Should not raise exception, just log error
        await service.save_preferences(preferences)
        
        # Temp file should have been attempted to be created
        mock_temp_file.assert_called_once()

    @patch("tempfile.NamedTemporaryFile")
    @patch("os.rename")
    @patch("os.makedirs")
    async def test_save_preferences_atomic_write(self, mock_makedirs, mock_rename, mock_temp_file):
        """Test save_preferences uses atomic write operations."""
        from services.user_preferences_service import UserPreferencesService
        
        # Mock temporary file
        mock_temp_file_obj = MagicMock()
        mock_temp_file_obj.name = "temp_file.tmp"
        mock_temp_file_obj.__enter__.return_value = mock_temp_file_obj
        mock_temp_file_obj.__exit__.return_value = None
        mock_temp_file.return_value = mock_temp_file_obj
        
        service = UserPreferencesService("atomic_preferences.txt")
        preferences = UserPreferences()
        
        await service.save_preferences(preferences)
        
        # Check that atomic write was used
        mock_temp_file.assert_called_once()
        mock_rename.assert_called_once_with("temp_file.tmp", "atomic_preferences.txt")


class TestUserPreferencesServiceUpdatePreference:
    """Test UserPreferencesService update_preference method."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_voting_strategy(self, mock_exists, mock_file):
        """Test updating voting strategy preference."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        # Mock the save_preferences method to avoid actual file writing
        with patch.object(service, 'save_preferences', new_callable=AsyncMock) as mock_save:
            await service.update_preference("voting_strategy", "conservative")
            
            # Check that save_preferences was called with updated preferences
            mock_save.assert_called_once()
            saved_preferences = mock_save.call_args[0][0]
            assert saved_preferences.voting_strategy == VotingStrategy.CONSERVATIVE

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_confidence_threshold(self, mock_exists, mock_file):
        """Test updating confidence threshold preference."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        with patch.object(service, 'save_preferences', new_callable=AsyncMock) as mock_save:
            await service.update_preference("confidence_threshold", 0.85)
            
            mock_save.assert_called_once()
            saved_preferences = mock_save.call_args[0][0]
            assert saved_preferences.confidence_threshold == 0.85

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_max_proposals_per_run(self, mock_exists, mock_file):
        """Test updating max proposals per run preference."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        with patch.object(service, 'save_preferences', new_callable=AsyncMock) as mock_save:
            await service.update_preference("max_proposals_per_run", 7)
            
            mock_save.assert_called_once()
            saved_preferences = mock_save.call_args[0][0]
            assert saved_preferences.max_proposals_per_run == 7

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_blacklisted_proposers(self, mock_exists, mock_file):
        """Test updating blacklisted proposers preference."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        with patch.object(service, 'save_preferences', new_callable=AsyncMock) as mock_save:
            await service.update_preference("blacklisted_proposers", ["0x123", "0x456"])
            
            mock_save.assert_called_once()
            saved_preferences = mock_save.call_args[0][0]
            assert saved_preferences.blacklisted_proposers == ["0x123", "0x456"]

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_whitelisted_proposers(self, mock_exists, mock_file):
        """Test updating whitelisted proposers preference."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        with patch.object(service, 'save_preferences', new_callable=AsyncMock) as mock_save:
            await service.update_preference("whitelisted_proposers", ["0x789", "0xabc"])
            
            mock_save.assert_called_once()
            saved_preferences = mock_save.call_args[0][0]
            assert saved_preferences.whitelisted_proposers == ["0x789", "0xabc"]

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_invalid_key(self, mock_exists, mock_file):
        """Test updating preference with invalid key raises error."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        with pytest.raises(ValueError, match="Invalid preference key"):
            await service.update_preference("invalid_key", "value")

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_invalid_value(self, mock_exists, mock_file):
        """Test updating preference with invalid value raises error."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("test_preferences.txt")
        
        with pytest.raises(ValueError, match="Invalid value"):
            await service.update_preference("confidence_threshold", 1.5)  # Out of range


class TestUserPreferencesServiceConcurrentAccess:
    """Test UserPreferencesService concurrent access scenarios."""

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_concurrent_load_and_save(self, mock_exists, mock_file):
        """Test concurrent load and save operations."""
        from services.user_preferences_service import UserPreferencesService
        import asyncio
        
        mock_exists.return_value = True
        service = UserPreferencesService("concurrent_preferences.txt")
        
        # Simulate concurrent operations
        async def concurrent_operations():
            tasks = []
            
            # Create multiple concurrent operations
            for i in range(5):
                tasks.append(service.load_preferences())
                
            preferences = UserPreferences(confidence_threshold=0.8)
            for i in range(3):
                tasks.append(service.save_preferences(preferences))
            
            # Wait for all operations to complete
            await asyncio.gather(*tasks)
        
        # Should not raise any exceptions
        await concurrent_operations()


class TestUserPreferencesServiceErrorHandling:
    """Test UserPreferencesService error handling scenarios."""

    @patch("builtins.open", side_effect=OSError("Disk full"))
    @patch("os.path.exists")
    async def test_load_preferences_os_error(self, mock_exists, mock_file):
        """Test load_preferences handles OS errors gracefully."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("error_preferences.txt")
        
        # Should not raise exception, return defaults
        preferences = await service.load_preferences()
        assert preferences.voting_strategy == VotingStrategy.BALANCED

    @patch("tempfile.NamedTemporaryFile", side_effect=OSError("Disk full"))
    @patch("os.makedirs")
    async def test_save_preferences_os_error(self, mock_makedirs, mock_temp_file):
        """Test save_preferences handles OS errors gracefully."""
        from services.user_preferences_service import UserPreferencesService
        
        service = UserPreferencesService("error_preferences.txt")
        preferences = UserPreferences()
        
        # Should not raise exception, just log error
        await service.save_preferences(preferences)
        
        # Temp file should have been attempted to be created
        mock_temp_file.assert_called_once()

    @patch("builtins.open", new_callable=mock_open, read_data='{"voting_strategy": "balanced", "confidence_threshold": 0.7, "max_proposals_per_run": 3, "blacklisted_proposers": [], "whitelisted_proposers": []}')
    @patch("os.path.exists")
    async def test_update_preference_load_error(self, mock_exists, mock_file):
        """Test update_preference handles load errors gracefully."""
        from services.user_preferences_service import UserPreferencesService
        
        mock_exists.return_value = True
        service = UserPreferencesService("load_error_preferences.txt")
        
        # Mock load_preferences to raise an error
        with patch.object(service, 'load_preferences', side_effect=OSError("Load error")):
            with pytest.raises(OSError):
                await service.update_preference("voting_strategy", "conservative")
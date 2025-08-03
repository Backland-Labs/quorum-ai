"""Test suite for the State Persistence Manager service.

This module contains comprehensive tests for the state manager service that handles
persistent data storage for the Quorum AI agent. Each test validates critical
functionality required for reliable state persistence in the Pearl/Olas environment.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from datetime import datetime, timezone

from services.state_manager import (
    StateManager,
    StateCorruptionError,
    StateMigrationError,
    StatePermissionError,
    StateSchema,
    StateVersion
)


class TestStateManager:
    """Test suite for StateManager service."""

    @pytest.fixture
    async def state_manager(self, tmp_path):
        """Create a StateManager instance with a temporary directory.
        
        This fixture ensures each test has an isolated storage environment
        to prevent test interference and validate state isolation.
        """
        with patch.dict(os.environ, {'STORE_PATH': str(tmp_path)}):
            manager = StateManager()
            yield manager
            # Cleanup any locks or resources
            if hasattr(manager, 'cleanup'):
                await manager.cleanup()

    @pytest.fixture
    def sample_state_data(self):
        """Provide sample state data for testing.
        
        This represents typical state data that the agent would persist,
        including user preferences, voting history, and agent configuration.
        """
        return {
            "user_preferences": {
                "voting_strategy": "balanced",
                "risk_threshold": 0.7,
                "auto_vote_enabled": True
            },
            "voting_history": [
                {
                    "proposal_id": "0x123",
                    "vote": "FOR",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ],
            "agent_config": {
                "poll_interval": 300,
                "max_retries": 3
            }
        }

    @pytest.mark.asyncio
    async def test_store_path_environment_variable_handling(self, tmp_path):
        """Test that StateManager correctly uses STORE_PATH environment variable.
        
        This test is critical because Pearl/Olas agents must store all persistent
        data in the designated STORE_PATH directory. Failure to do so could result
        in data loss when the container is restarted.
        """
        # Test with STORE_PATH set
        custom_path = tmp_path / "custom_store"
        with patch.dict(os.environ, {'STORE_PATH': str(custom_path)}):
            manager = StateManager()
            assert manager.store_path == custom_path
            assert manager.store_path.exists()
            assert manager.store_path.is_dir()

        # Test without STORE_PATH (should use default)
        with patch.dict(os.environ, {}, clear=True):
            manager = StateManager()
            assert manager.store_path == Path.home() / ".quorum_ai" / "state"
            
    @pytest.mark.asyncio
    async def test_atomic_file_save_operation(self, state_manager, sample_state_data):
        """Test atomic file save operations to prevent data corruption.
        
        Atomic writes are essential for data integrity. This test verifies that
        state saves are atomic - either fully completed or not at all. This prevents
        partial writes that could corrupt the state file during crashes or interruptions.
        """
        # Save state atomically
        state_file = await state_manager.save_state("test_state", sample_state_data)
        
        # Verify file exists and contains correct data
        assert state_file.exists()
        
        # Verify atomic operation by checking no temp files remain
        temp_files = list(state_file.parent.glob("*.tmp"))
        assert len(temp_files) == 0
        
        # Verify saved data integrity
        loaded_data = await state_manager.load_state("test_state")
        assert loaded_data == sample_state_data

    @pytest.mark.asyncio
    async def test_atomic_file_load_operation(self, state_manager, sample_state_data):
        """Test atomic file load operations with validation.
        
        Loading state must be reliable and validate data integrity. This test
        ensures that corrupted or invalid state files are detected and handled
        appropriately to prevent the agent from operating with bad data.
        """
        # First save valid state
        await state_manager.save_state("test_state", sample_state_data)
        
        # Test loading valid state
        loaded_data = await state_manager.load_state("test_state")
        assert loaded_data == sample_state_data
        
        # Test loading non-existent state returns None
        missing_data = await state_manager.load_state("missing_state")
        assert missing_data is None

    @pytest.mark.asyncio
    async def test_corruption_detection_and_recovery(self, state_manager, sample_state_data):
        """Test detection of corrupted state files and recovery mechanisms.
        
        State corruption can occur due to disk errors, incomplete writes, or
        manual tampering. This test verifies that the system can detect corruption
        via checksums and recover using backups, ensuring agent resilience.
        """
        # Save valid state with checksum
        state_file = await state_manager.save_state("test_state", sample_state_data)
        
        # Save again to create a backup
        await state_manager.save_state("test_state", sample_state_data)
        
        # Corrupt the state file
        with open(state_file, 'r') as f:
            content = json.load(f)
        
        # Modify data without updating checksum
        content['data']['user_preferences']['voting_strategy'] = 'aggressive'
        
        with open(state_file, 'w') as f:
            json.dump(content, f)
        
        # Attempt to load corrupted state
        with pytest.raises(StateCorruptionError) as exc_info:
            await state_manager.load_state("test_state")
        
        assert "checksum mismatch" in str(exc_info.value)
        
        # Verify automatic recovery from backup
        recovered_data = await state_manager.load_state("test_state", allow_recovery=True)
        assert recovered_data == sample_state_data

    @pytest.mark.asyncio
    async def test_concurrent_access_protection(self, state_manager, sample_state_data):
        """Test protection against concurrent access to state files.
        
        Multiple processes or threads might try to access state simultaneously.
        This test ensures that file locking prevents race conditions and data
        corruption from concurrent writes, maintaining data consistency.
        """
        # Create multiple concurrent save operations
        async def save_with_id(manager, id_suffix):
            data = sample_state_data.copy()
            data['id'] = f"concurrent_{id_suffix}"
            await manager.save_state("concurrent_test", data)
            return data
        
        # Run concurrent saves
        tasks = [save_with_id(state_manager, i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # Verify only one write succeeded (last one)
        final_data = await state_manager.load_state("concurrent_test")
        assert final_data in results
        
        # Verify no corruption occurred
        assert 'id' in final_data
        assert final_data['id'].startswith('concurrent_')

    @pytest.mark.asyncio
    async def test_state_migration_from_old_locations(self, state_manager, tmp_path, sample_state_data):
        """Test migration of state from legacy storage locations.
        
        When upgrading the agent, old state files might exist in different locations
        or formats. This test ensures smooth migration to the new structure without
        data loss, maintaining continuity for users.
        """
        # Create old state file in legacy location
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        legacy_file = legacy_dir / "old_state.json"
        
        # Save in old format (no versioning or checksum)
        with open(legacy_file, 'w') as f:
            json.dump(sample_state_data, f)
        
        # Configure manager to check legacy location
        state_manager.add_migration_path(legacy_dir)
        
        # Attempt to load state (should trigger migration)
        migrated_data = await state_manager.load_state("old_state")
        assert migrated_data == sample_state_data
        
        # Verify state was migrated to new location with proper format
        new_file = state_manager.store_path / "old_state.json"
        assert new_file.exists()
        
        with open(new_file, 'r') as f:
            new_content = json.load(f)
        
        assert 'version' in new_content
        assert 'checksum' in new_content
        assert new_content['data'] == sample_state_data

    @pytest.mark.asyncio
    async def test_permission_validation_for_sensitive_files(self, state_manager, sample_state_data):
        """Test validation of file permissions for sensitive state data.
        
        State files may contain sensitive information like API keys or voting
        strategies. This test ensures files are created with restrictive permissions
        (owner-only access) to prevent unauthorized access in shared environments.
        """
        # Save sensitive state
        sensitive_data = sample_state_data.copy()
        sensitive_data['api_keys'] = {'openrouter': 'secret_key'}
        
        state_file = await state_manager.save_state("sensitive_state", sensitive_data, sensitive=True)
        
        # Check file permissions (owner read/write only)
        stat_info = os.stat(state_file)
        permissions = stat_info.st_mode & 0o777
        
        # Should be 0o600 (owner read/write only)
        assert permissions == 0o600
        
        # Test rejection of world-readable files
        os.chmod(state_file, 0o644)
        
        with pytest.raises(StatePermissionError) as exc_info:
            await state_manager.load_state("sensitive_state", sensitive=True)
        
        assert "insufficient permissions" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_schema_validation_on_load(self, state_manager):
        """Test schema validation when loading state data.
        
        Schema validation ensures that loaded state conforms to expected structure,
        preventing runtime errors from missing or incorrectly typed fields. This is
        crucial for maintaining agent stability across updates.
        """
        # Define a schema for user preferences
        preferences_schema = StateSchema(
            required_fields=['voting_strategy', 'risk_threshold'],
            field_types={
                'voting_strategy': str,
                'risk_threshold': float,
                'auto_vote_enabled': bool
            },
            validators={
                'risk_threshold': lambda x: 0.0 <= x <= 1.0,
                'voting_strategy': lambda x: x in ['balanced', 'conservative', 'aggressive']
            }
        )
        
        # Save valid data
        valid_data = {
            'voting_strategy': 'balanced',
            'risk_threshold': 0.7,
            'auto_vote_enabled': True
        }
        await state_manager.save_state("preferences", valid_data, schema=preferences_schema)
        
        # Load with schema validation
        loaded = await state_manager.load_state("preferences", schema=preferences_schema)
        assert loaded == valid_data
        
        # Test invalid data
        invalid_data = {
            'voting_strategy': 'invalid_strategy',
            'risk_threshold': 1.5  # Out of range
        }
        
        with pytest.raises(ValueError) as exc_info:
            await state_manager.save_state("invalid_prefs", invalid_data, schema=preferences_schema)
        
        assert "schema validation failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_backup_and_restore_functionality(self, state_manager, sample_state_data):
        """Test automatic backup creation and restore capabilities.
        
        Backups provide a safety net against data loss from corruption or bad updates.
        This test verifies that the system maintains rotating backups and can restore
        from them when needed, ensuring data durability.
        """
        # Save state multiple times to create backup history
        # First save creates no backup
        await state_manager.save_state("test_state", {'version': 0})
        
        # Next saves create backups
        for i in range(1, 5):
            data = sample_state_data.copy()
            data['version'] = i
            await state_manager.save_state("test_state", data)
            await asyncio.sleep(0.1)  # Ensure different timestamps
        
        # List available backups
        backups = await state_manager.list_backups("test_state")
        assert len(backups) >= 3  # Should keep at least 3 backups
        
        # Restore from specific backup
        restored = await state_manager.restore_from_backup("test_state", backups[1])
        assert restored['version'] < 4  # Should be an earlier version
        
        # Test backup rotation (max 5 backups by default)
        for i in range(10):
            await state_manager.save_state("test_state", {'version': i + 5})
        
        backups = await state_manager.list_backups("test_state")
        assert len(backups) <= 5  # Should rotate old backups

    @pytest.mark.asyncio
    async def test_state_versioning_and_compatibility(self, state_manager):
        """Test state versioning for backward compatibility.
        
        As the agent evolves, state structure may change. This test ensures that
        the system can handle different state versions and migrate old formats
        to new ones, preventing breaks during updates.
        """
        # Define version 1 state
        v1_data = {
            'preferences': {
                'strategy': 'balanced'  # Old field name
            }
        }
        
        # Define migration from v1 to v2
        async def migrate_v1_to_v2(data):
            """Migrate strategy field to voting_strategy."""
            if 'preferences' in data and 'strategy' in data['preferences']:
                data['preferences']['voting_strategy'] = data['preferences'].pop('strategy')
            return data
        
        state_manager.register_migration(
            from_version=StateVersion(1, 0, 0),
            to_version=StateVersion(2, 0, 0),
            migration_func=migrate_v1_to_v2
        )
        
        # Save v1 state
        await state_manager.save_state("versioned_state", v1_data, version=StateVersion(1, 0, 0))
        
        # Load with automatic migration to v2
        loaded = await state_manager.load_state("versioned_state", target_version=StateVersion(2, 0, 0))
        
        assert 'voting_strategy' in loaded['preferences']
        assert loaded['preferences']['voting_strategy'] == 'balanced'
        assert 'strategy' not in loaded['preferences']

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, state_manager, caplog):
        """Test comprehensive error handling and Pearl-compliant logging.
        
        Proper error handling and logging are essential for debugging issues in
        production. This test verifies that all operations log appropriately and
        errors are handled gracefully with informative messages.
        """
        # Test logging for successful operations
        await state_manager.save_state("test_state", {"test": "data"})
        assert "Successfully saved state" in caplog.text
        assert "test_state" in caplog.text
        
        # Test error logging for corrupted data
        # Create a corrupted state file
        corrupted_file = state_manager.store_path / "corrupted_state.json"
        with open(corrupted_file, 'w') as f:
            f.write("{ invalid json")
        
        with pytest.raises(json.JSONDecodeError):
            await state_manager.load_state("corrupted_state")
        
        assert "Failed to load state corrupted_state" in caplog.text
        assert "ERROR" in caplog.text
        
        # Cleanup
        corrupted_file.unlink()

    @pytest.mark.asyncio
    async def test_performance_optimization(self, state_manager, sample_state_data):
        """Test performance optimizations for large state files.
        
        The agent may accumulate large amounts of historical data. This test
        ensures that the state manager can handle large files efficiently without
        blocking the event loop or consuming excessive memory.
        """
        # Create large state data (1MB+)
        large_data = {
            "history": [
                {
                    "id": f"item_{i}",
                    "data": "x" * 1000,  # 1KB per item
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                for i in range(1000)  # 1000 items = ~1MB
            ]
        }
        
        # Measure save performance
        start_time = asyncio.get_event_loop().time()
        await state_manager.save_state("large_state", large_data)
        save_duration = asyncio.get_event_loop().time() - start_time
        
        # Should complete reasonably fast (under 1 second for 1MB)
        assert save_duration < 1.0
        
        # Measure load performance
        start_time = asyncio.get_event_loop().time()
        loaded = await state_manager.load_state("large_state")
        load_duration = asyncio.get_event_loop().time() - start_time
        
        assert load_duration < 1.0
        assert len(loaded['history']) == 1000
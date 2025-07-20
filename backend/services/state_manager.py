"""State Persistence Manager for Quorum AI Agent.

This module provides a robust state persistence system that handles all persistent
data storage for the agent. It ensures data integrity, supports atomic operations,
and provides migration capabilities for evolving state schemas.
"""

import asyncio
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from logging_config import setup_pearl_logger


class StateCorruptionError(Exception):
    """Raised when state file corruption is detected."""

    pass


class StateMigrationError(Exception):
    """Raised when state migration fails."""

    pass


class StatePermissionError(Exception):
    """Raised when file permissions are insufficient."""

    pass


@dataclass(frozen=True)
class StateVersion:
    """Represents a semantic version for state schemas."""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "StateVersion") -> bool:
        return (self.major, self.minor, self.patch) < (
            other.major,
            other.minor,
            other.patch,
        )

    def __le__(self, other: "StateVersion") -> bool:
        return (self.major, self.minor, self.patch) <= (
            other.major,
            other.minor,
            other.patch,
        )

    def __gt__(self, other: "StateVersion") -> bool:
        return (self.major, self.minor, self.patch) > (
            other.major,
            other.minor,
            other.patch,
        )

    def __ge__(self, other: "StateVersion") -> bool:
        return (self.major, self.minor, self.patch) >= (
            other.major,
            other.minor,
            other.patch,
        )

    def __eq__(self, other: "StateVersion") -> bool:
        return (self.major, self.minor, self.patch) == (
            other.major,
            other.minor,
            other.patch,
        )


@dataclass
class StateSchema:
    """Defines the schema for validating state data."""

    required_fields: List[str]
    field_types: Dict[str, type]
    validators: Dict[str, Callable[[Any], bool]]


class StateManager:
    """Manages persistent state storage for the Quorum AI agent."""

    def __init__(self):
        """Initialize the state manager with configured storage paths."""
        # Set up Pearl-compliant logging
        self.logger = setup_pearl_logger("state_manager")

        # Get store path from environment or use default
        store_path_env = os.environ.get("STORE_PATH")
        if store_path_env:
            self.store_path = Path(store_path_env)
        else:
            self.store_path = Path.home() / ".quorum_ai" / "state"

        # Ensure store path exists
        self.store_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for organization
        self.backups_dir = self.store_path / "backups"
        self.backups_dir.mkdir(exist_ok=True)

        # Migration paths for legacy data
        self._migration_paths: List[Path] = []

        # Registered migrations
        self._migrations: Dict[Tuple[StateVersion, StateVersion], Callable] = {}

        # File locks for concurrent access protection
        self._locks: Dict[str, asyncio.Lock] = {}

        # Maximum number of backups to keep
        self.max_backups = 5

    async def save_state(
        self,
        name: str,
        data: Dict[str, Any],
        sensitive: bool = False,
        schema: Optional[StateSchema] = None,
        version: Optional[StateVersion] = None,
    ) -> Path:
        """Save state data atomically."""
        # Validate schema if provided
        if schema:
            self._validate_schema(data, schema)

        # Get or create lock for this state file
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()

        async with self._locks[name]:
            state_file = self.store_path / f"{name}.json"

            # Create backup of existing file
            if state_file.exists():
                await self._create_backup(name, state_file)

            # Prepare state data with metadata
            state_data = {
                "version": str(version) if version else "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data,
                "checksum": self._calculate_checksum(data),
            }

            # Write atomically using temporary file
            temp_fd, temp_path = tempfile.mkstemp(dir=self.store_path, suffix=".tmp")
            try:
                with os.fdopen(temp_fd, "w") as f:
                    json.dump(state_data, f, indent=2)

                # Set permissions for sensitive files
                if sensitive:
                    os.chmod(temp_path, 0o600)

                # Atomic rename
                Path(temp_path).replace(state_file)

                # Check if file is writable after creation
                if not os.access(state_file, os.W_OK):
                    raise PermissionError(f"State file {name} is not writable")

                self.logger.info(f"Successfully saved state: {name}")
                return state_file

            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                self.logger.error(f"Failed to save state {name}: {e}")
                raise

    async def load_state(
        self,
        name: str,
        sensitive: bool = False,
        schema: Optional[StateSchema] = None,
        allow_recovery: bool = False,
        target_version: Optional[StateVersion] = None,
    ) -> Optional[Dict[str, Any]]:
        """Load state data with validation."""
        state_file = self.store_path / f"{name}.json"

        # Try to find state file, migrating if necessary
        state_file = await self._find_or_migrate_state(name, state_file)
        if not state_file or not state_file.exists():
            return None

        # Validate permissions for sensitive files
        if sensitive:
            self._validate_file_permissions(state_file, name)

        try:
            # Load and validate state data
            data = await self._load_and_validate_state(state_file, name, target_version)

            # Validate schema if provided
            if schema:
                self._validate_schema(data, schema)

            return data

        except (json.JSONDecodeError, StateCorruptionError) as e:
            self.logger.error(f"Failed to load state {name}: {e}")

            if allow_recovery:
                return await self._attempt_recovery(name)

            raise

    async def _find_or_migrate_state(
        self, name: str, state_file: Path
    ) -> Optional[Path]:
        """Find state file or migrate from legacy location."""
        if state_file.exists():
            return state_file

        for migration_path in self._migration_paths:
            legacy_file = migration_path / f"{name}.json"
            if legacy_file.exists():
                await self._migrate_legacy_file(legacy_file, state_file)
                return state_file

        return None

    def _validate_file_permissions(self, state_file: Path, name: str) -> None:
        """Validate file permissions for sensitive files."""
        stat_info = os.stat(state_file)
        permissions = stat_info.st_mode & 0o777
        if permissions != 0o600:
            raise StatePermissionError(
                f"State file {name} has insufficient permissions: {oct(permissions)}"
            )

    async def _load_and_validate_state(
        self, state_file: Path, name: str, target_version: Optional[StateVersion]
    ) -> Dict[str, Any]:
        """Load state data and validate integrity."""
        with open(state_file, "r") as f:
            state_data = json.load(f)

        # Verify checksum
        if "checksum" in state_data:
            expected_checksum = state_data["checksum"]
            actual_checksum = self._calculate_checksum(state_data["data"])
            if expected_checksum != actual_checksum:
                raise StateCorruptionError(f"State file {name} has checksum mismatch")

        data = state_data.get("data", state_data)  # Handle legacy format

        # Apply migrations if needed
        if target_version and "version" in state_data:
            current_version = self._parse_version(state_data["version"])
            if current_version < target_version:
                data = await self._apply_migrations(
                    data, current_version, target_version
                )

        return data

    async def _attempt_recovery(self, name: str) -> Optional[Dict[str, Any]]:
        """Attempt to recover from backup."""
        backups = await self.list_backups(name)
        if backups:
            self.logger.info(f"Attempting to recover {name} from backup")
            return await self.restore_from_backup(name, backups[0])
        return None

    def add_migration_path(self, path: Path) -> None:
        """Add a legacy path to check for state migration."""
        self._migration_paths.append(path)

    def register_migration(
        self,
        from_version: StateVersion,
        to_version: StateVersion,
        migration_func: Callable,
    ) -> None:
        """Register a migration function between versions."""
        self._migrations[(from_version, to_version)] = migration_func

    async def list_backups(self, name: str) -> List[Path]:
        """List available backups for a state file."""
        backup_pattern = f"{name}.*.backup"
        backups = sorted(
            self.backups_dir.glob(backup_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return backups

    async def restore_from_backup(
        self, _name: str, backup_path: Path
    ) -> Dict[str, Any]:
        """Restore state from a specific backup."""
        with open(backup_path, "r") as f:
            backup_data = json.load(f)

        # Verify backup integrity
        if "checksum" in backup_data:
            expected_checksum = backup_data["checksum"]
            actual_checksum = self._calculate_checksum(backup_data["data"])
            if expected_checksum != actual_checksum:
                raise StateCorruptionError(f"Backup {backup_path} is corrupted")

        return backup_data.get("data", backup_data)

    async def cleanup(self) -> None:
        """Cleanup any resources like file locks."""
        # Release all locks
        self._locks.clear()

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate SHA256 checksum of data."""
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def _validate_schema(self, data: Dict[str, Any], schema: StateSchema) -> None:
        """Validate data against schema."""
        # Check required fields
        for field in schema.required_fields:
            if field not in data:
                raise ValueError(
                    f"Schema validation failed: missing required field '{field}'"
                )

        # Check field types
        for field, expected_type in schema.field_types.items():
            if field in data and not isinstance(data[field], expected_type):
                raise ValueError(
                    f"Schema validation failed: field '{field}' has wrong type. "
                    f"Expected {expected_type.__name__}, got {type(data[field]).__name__}"
                )

        # Run custom validators
        for field, validator in schema.validators.items():
            if field in data and not validator(data[field]):
                raise ValueError(
                    f"Schema validation failed: field '{field}' failed validation"
                )

    async def _create_backup(self, name: str, state_file: Path) -> None:
        """Create a backup of the state file."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        backup_file = self.backups_dir / f"{name}.{timestamp}.backup"

        shutil.copy2(state_file, backup_file)

        # Rotate old backups
        backups = await self.list_backups(name)
        if len(backups) > self.max_backups:
            for old_backup in backups[self.max_backups :]:
                old_backup.unlink()

    async def _migrate_legacy_file(self, legacy_file: Path, new_file: Path) -> None:
        """Migrate a legacy state file to the new format."""
        with open(legacy_file, "r") as f:
            data = json.load(f)

        # Save in new format
        await self.save_state(new_file.stem, data)

        self.logger.info(f"Migrated legacy state from {legacy_file} to {new_file}")

    def _parse_version(self, version_str: str) -> StateVersion:
        """Parse version string to StateVersion."""
        parts = version_str.split(".")
        return StateVersion(
            major=int(parts[0]),
            minor=int(parts[1]) if len(parts) > 1 else 0,
            patch=int(parts[2]) if len(parts) > 2 else 0,
        )

    async def _apply_migrations(
        self, data: Dict[str, Any], from_version: StateVersion, to_version: StateVersion
    ) -> Dict[str, Any]:
        """Apply migrations to upgrade data to target version."""
        current_data = data

        # Find and apply migrations in order
        for (from_v, to_v), migration_func in sorted(self._migrations.items()):
            if from_v >= from_version and to_v <= to_version:
                if asyncio.iscoroutinefunction(migration_func):
                    current_data = await migration_func(current_data)
                else:
                    current_data = migration_func(current_data)

                self.logger.info(f"Applied migration from {from_v} to {to_v}")

        return current_data
    
    async def shutdown(self) -> None:
        """Implement shutdown method for graceful shutdown."""
        self.logger.info("State manager shutdown initiated")
        await self.cleanup()
        self.logger.info("State manager shutdown completed")
    
    async def save_service_state(self) -> None:
        """Save current service state (StateManager has no internal state to save)."""
        # StateManager itself doesn't maintain state that needs to be saved
        # It manages state for other services
        pass
    
    async def stop(self) -> None:
        """Stop the service gracefully."""
        await self.cleanup()


# Example usage:
"""
async def example_usage():
    # Initialize state manager
    manager = StateManager()

    # Save simple state
    await manager.save_state("agent_config", {
        "poll_interval": 300,
        "max_retries": 3,
        "enabled": True
    })

    # Save sensitive state with permissions
    await manager.save_state("api_keys", {
        "openrouter": "secret_key",
        "snapshot": "another_key"
    }, sensitive=True)

    # Define schema for validation
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

    # Save with schema validation
    await manager.save_state("user_preferences", {
        'voting_strategy': 'balanced',
        'risk_threshold': 0.7,
        'auto_vote_enabled': True
    }, schema=preferences_schema)

    # Load state
    config = await manager.load_state("agent_config")
    print(f"Agent config: {config}")

    # Load with schema validation
    prefs = await manager.load_state("user_preferences", schema=preferences_schema)
    print(f"User preferences: {prefs}")

    # Handle versioning
    await manager.save_state("versioned_data",
        {"format": "v1", "data": "example"},
        version=StateVersion(1, 0, 0)
    )

    # Define migration
    def migrate_v1_to_v2(data):
        data['format'] = 'v2'
        data['migrated'] = True
        return data

    manager.register_migration(
        StateVersion(1, 0, 0),
        StateVersion(2, 0, 0),
        migrate_v1_to_v2
    )

    # Load with migration
    migrated = await manager.load_state("versioned_data",
        target_version=StateVersion(2, 0, 0)
    )
    print(f"Migrated data: {migrated}")

    # List backups
    backups = await manager.list_backups("user_preferences")
    if backups:
        # Restore from latest backup
        restored = await manager.restore_from_backup("user_preferences", backups[0])
        print(f"Restored from backup: {restored}")

    # Cleanup
    await manager.cleanup()
"""

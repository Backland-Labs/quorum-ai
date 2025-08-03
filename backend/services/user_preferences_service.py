"""User preferences file management service."""

import os
import json
import tempfile
from typing import Any

from logging_config import setup_pearl_logger
from models import UserPreferences, VotingStrategy


class UserPreferencesService:
    """Service for managing user preferences stored in user_preferences.txt file."""

    def __init__(
        self, preferences_file: str = "user_preferences.txt", state_manager=None
    ):
        """Initialize user preferences service.

        Args:
            preferences_file: Path to the preferences file (default: "user_preferences.txt")
            state_manager: Optional StateManager instance for state persistence
        """
        self.preferences_file = preferences_file
        self.state_manager = state_manager
        self.logger = setup_pearl_logger(__name__)

        # Cache for preferences to avoid frequent reads
        self._preferences_cache = None

    async def load_preferences(self) -> UserPreferences:
        """Load user preferences from file, return defaults if not found.

        Returns:
            UserPreferences: User preferences object with loaded or default values
        """
        # Try state manager first if available
        if self.state_manager:
            try:
                state_data = await self.state_manager.load_state(
                    "user_preferences", sensitive=False, allow_recovery=True
                )
                if state_data:
                    preferences = UserPreferences(**state_data)
                    self._preferences_cache = preferences
                    self.logger.info(
                        "User preferences loaded from state manager, voting_strategy=%s, confidence_threshold=%s, max_proposals_per_run=%s",
                        preferences.voting_strategy.value,
                        preferences.confidence_threshold,
                        preferences.max_proposals_per_run,
                    )
                    return preferences
            except Exception as e:
                self.logger.warning(
                    "Could not load from state manager, falling back to file, error=%s",
                    str(e),
                )

        # Fall back to file-based loading
        try:
            if not os.path.exists(self.preferences_file):
                self.logger.info(
                    "Preferences file not found, returning defaults, preferences_file=%s",
                    self.preferences_file,
                )
                return UserPreferences()

            with open(self.preferences_file, "r") as f:
                data = json.load(f)

            # Try to create UserPreferences from loaded data
            preferences = UserPreferences(**data)
            self._preferences_cache = preferences

            # Migrate to state manager if available
            if self.state_manager:
                await self._migrate_to_state_manager(preferences)

            self.logger.info(
                "User preferences loaded successfully, preferences_file=%s, voting_strategy=%s, confidence_threshold=%s, max_proposals_per_run=%s",
                self.preferences_file,
                preferences.voting_strategy.value,
                preferences.confidence_threshold,
                preferences.max_proposals_per_run,
            )

            return preferences

        except (json.JSONDecodeError, OSError, PermissionError) as e:
            self.logger.warning(
                "Could not load user preferences, returning defaults, preferences_file=%s, error=%s",
                self.preferences_file,
                str(e),
            )
            return UserPreferences()
        except Exception as e:
            self.logger.warning(
                "Unexpected error loading user preferences, returning defaults, preferences_file=%s, error=%s",
                self.preferences_file,
                str(e),
            )
            return UserPreferences()

    async def save_preferences(self, preferences: UserPreferences) -> None:
        """Save preferences to file using atomic write.

        Args:
            preferences: UserPreferences object to save
        """
        # Update cache
        self._preferences_cache = preferences

        # Save to state manager if available
        if self.state_manager:
            try:
                await self.state_manager.save_state(
                    "user_preferences", preferences.model_dump(), sensitive=False
                )
                self.logger.info(
                    "User preferences saved to state manager, voting_strategy=%s, confidence_threshold=%s, max_proposals_per_run=%s",
                    preferences.voting_strategy.value,
                    preferences.confidence_threshold,
                    preferences.max_proposals_per_run,
                )
                # Also save to file for backward compatibility
            except Exception as e:
                self.logger.error(
                    "Could not save to state manager, falling back to file, error=%s",
                    str(e),
                )

        # Save to file (for backward compatibility or as fallback)
        try:
            # Ensure directory exists
            directory = os.path.dirname(self.preferences_file)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # Serialize preferences to JSON
            data = preferences.model_dump()

            # Use atomic write with temporary file
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=os.path.dirname(self.preferences_file) or ".",
                delete=False,
            ) as temp_file:
                json.dump(data, temp_file, indent=2)
                temp_file_path = temp_file.name

            # Atomically rename temp file to final location
            os.rename(temp_file_path, self.preferences_file)

            self.logger.info(
                "User preferences saved successfully, preferences_file=%s, voting_strategy=%s, confidence_threshold=%s, max_proposals_per_run=%s",
                self.preferences_file,
                preferences.voting_strategy.value,
                preferences.confidence_threshold,
                preferences.max_proposals_per_run,
            )

        except (OSError, PermissionError) as e:
            self.logger.error(
                "Could not save user preferences, preferences_file=%s, error=%s",
                self.preferences_file,
                str(e),
            )
            # Clean up temp file if it exists
            try:
                if "temp_file_path" in locals():
                    os.unlink(temp_file_path)
            except:
                pass
        except Exception as e:
            self.logger.error(
                "Unexpected error saving user preferences, preferences_file=%s, error=%s",
                self.preferences_file,
                str(e),
            )

    async def update_preference(self, key: str, value: Any) -> None:
        """Update a single preference value.

        Args:
            key: Preference key to update
            value: New value for the preference

        Raises:
            ValueError: If key is invalid or value is invalid for the key
        """
        # Load current preferences
        current_preferences = await self.load_preferences()

        # Validate key and update value
        if key == "voting_strategy":
            if isinstance(value, str):
                try:
                    value = VotingStrategy(value)
                except ValueError:
                    raise ValueError(f"Invalid value for voting_strategy: {value}")
            elif not isinstance(value, VotingStrategy):
                raise ValueError(
                    f"Invalid value type for voting_strategy: {type(value)}"
                )
            current_preferences.voting_strategy = value

        elif key == "confidence_threshold":
            if not isinstance(value, (int, float)):
                raise ValueError(
                    f"Invalid value type for confidence_threshold: {type(value)}"
                )
            if not (0.0 <= value <= 1.0):
                raise ValueError(
                    f"Invalid value for confidence_threshold: {value}. Must be between 0.0 and 1.0"
                )
            current_preferences.confidence_threshold = float(value)

        elif key == "max_proposals_per_run":
            if not isinstance(value, int):
                raise ValueError(
                    f"Invalid value type for max_proposals_per_run: {type(value)}"
                )
            if not (1 <= value <= 10):
                raise ValueError(
                    f"Invalid value for max_proposals_per_run: {value}. Must be between 1 and 10"
                )
            current_preferences.max_proposals_per_run = value

        elif key == "blacklisted_proposers":
            if not isinstance(value, list):
                raise ValueError(
                    f"Invalid value type for blacklisted_proposers: {type(value)}"
                )
            if not all(isinstance(item, str) for item in value):
                raise ValueError("All items in blacklisted_proposers must be strings")
            current_preferences.blacklisted_proposers = value

        elif key == "whitelisted_proposers":
            if not isinstance(value, list):
                raise ValueError(
                    f"Invalid value type for whitelisted_proposers: {type(value)}"
                )
            if not all(isinstance(item, str) for item in value):
                raise ValueError("All items in whitelisted_proposers must be strings")
            current_preferences.whitelisted_proposers = value

        else:
            raise ValueError(f"Invalid preference key: {key}")

        # Save updated preferences
        await self.save_preferences(current_preferences)

        self.logger.info(
            "User preference updated, preferences_file=%s, key=%s, value=%s",
            self.preferences_file,
            key,
            str(value),
        )

    async def shutdown(self) -> None:
        """Implement shutdown method required by ShutdownService protocol."""
        # Save current preferences if cached
        if self._preferences_cache:
            await self.save_preferences(self._preferences_cache)

        self.logger.info("User preferences service shutdown completed")

    async def save_service_state(self) -> None:
        """Save current service state for recovery."""
        if self._preferences_cache:
            await self.save_preferences(self._preferences_cache)

    async def stop(self) -> None:
        """Stop the service gracefully."""
        await self.save_state()

    async def _migrate_to_state_manager(self, preferences: UserPreferences) -> None:
        """Migrate preferences from file to state manager.

        Args:
            preferences: The preferences to migrate
        """
        if not self.state_manager:
            return

        try:
            await self.state_manager.save_state(
                "user_preferences", preferences.model_dump(), sensitive=False
            )
            self.logger.info("Successfully migrated preferences to state manager")
        except Exception as e:
            self.logger.warning(f"Failed to migrate preferences to state manager: {e}")

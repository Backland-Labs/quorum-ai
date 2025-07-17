"""User preferences file management service."""

import os
import json
import tempfile
from typing import Any
import logfire

from models import UserPreferences, VotingStrategy


class UserPreferencesService:
    """Service for managing user preferences stored in user_preferences.txt file."""

    def __init__(self, preferences_file: str = "user_preferences.txt"):
        """Initialize user preferences service.
        
        Args:
            preferences_file: Path to the preferences file (default: "user_preferences.txt")
        """
        self.preferences_file = preferences_file

    async def load_preferences(self) -> UserPreferences:
        """Load user preferences from file, return defaults if not found.
        
        Returns:
            UserPreferences: User preferences object with loaded or default values
        """
        try:
            if not os.path.exists(self.preferences_file):
                logfire.info(
                    "Preferences file not found, returning defaults",
                    preferences_file=self.preferences_file
                )
                return UserPreferences()
            
            with open(self.preferences_file, "r") as f:
                data = json.load(f)
            
            # Try to create UserPreferences from loaded data
            preferences = UserPreferences(**data)
            
            logfire.info(
                "User preferences loaded successfully",
                preferences_file=self.preferences_file,
                voting_strategy=preferences.voting_strategy.value,
                confidence_threshold=preferences.confidence_threshold,
                max_proposals_per_run=preferences.max_proposals_per_run
            )
            
            return preferences
            
        except (json.JSONDecodeError, OSError, PermissionError) as e:
            logfire.warn(
                "Could not load user preferences, returning defaults",
                preferences_file=self.preferences_file,
                error=str(e)
            )
            return UserPreferences()
        except Exception as e:
            logfire.warn(
                "Unexpected error loading user preferences, returning defaults",
                preferences_file=self.preferences_file,
                error=str(e)
            )
            return UserPreferences()

    async def save_preferences(self, preferences: UserPreferences) -> None:
        """Save preferences to file using atomic write.
        
        Args:
            preferences: UserPreferences object to save
        """
        try:
            # Ensure directory exists
            directory = os.path.dirname(self.preferences_file)
            if directory:
                os.makedirs(directory, exist_ok=True)
            
            # Serialize preferences to JSON
            data = preferences.model_dump()
            
            # Use atomic write with temporary file
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=os.path.dirname(self.preferences_file) or '.',
                delete=False
            ) as temp_file:
                json.dump(data, temp_file, indent=2)
                temp_file_path = temp_file.name
            
            # Atomically rename temp file to final location
            os.rename(temp_file_path, self.preferences_file)
            
            logfire.info(
                "User preferences saved successfully",
                preferences_file=self.preferences_file,
                voting_strategy=preferences.voting_strategy.value,
                confidence_threshold=preferences.confidence_threshold,
                max_proposals_per_run=preferences.max_proposals_per_run
            )
            
        except (OSError, PermissionError) as e:
            logfire.error(
                "Could not save user preferences",
                preferences_file=self.preferences_file,
                error=str(e)
            )
            # Clean up temp file if it exists
            try:
                if 'temp_file_path' in locals():
                    os.unlink(temp_file_path)
            except:
                pass
        except Exception as e:
            logfire.error(
                "Unexpected error saving user preferences",
                preferences_file=self.preferences_file,
                error=str(e)
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
                raise ValueError(f"Invalid value type for voting_strategy: {type(value)}")
            current_preferences.voting_strategy = value
            
        elif key == "confidence_threshold":
            if not isinstance(value, (int, float)):
                raise ValueError(f"Invalid value type for confidence_threshold: {type(value)}")
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"Invalid value for confidence_threshold: {value}. Must be between 0.0 and 1.0")
            current_preferences.confidence_threshold = float(value)
            
        elif key == "max_proposals_per_run":
            if not isinstance(value, int):
                raise ValueError(f"Invalid value type for max_proposals_per_run: {type(value)}")
            if not (1 <= value <= 10):
                raise ValueError(f"Invalid value for max_proposals_per_run: {value}. Must be between 1 and 10")
            current_preferences.max_proposals_per_run = value
            
        elif key == "blacklisted_proposers":
            if not isinstance(value, list):
                raise ValueError(f"Invalid value type for blacklisted_proposers: {type(value)}")
            if not all(isinstance(item, str) for item in value):
                raise ValueError("All items in blacklisted_proposers must be strings")
            current_preferences.blacklisted_proposers = value
            
        elif key == "whitelisted_proposers":
            if not isinstance(value, list):
                raise ValueError(f"Invalid value type for whitelisted_proposers: {type(value)}")
            if not all(isinstance(item, str) for item in value):
                raise ValueError("All items in whitelisted_proposers must be strings")
            current_preferences.whitelisted_proposers = value
            
        else:
            raise ValueError(f"Invalid preference key: {key}")
        
        # Save updated preferences
        await self.save_preferences(current_preferences)
        
        logfire.info(
            "User preference updated",
            preferences_file=self.preferences_file,
            key=key,
            value=str(value)
        )
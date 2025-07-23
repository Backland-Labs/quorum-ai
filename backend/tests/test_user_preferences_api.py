"""
Test suite for user preferences API endpoints.

This test file validates the GET and PUT endpoints for user preferences,
ensuring proper integration between the API layer and the UserPreferencesService.
These tests are crucial for enabling user configuration persistence in the application.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from models import UserPreferences
from services.user_preferences_service import UserPreferencesService


class TestUserPreferencesAPI:
    """Test class for user preferences API endpoints."""

    def setup_method(self):
        """Set up mock service before each test."""
        # Import main module and set up the global variable
        import main
        if not hasattr(main, 'user_preferences_service') or main.user_preferences_service is None:
            main.user_preferences_service = MagicMock(spec=UserPreferencesService)

    @pytest.mark.asyncio
    async def test_get_user_preferences_success(self, async_client: AsyncClient):
        """
        Test successful retrieval of user preferences.
        
        This test ensures that the GET endpoint correctly returns user preferences
        when they exist. This is important for loading user settings in the UI.
        """
        # Arrange
        mock_preferences = UserPreferences(
            voting_strategy="balanced",
            confidence_threshold=0.7,
            max_proposals_per_run=10,
            blacklisted_proposers=["0xBadActor"],
            whitelisted_proposers=["0xTrusted"]
        )
        
        import main
        main.user_preferences_service.load_preferences = AsyncMock(return_value=mock_preferences)
        
        # Act
        response = await async_client.get("/user-preferences")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["voting_strategy"] == "balanced"
        assert data["confidence_threshold"] == 0.7
        assert data["max_proposals_per_run"] == 10
        assert data["blacklisted_proposers"] == ["0xBadActor"]
        assert data["whitelisted_proposers"] == ["0xTrusted"]
        main.user_preferences_service.load_preferences.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_preferences_not_found(self, async_client: AsyncClient):
        """
        Test GET endpoint when no preferences exist.
        
        This test ensures proper error handling when preferences haven't been set yet,
        which is critical for first-time users who need to be redirected to setup.
        """
        # Arrange
        import main
        main.user_preferences_service.load_preferences = AsyncMock(return_value=None)
        
        # Act
        response = await async_client.get("/user-preferences")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_put_user_preferences_success(self, async_client: AsyncClient):
        """
        Test successful update of user preferences.
        
        This test validates that users can save their preferences, which is
        the core functionality enabling autonomous voting configuration.
        """
        # Arrange
        preferences_data = {
            "voting_strategy": "conservative",
            "confidence_threshold": 0.9,
            "max_proposals_per_run": 5,
            "blacklisted_proposers": ["0xSpammer"],
            "whitelisted_proposers": []
        }
        
        import main
        main.user_preferences_service.save_preferences = AsyncMock(return_value=True)
        
        # Act
        response = await async_client.put("/user-preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["voting_strategy"] == "conservative"
        assert data["confidence_threshold"] == 0.9
        assert data["max_proposals_per_run"] == 5
        
        # Verify the service was called with correct data
        main.user_preferences_service.save_preferences.assert_called_once()
        saved_prefs = main.user_preferences_service.save_preferences.call_args[0][0]
        assert isinstance(saved_prefs, UserPreferences)
        assert saved_prefs.voting_strategy == "conservative"

    @pytest.mark.asyncio
    async def test_put_user_preferences_validation_error(self, async_client: AsyncClient):
        """
        Test PUT endpoint with invalid data.
        
        This test ensures that the API properly validates user input and returns
        meaningful error messages, preventing invalid configurations that could
        break the autonomous voting system.
        """
        # Arrange - Invalid voting strategy
        invalid_data = {
            "voting_strategy": "invalid_strategy",
            "confidence_threshold": 0.7,
            "max_proposals_per_run": 10
        }
        
        # Act
        response = await async_client.put("/user-preferences", json=invalid_data)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Verify validation error mentions the invalid field
        assert any("voting_strategy" in str(error) for error in data["detail"])

    @pytest.mark.asyncio
    async def test_put_user_preferences_threshold_validation(self, async_client: AsyncClient):
        """
        Test PUT endpoint with out-of-range confidence threshold.
        
        This test validates that confidence thresholds are properly bounded,
        as invalid thresholds could cause the AI to make poor voting decisions.
        """
        # Arrange - Threshold > 1.0
        invalid_data = {
            "voting_strategy": "balanced",
            "confidence_threshold": 1.5,  # Invalid: must be <= 1.0
            "max_proposals_per_run": 10
        }
        
        # Act
        response = await async_client.put("/user-preferences", json=invalid_data)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_put_user_preferences_save_failure(self, async_client: AsyncClient):
        """
        Test PUT endpoint when save operation fails.
        
        This test ensures proper error handling when the underlying service
        fails to persist preferences, which could happen due to disk issues.
        """
        # Arrange
        preferences_data = {
            "voting_strategy": "balanced",
            "confidence_threshold": 0.7,
            "max_proposals_per_run": 10
        }
        
        import main
        main.user_preferences_service.save_preferences = AsyncMock(side_effect=Exception("Failed to save preferences"))
        
        # Act
        response = await async_client.put("/user-preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "failed to save" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_put_user_preferences_with_optional_fields(self, async_client: AsyncClient):
        """
        Test PUT endpoint with optional fields (blacklist/whitelist).
        
        This test ensures that optional fields are handled correctly, allowing
        users to configure advanced filtering of proposal creators.
        """
        # Arrange - Include optional fields
        preferences_data = {
            "voting_strategy": "aggressive",
            "confidence_threshold": 0.5,
            "max_proposals_per_run": 10,  # Maximum allowed value
            "blacklisted_proposers": ["0xBad1", "0xBad2"],
            "whitelisted_proposers": ["0xGood1", "0xGood2", "0xGood3"]
        }
        
        import main
        main.user_preferences_service.save_preferences = AsyncMock(return_value=True)
        
        # Act
        response = await async_client.put("/user-preferences", json=preferences_data)
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["blacklisted_proposers"]) == 2
        assert len(data["whitelisted_proposers"]) == 3
        assert "0xBad1" in data["blacklisted_proposers"]
        assert "0xGood3" in data["whitelisted_proposers"]
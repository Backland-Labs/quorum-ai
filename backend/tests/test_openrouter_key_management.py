"""Tests for OpenRouter API key management functionality.

These tests validate the core business logic for user-provided API key management:
- Secure storage and retrieval of API keys 
- No secret leakage in logs or API responses
- Fallback behavior when no key is configured  
- AI Service lazy initialization
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import UserPreferences


class TestApiKeyStorage:
    """Test core API key storage and retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_api_key(self):
        """
        Test basic API key storage and retrieval using StateManager.
        
        This test validates the happy path for API key management - the most 
        critical functionality that must work correctly. It ensures keys are
        stored securely and can be retrieved without corruption.
        """
        from services.user_preferences_service import UserPreferencesService
        
        # Create mock state manager with sensitive storage
        mock_state_manager = AsyncMock()
        mock_state_manager.save_state.return_value = None
        mock_state_manager.load_state.return_value = {"openrouter_key": "sk-or-test123"}
        
        service = UserPreferencesService(state_manager=mock_state_manager)
        
        # Store API key
        await service.set_api_key("sk-or-test123")
        
        # Verify secure storage was called with sensitive=True
        mock_state_manager.save_state.assert_called_once()
        call_args = mock_state_manager.save_state.call_args
        assert call_args[1]['sensitive'] is True  # Must use secure storage
        assert "openrouter_key" in call_args[0][1]  # Data contains key
        
        # Retrieve API key
        retrieved_key = await service.get_api_key()
        assert retrieved_key == "sk-or-test123"


class TestNoSecretLeakage:
    """Test that API keys are never leaked in logs or responses."""
    
    @pytest.mark.asyncio
    async def test_no_key_in_logs(self):
        """
        Ensure API keys are never logged - critical security requirement.
        
        This test validates that during normal operation, API keys are never
        written to log files, which could be a major security vulnerability.
        """
        from services.user_preferences_service import UserPreferencesService
        
        mock_state_manager = AsyncMock()
        mock_state_manager.save_state.return_value = None
        
        with patch('logging_config.setup_pearl_logger') as mock_logger_setup:
            mock_logger = MagicMock()
            mock_logger_setup.return_value = mock_logger
            
            service = UserPreferencesService(state_manager=mock_state_manager)
            await service.set_api_key("sk-or-secret123")
            
            # Verify logger was never called with the secret
            for call in mock_logger.info.call_args_list + mock_logger.error.call_args_list + mock_logger.warning.call_args_list:
                args_str = str(call)
                assert "sk-or-secret123" not in args_str, "API key found in log call"


class TestFallbackBehavior:
    """Test graceful fallback when no user key is configured."""
    
    def test_ai_service_lazy_init(self):
        """
        Test AI Service can initialize without API key - enables lazy loading.
        
        This test ensures the system can start up and run without requiring
        an API key to be configured upfront, which is essential for allowing
        users to configure their keys through the frontend.
        """
        from services.ai_service import AIService
        
        # Mock settings to have no API key
        with patch('services.ai_service.settings') as mock_settings:
            mock_settings.openrouter_api_key = None
            
            # Should not raise exception during initialization
            try:
                service = AIService()
                # Service should be created but not functional yet
                assert service is not None
            except Exception as e:
                pytest.fail(f"AIService should initialize without API key, but got: {e}")
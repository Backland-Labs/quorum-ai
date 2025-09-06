"""Tests for API key management endpoints.

Tests the API endpoints for setting and getting OpenRouter API key status.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestApiKeyEndpoints:
    """Test API key management endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked services."""
        from main import app
        
        # Mock the services to avoid initialization issues
        with patch('main.user_preferences_service') as mock_user_prefs, \
             patch('main.ai_service') as mock_ai_service:
            
            mock_user_prefs.set_api_key = AsyncMock()
            mock_user_prefs.get_api_key = AsyncMock(return_value=None)
            mock_ai_service.swap_api_key = lambda x: None
            
            yield TestClient(app)

    def test_set_api_key_success(self, client):
        """Test successful API key setting."""
        response = client.post("/config/openrouter-key", 
                             json={"api_key": "sk-or-test123456789012345"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["configured"] is True

    def test_set_api_key_validation_error(self, client):
        """Test API key validation error for short key."""
        response = client.post("/config/openrouter-key", 
                             json={"api_key": "short"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"] == "VALIDATION_ERROR"

    def test_get_api_key_status(self, client):
        """Test getting API key status.""" 
        response = client.get("/config/openrouter-key")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "configured" in data["data"]
        assert "source" in data["data"]
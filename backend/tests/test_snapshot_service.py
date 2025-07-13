"""Tests for SnapshotService."""

import pytest
from unittest.mock import patch
import httpx

from services.snapshot_service import SnapshotService
from config import settings


class TestSnapshotServiceInitialization:
    """Test SnapshotService initialization."""

    def test_snapshot_service_initialization_uses_settings(self) -> None:
        """Test that SnapshotService initialization uses configuration settings."""
        service = SnapshotService()

        assert service.base_url == "https://hub.snapshot.org/graphql"
        assert service.timeout == settings.request_timeout
        assert service.semaphore is not None
        assert service.semaphore._value == 5  # Default semaphore limit


class TestSnapshotServiceProperties:
    """Test SnapshotService properties and basic functionality."""

    def test_snapshot_service_has_required_attributes(self) -> None:
        """Test that SnapshotService has all required attributes."""
        service = SnapshotService()

        # Check that service has the expected attributes
        assert hasattr(service, 'base_url')
        assert hasattr(service, 'timeout')
        assert hasattr(service, 'semaphore')
        assert hasattr(service, 'client')

    def test_snapshot_service_client_configuration(self) -> None:
        """Test that SnapshotService client is properly configured."""
        service = SnapshotService()

        # Check that client is an httpx.AsyncClient
        assert isinstance(service.client, httpx.AsyncClient)
        assert service.client.timeout.read == settings.request_timeout

    @patch.object(settings, 'request_timeout', 30.0)
    def test_snapshot_service_respects_timeout_setting(self) -> None:
        """Test that SnapshotService respects the configured timeout."""
        service = SnapshotService()

        assert service.timeout == 30.0
        assert service.client.timeout.read == 30.0

    def test_snapshot_service_has_default_headers(self) -> None:
        """Test that SnapshotService client has proper default headers."""
        service = SnapshotService()
        
        # This test will fail because default headers are not yet implemented
        expected_headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'QuorumAI/{settings.app_name}',
            'Accept': 'application/json'
        }
        
        # Check that client has the expected default headers
        for key, value in expected_headers.items():
            assert key in service.client.headers
            assert service.client.headers[key] == value


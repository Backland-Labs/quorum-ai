"""Tests for ActivityService."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import date, timedelta
import json
import os

from services.activity_service import ActivityService


class TestActivityServiceInitialization:
    """Test ActivityService initialization."""

    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_activity_service_initialization_no_store_path(self, mock_exists, mock_settings):
        """Test ActivityService initialization without store path."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        assert service.persistent_file == "activity_tracker.json"
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_activity_service_initialization_with_store_path(self, mock_exists, mock_settings):
        """Test ActivityService initialization with store path."""
        mock_settings.store_path = "/tmp/olas"
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.persistent_file == "/tmp/olas/activity_tracker.json"


class TestActivityServiceStateManagement:
    """Test ActivityService state loading and saving."""
    
    @patch("services.activity_service.settings")
    @patch("builtins.open", new_callable=mock_open, read_data='{"last_activity_date": "2024-01-15", "last_tx_hash": "0x123"}')
    @patch("os.path.exists")
    def test_load_state_success(self, mock_exists, mock_file, mock_settings):
        """Test successful state loading from file."""
        mock_settings.store_path = None
        mock_exists.return_value = True
        
        service = ActivityService()
        
        assert service.last_activity_date == date(2024, 1, 15)
        assert service.last_tx_hash == "0x123"
        mock_file.assert_called_once_with("activity_tracker.json", 'r')
        
    @patch("services.activity_service.settings")
    @patch("builtins.open", new_callable=mock_open, read_data='{}')
    @patch("os.path.exists")
    def test_load_state_empty_file(self, mock_exists, mock_file, mock_settings):
        """Test loading state from empty file."""
        mock_settings.store_path = None
        mock_exists.return_value = True
        
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_load_state_file_not_exists(self, mock_exists, mock_settings):
        """Test loading state when file doesn't exist."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        
    @patch("services.activity_service.settings")
    @patch("builtins.open", side_effect=Exception("File error"))
    @patch("os.path.exists")
    def test_load_state_exception_handling(self, mock_exists, mock_file, mock_settings):
        """Test exception handling during state loading."""
        mock_settings.store_path = None
        mock_exists.return_value = True
        
        # Should not raise exception
        service = ActivityService()
        
        assert service.last_activity_date is None
        assert service.last_tx_hash is None
        
    @patch("services.activity_service.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_save_state_success(self, mock_exists, mock_file, mock_makedirs, mock_settings):
        """Test successful state saving."""
        mock_settings.store_path = "/tmp/olas"
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        service.last_tx_hash = "0x123"
        
        service.save_state()
        
        # Check that file was opened for writing
        mock_file.assert_called_with("/tmp/olas/activity_tracker.json", 'w')
        
        # Check that json.dump was called with correct data
        written_data = mock_file().write.call_args_list
        written_content = ''.join(call[0][0] for call in written_data)
        parsed_data = json.loads(written_content)
        
        assert parsed_data["last_activity_date"] == "2024-01-15"
        assert parsed_data["last_tx_hash"] == "0x123"
        
    @patch("services.activity_service.settings")
    @patch("os.makedirs", side_effect=Exception("Directory error"))
    @patch("os.path.exists")
    def test_save_state_exception_handling(self, mock_exists, mock_makedirs, mock_settings):
        """Test exception handling during state saving."""
        mock_settings.store_path = "/tmp/olas"
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        
        # Should not raise exception
        service.save_state()


class TestActivityServiceActivityChecking:
    """Test ActivityService activity checking logic."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_is_daily_activity_needed_no_previous_activity(self, mock_exists, mock_settings):
        """Test activity needed when no previous activity recorded."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        
        assert service.is_daily_activity_needed() is True
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_is_daily_activity_needed_today_already_done(self, mock_exists, mock_settings):
        """Test no activity needed when already done today."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today()
        
        assert service.is_daily_activity_needed() is False
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_is_daily_activity_needed_yesterday(self, mock_exists, mock_settings):
        """Test activity needed when last activity was yesterday."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today() - timedelta(days=1)
        
        assert service.is_daily_activity_needed() is True


class TestActivityServiceActivityMarking:
    """Test ActivityService activity marking functionality."""
    
    @patch("services.activity_service.settings")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_mark_activity_completed(self, mock_exists, mock_file, mock_makedirs, mock_settings):
        """Test marking activity as completed."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        test_tx_hash = "0xabcdef123456"
        
        service.mark_activity_completed(test_tx_hash)
        
        assert service.last_activity_date == date.today()
        assert service.last_tx_hash == test_tx_hash
        
        # Verify save_state was called (file operations)
        mock_file.assert_called_with("activity_tracker.json", 'w')


class TestActivityServiceOLASCompliance:
    """Test ActivityService OLAS compliance checking."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_get_activity_status_no_activity(self, mock_exists, mock_settings):
        """Test getting activity status when no activity recorded."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        status = service.get_activity_status()
        
        assert status["daily_activity_needed"] is True
        assert status["last_activity_date"] is None
        assert status["last_tx_hash"] is None
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_get_activity_status_with_activity(self, mock_exists, mock_settings):
        """Test getting activity status with previous activity."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today()
        service.last_tx_hash = "0x123"
        
        status = service.get_activity_status()
        
        assert status["daily_activity_needed"] is False
        assert status["last_activity_date"] == date.today().isoformat()
        assert status["last_tx_hash"] == "0x123"
        
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_check_olas_compliance_needed(self, mock_exists, mock_settings):
        """Test OLAS compliance check when activity is needed."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        # No previous activity
        
        compliance = service.check_olas_compliance()
        
        assert compliance["compliant"] is False
        assert compliance["reason"] == "Daily activity required for OLAS staking"
        assert compliance["action_required"] == "safe_transaction"
        
    @patch("services.activity_service.settings")  
    @patch("os.path.exists")
    def test_check_olas_compliance_satisfied(self, mock_exists, mock_settings):
        """Test OLAS compliance check when already satisfied."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date.today()
        
        compliance = service.check_olas_compliance()
        
        assert compliance["compliant"] is True
        assert compliance["reason"] == "Daily activity completed"
        assert compliance["action_required"] is None


class TestActivityServiceIntegration:
    """Test ActivityService integration methods."""
    
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_get_compliance_summary(self, mock_exists, mock_settings):
        """Test getting compliance summary."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        service = ActivityService()
        service.last_activity_date = date(2024, 1, 15)
        service.last_tx_hash = "0x123"
        
        summary = service.get_compliance_summary()
        
        assert "activity_status" in summary
        assert "olas_compliance" in summary
        assert summary["activity_status"]["last_activity_date"] == "2024-01-15"
        assert summary["olas_compliance"]["compliant"] is False  # Old date
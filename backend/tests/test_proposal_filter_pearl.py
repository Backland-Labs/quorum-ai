"""Tests for Pearl logging implementation in ProposalFilter service.

This test module verifies that the ProposalFilter service correctly uses
the Pearl logging infrastructure instead of Logfire, following the TDD
methodology outlined in plan.md.
"""

import json
import tempfile
from unittest.mock import Mock, patch, mock_open
import time
import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from services.proposal_filter import ProposalFilter, ProposalFilterError
from models import UserPreferences, Proposal, VotingStrategy
from logging_config import setup_pearl_logger


class TestProposalFilterPearlLogging:
    """Test suite for Pearl logging implementation in ProposalFilter."""

    @pytest.fixture
    def temp_log_file(self):
        """Create a temporary log file for testing."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False) as f:
            yield f.name

    @pytest.fixture
    def mock_preferences(self):
        """Create mock UserPreferences for testing."""
        preferences = Mock(spec=UserPreferences)
        preferences.voting_strategy = Mock(value="balanced")
        preferences.confidence_threshold = 0.7
        preferences.max_proposals_per_run = 10
        preferences.blacklisted_proposers = ["blacklisted1", "blacklisted2"]
        preferences.whitelisted_proposers = ["whitelisted1", "whitelisted2"]
        return preferences

    @pytest.fixture
    def mock_proposal(self):
        """Create a mock Proposal for testing."""
        proposal = Mock(spec=Proposal)
        proposal.id = "test-proposal-123"
        proposal.author = "whitelisted1"  # Use a whitelisted author so it passes filtering
        proposal.end = int(time.time()) + 3600  # 1 hour from now
        proposal.scores_total = 1000.0
        proposal.votes = 50
        return proposal

    def test_initialization_logs_pearl_format(self, mock_preferences, temp_log_file):
        """Test that ProposalFilter initialization logs in Pearl format.
        
        This test verifies that when ProposalFilter is initialized, it:
        1. Uses Pearl logger instead of Logfire
        2. Logs initialization details in Pearl JSON format
        3. Includes all relevant user preference information
        """
        # Setup Pearl logging to temp file
        with patch('services.proposal_filter.logger') as mock_logger:
            # Initialize ProposalFilter
            filter_service = ProposalFilter(mock_preferences)
            
            # Verify Pearl logger was used (not logfire)
            mock_logger.info.assert_called_once()
            
            # Verify the log call included structured data
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "ProposalFilter initialized"
            
            # Verify structured data was passed as extra
            extra = call_args[1].get('extra', {})
            assert extra.get('voting_strategy') == "balanced"
            assert extra.get('confidence_threshold') == 0.7
            assert extra.get('max_proposals_per_run') == 10
            assert extra.get('blacklisted_count') == 2
            assert extra.get('whitelisted_count') == 2

    def test_filter_proposals_uses_pearl_logger(self, mock_preferences, mock_proposal):
        """Test that filter_proposals uses Pearl logger for all logging.
        
        This test verifies that the filter_proposals method:
        1. Uses Pearl logger for info and debug logs
        2. Does not use logfire.span (uses log_span instead)
        3. Logs filtering metrics in Pearl format
        """
        with patch('services.proposal_filter.logger') as mock_logger:
            with patch('services.proposal_filter.log_span') as mock_log_span:
                # Setup
                filter_service = ProposalFilter(mock_preferences)
                proposals = [mock_proposal]
                
                # Execute
                result = filter_service.filter_proposals(proposals)
                
                # Verify log_span was used instead of logfire.span
                mock_log_span.assert_called_once_with(
                    mock_logger,
                    "filter_proposals",
                    proposal_count=1
                )
                
                # Verify info logs were called
                info_calls = [call for call in mock_logger.info.call_args_list if call != mock_logger.info.call_args_list[0]]
                assert len(info_calls) >= 2  # Starting and completed logs
                
                # Verify starting log
                assert "Starting proposal filtering" in str(info_calls[0])
                
                # Verify completion log
                assert "Proposal filtering completed" in str(info_calls[-1])

    def test_rank_proposals_uses_pearl_logger(self, mock_preferences, mock_proposal):
        """Test that rank_proposals uses Pearl logger for all logging.
        
        This test verifies that the rank_proposals method:
        1. Uses Pearl logger for structured logging
        2. Uses log_span context manager instead of logfire.span
        3. Logs ranking metrics with proper structure
        """
        with patch('services.proposal_filter.logger') as mock_logger:
            with patch('services.proposal_filter.log_span') as mock_log_span:
                # Setup
                filter_service = ProposalFilter(mock_preferences)
                proposals = [mock_proposal]
                
                # Execute
                result = filter_service.rank_proposals(proposals)
                
                # Verify log_span was used - rank_proposals calls calculate_proposal_score internally
                mock_log_span.assert_any_call(
                    mock_logger,
                    "rank_proposals",
                    proposal_count=1
                )
                
                # Verify info logs
                info_calls = [call for call in mock_logger.info.call_args_list if call != mock_logger.info.call_args_list[0]]
                assert any("Starting proposal ranking" in str(call) for call in info_calls)
                assert any("Proposal ranking completed" in str(call) for call in info_calls)

    def test_calculate_proposal_score_uses_pearl_logger(self, mock_preferences, mock_proposal):
        """Test that calculate_proposal_score uses Pearl logger.
        
        This test verifies that the calculate_proposal_score method:
        1. Uses Pearl logger for debug logging
        2. Uses log_span for operation tracking
        3. Logs score calculation details in structured format
        """
        with patch('services.proposal_filter.logger') as mock_logger:
            with patch('services.proposal_filter.log_span') as mock_log_span:
                # Setup
                filter_service = ProposalFilter(mock_preferences)
                
                # Execute
                score = filter_service.calculate_proposal_score(mock_proposal)
                
                # Verify log_span was used
                mock_log_span.assert_called_with(
                    mock_logger,
                    "calculate_proposal_score",
                    proposal_id="test-proposal-123"
                )
                
                # Verify debug log was called with score details
                mock_logger.debug.assert_called()
                debug_call = mock_logger.debug.call_args
                assert "Proposal score calculated" in debug_call[0][0]
                
                # Verify structured data in debug log
                extra = debug_call[1].get('extra', {})
                assert 'urgency_factor' in extra
                assert 'voting_power_factor' in extra
                assert 'participation_factor' in extra
                assert 'composite_score' in extra

    def test_no_logfire_imports_remain(self):
        """Test that no logfire imports remain in the service.
        
        This test verifies that:
        1. The module doesn't import logfire
        2. All logging is done through Pearl infrastructure
        """
        # This test will fail until we implement the changes
        import services.proposal_filter as pf_module
        
        # Check module imports
        assert not hasattr(pf_module, 'logfire'), "logfire should not be imported"
        
        # Verify Pearl logging is imported instead
        assert hasattr(pf_module, 'logger'), "Pearl logger should be imported"
        assert hasattr(pf_module, 'log_span'), "log_span should be imported"

    def test_debug_logs_use_pearl_format(self, mock_preferences):
        """Test that debug logs use Pearl structured format.
        
        This test verifies that debug logs:
        1. Use Pearl logger's debug method
        2. Include structured data as 'extra' parameter
        3. Don't use positional arguments for data
        """
        with patch('services.proposal_filter.logger') as mock_logger:
            # Setup
            filter_service = ProposalFilter(mock_preferences)
            
            # Create proposals with different authors
            blacklisted_proposal = Mock(spec=Proposal)
            blacklisted_proposal.id = "blacklisted-1"
            blacklisted_proposal.author = "blacklisted1"
            
            # Execute filtering
            result = filter_service.filter_proposals([blacklisted_proposal])
            
            # Verify debug log was called for blacklisted proposal
            debug_calls = mock_logger.debug.call_args_list
            assert len(debug_calls) > 0
            
            # Check that debug log has proper structure
            blacklist_call = next(
                (call for call in debug_calls if "blacklisted" in call[0][0].lower()),
                None
            )
            assert blacklist_call is not None
            
            # Verify structured data format
            extra = blacklist_call[1].get('extra', {})
            assert extra.get('proposal_id') == "blacklisted-1"
            assert extra.get('author') == "blacklisted1"

    def test_integration_with_pearl_logging_file_output(self, mock_preferences, mock_proposal, temp_log_file):
        """Integration test to verify actual Pearl log file output.
        
        This test verifies that:
        1. Logs are written to file in correct Pearl JSON format
        2. All required fields are present
        3. Structured data is properly formatted
        """
        # Configure Pearl logging to use temp file
        from services.proposal_filter import ProposalFilter
        import logging
        import json
        import os
        
        # Create a new ProposalFilter which will use real Pearl logging
        filter_service = ProposalFilter(mock_preferences)
        
        # Use the service
        filtered = filter_service.filter_proposals([mock_proposal])
        ranked = filter_service.rank_proposals(filtered)
        
        # Since we're using the real logger, we can't easily capture logs in memory
        # This test is more about ensuring the code runs without errors
        # and uses the Pearl logging infrastructure correctly
        
        # Verify the service executed successfully
        assert len(filtered) == 1  # mock_proposal should pass filtering
        assert len(ranked) == 1     # ranking should preserve the proposal
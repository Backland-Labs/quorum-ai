"""
Tests for VotingService Pearl logging migration.

This test module ensures that the VotingService properly uses Pearl-compliant
logging infrastructure while maintaining its critical audit trail requirements
for DAO voting operations.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import logging
import time
from typing import Dict, Any
from pytest_httpx import HTTPXMock

from services.voting_service import VotingService


class TestVotingServicePearlLogging:
    """Test VotingService Pearl logging compliance."""

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_initialization_uses_pearl_logger(self, mock_file):
        """
        Test that VotingService initialization uses Pearl logger instead of logfire.
        
        This test validates that:
        1. VotingService no longer imports logfire
        2. Pearl logger is properly initialized
        3. Initialization is logged with structured format
        """
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            mock_logger = MagicMock()
            mock_setup_logger.return_value = mock_logger
            
            service = VotingService()
            
            # Verify Pearl logger setup was called
            mock_setup_logger.assert_called_once_with(
                name='voting_service',
                level=logging.INFO
            )
            
            # Verify initialization was logged with structured format
            mock_logger.info.assert_called_once()
            log_call = mock_logger.info.call_args[0][0]
            assert 'VotingService initialized' in log_call
            assert f'eoa_address={service.account.address}' in log_call

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_create_vote_message_pearl_logging(self, mock_file):
        """
        Test that create_snapshot_vote_message uses Pearl logging.
        
        This test ensures:
        1. Vote message creation is logged with Pearl format
        2. All relevant parameters are included in structured format
        3. No logfire calls are made
        """
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            mock_logger = MagicMock()
            mock_setup_logger.return_value = mock_logger
            
            service = VotingService()
            mock_logger.reset_mock()  # Reset after initialization
            
            space = "aave.eth"
            proposal = "0xabc123"
            choice = 1
            timestamp = 1640995200
            
            service.create_snapshot_vote_message(space, proposal, choice, timestamp)
            
            # Verify structured logging
            log_call = mock_logger.info.call_args[0][0]
            assert 'Snapshot vote message created' in log_call
            assert f'space={space}' in log_call
            assert f'proposal={proposal}' in log_call
            assert f'choice={choice}' in log_call
            assert f'timestamp={timestamp}' in log_call
            assert f'from_address={service.account.address}' in log_call

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    def test_sign_message_pearl_logging(self, mock_file):
        """
        Test that sign_snapshot_message uses Pearl logging.
        
        This test validates:
        1. Signature creation is logged with Pearl format
        2. Sensitive data (full signature) is properly handled
        3. Signature preview is included for audit trail
        """
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            mock_logger = MagicMock()
            mock_setup_logger.return_value = mock_logger
            
            service = VotingService()
            mock_logger.reset_mock()
            
            message = service.create_snapshot_vote_message("test.eth", "proposal123", 1)
            signature = service.sign_snapshot_message(message)
            
            # Find the signing log call
            log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            sign_log = next(call for call in log_calls if 'Snapshot message signed' in call)
            
            assert 'signature_length=132' in sign_log
            assert f'signature_preview={signature[:10]}...{signature[-10:]}' in sign_log

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_submit_vote_uses_log_span(self, mock_file, httpx_mock: HTTPXMock):
        """
        Test that submit_vote_to_snapshot uses log_span context manager.
        
        This test ensures:
        1. The logfire.span is replaced with Pearl's log_span
        2. Operation start and completion are logged
        3. Duration tracking is maintained
        """
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123", "ipfs": "QmHash"},
            status_code=200
        )
        
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            with patch('services.voting_service.log_span') as mock_log_span:
                mock_logger = MagicMock()
                mock_setup_logger.return_value = mock_logger
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                service = VotingService()
                message = service.create_snapshot_vote_message("test.eth", "proposal123", 1)
                signature = service.sign_snapshot_message(message)
                
                result = await service.submit_vote_to_snapshot(message, signature)
                
                # Verify log_span was called
                mock_log_span.assert_called_once_with(
                    mock_logger,
                    'voting_service.submit_vote_to_snapshot'
                )
                
                # Verify result logging
                assert result["success"] is True
                log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any('Submitting Snapshot vote' in call for call in log_calls)
                assert any('Snapshot vote submitted successfully' in call for call in log_calls)

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_submit_vote_error_logging(self, mock_file, httpx_mock: HTTPXMock):
        """
        Test error logging in submit_vote_to_snapshot.
        
        This test validates:
        1. HTTP errors are logged with Pearl format
        2. Error details include status code and response
        3. Structured error format for debugging
        """
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            status_code=400,
            text="Invalid signature"
        )
        
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            with patch('services.voting_service.log_span') as mock_log_span:
                mock_logger = MagicMock()
                mock_setup_logger.return_value = mock_logger
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                service = VotingService()
                message = service.create_snapshot_vote_message("test.eth", "proposal123", 1)
                signature = service.sign_snapshot_message(message)
                
                result = await service.submit_vote_to_snapshot(message, signature)
                
                # Verify error logging
                error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
                assert any('Snapshot vote submission failed' in call for call in error_calls)
                error_log = next(call for call in error_calls if 'Snapshot vote submission failed' in call)
                assert 'status_code=400' in error_log
                assert 'response_text=Invalid signature' in error_log

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_vote_on_proposal_span_with_context(self, mock_file, httpx_mock: HTTPXMock):
        """
        Test that vote_on_proposal uses log_span with proper context.
        
        This test ensures:
        1. The vote workflow span includes all relevant context
        2. Space, proposal, and choice are passed to log_span
        3. Nested operations are properly tracked
        """
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123"},
            status_code=200
        )
        
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            with patch('services.voting_service.log_span') as mock_log_span:
                mock_logger = MagicMock()
                mock_setup_logger.return_value = mock_logger
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                service = VotingService()
                
                space = "aave.eth"
                proposal = "proposal123"
                choice = 2
                
                result = await service.vote_on_proposal(space, proposal, choice)
                
                # Verify log_span calls
                calls = mock_log_span.call_args_list
                vote_span_call = next(
                    call for call in calls 
                    if 'voting_service.vote_on_proposal' in call[0]
                )
                
                # Check context parameters
                _, kwargs = vote_span_call
                assert kwargs['space'] == space
                assert kwargs['proposal'] == proposal
                assert kwargs['choice'] == choice

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_vote_workflow_completion_logging(self, mock_file, httpx_mock: HTTPXMock):
        """
        Test vote workflow completion logging.
        
        This test validates:
        1. Successful completion is logged with Pearl format
        2. Failed completion includes error details
        3. Audit trail is maintained for all outcomes
        """
        # Test successful completion
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123"},
            status_code=200
        )
        
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            with patch('services.voting_service.log_span') as mock_log_span:
                mock_logger = MagicMock()
                mock_setup_logger.return_value = mock_logger
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                service = VotingService()
                mock_logger.reset_mock()
                
                result = await service.vote_on_proposal("test.eth", "proposal123", 1)
                
                # Check completion logging
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert any('Vote workflow completed successfully' in call for call in info_calls)
                
        # Test failed completion
        httpx_mock.reset()
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            status_code=400,
            text="Failed"
        )
        
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            with patch('services.voting_service.log_span') as mock_log_span:
                mock_logger = MagicMock()
                mock_setup_logger.return_value = mock_logger
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                service = VotingService()
                mock_logger.reset_mock()
                
                result = await service.vote_on_proposal("test.eth", "proposal123", 1)
                
                # Check failure logging
                error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
                assert any('Vote workflow failed' in call for call in error_calls)
                error_log = next(call for call in error_calls if 'Vote workflow failed' in call)
                assert 'error=HTTP 400' in error_log

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_test_snapshot_voting_pearl_logging(self, mock_file, httpx_mock: HTTPXMock):
        """
        Test that test_snapshot_voting uses Pearl logging.
        
        This test ensures:
        1. Test function uses log_span for tracking
        2. Validation errors are logged properly
        3. Test completion is tracked with Pearl format
        """
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123"},
            status_code=200
        )
        
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            with patch('services.voting_service.log_span') as mock_log_span:
                mock_logger = MagicMock()
                mock_setup_logger.return_value = mock_logger
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                service = VotingService()
                
                space = "spectradao.eth"
                proposal = "0xfbfc4f16d1f44d4298f4a7c958e3ad158ec0c8fc582d1151f766c26dbe50b237"
                choice = 1
                
                result = await service.test_snapshot_voting(space, proposal, choice)
                
                # Verify test span
                test_span_call = next(
                    call for call in mock_log_span.call_args_list
                    if 'voting_service.test_snapshot_voting' in call[0]
                )
                assert test_span_call is not None
                
                # Verify test logging includes context
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                test_log = next(call for call in info_calls if 'Testing Snapshot voting workflow' in call)
                assert f'space={space}' in test_log
                assert f'proposal={proposal}' in test_log
                assert f'choice={choice}' in test_log
                assert 'choice_description=For' in test_log

    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @pytest.mark.asyncio
    async def test_exception_logging_with_pearl(self, mock_file):
        """
        Test that exceptions are properly logged with Pearl format.
        
        This test validates:
        1. Network errors use Pearl error logging
        2. Exception details are included
        3. Audit trail is maintained even on failure
        """
        with patch('services.voting_service.setup_pearl_logger') as mock_setup_logger:
            with patch('services.voting_service.log_span') as mock_log_span:
                mock_logger = MagicMock()
                mock_setup_logger.return_value = mock_logger
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                service = VotingService()
                message = service.create_snapshot_vote_message("test.eth", "proposal123", 1)
                signature = service.sign_snapshot_message(message)
                
                # Mock network error
                with patch('httpx.AsyncClient.post', side_effect=Exception("Network error")):
                    result = await service.submit_vote_to_snapshot(message, signature)
                    
                    # Verify exception logging
                    error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
                    assert any('Snapshot vote submission error: Network error' in call for call in error_calls)
                    assert result["success"] is False
                    assert "Network error" in result["error"]

    def test_no_logfire_imports(self):
        """
        Test that VotingService module no longer imports logfire.
        
        This test ensures complete removal of logfire dependency.
        """
        # This test will fail initially since voting_service.py still imports logfire
        # After implementation, the service should not have logfire in its namespace
        with patch('services.voting_service.setup_pearl_logger'):
            with patch("builtins.open", new_callable=mock_open, read_data="0x1234"):
                # This will fail if logfire is still imported
                import services.voting_service
                assert not hasattr(services.voting_service, 'logfire'), "logfire should not be imported"
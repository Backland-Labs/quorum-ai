"""
Tests for SnapshotService Pearl logging migration.

This test file validates that the SnapshotService correctly uses Pearl-compliant
logging instead of Logfire. It tests all logging patterns including:
- Logger initialization
- Info/error/debug logging with structured data
- Span context managers for operation tracking
- Error handling with proper logging
- Removal of all Logfire dependencies
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
import httpx
from pytest_httpx import HTTPXMock
import logging
from contextlib import contextmanager

from services.snapshot_service import SnapshotService, SnapshotServiceError, NetworkError, GraphQLError
from logging_config import setup_pearl_logger, log_span


class TestSnapshotServicePearlLoggingMigration:
    """Test that SnapshotService uses Pearl-compliant logging instead of Logfire."""

    def test_no_logfire_imports(self):
        """
        Test that snapshot_service.py has no Logfire imports.
        
        This test is important because it ensures complete removal of Logfire
        dependencies, which is a key requirement of the Pearl logging migration.
        """
        import inspect
        import services.snapshot_service as snapshot_module
        
        # Get the source code
        source = inspect.getsource(snapshot_module)
        
        # Check that logfire is not imported
        assert "import logfire" not in source, "Found 'import logfire' in snapshot_service.py"
        assert "from logfire" not in source, "Found 'from logfire' import in snapshot_service.py"
        assert "logfire." not in source, "Found logfire usage in snapshot_service.py"

    def test_pearl_logger_initialization(self):
        """
        Test that SnapshotService initializes a Pearl-compliant logger.
        
        This test verifies that the service uses setup_pearl_logger() to create
        a logger instance, which is the standard pattern for Pearl services.
        """
        # Since the logger is already initialized when the module is imported,
        # we just verify that it exists and is a logger instance
        from services.snapshot_service import logger
        import logging
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        # Verify the logger has the correct name
        assert logger.name == 'services.snapshot_service'

    @pytest.mark.asyncio
    async def test_execute_query_logging_with_pearl(self, httpx_mock: HTTPXMock):
        """
        Test that execute_query uses Pearl logging for request/response tracking.
        
        This test ensures that API calls are properly logged with structured data
        using Pearl's logging format instead of Logfire's format.
        """
        service = SnapshotService()
        
        # Mock response
        mock_response_data = {"data": {"test": "value"}}
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            json=mock_response_data,
            status_code=200
        )
        
        with patch('services.snapshot_service.logger') as mock_logger:
            with patch('services.snapshot_service.log_span') as mock_log_span:
                # Setup mock context manager
                mock_span_cm = MagicMock()
                mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                
                # Execute query
                query = "query { test }"
                await service.execute_query(query)
                
                # Verify log_span was called with correct parameters
                mock_log_span.assert_called_once_with(
                    mock_logger,
                    "snapshot_api_request",
                    query=service._truncate_query_for_logging(query),
                    has_variables=False
                )
                
                # Verify info logs were called
                expected_calls = [
                    call.info(
                        "Sending GraphQL request to Snapshot API, endpoint=%s, query_length=%s, has_variables=%s",
                        service.base_url,
                        len(query),
                        False
                    ),
                    call.info(
                        "Received HTTP response from Snapshot API, status_code=%s, content_type=%s",
                        200,
                        "application/json"
                    ),
                    call.info(
                        "Snapshot GraphQL query completed successfully, data_keys=%s, response_size=%s",
                        "['test']",
                        len(str(mock_response_data["data"]))
                    )
                ]
                
                # Check that the expected log calls were made
                for expected_call in expected_calls:
                    assert expected_call in mock_logger.mock_calls
        
        await service.close()

    @pytest.mark.asyncio
    async def test_network_error_logging_with_pearl(self, httpx_mock: HTTPXMock):
        """
        Test that network errors are logged using Pearl format.
        
        This test verifies that timeout, connection, and HTTP errors are properly
        logged with structured data in Pearl format.
        """
        service = SnapshotService()
        
        # Test timeout error
        httpx_mock.add_exception(httpx.TimeoutException("Request timed out"))
        
        with patch('services.snapshot_service.logger') as mock_logger:
            with pytest.raises(NetworkError):
                await service.execute_query("query { test }")
            
            # Verify error was logged - the log_span will add its own "Failed" message
            # We need to check that our custom error was logged somewhere in the calls
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            # The call uses %s placeholders, so we need to check for the pattern
            assert any("'Network error: %s" in str(call) and "'timeout'" in str(call) for call in error_calls), \
                f"Expected 'Network error: %s' with 'timeout' in error calls, but got: {error_calls}"
        
        await service.close()

    @pytest.mark.asyncio
    async def test_graphql_error_logging_with_pearl(self, httpx_mock: HTTPXMock):
        """
        Test that GraphQL errors are logged using Pearl format.
        
        This test ensures GraphQL-specific errors (field errors, syntax errors)
        are properly logged with error details in Pearl format.
        """
        service = SnapshotService()
        
        # Mock GraphQL error response
        error_response = {
            "errors": [
                {
                    "message": "Field 'invalid' not found",
                    "extensions": {"code": "FIELD_NOT_FOUND"}
                }
            ]
        }
        
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            json=error_response,
            status_code=200
        )
        
        with patch('services.snapshot_service.logger') as mock_logger:
            with pytest.raises(GraphQLError):
                await service.execute_query("query { invalid }")
            
            # Verify GraphQL error was logged
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any("GraphQL query failed at Snapshot API" in str(call) for call in error_calls), \
                f"Expected 'GraphQL query failed at Snapshot API' in error calls, but got: {error_calls}"
        
        await service.close()

    @pytest.mark.asyncio
    async def test_service_method_spans_with_pearl(self):
        """
        Test that service methods use Pearl log_span for operation tracking.
        
        This test verifies that each service method (get_space, get_proposals, etc.)
        properly uses log_span context manager with appropriate context data.
        """
        service = SnapshotService()
        
        # Mock execute_query to avoid actual API calls
        # Include all required fields for Space model
        mock_response = {
            "space": {
                "id": "test.eth",
                "name": "Test",
                "network": "1",
                "symbol": "TEST",
                "created": 1234567890,
                "strategies": [],
                "admins": [],
                "moderators": [],
                "members": [],
                "private": False
            }
        }
        
        with patch.object(service, 'execute_query', return_value=mock_response):
            with patch('services.snapshot_service.logger') as mock_logger:
                with patch('services.snapshot_service.log_span') as mock_log_span:
                    # Setup mock context manager
                    mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                    mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                    
                    # Test get_space
                    await service.get_space("test.eth")
                    
                    # Verify span was created with correct parameters
                    mock_log_span.assert_called_with(
                        mock_logger,
                        "get_space",
                        space_id="test.eth"
                    )
        
        await service.close()

    @pytest.mark.asyncio
    async def test_get_proposals_span_with_pearl(self):
        """
        Test that get_proposals uses Pearl log_span with all parameters.
        
        This test specifically checks that complex methods with multiple parameters
        properly pass all context to the log_span.
        """
        service = SnapshotService()
        
        mock_response = {"proposals": []}
        
        with patch.object(service, 'execute_query', return_value=mock_response):
            with patch('services.snapshot_service.logger') as mock_logger:
                with patch('services.snapshot_service.log_span') as mock_log_span:
                    # Setup mock context manager
                    mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                    mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                    
                    # Test get_proposals with multiple parameters
                    await service.get_proposals(
                        space_ids=["test.eth", "test2.eth"],
                        state="active",
                        first=10,
                        skip=5
                    )
                    
                    # Verify span includes all parameters
                    mock_log_span.assert_called_with(
                        mock_logger,
                        "get_proposals",
                        space_ids=["test.eth", "test2.eth"],
                        state="active",
                        first=10,
                        skip=5
                    )
        
        await service.close()

    @pytest.mark.asyncio
    async def test_json_parsing_error_logging_with_pearl(self, httpx_mock: HTTPXMock):
        """
        Test that JSON parsing errors are logged using Pearl format.
        
        This test ensures that when the API returns invalid JSON, the error
        is properly logged with truncated response text.
        """
        service = SnapshotService()
        
        # Mock invalid JSON response
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            text="Invalid JSON {not valid}",
            status_code=200
        )
        
        with patch('services.snapshot_service.logger') as mock_logger:
            with pytest.raises(SnapshotServiceError):
                await service.execute_query("query { test }")
            
            # Verify JSON error was logged
            assert any(
                "Failed to parse JSON response from Snapshot API" in str(call)
                for call in mock_logger.error.call_args_list
            )
        
        await service.close()

    @pytest.mark.asyncio
    async def test_unexpected_error_logging_with_pearl(self):
        """
        Test that unexpected errors are logged using Pearl format.
        
        This test verifies the catch-all exception handler logs errors
        with proper context including error type.
        """
        service = SnapshotService()
        
        # Create an unexpected error scenario
        with patch.object(service.client, 'post', side_effect=RuntimeError("Unexpected error")):
            with patch('services.snapshot_service.logger') as mock_logger:
                with pytest.raises(SnapshotServiceError):
                    await service.execute_query("query { test }")
                
                # Verify unexpected error was logged
                error_calls = [str(call) for call in mock_logger.error.call_args_list]
                assert any("Unexpected error during Snapshot API interaction" in str(call) for call in error_calls), \
                    f"Expected 'Unexpected error during Snapshot API interaction' in error calls, but got: {error_calls}"
        
        await service.close()

    def test_truncate_query_for_logging_exists(self):
        """
        Test that _truncate_query_for_logging method exists and works.
        
        This test ensures the helper method for query truncation is present
        and functioning, as it's used in logging to avoid logging sensitive data.
        """
        service = SnapshotService()
        
        # Test short query
        short_query = "query { test }"
        assert service._truncate_query_for_logging(short_query) == short_query
        
        # Test long query
        long_query = "query " + "x" * 1000
        truncated = service._truncate_query_for_logging(long_query)
        assert len(truncated) < len(long_query)
        assert truncated.endswith("...")

    @pytest.mark.asyncio
    async def test_structured_logging_format_compliance(self, httpx_mock: HTTPXMock):
        """
        Test that all logging follows Pearl's structured format.
        
        This test verifies that structured data is logged using key=value format
        with %s placeholders, not f-strings or .format().
        """
        service = SnapshotService()
        
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            json={"data": {"result": "test"}},
            status_code=200
        )
        
        with patch('services.snapshot_service.logger') as mock_logger:
            await service.execute_query("query { test }", {"var": "value"})
            
            # Check all info calls use %s format, not f-strings
            for call in mock_logger.info.call_args_list:
                message = call[0][0]
                # Should not contain f-string style braces (except in GraphQL queries)
                # Check for f-string patterns like {variable} but allow GraphQL query syntax
                if "{" in message and "query" not in message.lower():
                    # This would be an f-string, which we don't want
                    assert False, f"Found f-string pattern in log message: {message}"
                # Should contain %s placeholders if it has additional args
                if len(call[0]) > 1:
                    assert "%s" in message
        
        await service.close()

    @pytest.mark.asyncio 
    async def test_response_validation_logging_with_pearl(self, httpx_mock: HTTPXMock):
        """
        Test that response validation errors are logged using Pearl format.
        
        This test checks that when the API response is missing expected fields,
        the error is logged with response structure details.
        """
        service = SnapshotService()
        
        # Mock response missing 'data' field
        httpx_mock.add_response(
            method="POST",
            url="https://hub.snapshot.org/graphql",
            json={"errors": [], "extensions": {}},  # Missing 'data'
            status_code=200
        )
        
        with patch('services.snapshot_service.logger') as mock_logger:
            with pytest.raises(SnapshotServiceError):
                await service.execute_query("query { test }")
            
            # Verify missing data field was logged
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any("Snapshot API response missing 'data' field" in str(call) for call in error_calls), \
                f"Expected 'Snapshot API response missing data field' in error calls, but got: {error_calls}"
        
        await service.close()

    def test_max_log_response_length_constant(self):
        """
        Test that MAX_LOG_RESPONSE_LENGTH constant is defined.
        
        This constant is important for truncating large responses in error logs
        to prevent log bloat while maintaining debuggability.
        """
        from services.snapshot_service import MAX_LOG_RESPONSE_LENGTH
        
        assert isinstance(MAX_LOG_RESPONSE_LENGTH, int)
        assert MAX_LOG_RESPONSE_LENGTH > 0
        assert MAX_LOG_RESPONSE_LENGTH <= 1000  # Reasonable limit

    @pytest.mark.asyncio
    async def test_all_service_methods_use_pearl_spans(self):
        """
        Test that all public service methods use Pearl log_span.
        
        This comprehensive test ensures every public method that makes API calls
        is properly instrumented with Pearl logging spans.
        """
        service = SnapshotService()
        
        # Methods that should have spans
        methods_with_spans = [
            ('get_space', {'space_id': 'test.eth'}),
            ('get_spaces', {'space_ids': ['test.eth']}),
            ('get_proposal', {'proposal_id': '0x123'}),
            ('get_proposals', {'space_ids': ['test.eth']}),
            ('get_votes', {'proposal_id': '0x123'}),
            ('get_voting_power', {'space_id': 'test.eth', 'voter_address': '0xabc'})
        ]
        
        with patch.object(service, 'execute_query', return_value={}):
            with patch('services.snapshot_service.logger') as mock_logger:
                with patch('services.snapshot_service.log_span') as mock_log_span:
                    # Setup mock context manager
                    mock_log_span.return_value.__enter__ = MagicMock(return_value={})
                    mock_log_span.return_value.__exit__ = MagicMock(return_value=None)
                    
                    for method_name, kwargs in methods_with_spans:
                        mock_log_span.reset_mock()
                        
                        # Call the method
                        method = getattr(service, method_name)
                        await method(**kwargs)
                        
                        # Verify span was created
                        assert mock_log_span.called, f"{method_name} should use log_span"
                        
                        # Verify span name matches method name
                        span_name = mock_log_span.call_args[0][1]
                        assert span_name == method_name
        
        await service.close()
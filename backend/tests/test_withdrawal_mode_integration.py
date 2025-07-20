"""
Test suite for WITHDRAWAL_MODE integration in main.py.

Tests the implementation of BAC-177: Ensures that when WITHDRAWAL_MODE is active,
the application skips normal voting operations and executes withdrawal procedures.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
import asyncio

from main import app, lifespan
from services.withdrawal_service import WithdrawalService
from models import WithdrawalTransaction, WithdrawalStatus, InvestedPosition
from decimal import Decimal


@pytest.fixture
async def test_client():
    """Create test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestWithdrawalModeIntegration:
    """Test WITHDRAWAL_MODE environment variable integration."""
    
    async def test_withdrawal_mode_prevents_normal_operations(self):
        """
        Test that when WITHDRAWAL_MODE is active, normal voting operations are skipped.
        This ensures the system prioritizes emergency withdrawals over regular operations.
        """
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            # Mock the agent run service to verify it's not called
            with patch('main.agent_run_service') as mock_agent_run:
                mock_agent_run.run = AsyncMock()
                
                # Mock withdrawal service
                with patch('main.withdrawal_service') as mock_withdrawal:
                    mock_withdrawal.run_withdrawal_process = AsyncMock(return_value=[])
                    
                    # Simulate the startup process
                    async with lifespan(app):
                        # Verify agent run service was not called
                        mock_agent_run.run.assert_not_called()
                        
                        # Verify withdrawal service was called
                        mock_withdrawal.run_withdrawal_process.assert_called_once()
    
    async def test_normal_mode_executes_voting_operations(self):
        """
        Test that when WITHDRAWAL_MODE is not active, normal voting operations proceed.
        This ensures the system operates normally when not in emergency mode.
        """
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'false'}):
            # Mock the agent run service
            with patch('main.agent_run_service') as mock_agent_run:
                mock_agent_run.run = AsyncMock()
                
                # Mock withdrawal service
                with patch('main.withdrawal_service') as mock_withdrawal:
                    mock_withdrawal.run_withdrawal_process = AsyncMock()
                    
                    # Simulate the startup process
                    async with lifespan(app):
                        # Verify agent run service was called
                        mock_agent_run.run.assert_called()
                        
                        # Verify withdrawal service was not called
                        mock_withdrawal.run_withdrawal_process.assert_not_called()
    
    async def test_withdrawal_mode_startup_logging(self):
        """
        Test that appropriate warnings are logged when WITHDRAWAL_MODE is active.
        This ensures operators are aware the system is in emergency mode.
        """
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            with patch('main.logger') as mock_logger:
                with patch('main.withdrawal_service') as mock_withdrawal:
                    mock_withdrawal.run_withdrawal_process = AsyncMock(return_value=[])
                    
                    async with lifespan(app):
                        # Verify warning was logged
                        mock_logger.warning.assert_called_with(
                            "WITHDRAWAL MODE ACTIVE - Skipping normal voting operations"
                        )
    
    async def test_withdrawal_process_execution(self):
        """
        Test that the withdrawal process is executed correctly when WITHDRAWAL_MODE is active.
        This verifies the complete withdrawal flow is triggered.
        """
        mock_withdrawals = [
            WithdrawalTransaction(
                transaction_hash="0x" + "1" * 64,
                status=WithdrawalStatus.PENDING,
                position_id="test-position-1",
                amount=Decimal("1000.0"),
                chain_id=1
            )
        ]
        
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            with patch('main.withdrawal_service') as mock_withdrawal:
                mock_withdrawal.run_withdrawal_process = AsyncMock(return_value=mock_withdrawals)
                
                async with lifespan(app):
                    # Verify withdrawal process was called
                    mock_withdrawal.run_withdrawal_process.assert_called_once()
                    
                    # Verify return value
                    result = await mock_withdrawal.run_withdrawal_process()
                    assert len(result) == 1
                    assert result[0].transaction_hash == "0x" + "1" * 64
    
    async def test_withdrawal_mode_error_handling(self):
        """
        Test that errors during withdrawal process are handled gracefully.
        This ensures the system doesn't crash if withdrawals fail.
        """
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            with patch('main.withdrawal_service') as mock_withdrawal:
                mock_withdrawal.run_withdrawal_process = AsyncMock(
                    side_effect=Exception("Withdrawal failed")
                )
                
                with patch('main.logger') as mock_logger:
                    # The app should handle the error gracefully
                    try:
                        async with lifespan(app):
                            pass
                    except Exception:
                        # Should not raise exception to the caller
                        pytest.fail("Withdrawal error should be handled gracefully")
                    
                    # Verify error was logged
                    mock_logger.error.assert_called()
    
    async def test_withdrawal_mode_api_endpoint_disabled(self, test_client):
        """
        Test that certain API endpoints return appropriate responses in WITHDRAWAL_MODE.
        This ensures the API communicates the system's emergency state.
        """
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            # Test that agent-run endpoint returns a specific response
            response = await test_client.post(
                "/agent-run",
                json={"space_id": "test.eth", "dry_run": False}
            )
            
            # Should return a specific status indicating withdrawal mode
            assert response.status_code == 503  # Service Unavailable
            assert "withdrawal mode" in response.json()["detail"].lower()
    
    async def test_withdrawal_mode_health_check(self, test_client):
        """
        Test that health check endpoint reports withdrawal mode status.
        This allows monitoring systems to detect emergency mode.
        """
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            response = await test_client.get("/health")
            
            assert response.status_code == 200
            health_data = response.json()
            assert "withdrawal_mode" in health_data
            assert health_data["withdrawal_mode"] is True
    
    async def test_withdrawal_mode_concurrent_safety(self):
        """
        Test that withdrawal mode handles concurrent requests safely.
        This ensures the system remains stable under load during emergency mode.
        """
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            with patch('main.withdrawal_service') as mock_withdrawal:
                call_count = 0
                
                async def mock_withdrawal_process():
                    nonlocal call_count
                    call_count += 1
                    await asyncio.sleep(0.1)  # Simulate processing time
                    return []
                
                mock_withdrawal.run_withdrawal_process = mock_withdrawal_process
                
                # Simulate multiple concurrent startup attempts
                tasks = []
                for _ in range(5):
                    task = asyncio.create_task(lifespan(app).__aenter__())
                    tasks.append(task)
                
                # Wait for all tasks
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Should only execute withdrawal once despite concurrent calls
                assert call_count == 1
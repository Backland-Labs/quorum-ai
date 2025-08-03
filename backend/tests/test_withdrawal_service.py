"""
Test suite for the Withdrawal Service.

Tests the implementation of BAC-177: Withdrawal Mode for emergency fund recovery.
These tests ensure that the system can properly detect withdrawal mode, list invested
positions, calculate withdrawal amounts, and execute withdrawals through Safe contracts.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from typing import Dict, List

from services.withdrawal_service import WithdrawalService
from services.state_manager import StateManager
from services.safe_service import SafeService
from services.snapshot_service import SnapshotService
from models import WithdrawalStatus, InvestedPosition, WithdrawalTransaction


@pytest.fixture
def state_manager():
    """Mock state manager for testing."""
    return AsyncMock(spec=StateManager)


@pytest.fixture
def safe_service():
    """Mock Safe service for testing."""
    return AsyncMock(spec=SafeService)


@pytest.fixture
def snapshot_service():
    """Mock Snapshot service for testing."""
    return AsyncMock(spec=SnapshotService)


@pytest.fixture
def withdrawal_service(state_manager, safe_service, snapshot_service):
    """Create a withdrawal service instance for testing."""
    return WithdrawalService(
        state_manager=state_manager,
        safe_service=safe_service,
        snapshot_service=snapshot_service
    )


class TestWithdrawalServiceInitialization:
    """Test withdrawal service initialization and configuration."""
    
    async def test_service_initialization(self, withdrawal_service):
        """
        Test that the withdrawal service initializes correctly with all dependencies.
        This ensures the service can be properly instantiated and is ready for use.
        """
        assert withdrawal_service is not None
        assert withdrawal_service.state_manager is not None
        assert withdrawal_service.safe_service is not None
        assert withdrawal_service.snapshot_service is not None
    
    async def test_withdrawal_mode_detection(self, withdrawal_service):
        """
        Test that the service can detect when withdrawal mode is active.
        This is critical for determining when to execute withdrawal operations
        instead of normal voting operations.
        """
        # Test when withdrawal mode is not set
        with patch.dict('os.environ', {}, clear=True):
            assert not await withdrawal_service.is_withdrawal_mode_active()
        
        # Test when withdrawal mode is set to false
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'false'}):
            assert not await withdrawal_service.is_withdrawal_mode_active()
        
        # Test when withdrawal mode is set to true
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            assert await withdrawal_service.is_withdrawal_mode_active()


class TestPositionDiscovery:
    """Test discovering invested positions across different protocols."""
    
    async def test_list_invested_positions_empty(self, withdrawal_service, state_manager):
        """
        Test listing positions when no investments have been made.
        This ensures the service handles empty states gracefully.
        """
        state_manager.get_state = AsyncMock(return_value={"invested_positions": []})
        
        positions = await withdrawal_service.list_invested_positions()
        
        assert positions == []
        state_manager.get_state.assert_called_once()
    
    async def test_list_invested_positions_with_data(self, withdrawal_service, state_manager):
        """
        Test listing positions when investments exist across multiple protocols.
        This verifies that the service can track positions from different sources
        and return comprehensive investment data.
        """
        mock_positions = [
            {
                "protocol": "Aave",
                "asset": "USDC",
                "amount": "10000.0",
                "chain_id": 1,
                "position_id": "aave-usdc-1",
                "timestamp": "2025-01-20T12:00:00Z"
            },
            {
                "protocol": "Compound",
                "asset": "DAI",
                "amount": "5000.0",
                "chain_id": 1,
                "position_id": "compound-dai-1",
                "timestamp": "2025-01-20T13:00:00Z"
            }
        ]
        state_manager.get_state = AsyncMock(return_value={"invested_positions": mock_positions})
        
        positions = await withdrawal_service.list_invested_positions()
        
        assert len(positions) == 2
        assert positions[0].protocol == "Aave"
        assert positions[0].amount == Decimal("10000.0")
        assert positions[1].protocol == "Compound"
        assert positions[1].amount == Decimal("5000.0")
    
    async def test_discover_onchain_positions(self, withdrawal_service, safe_service):
        """
        Test discovering positions directly from on-chain data.
        This is important for reconciling state with actual blockchain state
        and discovering positions that might not be tracked locally.
        """
        # Mock Safe contract addresses
        safe_service.get_safe_addresses = AsyncMock(return_value={
            1: "0x1234...safe",
            100: "0x5678...safe"
        })
        
        # Mock on-chain position discovery
        mock_positions = [
            InvestedPosition(
                protocol="Uniswap",
                asset="ETH-USDC-LP",
                amount=Decimal("1000.0"),
                chain_id=1,
                position_id="uni-v3-1",
                timestamp="2025-01-20T14:00:00Z",
                contract_address="0xabcd...pool"
            )
        ]
        
        async def mock_query_defi_positions(chain_id, safe_address):
            # Only return positions for chain 1
            if chain_id == 1:
                return mock_positions
            return []
        
        with patch.object(withdrawal_service, '_query_defi_positions', side_effect=mock_query_defi_positions):
            positions = await withdrawal_service.discover_onchain_positions()
            
            assert len(positions) == 1
            assert positions[0].protocol == "Uniswap"
            safe_service.get_safe_addresses.assert_called_once()


class TestWithdrawalCalculation:
    """Test withdrawal amount calculations and strategies."""
    
    async def test_calculate_withdrawal_amounts_full(self, withdrawal_service):
        """
        Test calculating withdrawal amounts for full withdrawal.
        This ensures that when a full withdrawal is requested, all positions
        are marked for complete withdrawal.
        """
        positions = [
            InvestedPosition(
                protocol="Aave",
                asset="USDC",
                amount=Decimal("10000.0"),
                chain_id=1,
                position_id="aave-usdc-1",
                timestamp="2025-01-20T12:00:00Z"
            ),
            InvestedPosition(
                protocol="Compound",
                asset="DAI",
                amount=Decimal("5000.0"),
                chain_id=1,
                position_id="compound-dai-1",
                timestamp="2025-01-20T13:00:00Z"
            )
        ]
        
        withdrawals = await withdrawal_service.calculate_withdrawal_amounts(
            positions, 
            withdrawal_percentage=100
        )
        
        assert len(withdrawals) == 2
        assert withdrawals[0]["amount"] == Decimal("10000.0")
        assert withdrawals[0]["position_id"] == "aave-usdc-1"
        assert withdrawals[1]["amount"] == Decimal("5000.0")
        assert withdrawals[1]["position_id"] == "compound-dai-1"
    
    async def test_calculate_withdrawal_amounts_partial(self, withdrawal_service):
        """
        Test calculating withdrawal amounts for partial withdrawal.
        This verifies that partial withdrawals correctly calculate percentages
        and maintain precision for financial calculations.
        """
        positions = [
            InvestedPosition(
                protocol="Aave",
                asset="USDC",
                amount=Decimal("10000.0"),
                chain_id=1,
                position_id="aave-usdc-1",
                timestamp="2025-01-20T12:00:00Z"
            )
        ]
        
        withdrawals = await withdrawal_service.calculate_withdrawal_amounts(
            positions,
            withdrawal_percentage=50
        )
        
        assert len(withdrawals) == 1
        assert withdrawals[0]["amount"] == Decimal("5000.0")
        assert withdrawals[0]["percentage"] == 50
    
    async def test_calculate_withdrawal_priority(self, withdrawal_service):
        """
        Test withdrawal prioritization based on position characteristics.
        This ensures that withdrawals are ordered optimally, considering factors
        like liquidity, gas costs, and position size.
        """
        positions = [
            InvestedPosition(
                protocol="Aave",
                asset="USDC",
                amount=Decimal("1000.0"),
                chain_id=1,
                position_id="small-position",
                timestamp="2025-01-20T12:00:00Z"
            ),
            InvestedPosition(
                protocol="Compound",
                asset="DAI",
                amount=Decimal("50000.0"),
                chain_id=1,
                position_id="large-position",
                timestamp="2025-01-20T13:00:00Z"
            ),
            InvestedPosition(
                protocol="Uniswap",
                asset="ETH-USDC-LP",
                amount=Decimal("10000.0"),
                chain_id=100,  # Different chain
                position_id="cross-chain-position",
                timestamp="2025-01-20T14:00:00Z"
            )
        ]
        
        prioritized = await withdrawal_service.prioritize_withdrawals(positions)
        
        # Should prioritize by size and same-chain first
        assert prioritized[0].position_id == "large-position"
        assert prioritized[1].position_id == "small-position"
        assert prioritized[2].position_id == "cross-chain-position"


class TestWithdrawalExecution:
    """Test withdrawal transaction execution and monitoring."""
    
    async def test_execute_withdrawal_single_position(self, withdrawal_service, safe_service, state_manager):
        """
        Test executing a withdrawal for a single position.
        This verifies that the service can correctly build and execute
        withdrawal transactions through the Safe contract.
        """
        position = InvestedPosition(
            protocol="Aave",
            asset="USDC",
            amount=Decimal("10000.0"),
            chain_id=1,
            position_id="aave-usdc-1",
            timestamp="2025-01-20T12:00:00Z",
            contract_address="0xaave...lending"
        )
        
        withdrawal_amount = Decimal("10000.0")
        
        # Mock Safe transaction execution
        safe_service.execute_transaction = AsyncMock(return_value={
            "transaction_hash": "0x" + "1" * 64,
            "safe_tx_hash": "0x" + "2" * 64,
            "status": "pending"
        })
        
        # Mock state manager for updating pending withdrawals
        state_manager.get_state = AsyncMock(return_value={"pending_withdrawals": []})
        state_manager.update_state = AsyncMock()
        
        result = await withdrawal_service.execute_withdrawal(
            position=position,
            amount=withdrawal_amount
        )
        
        assert result.transaction_hash == "0x" + "1" * 64
        assert result.status == WithdrawalStatus.PENDING
        assert result.position_id == "aave-usdc-1"
        assert result.amount == withdrawal_amount
        
        safe_service.execute_transaction.assert_called_once()
    
    async def test_execute_withdrawal_with_retry(self, withdrawal_service, safe_service, state_manager):
        """
        Test withdrawal execution with retry logic for transient failures.
        This ensures the service can handle temporary failures and retry
        operations appropriately.
        """
        position = InvestedPosition(
            protocol="Compound",
            asset="DAI",
            amount=Decimal("5000.0"),
            chain_id=1,
            position_id="compound-dai-1",
            timestamp="2025-01-20T13:00:00Z"
        )
        
        # First call fails, second succeeds
        safe_service.execute_transaction = AsyncMock(side_effect=[
            Exception("Network error"),
            {
                "transaction_hash": "0x" + "3" * 64,
                "safe_tx_hash": "0x" + "4" * 64,
                "status": "pending"
            }
        ])
        
        # Mock state manager for updating pending withdrawals
        state_manager.get_state = AsyncMock(return_value={"pending_withdrawals": []})
        state_manager.update_state = AsyncMock()
        
        result = await withdrawal_service.execute_withdrawal(
            position=position,
            amount=Decimal("5000.0"),
            max_retries=2
        )
        
        assert result.transaction_hash == "0x" + "3" * 64
        assert safe_service.execute_transaction.call_count == 2
    
    async def test_monitor_withdrawal_status(self, withdrawal_service, safe_service, state_manager):
        """
        Test monitoring withdrawal transaction status.
        This verifies that the service can track pending withdrawals
        and update their status based on blockchain confirmations.
        """
        # Mock pending withdrawal
        pending_withdrawal = {
            "transaction_hash": "0x" + "1" * 64,
            "safe_tx_hash": "0x" + "2" * 64,
            "status": "pending",
            "position_id": "aave-usdc-1",
            "amount": "10000.0",
            "chain_id": 1
        }
        
        state_manager.get_state = AsyncMock(return_value={
            "pending_withdrawals": [pending_withdrawal]
        })
        
        # Mock transaction confirmed
        safe_service.get_transaction_status = AsyncMock(return_value={
            "status": "confirmed",
            "confirmations": 12,
            "block_number": 123456
        })
        
        state_manager.update_state = AsyncMock()
        
        await withdrawal_service.monitor_pending_withdrawals()
        
        # Should update state with confirmed status
        state_manager.update_state.assert_called()
        updated_state = state_manager.update_state.call_args[0][0]
        assert updated_state["pending_withdrawals"][0]["status"] == "confirmed"


class TestWithdrawalOrchestration:
    """Test end-to-end withdrawal orchestration."""
    
    async def test_run_withdrawal_process(self, withdrawal_service, state_manager):
        """
        Test running the complete withdrawal process.
        This verifies the full orchestration flow from detection to execution,
        ensuring all components work together correctly.
        """
        # Mock withdrawal mode active
        with patch.dict('os.environ', {'WITHDRAWAL_MODE': 'true'}):
            # Mock positions
            mock_positions = [
                InvestedPosition(
                    protocol="Aave",
                    asset="USDC",
                    amount=Decimal("10000.0"),
                    chain_id=1,
                    position_id="aave-usdc-1",
                    timestamp="2025-01-20T12:00:00Z"
                )
            ]
            
            # Mock list_invested_positions to be an async function
            async def mock_list_invested_positions():
                return mock_positions
            
            with patch.object(withdrawal_service, 'list_invested_positions', side_effect=mock_list_invested_positions):
                with patch.object(withdrawal_service, 'execute_withdrawal') as mock_execute:
                    mock_execute.return_value = WithdrawalTransaction(
                        transaction_hash="0x" + "5" * 64,
                        status=WithdrawalStatus.PENDING,
                        position_id="aave-usdc-1",
                        amount=Decimal("10000.0"),
                        chain_id=1
                    )
                    
                    # Mock state manager for monitor_pending_withdrawals
                    state_manager.get_state = AsyncMock(return_value={"pending_withdrawals": []})
                    state_manager.update_state = AsyncMock()
                    
                    results = await withdrawal_service.run_withdrawal_process()
                    
                    assert len(results) == 1
                    assert results[0].status == WithdrawalStatus.PENDING
                    mock_execute.assert_called_once()
    
    async def test_withdrawal_progress_reporting(self, withdrawal_service, state_manager):
        """
        Test withdrawal progress reporting and status updates.
        This ensures users can track the progress of their withdrawal operations
        and understand the current state of the process.
        """
        # Mock withdrawal state
        state_manager.get_state = AsyncMock(return_value={
            "withdrawal_progress": {
                "total_positions": 3,
                "processed_positions": 1,
                "pending_transactions": 1,
                "confirmed_transactions": 1,
                "failed_transactions": 0,
                "total_value_withdrawn": "15000.0",
                "start_time": "2025-01-20T12:00:00Z"
            }
        })
        
        progress = await withdrawal_service.get_withdrawal_progress()
        
        assert progress["total_positions"] == 3
        assert progress["processed_positions"] == 1
        assert progress["completion_percentage"] == 33.33
        assert progress["status"] == "in_progress"
    
    async def test_withdrawal_emergency_stop(self, withdrawal_service, state_manager):
        """
        Test emergency stop functionality for withdrawal process.
        This is critical for allowing users to halt withdrawals if needed,
        preventing further transactions from being executed.
        """
        # Set up active withdrawal state
        state_manager.get_state = AsyncMock(return_value={
            "withdrawal_active": True,
            "emergency_stop": False
        })
        
        # Set up update_state mock
        state_manager.update_state = AsyncMock()
        
        # Trigger emergency stop
        await withdrawal_service.emergency_stop()
        
        # Verify state updated
        state_manager.update_state.assert_called()
        updated_state = state_manager.update_state.call_args[0][0]
        assert updated_state["emergency_stop"] is True
        assert updated_state["withdrawal_active"] is False
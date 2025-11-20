import pytest
from unittest.mock import MagicMock, patch
from services.staking_service import StakingService, StakingState, ServiceStatus

@pytest.fixture
def mock_web3():
    with patch("services.staking_service.Web3") as mock:
        yield mock

@pytest.fixture
def mock_settings():
    with patch("services.staking_service.settings") as mock:
        mock.staking_contract_address = "0xStakingToken"
        mock.activity_checker_contract_address = "0xActivityChecker"
        yield mock

def test_staking_service_initialization(mock_web3, mock_settings):
    service = StakingService()
    assert service.staking_contract is not None
    assert service.activity_checker is not None

def test_get_service_staking_state_unstaked(mock_web3, mock_settings):
    service = StakingService()
    
    # Mock getStakingState to return UNSTAKED (0)
    service.staking_contract.functions.getStakingState.return_value.call.return_value = 0
    
    result = service.get_service_staking_state(1)
    
    assert result["service_id"] == 1
    assert result["state"] == "UNSTAKED"
    assert result["status"] == "unstaked"
    assert result["is_live"] is False

def test_get_service_staking_state_staked_live(mock_web3, mock_settings):
    service = StakingService()
    
    # Mock getStakingState to return STAKED (1)
    service.staking_contract.functions.getStakingState.return_value.call.return_value = 1
    
    # Mock isPassRatio to return True
    service.activity_checker.functions.isPassRatio.return_value.call.return_value = True
    
    result = service.get_service_staking_state(1)
    
    assert result["service_id"] == 1
    assert result["state"] == "STAKED"
    assert result["status"] == "meeting_threshold"
    assert result["is_live"] is True

def test_get_service_staking_state_staked_not_live(mock_web3, mock_settings):
    service = StakingService()
    
    # Mock getStakingState to return STAKED (1)
    service.staking_contract.functions.getStakingState.return_value.call.return_value = 1
    
    # Mock isPassRatio to return False
    service.activity_checker.functions.isPassRatio.return_value.call.return_value = False
    
    result = service.get_service_staking_state(1)
    
    assert result["service_id"] == 1
    assert result["state"] == "STAKED"
    assert result["status"] == "not_meeting_threshold"
    assert result["is_live"] is False

def test_get_service_staking_state_error(mock_web3, mock_settings):
    service = StakingService()
    
    # Mock getStakingState to raise exception
    service.staking_contract.functions.getStakingState.return_value.call.side_effect = Exception("RPC Error")
    
    result = service.get_service_staking_state(1)
    
    assert result["state"] == "ERROR"
    assert "RPC Error" in result["error"]

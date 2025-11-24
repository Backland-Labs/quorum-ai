"""Service for interacting with OLAS Staking Contract."""

from typing import Dict, Optional, Any
from enum import Enum

from web3 import Web3
from web3.contract import Contract

from logging_config import setup_pearl_logger
from config import settings


class StakingState(Enum):
    """Staking states as defined in the contract."""
    UNSTAKED = 0
    STAKED = 1
    EVICTED = 2


class ServiceStatus(Enum):
    """Service status for UI display."""
    UNSTAKED = "unstaked"
    MEETING_THRESHOLD = "meeting_threshold"
    NOT_MEETING_THRESHOLD = "not_meeting_threshold"
    UNKNOWN = "unknown"


# Minimal Staking Contract ABI
STAKING_CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "serviceId", "type": "uint256"}],
        "name": "getStakingState",
        "outputs": [{"internalType": "enum StakingBase.StakingState", "name": "stakingState", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "activityChecker",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    }
]

# Minimal Activity Checker ABI
ACTIVITY_CHECKER_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "serviceId", "type": "uint256"}],
        "name": "isPassRatio",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    }
]


class StakingService:
    """Encapsulates logic for interacting with the Staking Contract."""

    def __init__(self, rpc_url: str = settings.rpc_url) -> None:
        self.logger = setup_pearl_logger(__name__)

        # Check for Olas placeholder values which cause confusing ENS errors in Web3
        if rpc_url and isinstance(rpc_url, str) and rpc_url.startswith(("str:", "int:", "float:")):
            raise ValueError(
                f"Invalid RPC configuration. The 'rpc_url' parameter contains an Olas placeholder value: '{rpc_url}'. "
                "Please ensure the RPC_URL environment variable is set to a valid URL (e.g., http://localhost:8545)."
            )

        try:
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        except Exception as e:
            # Enhance error message if it looks like an ENS error
            if "ENS name" in str(e) and "invalid" in str(e):
                raise ValueError(
                    f"Web3 initialization failed. The RPC URL '{rpc_url}' was interpreted as an invalid ENS name. "
                    "This usually happens when the URL is not properly formatted (missing http:// prefix) "
                    "or contains invalid characters. Check your RPC_URL environment variable."
                ) from e
            self.logger.error(f"Failed to initialize Web3 provider with URL '{rpc_url}': {e}")
            raise e

        # Initialize Staking Contract
        if settings.staking_contract_address:
            self.staking_contract = self.web3.eth.contract(
                address=settings.staking_contract_address,
                abi=STAKING_CONTRACT_ABI
            )
        else:
            self.logger.warning("STAKING_CONTRACT_ADDRESS not set. Staking features disabled.")
            self.staking_contract = None

        # Initialize Activity Checker Contract
        # We prioritize the config value, but if not set, we could fetch it from the staking contract
        # For now, we rely on the config value which we just updated.
        if settings.activity_checker_contract_address:
            self.activity_checker = self.web3.eth.contract(
                address=settings.activity_checker_contract_address,
                abi=ACTIVITY_CHECKER_ABI
            )
        else:
            self.logger.warning("ACTIVITY_CHECKER_CONTRACT_ADDRESS not set.")
            self.activity_checker = None

    def get_service_staking_state(self, service_id: int) -> Dict[str, Any]:
        """Get the staking state and liveliness status for a service."""
        if not self.staking_contract:
            return {
                "service_id": service_id,
                "state": StakingState.UNSTAKED.name,
                "status": ServiceStatus.UNKNOWN.value,
                "is_live": False
            }

        try:
            # 1. Get Staking State
            state_val = self.staking_contract.functions.getStakingState(service_id).call()
            staking_state = StakingState(state_val)
            
            # Default status
            status = ServiceStatus.UNSTAKED
            is_live = False

            if staking_state == StakingState.STAKED:
                # 2. Check Liveliness via Activity Checker
                if self.activity_checker:
                    try:
                        is_live = self.activity_checker.functions.isPassRatio(service_id).call()
                        status = ServiceStatus.MEETING_THRESHOLD if is_live else ServiceStatus.NOT_MEETING_THRESHOLD
                    except Exception as e:
                        self.logger.error(f"Error calling isPassRatio: {e}")
                        # Fallback or keep as unstaked/unknown? 
                        # If staked but check fails, maybe show unknown or keep as staked but unknown liveliness
                        status = ServiceStatus.UNKNOWN
                else:
                     self.logger.warning("Activity Checker not configured, cannot check liveliness")
                     status = ServiceStatus.UNKNOWN

            return {
                "service_id": service_id,
                "state": staking_state.name,
                "status": status.value,
                "is_live": is_live
            }

        except Exception as e:
            self.logger.error(f"Error getting staking state for service {service_id}: {e}")
            return {
                "service_id": service_id,
                "state": "ERROR",
                "status": ServiceStatus.UNKNOWN.value,
                "is_live": False,
                "error": str(e)
            }

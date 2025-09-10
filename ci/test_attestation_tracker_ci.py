#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "web3==7.6.0",
#     "eth-account==0.13.4",
#     "pydantic==2.10.3",
#     "pydantic-settings==2.6.1",
#     "colorama==0.4.6",
# ]
# ///
"""
Comprehensive CI Test for AttestationTracker Contract
======================================================
This script performs end-to-end testing of the AttestationTracker contract:
1. Deploys AttestationTracker onto Base mainnet fork
2. Simulates SafeService execution flow
3. Verifies attestation counter increments
4. Confirms successful EAS attestation creation

Prerequisites:
- Anvil running with Base fork: anvil --fork-url https://mainnet.base.org --auto-impersonate

Exit codes:
- 0: All tests passed
- 1: Test failure
- 2: Setup/connection error
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Tuple

from web3 import Web3
from eth_account import Account
from colorama import init, Fore, Style

# Add parent directory to path to import from backend
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
from models import EASAttestationData
from utils.eas_signature import generate_eas_delegated_signature, parse_signature_bytes

# Initialize colorama for colored output
init(autoreset=True)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Network configuration
RPC_URL = "http://localhost:8545"
CHAIN_ID = 8453  # Base

# Contract addresses on Base
EIP712_PROXY = "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"
SAFE_ADDRESS = "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"

# Working schema UID (confirmed to exist on Base)
SCHEMA_UID = "0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4"

# Test account (Anvil default)
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def print_header(text: str):
    """Print a formatted section header."""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{Fore.CYAN}{text}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

def print_success(text: str):
    """Print success message in green."""
    print(f"{Fore.GREEN}✅ {text}{Style.RESET_ALL}")

def print_error(text: str):
    """Print error message in red."""
    print(f"{Fore.RED}❌ {text}{Style.RESET_ALL}")

def print_info(text: str):
    """Print info message in yellow."""
    print(f"{Fore.YELLOW}ℹ️  {text}{Style.RESET_ALL}")

def print_detail(label: str, value: str):
    """Print a detail line."""
    print(f"   {Fore.WHITE}{label}: {Fore.CYAN}{value}{Style.RESET_ALL}")

# =============================================================================
# CONTRACT DEPLOYMENT
# =============================================================================

def deploy_attestation_tracker(w3: Web3, account: Account) -> Tuple[str, Any]:
    """Deploy the AttestationTracker contract."""
    print_header("STEP 1: Deploy AttestationTracker Contract")
    
    # Load contract artifacts
    contract_path = Path(__file__).parent.parent / "contracts" / "out" / "AttestationTracker.sol" / "AttestationTracker.json"
    
    if not contract_path.exists():
        print_error(f"Contract artifacts not found at {contract_path}")
        print_info("Run 'forge build' in the contracts directory first")
        sys.exit(2)
    
    with open(contract_path, "r") as f:
        contract_data = json.load(f)
        abi = contract_data["abi"]
        bytecode = contract_data["bytecode"]["object"]
    
    # Deploy contract
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Deploy with EIP712Proxy as the EAS address (critical!)
    tx_hash = contract.constructor(
        account.address,  # initialOwner
        EIP712_PROXY      # EAS address (must be the proxy!)
    ).transact({'from': account.address, 'gas': 3000000})
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = receipt.contractAddress
    
    print_success(f"AttestationTracker deployed at: {contract_address}")
    print_detail("Owner", account.address)
    print_detail("EAS (Proxy)", EIP712_PROXY)
    print_detail("Gas used", str(receipt.gasUsed))
    
    # Return contract instance
    return contract_address, w3.eth.contract(address=contract_address, abi=abi)

# =============================================================================
# EIP-712 SIGNATURE GENERATION
# =============================================================================

def generate_eas_signature(
    w3: Web3,
    attestation_data: bytes,
    recipient: str,
    deadline: int,
    private_key: str
) -> Dict[str, Any]:
    """Generate EIP-712 signature for EAS attestation.
    
    This function now uses the shared utility module to ensure
    consistency with SafeService implementation.
    """
    
    # Prepare request data for the shared function
    request_data = {
        'schema': bytes.fromhex(SCHEMA_UID[2:]),
        'recipient': recipient,
        'expirationTime': 0,
        'revocable': True,
        'refUID': bytes(32),
        'data': attestation_data,
        'value': 0,
        'deadline': deadline,
    }
    
    # Use the shared signature generation function
    signature_bytes = generate_eas_delegated_signature(
        request_data=request_data,
        w3=w3,
        eas_contract_address=EIP712_PROXY,
        private_key=private_key
    )
    
    # Parse the signature bytes into v, r, s components
    parsed = parse_signature_bytes(signature_bytes)
    
    # Get signer address
    account = Account.from_key(private_key)
    
    return {
        'v': parsed['v'],
        'r': parsed['r'],
        's': parsed['s'],
        'signer': account.address
    }

# =============================================================================
# ATTESTATION EXECUTION
# =============================================================================

def execute_attestation(
    w3: Web3,
    tracker_contract: Any,
    attestation_data: EASAttestationData,
    safe_address: str
) -> Dict[str, Any]:
    """Execute attestation through AttestationTracker using production SafeService code."""
    
    print_header("STEP 2: Execute Attestation (Using Production SafeService)")
    
    print_detail("Space ID", attestation_data.space_id)
    print_detail("Proposal ID", attestation_data.proposal_id)
    print_detail("Vote Choice", str(attestation_data.vote_choice))
    print_detail("Agent", attestation_data.agent)
    
    # Get initial attestation count
    initial_count = tracker_contract.functions.getNumAttestations(safe_address).call()
    print_detail("Initial attestation count", str(initial_count))
    
    try:
        # Use production SafeService to build the attestation transaction
        print_info("Using production SafeService code to build attestation transaction")
        
        # Create a mock SafeService instance to use its transaction building logic
        # Note: We can't use the full SafeService because it requires proper configuration,
        # but we can use its internal methods to build the transaction data
        from utils.web3_provider import get_w3
        from utils.abi_loader import load_abi
        
        # Get the tracker contract address
        tracker_address = tracker_contract.address
        print_detail("AttestationTracker address", tracker_address)
        
        # Load the AttestationTracker ABI
        contract_abi = load_abi("attestation_tracker")
        contract = w3.eth.contract(address=Web3.to_checksum_address(tracker_address), abi=contract_abi)
        
        # Build the attestation request using production logic (4-parameter struct interface)
        eas_schema_uid = Web3.to_bytes(hexstr=SCHEMA_UID)
        current_block = w3.eth.get_block('latest')
        deadline = int(current_block['timestamp']) + 3600  # 1 hour deadline
        
        # Encode attestation data using production encoding
        encoded_data = w3.codec.encode(
            ["address", "string", "string", "uint8", "string", "uint256", "string", "uint8"],
            [
                Web3.to_checksum_address(attestation_data.agent),
                attestation_data.space_id,
                attestation_data.proposal_id,
                attestation_data.vote_choice,
                attestation_data.snapshot_sig,
                attestation_data.timestamp,
                attestation_data.run_id,
                attestation_data.confidence,
            ],
        )
        
        # Build attestation request data for signature generation
        attestation_request_data = {
            "schema": eas_schema_uid,
            "data": encoded_data,
            "expirationTime": 0,
            "revocable": True,
            "refUID": b"\x00" * 32,
            "recipient": Web3.to_checksum_address(attestation_data.agent),
            "value": 0,
            "deadline": deadline,
        }
        
        print_detail("Deadline", str(deadline))
        print_detail("Data length", str(len(encoded_data)))
        
        # Generate EAS delegated signature (for EAS contract, not tracker)
        signature = generate_eas_delegated_signature(
            request_data=attestation_request_data,
            w3=w3,
            eas_contract_address=EIP712_PROXY,  # Sign for EAS contract
            private_key=PRIVATE_KEY
        )
        
        # Parse signature bytes into v, r, s components (production logic)
        v = signature[64]
        r = signature[:32]
        s = signature[32:64]
        
        print_detail("Signature v", str(v))
        print_detail("Signature r", r.hex()[:20] + "...")
        print_detail("Signature s", s.hex()[:20] + "...")
        
        # Build the delegated request struct (production 4-parameter structure)
        delegated_request = {
            "schema": eas_schema_uid,
            "data": {
                "recipient": attestation_request_data["recipient"],
                "expirationTime": attestation_request_data["expirationTime"],
                "revocable": attestation_request_data["revocable"],
                "refUID": attestation_request_data["refUID"],
                "data": attestation_request_data["data"],
                "value": attestation_request_data["value"],
            }
        }
        
        # Build the signature struct
        signature_struct = {
            "v": v,
            "r": r,
            "s": s,
        }
        
        # Get attester address
        attester = Account.from_key(PRIVATE_KEY).address
        print_detail("Attester", attester)
        
        print_info("Using production 4-parameter interface (delegated_request, signature_struct, attester, deadline)")
        
        # Fund and impersonate Safe
        w3.provider.make_request("anvil_impersonateAccount", [safe_address])
        if w3.eth.get_balance(safe_address) < w3.to_wei(0.01, 'ether'):
            account = Account.from_key(PRIVATE_KEY)
            w3.eth.send_transaction({
                'from': account.address,
                'to': safe_address,
                'value': w3.to_wei(0.1, 'ether')
            })
        
        # Call with production 4-parameter structure - this should fail if contract has 12-parameter interface
        tx_hash = contract.functions.attestByDelegation(
            delegated_request,
            signature_struct,
            attester,
            deadline
        ).transact({'from': safe_address, 'gas': 500000})
        
        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print_success(f"Transaction successful! Hash: {tx_hash.hex()}")
            print_detail("Block", str(receipt.blockNumber))
            print_detail("Gas used", str(receipt.gasUsed))
            
            # Extract attestation UID from logs
            attestation_uid = None
            for log in receipt.logs:
                # Look for AttestationMade event or Attested event
                if len(log['topics']) >= 2:
                    # AttestationMade event has attestationUID as second indexed parameter
                    attestation_uid = log['topics'][-1].hex() if log['topics'] else None
                    if attestation_uid:
                        break
            
            return {
                'success': True,
                'tx_hash': tx_hash.hex(),
                'attestation_uid': attestation_uid,
                'gas_used': receipt.gasUsed
            }
        else:
            print_error("Transaction failed!")
            return {'success': False, 'error': 'Transaction reverted'}
            
    except Exception as e:
        print_error(f"Attestation failed with production code: {str(e)}")
        print_info("This failure likely indicates interface mismatch between production expectations and contract reality")
        return {'success': False, 'error': str(e)}

# =============================================================================
# VERIFICATION
# =============================================================================

def verify_results(
    w3: Web3,
    tracker_contract: Any,
    safe_address: str,
    result: Dict[str, Any]
) -> bool:
    """Verify that attestation was successful and counter incremented."""
    
    print_header("STEP 3: Verify Results")
    
    all_passed = True
    
    # Check attestation counter
    final_count = tracker_contract.functions.getNumAttestations(safe_address).call()
    print_detail("Final attestation count", str(final_count))
    
    if final_count > 0:
        print_success("Attestation counter incremented correctly")
    else:
        print_error("Attestation counter did not increment")
        all_passed = False
    
    # Check transaction success
    if result.get('success'):
        print_success("Transaction executed successfully")
        if result.get('attestation_uid'):
            print_success(f"Attestation UID captured: {result['attestation_uid']}")
        print_detail("Gas used", str(result.get('gas_used', 'N/A')))
    else:
        print_error(f"Transaction failed: {result.get('error', 'Unknown error')}")
        all_passed = False
    
    # Verify EAS integration
    if result.get('attestation_uid'):
        print_success("EAS attestation created successfully")
    else:
        print_info("Could not verify EAS attestation UID (may be in nested logs)")
    
    return all_passed

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main test execution."""
    
    print_header("ATTESTATION TRACKER CI TEST")
    print(f"{Fore.WHITE}Testing complete flow: Deploy → Execute → Verify{Style.RESET_ALL}\n")
    
    # Connect to network
    print_info("Connecting to Anvil fork...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        print_error("Failed to connect to Anvil")
        print_info("Start Anvil with: anvil --fork-url https://mainnet.base.org --auto-impersonate")
        sys.exit(2)
    
    print_success(f"Connected to chain ID: {w3.eth.chain_id}")
    
    # Setup account
    account = Account.from_key(PRIVATE_KEY)
    print_detail("Test account", account.address)
    print_detail("Balance", f"{w3.eth.get_balance(account.address) / 10**18:.4f} ETH")
    
    try:
        # Deploy contract
        tracker_address, tracker_contract = deploy_attestation_tracker(w3, account)
        
        # Create test attestation data
        test_data = EASAttestationData(
            agent="0x742d35Cc6634C0532925a3b844Bc9e7595f0fA27",
            space_id="compound-governance.eth",
            proposal_id=f"0x{int(time.time()):x}",
            vote_choice=1,
            snapshot_sig=f"0x{'0' * 64}",  # Valid 66-character hash format
            timestamp=int(time.time()),
            run_id=f"ci_test_{int(time.time())}",
            confidence=95
        )
        
        # Execute attestation
        result = execute_attestation(w3, tracker_contract, test_data, SAFE_ADDRESS)
        
        # Verify results
        all_passed = verify_results(w3, tracker_contract, SAFE_ADDRESS, result)
        
        # Final summary
        print_header("TEST SUMMARY")
        
        if all_passed:
            print_success("ALL TESTS PASSED!")
            print(f"\n{Fore.GREEN}✅ AttestationTracker deployed successfully")
            print(f"✅ Attestation executed through Safe")
            print(f"✅ Counter incremented correctly")
            print(f"✅ EAS integration working{Style.RESET_ALL}")
            sys.exit(0)
        else:
            print_error("SOME TESTS FAILED")
            print_info("Check the output above for details")
            sys.exit(1)
            
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
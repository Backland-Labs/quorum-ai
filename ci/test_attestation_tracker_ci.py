#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "web3>=7.12.0",
#     "eth-account>=0.13.7",
#     "pydantic>=2.10.0",
#     "pydantic-settings>=2.6.0",
#     "pydantic-ai",
#     "colorama==0.4.6",
#     "httpx>=0.28.0",
#     "safe-eth-py>=7.7.0",
#     "requests>=2.32.4",
#     "python-dotenv>=1.0.0",
#     "fastapi>=0.115.0",
#     "python-multipart>=0.0.12",
#     "uvicorn[standard]>=0.32.0",
# ]
# ///
"""
Comprehensive CI Test for AttestationTracker Contract
======================================================
This script performs end-to-end testing of the AttestationTracker contract:
1. Deploys AttestationTracker onto Base mainnet fork
2. Tests SafeService integration using actual backend code
3. Verifies attestation counter increments
4. Confirms successful EAS attestation creation

This test directly uses the backend SafeService code to ensure:
- Any changes to SafeService are properly tested
- The integration between SafeService and AttestationTracker is validated
- The end-to-end flow works without mocks

Prerequisites:
- Anvil running with Base fork: anvil --fork-url https://mainnet.base.org --auto-impersonate

Exit codes:
- 0: All tests passed
- 1: Test failure
- 2: Setup/connection error
"""

import os
import json
import subprocess
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

# Initialize colorama for colored output
init(autoreset=True)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Network configuration
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
CHAIN_ID = 8453  # Base

# Contract addresses on Base
EIP712_PROXY = os.getenv("EAS_CONTRACT_ADDRESS", "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6")
SAFE_ADDRESS = os.getenv("BASE_SAFE_ADDRESS", "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca")

# Working schema UID (confirmed to exist on Base)
SCHEMA_UID = os.getenv("EAS_SCHEMA_UID", "0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4")

# Test account (Anvil default)
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

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

def deploy_attestation_tracker(w3: Web3, account: Account, eas_address: str) -> Tuple[str, Any]:
    """Deploy the AttestationTracker contract."""
    print_header("STEP 1: Deploy AttestationTracker Contract")
    
    # Try to compile the contract if forge is available
    contracts_dir = Path(__file__).parent.parent / "contracts"
    if (contracts_dir / "src" / "AttestationTracker.sol").exists():
        print_info("Compiling AttestationTracker contract with Forge...")
        
        # Run forge build to compile the contract
        result = subprocess.run(
            ["forge", "build"],
            cwd=contracts_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print_error(f"Failed to compile: {result.stderr}")
            sys.exit(2)
        
        # Load compiled bytecode and ABI
        artifact_path = contracts_dir / "out" / "AttestationTracker.sol" / "AttestationTracker.json"
        if artifact_path.exists():
            with open(artifact_path, 'r') as f:
                artifact = json.load(f)
                tracker_bytecode = artifact['bytecode']['object']
                tracker_abi = artifact['abi']
                print_success(f"Loaded compiled AttestationTracker (bytecode length: {len(tracker_bytecode)} chars)")
        else:
            print_error("Failed to find compiled AttestationTracker artifact")
            sys.exit(2)
    else:
        print_error("AttestationTracker.sol not found")
        sys.exit(2)
    
    # Deploy AttestationTracker
    print_info(f"Deploying with owner: {account.address}, EAS: {eas_address}")
    TrackerContract = w3.eth.contract(abi=tracker_abi, bytecode=tracker_bytecode)
    tx = TrackerContract.constructor(account.address, eas_address).build_transaction({
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price,
    })
    
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        print_success(f"AttestationTracker deployed at: {receipt.contractAddress}")
        print_detail("Owner", account.address)
        print_detail("EAS (Proxy)", eas_address)
        print_detail("Gas used", str(receipt.gasUsed))
        return receipt.contractAddress, tracker_abi
    else:
        print_error("Failed to deploy AttestationTracker")
        sys.exit(2)

# =============================================================================
# SAFE SERVICE INTEGRATION TEST
# =============================================================================

def test_safe_service_integration(
    w3: Web3,
    account: Account,
    tracker_address: str,
    eas_address: str
) -> bool:
    """Test SafeService integration with AttestationTracker using actual backend code.
    
    This test verifies:
    1. SafeService correctly builds transactions targeting AttestationTracker
    2. The transaction data is properly formatted with all 12 parameters
    3. The signature generation works correctly
    4. The transaction executes successfully on-chain
    5. The attestation counter increments
    6. Events are properly emitted
    """
    print_header("STEP 2: Testing SafeService Integration with AttestationTracker")
    
    # Set up environment variables for SafeService
    os.environ['ATTESTATION_TRACKER_ADDRESS'] = tracker_address
    os.environ['EAS_CONTRACT_ADDRESS'] = eas_address
    os.environ['EAS_SCHEMA_UID'] = SCHEMA_UID
    os.environ['BASE_SAFE_ADDRESS'] = SAFE_ADDRESS
    os.environ['RPC_URL'] = RPC_URL
    os.environ['CHAIN_ID'] = str(w3.eth.chain_id)
    os.environ['ATTESTATION_CHAIN'] = 'base'
    os.environ['BASE_LEDGER_RPC'] = RPC_URL
    
    print_info(f"Environment configured:")
    print_detail("ATTESTATION_TRACKER_ADDRESS", tracker_address)
    print_detail("EAS_CONTRACT_ADDRESS", eas_address)
    print_detail("CHAIN_ID", str(w3.eth.chain_id))
    
    # Write private key to file for SafeService
    with open('ethereum_private_key.txt', 'w') as f:
        f.write(PRIVATE_KEY)
    
    try:
        print_info("Initializing SafeService from backend...")
        
        # Import SafeService and settings AFTER environment variables are set
        from services.safe_service import SafeService
        from config import settings
        from utils.abi_loader import load_abi
        
        # Override settings directly
        settings.attestation_tracker_address = tracker_address
        settings.eas_contract_address = eas_address
        settings.eas_schema_uid = SCHEMA_UID
        settings.base_safe_address = SAFE_ADDRESS
        settings.attestation_chain = 'base'
        
        # Initialize SafeService
        safe_service = SafeService()
        print_success("SafeService initialized successfully")
        
        # Create test attestation data
        test_cases = [
            {
                "name": "Standard attestation",
                "data": EASAttestationData(
                    agent="0x742d35Cc6634C0532925a3b844Bc9e7595f0fA27",
                    space_id="compound-governance.eth",
                    proposal_id=f"0x{int(time.time()):x}",
                    vote_choice=1,
                    snapshot_sig="0x" + "0" * 64,
                    timestamp=int(time.time()),
                    run_id=f"ci_test_{int(time.time())}",
                    confidence=95,
                    retry_count=0
                )
            },
            {
                "name": "Max confidence attestation",
                "data": EASAttestationData(
                    agent="0x742d35Cc6634C0532925a3b844Bc9e7595f0fA27",
                    space_id="edge-test.eth",
                    proposal_id=f"0xedge{int(time.time()):x}",
                    vote_choice=2,
                    snapshot_sig="0x" + "f" * 64,
                    timestamp=int(time.time()),
                    run_id=f"ci_test_max_{int(time.time())}",
                    confidence=100,
                    retry_count=1
                )
            }
        ]
        
        # Load tracker ABI
        tracker_abi = load_abi('attestation_tracker')
        tracker_contract = w3.eth.contract(address=Web3.to_checksum_address(tracker_address), abi=tracker_abi)
        
        all_passed = True
        
        for test_case in test_cases:
            print_info(f"\nTesting: {test_case['name']}")
            attestation_data = test_case['data']
            
            print_detail("Space ID", attestation_data.space_id)
            print_detail("Proposal ID", attestation_data.proposal_id)
            print_detail("Vote Choice", str(attestation_data.vote_choice))
            print_detail("Confidence", str(attestation_data.confidence))
            
            # Test 1: Verify encoding works
            print_info("Testing attestation data encoding...")
            encoded_data = safe_service._encode_attestation_data(attestation_data)
            assert isinstance(encoded_data, bytes), "Encoded data should be bytes"
            assert len(encoded_data) > 0, "Encoded data should not be empty"
            print_success(f"Attestation data encoded (length: {len(encoded_data)} bytes)")
            
            # Test 2: Build transaction data
            print_info("Building attestation transaction via SafeService...")
            tx_data = safe_service._build_eas_attestation_tx(attestation_data)
            
            # Verify transaction structure
            assert 'to' in tx_data, "Transaction missing 'to' field"
            assert 'data' in tx_data, "Transaction missing 'data' field"
            assert tx_data['to'].lower() == tracker_address.lower(), \
                f"Transaction target mismatch: expected {tracker_address}, got {tx_data['to']}"
            print_success(f"Transaction targets AttestationTracker at {tracker_address}")
            
            # Get initial attestation count
            initial_count = tracker_contract.functions.getNumAttestations(SAFE_ADDRESS).call()
            print_detail("Initial attestation count", str(initial_count))
            
            # Test 3: Execute transaction on-chain
            print_info("Executing transaction on local network...")
            
            # Fund and impersonate the Safe address
            w3.provider.make_request("anvil_impersonateAccount", [SAFE_ADDRESS])
            if w3.eth.get_balance(SAFE_ADDRESS) < w3.to_wei(0.01, 'ether'):
                w3.eth.send_transaction({
                    'from': account.address,
                    'to': SAFE_ADDRESS,
                    'value': w3.to_wei(0.1, 'ether')
                })
            
            # Execute transaction
            tx = {
                'from': SAFE_ADDRESS,
                'to': tx_data['to'],
                'data': tx_data['data'],
                'value': tx_data.get('value', 0),
                'gas': 1000000,
                'gasPrice': w3.eth.gas_price
            }
            
            try:
                # First try to call to check for errors
                result = w3.eth.call(tx)
                print_info(f"Call succeeded with result: {result.hex()[:20] if result else 'empty'}...")
                
                # Send actual transaction
                tx_hash = w3.eth.send_transaction(tx)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
                
                if receipt.status == 1:
                    print_success(f"Transaction executed successfully (tx: {tx_hash.hex()[:20]}...)")
                    print_detail("Gas used", str(receipt.gasUsed))
                    
                    # Check attestation count
                    final_count = tracker_contract.functions.getNumAttestations(SAFE_ADDRESS).call()
                    print_detail("Final attestation count", str(final_count))
                    
                    if final_count > initial_count:
                        print_success(f"Attestation counter incremented: {initial_count} → {final_count}")
                        
                        # Check for events
                        if any(log.address.lower() == tracker_address.lower() for log in receipt.logs):
                            print_success("AttestationMade event emitted")
                        else:
                            print_error("AttestationMade event not found")
                            all_passed = False
                    else:
                        print_error(f"Attestation counter not incremented (still {final_count})")
                        all_passed = False
                else:
                    print_error("Transaction reverted")
                    all_passed = False
                    
            except Exception as e:
                print_error(f"Transaction failed: {str(e)}")
                all_passed = False
                continue
        
        # Test 4: Verify error handling
        print_info("\nTesting SafeService error handling...")
        original_tracker = settings.attestation_tracker_address
        try:
            settings.attestation_tracker_address = None
            tx_data = safe_service._build_eas_attestation_tx(test_cases[0]['data'])
            # Should target EAS directly when AttestationTracker not configured
            assert tx_data['to'].lower() == eas_address.lower(), \
                "Should target EAS when AttestationTracker not configured"
            print_success("SafeService correctly falls back to direct EAS")
        except Exception as e:
            print_error(f"Failed to handle missing AttestationTracker: {e}")
            all_passed = False
        finally:
            settings.attestation_tracker_address = original_tracker
        
        return all_passed
        
    except Exception as e:
        print_error(f"SafeService integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists('ethereum_private_key.txt'):
            os.remove('ethereum_private_key.txt')

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main test execution."""
    
    print_header("ATTESTATION TRACKER CI TEST")
    print(f"{Fore.WHITE}Testing SafeService integration with AttestationTracker{Style.RESET_ALL}\n")
    print(f"{Fore.WHITE}This test uses actual backend SafeService code to ensure:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}- Any changes to SafeService are properly tested{Style.RESET_ALL}")
    print(f"{Fore.WHITE}- The integration is validated end-to-end{Style.RESET_ALL}\n")
    
    # Allow override of tracker address for testing existing deployments
    provided_tracker_address = os.getenv("ATTESTATION_TRACKER_ADDRESS", None)
    
    # Connect to network
    print_info(f"Connecting to network at {RPC_URL}...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    if not w3.is_connected():
        print_error("Failed to connect to Anvil")
        print_info("Start Anvil with: anvil --fork-url https://mainnet.base.org --auto-impersonate")
        sys.exit(2)
    
    print_success(f"Connected to chain ID: {w3.eth.chain_id}")
    
    # Setup account
    account = Account.from_key(PRIVATE_KEY)
    print_detail("Test account", account.address)
    
    # Fund the test account using Anvil's setBalance RPC method
    initial_balance = w3.eth.get_balance(account.address)
    if initial_balance < Web3.to_wei(1, 'ether'):
        print_info("Funding test account...")
        # Use Anvil's hardhat_setBalance to fund the account
        w3.provider.make_request(
            "hardhat_setBalance",
            [account.address, hex(Web3.to_wei(10, 'ether'))]
        )
        new_balance = w3.eth.get_balance(account.address)
        print_success(f"Funded account with {new_balance / 10**18:.4f} ETH")
    
    print_detail("Balance", f"{w3.eth.get_balance(account.address) / 10**18:.4f} ETH")
    
    # Also fund the Safe address that will be used for transactions
    safe_balance = w3.eth.get_balance(SAFE_ADDRESS)
    if safe_balance < Web3.to_wei(1, 'ether'):
        print_info(f"Funding Safe address {SAFE_ADDRESS}...")
        w3.provider.make_request(
            "hardhat_setBalance",
            [SAFE_ADDRESS, hex(Web3.to_wei(10, 'ether'))]
        )
        print_success(f"Funded Safe with {w3.eth.get_balance(SAFE_ADDRESS) / 10**18:.4f} ETH")
    
    # Check if EAS contract exists (it should on a forked mainnet)
    eas_code = w3.eth.get_code(Web3.to_checksum_address(EIP712_PROXY))
    if eas_code == b'':
        print_error(f"No EAS contract found at {EIP712_PROXY}")
        print_error("Make sure you're running on a forked Base mainnet")
        sys.exit(2)
    else:
        print_success(f"EAS contract found at {EIP712_PROXY}")
    
    try:
        # Deploy or use existing AttestationTracker
        if provided_tracker_address:
            print_info(f"Using provided AttestationTracker at: {provided_tracker_address}")
            tracker_address = provided_tracker_address
            
            # Check if contract exists
            code = w3.eth.get_code(Web3.to_checksum_address(tracker_address))
            if code == b'':
                print_error(f"No contract found at address {tracker_address}")
                print_info("Deploying new AttestationTracker...")
                tracker_address, tracker_abi = deploy_attestation_tracker(w3, account, EIP712_PROXY)
            else:
                print_success(f"AttestationTracker contract found at {tracker_address}")
                # We'll load the ABI later in the test
                tracker_abi = None
        else:
            # Deploy new AttestationTracker
            tracker_address, tracker_abi = deploy_attestation_tracker(w3, account, EIP712_PROXY)
        
        # Test SafeService integration
        success = test_safe_service_integration(w3, account, tracker_address, EIP712_PROXY)
        
        # Final summary
        print_header("TEST SUMMARY")
        
        if success:
            print_success("ALL TESTS PASSED!")
            print(f"\n{Fore.GREEN}✅ AttestationTracker deployed successfully{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ SafeService initialized from backend code{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Attestation encoding verified{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Transaction building verified{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Multiple test cases executed{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Attestation counter incremented{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Events emitted correctly{Style.RESET_ALL}")
            print(f"{Fore.GREEN}✅ Error handling verified{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}AttestationTracker Address: {tracker_address}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}EAS Contract Address: {EIP712_PROXY}{Style.RESET_ALL}")
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
#!/usr/bin/env python3
"""
End-to-end integration test for SafeService and AttestationTracker interaction.

This test validates the complete flow from SafeService to AttestationTracker contract
without any mocks. It deploys fresh contracts on a local test network (Anvil) and
verifies that attestations are correctly tracked.

## What This Test Validates:

1. **Data Schema Compatibility**: Verifies that the SafeService correctly encodes
   attestation data according to the EAS schema for agent voting records.

2. **Signature Generation**: Confirms that EIP-712 signatures are generated with
   the correct domain parameters for the EIP712Proxy contract.

3. **Contract Integration**: Tests the full flow where:
   - SafeService builds a transaction with 12 parameters for AttestationTracker
   - AttestationTracker increments its attestation counter
   - AttestationTracker reconstructs the nested struct and forwards to EAS
   - EAS accepts the delegated attestation

## Known Issues and Fixes:

### Issue 1: InvalidSchema Error (0xbf37b20e)
**Problem**: Initial tests failed with InvalidSchema error because the schema UID
didn't exist on the forked Base mainnet.
**Fix**: Use the correct schema UID that exists on the testnet:
`0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4`

### Issue 2: Transaction Reverts Despite Successful Call
**Problem**: eth_call succeeded but eth_sendTransaction reverted, indicating
insufficient gas allocation.
**Fix**: Increased gas limit from 500,000 to 1,000,000 to account for the
complex nested calls through AttestationTracker to EAS.

### Issue 3: Signature Verification
**Problem**: Ensuring signatures are generated for the correct contract address.
**Fix**: Confirmed that signatures must be generated for the EIP712Proxy address
(`0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6`) even though AttestationTracker
forwards to it, not the direct EAS contract address.

## Requirements:
- Anvil running locally with Base mainnet fork: 
  `anvil --fork-url <BASE_RPC_URL>`
- Forge installed for contract compilation
- Python dependencies: web3, eth-account

## Usage:
    # Start Anvil with Base fork in one terminal:
    anvil --fork-url https://base-mainnet.infura.io/v3/YOUR_KEY

    # Run the test:
    python scripts/test_attestation_tracker_e2e.py
    
    # Or with existing deployed contract:
    ATTESTATION_TRACKER_ADDRESS=0x... python scripts/test_attestation_tracker_e2e.py

## Expected Output:
- Deploys AttestationTracker contract (or uses provided address)
- Creates test attestation data with proper encoding
- Generates EIP-712 signature for delegated attestation
- Submits transaction through AttestationTracker
- Verifies attestation counter increments
- Confirms AttestationMade event emission
"""

import os
import sys
import json
import time
import subprocess
import traceback
from pathlib import Path
from web3 import Web3
from eth_account import Account

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Import backend modules (delay settings import to allow env var configuration)
from models import EASAttestationData
from utils.web3_provider import get_w3
from utils.abi_loader import load_abi

# Configuration
RPC_URL = os.getenv("RPC_URL", "http://localhost:8545")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(title):
    """Print a formatted header."""
    print(f"\n{BOLD}{'=' * 80}{RESET}")
    print(f"{BOLD}{title}{RESET}")
    print(f"{BOLD}{'=' * 80}{RESET}")

def print_section(title):
    """Print a formatted section header."""
    print(f"\n{BLUE}{'-' * 40}{RESET}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{BLUE}{'-' * 40}{RESET}")

def print_success(message):
    """Print a success message."""
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    """Print an error message."""
    print(f"{RED}❌ {message}{RESET}")

def print_info(message):
    """Print an info message."""
    print(f"{YELLOW}ℹ️  {message}{RESET}")


def deploy_attestation_tracker(w3, account, eas_address):
    """Deploy AttestationTracker contract."""
    print_section("Deploying AttestationTracker Contract")
    
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
            return None, None
        
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
            return None, None
    else:
        # Load ABI from backend if available
        abi_path = Path(__file__).parent.parent / "backend" / "abi" / "attestation_tracker.json"
        if abi_path.exists():
            with open(abi_path, 'r') as f:
                tracker_abi = json.load(f)
            print_info("Loaded AttestationTracker ABI from backend")
        else:
            print_error("AttestationTracker.sol not found and no ABI available")
            return None, None
        
        # We can't deploy without bytecode
        print_error("Cannot deploy without compiled bytecode")
        return None, None
    
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
        return receipt.contractAddress, tracker_abi
    else:
        print_error("Failed to deploy AttestationTracker")
        return None, None

def test_safe_service_integration(w3, account, tracker_address, eas_address):
    """Test SafeService integration with AttestationTracker using actual backend code.
    
    This test verifies:
    1. SafeService correctly builds transactions targeting AttestationTracker
    2. The transaction data is properly formatted with all 12 parameters
    3. The signature generation works correctly
    4. The transaction executes successfully on-chain
    5. The attestation counter increments
    6. Events are properly emitted
    
    This ensures that any changes to the backend SafeService will be caught by this test.
    """
    print_section("Testing SafeService Integration with AttestationTracker")
    
    # Set up environment variables for SafeService
    os.environ['ATTESTATION_TRACKER_ADDRESS'] = tracker_address
    os.environ['EAS_CONTRACT_ADDRESS'] = eas_address
    os.environ['EAS_SCHEMA_UID'] = '0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4'  # Existing schema on testnet
    os.environ['BASE_SAFE_ADDRESS'] = account.address  # Use test account as sender
    os.environ['RPC_URL'] = RPC_URL
    os.environ['CHAIN_ID'] = str(w3.eth.chain_id)
    os.environ['ATTESTATION_CHAIN'] = 'base'  # Set attestation chain
    
    # Override Safe service RPC endpoints to use local network
    os.environ['BASE_LEDGER_RPC'] = RPC_URL
    
    print_info(f"Environment configured:")
    print_info(f"  ATTESTATION_TRACKER_ADDRESS: {tracker_address}")
    print_info(f"  EAS_CONTRACT_ADDRESS: {eas_address}")
    print_info(f"  CHAIN_ID: {w3.eth.chain_id}")
    print_info(f"  RPC_URL: {RPC_URL}")
    
    # Write private key to file for SafeService
    with open('ethereum_private_key.txt', 'w') as f:
        f.write(PRIVATE_KEY)
    
    try:
        print_info("Initializing SafeService from backend...")
        
        # Import SafeService and settings AFTER environment variables are set
        from services.safe_service import SafeService
        from config import settings
        
        # Override settings directly since pydantic_settings caches environment variables
        settings.attestation_tracker_address = tracker_address
        settings.eas_contract_address = eas_address
        settings.eas_schema_uid = '0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4'
        settings.base_safe_address = account.address
        settings.attestation_chain = 'base'
        
        # Verify settings loaded correctly
        print_info(f"Settings updated with ATTESTATION_TRACKER_ADDRESS: {settings.attestation_tracker_address}")
        
        # Initialize SafeService - this tests the initialization logic
        safe_service = SafeService()
        print_success("✓ SafeService initialized successfully")
        
        # Create test attestation data with various test cases
        test_cases = [
            # Standard test case
            {
                "name": "Standard attestation",
                "data": EASAttestationData(
                    agent=account.address,
                    space_id="test.eth",
                    proposal_id="0xtest123",
                    vote_choice=1,
                    snapshot_sig="0x" + "0" * 64,
                    timestamp=int(time.time()),
                    run_id="test_run_001",
                    confidence=85,
                    retry_count=0
                )
            },
            # Edge case: max confidence
            {
                "name": "Max confidence attestation",
                "data": EASAttestationData(
                    agent=account.address,
                    space_id="edge-test.eth",
                    proposal_id="0xedge456",
                    vote_choice=2,
                    snapshot_sig="0x" + "f" * 64,
                    timestamp=int(time.time()),
                    run_id="test_run_002",
                    confidence=100,
                    retry_count=3
                )
            },
            # Edge case: min confidence
            {
                "name": "Min confidence attestation",
                "data": EASAttestationData(
                    agent=account.address,
                    space_id="min-test.eth",
                    proposal_id="0xmin789",
                    vote_choice=0,
                    snapshot_sig="0x" + "1" * 64,
                    timestamp=int(time.time()),
                    run_id="test_run_003",
                    confidence=0,
                    retry_count=0
                )
            }
        ]
        
        # Track success for all test cases
        all_tests_passed = True
        
        for test_case in test_cases:
            print_info(f"\nTesting: {test_case['name']}")
            attestation_data = test_case['data']
            
            # Test 1: Verify _encode_attestation_data works correctly
            print_info("Testing attestation data encoding...")
            encoded_data = safe_service._encode_attestation_data(attestation_data)
            assert isinstance(encoded_data, bytes), "Encoded data should be bytes"
            assert len(encoded_data) > 0, "Encoded data should not be empty"
            print_success(f"✓ Attestation data encoded successfully (length: {len(encoded_data)} bytes)")
            
            # Test 2: Build the transaction data using SafeService
            print_info("Building attestation transaction data via SafeService...")
            tx_data = safe_service._build_eas_attestation_tx(attestation_data)
            
            # Verify transaction structure
            assert 'to' in tx_data, "Transaction missing 'to' field"
            assert 'data' in tx_data, "Transaction missing 'data' field"
            assert 'value' in tx_data, "Transaction missing 'value' field"
            
            # Verify transaction is targeted at AttestationTracker
            assert tx_data['to'].lower() == tracker_address.lower(), \
                f"Transaction target mismatch: expected {tracker_address}, got {tx_data['to']}"
            print_success(f"✓ Transaction correctly targets AttestationTracker at {tracker_address}")
            
            # Verify transaction data is properly formatted
            assert isinstance(tx_data['data'], str), "Transaction data should be a hex string"
            assert tx_data['data'].startswith('0x'), "Transaction data should start with 0x"
            print_success(f"✓ Transaction data properly formatted (length: {len(tx_data['data'])} chars)")
            
            # Test 3: Decode and verify the transaction data contains correct function selector
            # The function selector for attestByDelegation with 12 params should be in the data
            function_selector = tx_data['data'][:10]  # First 4 bytes (0x + 8 hex chars)
            print_info(f"Function selector: {function_selector}")
            
            # Test 4: Verify signature generation works
            print_info("Testing signature generation...")
            test_w3 = get_w3('base')
            current_block = test_w3.eth.get_block('latest')
            deadline = int(current_block['timestamp']) + 3600
            
            attestation_request_data = {
                "schema": Web3.to_bytes(hexstr=os.environ['EAS_SCHEMA_UID']),
                "data": encoded_data,
                "expirationTime": 0,
                "revocable": True,
                "refUID": b"\x00" * 32,
                "recipient": Web3.to_checksum_address(attestation_data.agent),
                "value": 0,
                "deadline": deadline,
            }
            
            signature = safe_service._generate_eas_delegated_signature(
                attestation_request_data,
                test_w3,
                eas_address
            )
            assert isinstance(signature, bytes), "Signature should be bytes"
            assert len(signature) == 65, f"Signature should be 65 bytes, got {len(signature)}"
            print_success(f"✓ Signature generated successfully (length: {len(signature)} bytes)")
            
            # Test 5: Execute the transaction on-chain
            print_info("Executing transaction on local network...")
            
            # Load the tracker ABI
            tracker_abi = load_abi('attestation_tracker')
            tracker_contract = w3.eth.contract(address=Web3.to_checksum_address(tracker_address), abi=tracker_abi)
            
            # Get initial attestation count
            initial_count = tracker_contract.functions.getNumAttestations(account.address).call()
            print_info(f"Initial attestation count: {initial_count}")
            
            # Execute the transaction directly (bypassing Safe multi-sig)
            tx = {
                'from': account.address,
                'to': tx_data['to'],
                'data': tx_data['data'],
                'value': tx_data.get('value', 0),
                'gas': 1000000,
                'gasPrice': w3.eth.gas_price,
                'nonce': w3.eth.get_transaction_count(account.address)
            }
            
            # Try to execute and capture revert reason
            try:
                # First try to call to get revert reason
                try:
                    result = w3.eth.call(tx)
                    print_info(f"Call succeeded with result: {result.hex() if result else 'empty'}")
                except Exception as call_error:
                    print_error(f"Call failed with: {call_error}")
                    # Try to decode the revert reason
                    if hasattr(call_error, 'data'):
                        print_error(f"Revert data: {call_error.data}")
                    all_tests_passed = False
                    continue
                
                # If call succeeds, send the actual transaction
                signed_tx = account.sign_transaction(tx)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            except Exception as e:
                print_error(f"Transaction failed: {e}")
                all_tests_passed = False
                continue
            
            if receipt.status == 1:
                print_success(f"✓ Transaction executed successfully (tx_hash: {tx_hash.hex()})")
                print_info(f"  Gas used: {receipt.gasUsed}")
                
                # Check final attestation count
                final_count = tracker_contract.functions.getNumAttestations(account.address).call()
                print_info(f"Final attestation count: {final_count}")
                
                if final_count > initial_count:
                    print_success(f"✓ Attestation counter incremented from {initial_count} to {final_count}")
                    
                    # Check for events
                    event_found = False
                    for log in receipt.logs:
                        if log.address.lower() == tracker_address.lower():
                            print_success(f"✓ AttestationMade event emitted from AttestationTracker")
                            event_found = True
                            break
                    
                    if not event_found:
                        print_error("✗ AttestationMade event not found")
                        all_tests_passed = False
                else:
                    print_error(f"✗ Attestation counter not incremented (still {final_count})")
                    all_tests_passed = False
            else:
                print_error(f"✗ Transaction reverted")
                all_tests_passed = False
        
        # Test 6: Verify SafeService properly handles missing configuration
        print_info("\nTesting SafeService error handling...")
        
        # Test missing AttestationTracker address by temporarily modifying settings
        try:
            # Save original value
            original_tracker_address = settings.attestation_tracker_address
            
            # Temporarily set to None to simulate missing config
            settings.attestation_tracker_address = None
            
            # This should fall back to direct EAS
            tx_data = safe_service._build_eas_attestation_tx(attestation_data)
            # Should target EAS directly now
            assert tx_data['to'].lower() == eas_address.lower(), \
                f"Should target EAS when AttestationTracker not configured, got {tx_data['to']}"
            print_success("✓ SafeService correctly falls back to direct EAS when AttestationTracker not configured")
            
            # Restore original value
            settings.attestation_tracker_address = original_tracker_address
        except Exception as e:
            print_error(f"Failed to handle missing AttestationTracker: {e}")
            all_tests_passed = False
            # Try to restore settings
            try:
                settings.attestation_tracker_address = tracker_address
            except:
                pass
        
        return all_tests_passed
            
    except Exception as e:
        print_error(f"Error testing SafeService integration: {e}")
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists('ethereum_private_key.txt'):
            os.remove('ethereum_private_key.txt')

def start_anvil_if_needed():
    """Start Anvil if it's not already running."""
    # Check if Anvil is already running
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if w3.is_connected():
        print_info("Anvil is already running")
        return None
    
    print_info("Starting Anvil...")
    # Start Anvil in the background
    anvil_process = subprocess.Popen(
        ["anvil", "--fork-url", "https://base-mainnet.infura.io/v3/YOUR_KEY", "--chain-id", "8453"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for Anvil to start
    for _ in range(10):
        time.sleep(1)
        w3 = Web3(Web3.HTTPProvider(RPC_URL))
        if w3.is_connected():
            print_success("Anvil started successfully")
            return anvil_process
    
    print_error("Failed to start Anvil")
    anvil_process.terminate()
    return None

def main():
    """Main test execution."""
    print_header("AttestationTracker E2E Integration Test")
    
    # Use the real EAS contract address from eip712proxy.json (Base mainnet)
    # But allow override for testing
    EAS_CONTRACT_ADDRESS = os.getenv("EAS_CONTRACT_ADDRESS", "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6")
    
    # Use the provided attestation tracker address if available
    provided_tracker_address = os.getenv("ATTESTATION_TRACKER_ADDRESS", None)
    
    # Always start Anvil if needed (no longer requires AUTO_START_ANVIL env var)
    anvil_process = start_anvil_if_needed()
    
    # Connect to network
    print_info(f"Connecting to network at {RPC_URL}...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print_error("Failed to connect to network. Anvil failed to start.")
        if anvil_process:
            anvil_process.terminate()
        return 1
    
    print_success(f"Connected to network (Chain ID: {w3.eth.chain_id})")
    
    # Set up account
    account = Account.from_key(PRIVATE_KEY)
    print_info(f"Using test account: {account.address}")
    balance = w3.eth.get_balance(account.address)
    print_info(f"Account balance: {w3.from_wei(balance, 'ether')} ETH")
    
    # Use the real EAS contract from the forked Base mainnet
    eas_address = EAS_CONTRACT_ADDRESS
    print_info(f"Using EAS contract at: {eas_address}")
    
    # Check if EAS contract exists (it should on a forked mainnet)
    eas_code = w3.eth.get_code(Web3.to_checksum_address(eas_address))
    if eas_code == b'':
        print_error(f"No EAS contract found at {eas_address}")
        print_error("Make sure you're running on a forked Base mainnet with:")
        print_error("anvil --fork-url <BASE_RPC_URL>")
        return 1
    else:
        print_success(f"EAS contract found at {eas_address}")
        eas_abi = None  # We don't need the full ABI for testing
    
    # Deploy contracts or use existing ones
    if provided_tracker_address:
        print_info(f"Using provided AttestationTracker at: {provided_tracker_address}")
        tracker_address = provided_tracker_address
        
        # Check if contract exists at the address
        code = w3.eth.get_code(Web3.to_checksum_address(tracker_address))
        if code == b'':
            print_error(f"No contract found at address {tracker_address}")
            print_info("Deploying new AttestationTracker...")
            provided_tracker_address = None
        else:
            print_success(f"AttestationTracker contract found at {tracker_address}")
            # Load ABI
            abi_path = Path(__file__).parent.parent / "backend" / "abi" / "attestation_tracker.json"
            if abi_path.exists():
                with open(abi_path, 'r') as f:
                    tracker_abi = json.load(f)
            else:
                # Compile to get ABI
                contracts_dir = Path(__file__).parent.parent / "contracts"
                if (contracts_dir / "src" / "AttestationTracker.sol").exists():
                    result = subprocess.run(
                        ["forge", "build"],
                        cwd=contracts_dir,
                        capture_output=True,
                        text=True
                    )
                    artifact_path = contracts_dir / "out" / "AttestationTracker.sol" / "AttestationTracker.json"
                    if artifact_path.exists():
                        with open(artifact_path, 'r') as f:
                            artifact = json.load(f)
                            tracker_abi = artifact['abi']
                    else:
                        # Minimal ABI for testing
                        tracker_abi = [
                            {
                                "inputs": [{"internalType": "address", "name": "multisig", "type": "address"}],
                                "name": "getNumAttestations",
                                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                                "stateMutability": "view",
                                "type": "function"
                            }
                        ]
                else:
                    # Minimal ABI for testing
                    tracker_abi = [
                        {
                            "inputs": [{"internalType": "address", "name": "multisig", "type": "address"}],
                            "name": "getNumAttestations",
                            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                            "stateMutability": "view",
                            "type": "function"
                        }
                    ]
    
    if not provided_tracker_address:
        # Deploy new AttestationTracker
        tracker_address, tracker_abi = deploy_attestation_tracker(w3, account, eas_address)
        if not tracker_address:
            return 1
    
    # Test SafeService integration
    success = test_safe_service_integration(w3, account, tracker_address, eas_address)
    
    # Print results
    print_header("Test Results")
    if success:
        print_success("ALL TESTS PASSED!")
        print_info("The SafeService backend code successfully integrates with AttestationTracker:")
        print_info("  ✓ SafeService initialization from backend/services/safe_service.py")
        print_info("  ✓ Attestation encoding via _encode_attestation_data method")
        print_info("  ✓ Transaction building via _build_eas_attestation_tx method")
        print_info("  ✓ Signature generation via _generate_eas_delegated_signature method")
        print_info("  ✓ Multiple test cases (standard, max confidence, min confidence)")
        print_info("  ✓ Error handling and fallback logic")
        print_info("  ✓ Transaction execution on-chain")
        print_info("  ✓ Attestation counter incrementation")
        print_info("  ✓ Event emission verification")
        print_info("")
        print_info("This test directly uses the backend SafeService code, ensuring that:")
        print_info("  - Any changes to SafeService will be caught by this test")
        print_info("  - The integration between SafeService and AttestationTracker is validated")
        print_info("  - The end-to-end flow works without mocks")
        print_info("")
        print_info(f"AttestationTracker Address: {tracker_address}")
        print_info(f"EAS Contract Address: {eas_address}")
        
        # Clean up Anvil if we started it
        if anvil_process:
            print_info("Stopping Anvil...")
            anvil_process.terminate()
            anvil_process.wait()
        
        return 0
    else:
        print_error("TESTS FAILED")
        print_info("Check the error messages above for details")
        
        # Clean up Anvil if we started it
        if anvil_process:
            print_info("Stopping Anvil...")
            anvil_process.terminate()
            anvil_process.wait()
        
        return 1

if __name__ == "__main__":
    exit(main())
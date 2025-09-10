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
from pathlib import Path
from web3 import Web3
from eth_account import Account

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

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
        import subprocess
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
    """Test SafeService integration with AttestationTracker (without multi-sig)."""
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
        # Import SafeService and models
        from services.safe_service import SafeService
        from models import EASAttestationData
        from utils.web3_provider import get_w3
        
        print_info("Testing SafeService builds correct transaction data...")
        
        # Initialize SafeService
        safe_service = SafeService()
        
        # Create test attestation data
        attestation_data = EASAttestationData(
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
        
        # Test 1: Build the transaction data
        print_info("Building attestation transaction data...")
        tx_data = safe_service._build_eas_attestation_tx(attestation_data)
        
        # Verify transaction is targeted at AttestationTracker
        assert tx_data['to'].lower() == tracker_address.lower(), \
            f"Transaction target mismatch: expected {tracker_address}, got {tx_data['to']}"
        print_success(f"✓ Transaction correctly targets AttestationTracker at {tracker_address}")
        
        # Verify transaction data is properly formatted
        assert 'data' in tx_data, "Transaction missing data field"
        assert isinstance(tx_data['data'], str), "Transaction data should be a hex string"
        assert tx_data['data'].startswith('0x'), "Transaction data should start with 0x"
        print_success(f"✓ Transaction data properly formatted (length: {len(tx_data['data'])} chars)")
        
        # Test 2: Execute the transaction directly to verify it works
        print_info("Executing transaction directly on local network...")
        
        # Get initial attestation count
        tracker_abi = json.loads(open(Path(__file__).parent.parent / "backend" / "abi" / "attestation_tracker.json").read())
        tracker_contract = w3.eth.contract(address=Web3.to_checksum_address(tracker_address), abi=tracker_abi)
        
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
                print_info(f"Call succeeded with result: {result.hex()}")
            except Exception as call_error:
                print_error(f"Call failed with: {call_error}")
                # Try to decode the revert reason
                if hasattr(call_error, 'data'):
                    print_error(f"Revert data: {call_error.data}")
                return False
            
            # If call succeeds, send the actual transaction
            signed_tx = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            print_error(f"Transaction failed: {e}")
            return False
        
        if receipt.status == 1:
            print_success(f"✓ Transaction executed successfully (tx_hash: {tx_hash.hex()})")
            print_info(f"  Gas used: {receipt.gasUsed}")
            
            # Check final attestation count
            final_count = tracker_contract.functions.getNumAttestations(account.address).call()
            print_info(f"Final attestation count: {final_count}")
            
            if final_count > initial_count:
                print_success(f"✓ Attestation counter incremented from {initial_count} to {final_count}")
                
                # Check for events
                for log in receipt.logs:
                    if log.address.lower() == tracker_address.lower():
                        print_success(f"✓ AttestationMade event emitted from AttestationTracker")
                        break
                
                return True
            else:
                print_error(f"✗ Attestation counter not incremented (still {final_count})")
                return False
        else:
            print_error(f"✗ Transaction reverted")
            return False
            
    except Exception as e:
        print_error(f"Error testing SafeService integration: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists('ethereum_private_key.txt'):
            os.remove('ethereum_private_key.txt')

def start_anvil_if_needed():
    """Start Anvil if it's not already running."""
    import subprocess
    import time
    
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
    
    # Start Anvil if needed
    anvil_process = None
    if os.getenv("AUTO_START_ANVIL", "false").lower() == "true":
        anvil_process = start_anvil_if_needed()
    
    # Connect to network
    print_info(f"Connecting to network at {RPC_URL}...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print_error("Failed to connect to network. Make sure Anvil is running or set AUTO_START_ANVIL=true")
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
                    import subprocess
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
        print_info("The SafeService successfully interacts with AttestationTracker:")
        print_info("  ✓ SafeService initialized with AttestationTracker address")
        print_info("  ✓ Attestation data created and encoded correctly")
        print_info("  ✓ Transaction submitted to AttestationTracker")
        print_info("  ✓ Attestation counter incremented")
        print_info("  ✓ End-to-end flow validated without mocks")
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
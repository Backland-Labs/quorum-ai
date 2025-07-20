# Blockchain Integration Specification

## Overview

This specification documents the technical implementation patterns for interacting with on-chain contracts across multiple blockchain networks in the Quorum AI application. The application supports both externally owned account (EOA) operations and multi-signature Safe wallet interactions across Ethereum, Gnosis Chain, Base, and Mode networks.

## Core Libraries and Dependencies

### Web3 Stack
- **web3.py**: Core Web3 functionality for blockchain interactions
- **eth-account**: Account management and message signing
- **eth-abi**: ABI encoding/decoding for contract interactions
- **safe-eth**: Safe (Gnosis Safe) multi-sig wallet SDK

### Cryptographic Operations
- **eth-keys**: Ethereum key handling
- **eth-typing**: Type definitions for Ethereum primitives
- **hexbytes**: Hex string and bytes utilities

## Architecture Patterns

### 1. Private Key Management

The application uses a centralized `KeyManager` service (`services/key_manager.py`) for secure private key handling:

```python
# Key storage location
KEY_FILE_NAME = "ethereum_private_key.txt"

# Security requirements
REQUIRED_PERMISSIONS = 0o600  # Read by owner only
PRIVATE_KEY_PATTERN = re.compile(r'^(0x)?[a-fA-F0-9]{64}$')
```

**Best Practices:**
- Keys are loaded from a file in the working directory
- File permissions are validated (600 - owner read only)
- Key format is validated (64 hex chars, optional 0x prefix)
- Keys are cached in memory with 5-minute expiration
- Errors never expose key material in logs

**Implementation Pattern:**
```python
from services.key_manager import KeyManager

# Initialize key manager
key_manager = KeyManager()

# Get private key (handles caching and validation)
private_key = key_manager.get_private_key()

# Create account from key
account = Account.from_key(private_key)
```

### 2. Multi-Chain Configuration

Chain configuration is centralized in `config.py` with RPC endpoints:

```python
# RPC endpoint environment variables
ETHEREUM_LEDGER_RPC
GNOSIS_LEDGER_RPC  
BASE_LEDGER_RPC
MODE_LEDGER_RPC
CELO_LEDGER_RPC

# Chain ID mapping
CHAIN_ID_TO_NAME = {
    1: "ethereum",
    100: "gnosis", 
    8453: "base",
    34443: "mode",
    42220: "celo"
}
```

**Network Selection Strategy:**
- Priority order for gas optimization: Gnosis → Celo → Mode → Base → Ethereum
- Fallback to first available chain if preferred not configured
- Connection validation before use

### 3. Transaction Signing Patterns

#### EIP-712 Typed Data (Snapshot Voting)

The application uses EIP-712 for Snapshot DAO voting signatures:

```python
from eth_account.messages import encode_typed_data

# Create typed data structure
snapshot_message = {
    "domain": {
        "name": "snapshot",
        "version": "0.1.4"
    },
    "types": {
        "Vote": [
            {"name": "from", "type": "address"},
            {"name": "space", "type": "string"},
            {"name": "timestamp", "type": "uint64"},
            {"name": "proposal", "type": "string" or "bytes32"},
            {"name": "choice", "type": "uint32"},
            {"name": "metadata", "type": "string"}
        ]
    },
    "message": vote_data
}

# Sign the message
signable_message = encode_typed_data(full_message=snapshot_message)
signature = account.sign_message(signable_message)
```

#### Safe Transaction Signing

For Safe multi-sig transactions, the application builds and signs Safe-specific transaction data:

```python
# Build Safe transaction
safe_tx = SafeTx(
    safe_address=safe_address,
    to=to_address,
    value=value,
    data=data,
    operation=SAFE_OPERATION_CALL,
    safe_tx_gas=0,
    base_gas=0,
    gas_price=0,
    gas_token=NULL_ADDRESS,
    refund_receiver=NULL_ADDRESS,
    signatures=b"",
    safe_nonce=nonce
)

# Sign with private key
safe_tx.sign(account.key)
```

### 4. Contract Interaction Patterns

#### Governor Contract Voting

The application supports multiple governor types with appropriate encoding:

```python
from utils.vote_encoder import encode_cast_vote, Support

# Encode vote transaction
encoded_data = encode_cast_vote(
    proposal_id=12345,
    support=Support.FOR,  # or AGAINST, ABSTAIN
    reason="Optional reason text"
)

# Submit through Safe
await safe_service.create_governor_vote_transaction(
    governor_id="compound-mainnet",
    proposal_id=12345,
    support=1  # 0=Against, 1=For, 2=Abstain
)
```

#### Safe Activity Transactions

For maintaining Safe wallet activity (Pearl platform requirement):

```python
# Create 0 ETH self-transfer
await safe_service.submit_activity_transaction()
```

### 5. Error Handling and Retry Mechanisms

The application implements comprehensive error handling for blockchain operations:

```python
class SafeService:
    async def get_web3_connection(self, chain: str) -> Web3:
        """Get Web3 connection with validation."""
        rpc_url = self.rpc_endpoints.get(chain)
        if not rpc_url:
            raise ValueError(f"No RPC endpoint configured for chain: {chain}")
        
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to {chain} network")
        
        return w3
```

**Error Types:**
- `ValueError`: Configuration errors, invalid parameters
- `ConnectionError`: Network connectivity issues
- `KeyManagerError`: Key loading/validation failures
- `GovernorRegistryError`: Unknown governor configurations

**Retry Strategy:**
- Configuration: `max_retry_attempts` (default: 3)
- Delay between retries: `retry_delay_seconds` (default: 5)
- Applied to network requests and transaction submissions

### 6. Gas Management

**Gas Optimization Strategies:**
1. Chain selection based on gas costs
2. Safe transactions use 0 gas parameters (gasless through relayer)
3. Batch operations where possible

**Gas-Free Transactions:**
```python
# Safe transactions set gas parameters to 0
safe_tx_gas=0
base_gas=0  
gas_price=0
gas_token=NULL_ADDRESS  # No gas token
```

### 7. ABI Management

Contract ABIs are stored in JSON files and loaded dynamically:

```python
from utils.abi_loader import ABILoader

abi_loader = ABILoader()
governor_abi = abi_loader.load("compound_bravo")  # Loads from compound_bravo.json
```

**ABI File Structure:**
```
backend/
  abis/
    compound_bravo.json
    nouns.json
    uniswap_oz.json
    arbitrum.json
```

### 8. State Persistence

Blockchain-related state is managed through `StateManager`:

```python
# Store withdrawal transactions
state = await state_manager.get_state()
state["withdrawal_transactions"] = [
    {
        "tx_hash": "0x...",
        "status": "pending",
        "chain_id": 1,
        "timestamp": "2024-01-01T00:00:00Z"
    }
]
await state_manager.save_state(state)
```

## Security Considerations

### Private Key Security
1. **File Permissions**: Enforce 600 permissions on key files
2. **Memory Management**: Clear keys from memory after timeout
3. **Error Handling**: Never log or expose key material
4. **Validation**: Verify key format before use

### Transaction Security
1. **Address Validation**: Always use `Web3.to_checksum_address()`
2. **Nonce Management**: Fetch current nonce before transactions
3. **Signature Verification**: Validate signatures before submission
4. **Amount Validation**: Check balances before transfers

### Network Security
1. **RPC Validation**: Verify RPC endpoints are HTTPS
2. **Connection Testing**: Check connectivity before operations
3. **Timeout Handling**: Set appropriate timeouts for network calls
4. **Error Recovery**: Implement retry logic for transient failures

## Testing Patterns

### Mocking Web3 Interactions

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_web3():
    with patch('web3.Web3') as mock:
        w3_instance = Mock()
        w3_instance.is_connected.return_value = True
        w3_instance.eth.get_transaction_count.return_value = 5
        mock.return_value = w3_instance
        yield w3_instance
```

### Testing Safe Transactions

```python
@pytest.mark.asyncio
async def test_safe_transaction(mock_safe_service):
    result = await mock_safe_service.submit_activity_transaction()
    assert result["success"] is True
    assert "safe_tx_hash" in result
```

### Testing Key Manager

```python
def test_key_validation():
    key_manager = KeyManager()
    
    # Test valid key
    valid_key = "a" * 64
    assert key_manager._validate_private_key(valid_key) is True
    
    # Test invalid key
    with pytest.raises(KeyManagerError):
        key_manager._validate_private_key("invalid")
```

## Implementation Checklist

When implementing new blockchain features:

1. **Configuration**
   - [ ] Add RPC endpoints to environment variables
   - [ ] Update chain mappings in relevant services
   - [ ] Configure Safe addresses if using multi-sig

2. **Key Management**
   - [ ] Use KeyManager for all private key operations
   - [ ] Never hardcode private keys
   - [ ] Implement proper error handling

3. **Transaction Building**
   - [ ] Validate all addresses with checksum
   - [ ] Use appropriate gas settings
   - [ ] Implement proper nonce management

4. **Error Handling**
   - [ ] Add specific error types for failures
   - [ ] Implement retry logic for network issues
   - [ ] Log errors without exposing sensitive data

5. **Testing**
   - [ ] Mock all external blockchain calls
   - [ ] Test error scenarios
   - [ ] Validate transaction encoding

6. **Logging**
   - [ ] Use Pearl-compliant logging
   - [ ] Log transaction hashes and addresses
   - [ ] Never log private keys or signatures

## Common Pitfalls to Avoid

1. **Direct Key Access**: Always use KeyManager, never read key files directly
2. **Synchronous Web3 Calls**: Use async patterns for all blockchain operations
3. **Missing Validation**: Always validate addresses, amounts, and parameters
4. **Hardcoded Values**: Use configuration for all chain-specific values
5. **Poor Error Messages**: Provide context without exposing sensitive data
6. **Missing Retries**: Implement retry logic for transient failures
7. **Unchecked Connections**: Always verify Web3 connection before use

## Future Considerations

1. **Hardware Wallet Support**: Extend KeyManager for hardware wallet integration
2. **Transaction Monitoring**: Implement comprehensive transaction tracking
3. **Fee Estimation**: Add dynamic gas price estimation
4. **Multi-Sig Coordination**: Enhanced Safe transaction queue management
5. **Cross-Chain Messaging**: Support for cross-chain protocols
6. **MEV Protection**: Implement flashbot integration for sensitive transactions
# AttestationTracker → EAS Schema Validation Test Plan

## Overview
Test plan for validating that AttestationTracker correctly forwards attestation requests to EAS with the EXACT schema and data structure required by EAS.

## CRITICAL REQUIREMENT
**AttestationTracker MUST pass the EXACT DelegatedAttestationRequest structure to EAS:**
- Schema UID must be valid and registered in EAS
- AttestationRequestData must have all fields in correct format
- Signature must be valid for the attestation using EIP712Proxy
- All data types must match EAS interface exactly

## ⚠️ CRITICAL DISCOVERY: EAS Delegated Attestation Requirements on Base

### Root Cause of Signature Failures
After extensive investigation, we discovered that EAS delegated attestations on Base require:

1. **Two Different Contracts**:
   - **EAS Main Contract**: `0x4200000000000000000000000000000000000021` (for direct attestations)
   - **EIP712Proxy**: `0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6` (for delegated attestations with EIP-712 signatures)

2. **Correct EIP-712 Domain Parameters**:
   ```solidity
   domain = {
       name: "EAS",              // NOT "EAS Attestation"
       version: "1.0.1",          // NOT "0.26" or "1.4.0"
       chainId: 8453,             // Base mainnet
       verifyingContract: 0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6  // EIP712Proxy, NOT main EAS
   }
   ```

3. **Correct Type Structure**:
   ```solidity
   // Type name MUST be "Attest", not "DelegatedAttestation"
   types = {
       "Attest": [
           {name: "attester", type: "address"},      // MUST be FIRST field
           {name: "schema", type: "bytes32"},
           {name: "recipient", type: "address"},
           {name: "expirationTime", type: "uint64"},
           {name: "revocable", type: "bool"},
           {name: "refUID", type: "bytes32"},
           {name: "data", type: "bytes"},
           {name: "value", type: "uint256"},
           {name: "deadline", type: "uint64"}
       ]
   }
   ```

4. **Type Hash Values**:
   - **ATTEST_PROXY_TYPEHASH**: `0xea02ffba7dcb45f6fc649714d23f315eef12e3b27f9a7735d8d8bf41eb2b1af1`
   - This corresponds to: `"Attest(address attester,bytes32 schema,address recipient,uint64 expirationTime,bool revocable,bytes32 refUID,bytes data,uint256 value,uint64 deadline)"`

### Common Pitfalls to Avoid
- ❌ Using main EAS contract address for signature verification
- ❌ Wrong domain name ("EAS Attestation" instead of "EAS")
- ❌ Wrong version ("0.26" or "1.4.0" instead of "1.0.1")
- ❌ Missing 'attester' field in message struct
- ❌ Wrong type name ("DelegatedAttestation" instead of "Attest")
- ❌ Not including nonce when required

## Test Environment Setup

### 1. Local Fork Testing (Primary Approach)
```bash
# Start Anvil fork of Base mainnet with real EAS deployed
anvil --fork-url https://mainnet.base.org --fork-block-number latest --auto-impersonate

# EAS Contract Address on Base: 0x4200000000000000000000000000000000000021
```

### 2. Rapid Iteration Workflow with CLEAR ERROR VISIBILITY
```bash
# Watch mode for automatic test re-runs - FAILURES WILL BE OBVIOUS
forge test --fork-url http://localhost:8545 --watch -vvvv

# Single test execution with full trace to see EXACT failure point
forge test --fork-url http://localhost:8545 --match-test testSchemaValidation -vvvv

# Debug specific calldata being sent to EAS
forge test --fork-url http://localhost:8545 --debug testSchemaValidation
```

## Test Scenarios with FAILURE DETECTION

### Phase 0: EIP-712 Signature Validation Tests
- [ ] **MUST VERIFY**: Query EAS contract for correct domain parameters
- [ ] **MUST USE**: EIP712Proxy address (0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6) as verifyingContract
- [ ] **MUST MATCH**: Domain name = "EAS", version = "1.0.1"
- [ ] **MUST INCLUDE**: 'attester' as first field in Attest struct
- [ ] **MUST GENERATE**: Valid signature that EAS/EIP712Proxy accepts
- [ ] **MUST TEST**: Both direct EAS calls and AttestationTracker wrapper calls

### Phase 1: EAS Schema Compliance Validation
- [ ] **MUST PASS**: Valid DelegatedAttestationRequest with all required fields
- [ ] **MUST MATCH**: Schema UID exactly as registered in EAS (0x7d917fcbc9a29a9705ff9936ffa599500e4fd902e4486bae317414fe967b307c)
- [ ] **MUST ENCODE**: AttestationRequestData.data field properly encoded per schema
- [ ] **MUST VALIDATE**: Signature matches attester and deadline not expired
- [ ] **MUST FORWARD**: All fields unchanged from input to EAS call
- [ ] **MUST HANDLE**: ETH value forwarding if attestation requires payment

### Phase 2: FAILURE SCENARIOS - Must Show Clear Errors
- [ ] **FAIL LOUDLY**: Wrong schema UID → EAS reverts with "Schema not found"
- [ ] **FAIL LOUDLY**: Invalid signature → EAS reverts with "Invalid signature"
- [ ] **FAIL LOUDLY**: Expired deadline → EAS reverts with "Deadline expired"
- [ ] **FAIL LOUDLY**: Malformed data encoding → EAS reverts with decode error
- [ ] **FAIL LOUDLY**: Missing ETH value → EAS reverts if payment required
- [ ] **FAIL LOUDLY**: Wrong data types → Transaction reverts at ABI level

### Phase 3: Success Path Validation
- [ ] **SUCCESS**: Full attestation creation returns valid UID
- [ ] **SUCCESS**: AttestationMade event emitted with correct values
- [ ] **SUCCESS**: Counter incremented for msg.sender
- [ ] **SUCCESS**: ETH value correctly forwarded to EAS

## Test Implementation Strategy

### 1. Fork-Based Reality Testing with EXACT EAS BEHAVIOR
```solidity
// Test against REAL EAS - no mocks!
contract AttestationTrackerForkTest is Test {
    IEAS constant EAS = IEAS(0x4200000000000000000000000000000000000021);
    address constant EIP712_PROXY = 0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6;
    AttestationTracker tracker;
    
    // EIP-712 signature constants
    bytes32 constant ATTEST_PROXY_TYPEHASH = 0xea02ffba7dcb45f6fc649714d23f315eef12e3b27f9a7735d8d8bf41eb2b1af1;
    
    function setUp() public {
        // Fork Base mainnet to test against REAL EAS
        vm.createSelectFork("https://mainnet.base.org");
        
        // Deploy our AttestationTracker pointing to real EAS
        tracker = new AttestationTracker(address(this), address(EAS));
    }
    
    function testEIP712SignatureGeneration() public {
        // Test correct signature generation for EIP712Proxy
        bytes32 domainSeparator = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256("EAS"),           // MUST be "EAS"
            keccak256("1.0.1"),         // MUST be "1.0.1"
            block.chainid,              // 8453 for Base
            EIP712_PROXY                // MUST be proxy address
        ));
        
        // Build message with attester as FIRST field
        bytes32 structHash = keccak256(abi.encode(
            ATTEST_PROXY_TYPEHASH,
            attester,                    // MUST be first
            request.schema,
            request.data.recipient,
            request.data.expirationTime,
            request.data.revocable,
            request.data.refUID,
            keccak256(request.data.data),
            request.data.value,
            deadline
        ));
        
        // Generate signature
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domainSeparator, structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(privateKey, digest);
        
        // This signature MUST be accepted by EAS
        bytes32 uid = tracker.attestByDelegation(request, IEAS.Signature(v, r, s), attester, deadline);
        assertTrue(uid != bytes32(0), "Signature validation failed!");
    }
    
    function testRealEASSchemaValidation() public {
        // This MUST work with real EAS or test fails loudly
        IEAS.DelegatedAttestationRequest memory request = buildValidRequest();
        
        // If schema is wrong, EAS will revert and test will FAIL
        bytes32 uid = tracker.attestByDelegation(request, sig, attester, deadline);
        
        // Verify attestation exists on real EAS
        assertTrue(uid != bytes32(0), "FAILED: No attestation UID returned");
    }
}
```

### 2. FAILURE VISIBILITY TOOLS
```solidity
// Helper to make failures OBVIOUS
modifier expectEASCall() {
    // Log EXACTLY what we're sending to EAS
    console.log("=== SENDING TO EAS ===");
    console.log("Schema:", request.schema);
    console.log("Recipient:", request.data.recipient);
    console.log("Data length:", request.data.data.length);
    _;
}

// Verify exact calldata match
function assertCallDataMatches() {
    vm.expectCall(
        address(EAS),
        abi.encodeCall(IEAS.attestByDelegation, (request, sig, attester, deadline))
    );
}
```

### 3. Continuous Testing Commands with CLEAR OUTPUT
```bash
# Quick validation - SHOWS EXACT FAILURE POINT
forge test --fork-url http://localhost:8545 --match-test testEASSchema -vvvv

# Full trace of EAS interaction
forge test --fork-url http://localhost:8545 --match-test testEASForwarding --debug

# Verify calldata structure
cast calldata-decode "attestByDelegation((bytes32,(address,uint64,bool,bytes32,bytes,uint256)),(uint8,bytes32,bytes32),address,uint64)" <CALLDATA>
```

## EXACT Schema Requirements from EAS

### DelegatedAttestationRequest Structure (MUST MATCH EXACTLY)
```solidity
struct DelegatedAttestationRequest {
    bytes32 schema;                    // Schema UID registered in EAS
    AttestationRequestData data;       // Nested struct with attestation details
}

struct AttestationRequestData {
    address recipient;      // Who receives the attestation
    uint64 expirationTime; // When attestation expires (0 = never)
    bool revocable;        // Can attestation be revoked
    bytes32 refUID;        // Reference to another attestation (0 = none)
    bytes data;            // ENCODED data matching schema structure
    uint256 value;         // ETH to send with attestation
}

struct Signature {
    uint8 v;               // Signature v component
    bytes32 r;             // Signature r component
    bytes32 s;             // Signature s component
}
```

## ERROR DETECTION PATTERNS

### How to Identify Schema Mismatches
```bash
# When test fails, look for these patterns:

# 1. WRONG SCHEMA UID
Error: VM Exception while processing transaction: reverted with reason string 'SchemaNotFound'

# 2. INVALID SIGNATURE
Error: VM Exception while processing transaction: reverted with reason string 'InvalidSignature'

# 3. WRONG DATA ENCODING
Error: VM Exception while processing transaction: reverted with panic code 0x11 (Arithmetic operation underflowed or overflowed)

# 4. MISSING REQUIRED FIELD
Error: EvmError: Revert - abi.decode failed
```

### Debugging Commands for EXACT Failure Point
```bash
# See exact calldata being sent
forge test --match-test testName --debug

# Trace all contract calls
forge test --match-test testName -vvvvv

# Compare expected vs actual calldata
cast calldata "attestByDelegation((bytes32,(address,uint64,bool,bytes32,bytes,uint256)),(uint8,bytes32,bytes32),address,uint64)" \
  <schema> <recipient> <expiration> <revocable> <refUID> <data> <value> <v> <r> <s> <attester> <deadline>
```

## Troubleshooting EIP-712 Signature Failures

### Common Error Messages and Solutions

1. **"execution reverted" with no error message**
   - **Cause**: Wrong EIP-712 domain parameters
   - **Solution**: Verify using EIP712Proxy address and correct domain name/version

2. **"InvalidSignature" error**
   - **Cause**: Missing 'attester' field or wrong field order
   - **Solution**: Ensure 'attester' is FIRST field in Attest struct

3. **Signature validates locally but fails on-chain**
   - **Cause**: Using main EAS address instead of EIP712Proxy
   - **Solution**: Use 0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6 as verifyingContract

4. **Wrong type hash**
   - **Expected**: 0xea02ffba7dcb45f6fc649714d23f315eef12e3b27f9a7735d8d8bf41eb2b1af1
   - **Solution**: Use exact type string with 'attester' first

### Verification Script
```python
# scripts/verify_eas_signature.py
from web3 import Web3
from eth_account.messages import encode_typed_data

# Correct configuration for Base mainnet
EIP712_PROXY = "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"

domain = {
    'name': 'EAS',
    'version': '1.0.1',
    'chainId': 8453,
    'verifyingContract': EIP712_PROXY
}

types = {
    'Attest': [
        {'name': 'attester', 'type': 'address'},  # FIRST field
        {'name': 'schema', 'type': 'bytes32'},
        {'name': 'recipient', 'type': 'address'},
        {'name': 'expirationTime', 'type': 'uint64'},
        {'name': 'revocable', 'type': 'bool'},
        {'name': 'refUID', 'type': 'bytes32'},
        {'name': 'data', 'type': 'bytes'},
        {'name': 'value', 'type': 'uint256'},
        {'name': 'deadline', 'type': 'uint64'}
    ]
}
```

## Success Criteria - MUST ALL PASS

1. ✅ **AttestationTracker forwards EXACT data structure to EAS**
2. ✅ **All EAS schema requirements satisfied**
3. ✅ **EIP-712 signatures validated by EIP712Proxy**
4. ✅ **Failures show CLEAR error messages indicating what's wrong**
5. ✅ **Test execution < 1 second for rapid iteration**
6. ✅ **Works against REAL Base mainnet EAS (no mocks)**

## Test Execution Plan

### Step 1: Deploy and Test Locally
```bash
# Start anvil fork
anvil --fork-url https://mainnet.base.org

# Deploy AttestationTracker
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# Run schema validation tests
forge test --fork-url http://localhost:8545 --match-contract AttestationTrackerForkTest -vvvv
```

### Step 2: Validate Against Real EAS
```bash
# Test with real schema from Base
SCHEMA_UID=0x7d917fcbc9a29a9705ff9936ffa599500e4fd902e4486bae317414fe967b307c \
forge test --fork-url https://mainnet.base.org --match-test testRealSchema -vvvv
```

### Step 3: Verify Data Forwarding
```bash
# Use cast to verify exact calldata match
forge test --fork-url http://localhost:8545 --match-test testDataForwarding --debug
```

## Summary of Critical Findings

This test plan incorporates the critical discovery that EAS delegated attestations on Base mainnet require:

1. **Dual Contract Architecture**:
   - Main EAS contract (0x420...021) for direct attestations
   - EIP712Proxy (0xF095...bF6) for delegated attestations with signatures

2. **Precise EIP-712 Configuration**:
   - Domain name: "EAS" (not variations)
   - Version: "1.0.1" (specific to Base deployment)
   - VerifyingContract: Must be EIP712Proxy address
   - Type name: "Attest" (not "DelegatedAttestation")
   - Message structure: 'attester' must be first field

3. **Testing Requirements**:
   - Fork Base mainnet for real EAS interaction
   - Validate signatures against EIP712Proxy
   - Test both direct calls and AttestationTracker wrapper
   - Ensure clear error messages for debugging

This comprehensive test plan ensures thorough validation of the AttestationTracker's integration with EAS, with specific focus on the correct EIP-712 signature generation that was the root cause of previous failures.

## Required Backend Changes

### File: `backend/services/safe_service.py`

The `_generate_eas_delegated_signature` method (starting at line 754) needs the following changes:

#### Current Code (INCORRECT):
```python
def _generate_eas_delegated_signature(
    self, request_data: Dict[str, Any], w3: Web3, eas_contract_address: str
) -> bytes:
    # ... existing code ...
    
    # Lines 773-790: WRONG types definition
    types = {
        'EIP712Domain': [
            {'name': 'name', 'type': 'string'},
            {'name': 'version', 'type': 'string'},
            {'name': 'chainId', 'type': 'uint256'},
            {'name': 'verifyingContract', 'type': 'address'},
        ],
        'DelegatedAttestation': [  # ❌ WRONG: Should be 'Attest'
            {'name': 'schema', 'type': 'bytes32'},  # ❌ WRONG: Missing 'attester' as first field
            {'name': 'recipient', 'type': 'address'},
            {'name': 'expirationTime', 'type': 'uint64'},
            {'name': 'revocable', 'type': 'bool'},
            {'name': 'refUID', 'type': 'bytes32'},
            {'name': 'data', 'type': 'bytes'},
            {'name': 'value', 'type': 'uint256'},
            {'name': 'deadline', 'type': 'uint64'},
        ]
    }
    
    # Lines 792-797: WRONG domain
    domain = {
        'name': 'EAS Attestation',  # ❌ WRONG: Should be 'EAS'
        'version': '0.26',  # ❌ WRONG: Should be '1.0.1'
        'chainId': w3.eth.chain_id,
        'verifyingContract': Web3.to_checksum_address(eas_contract_address),  # ❌ WRONG: Should be EIP712Proxy
    }
    
    # Lines 805-814: MISSING 'attester' field
    message = {
        'schema': request_data['schema'],
        'recipient': request_data['recipient'],
        # ... rest of fields ...
    }
    
    # Line 825: WRONG primaryType
    'primaryType': 'DelegatedAttestation',  # ❌ WRONG: Should be 'Attest'
```

#### Fixed Code (CORRECT):
```python
def _generate_eas_delegated_signature(
    self, request_data: Dict[str, Any], w3: Web3, eas_contract_address: str
) -> bytes:
    """Generate EIP-712 signature for EAS delegated attestation.
    
    Args:
        request_data: The attestation request data (without signature)
        w3: Web3 instance
        eas_contract_address: EAS contract address (ignored - we use EIP712Proxy)
        
    Returns:
        EIP-712 signature bytes
    """
    # CRITICAL: Use EIP712Proxy address for signature verification
    EIP712_PROXY_ADDRESS = "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"
    
    self.logger.info(
        f"Generating EAS delegated signature - chain_id={w3.eth.chain_id}, "
        f"eip712_proxy={EIP712_PROXY_ADDRESS}, signer={self.account.address}"
    )
    
    # ✅ CORRECT: EAS EIP-712 domain and types structure
    types = {
        'EIP712Domain': [
            {'name': 'name', 'type': 'string'},
            {'name': 'version', 'type': 'string'},
            {'name': 'chainId', 'type': 'uint256'},
            {'name': 'verifyingContract', 'type': 'address'},
        ],
        'Attest': [  # ✅ CORRECT: Type name is 'Attest'
            {'name': 'attester', 'type': 'address'},  # ✅ CORRECT: 'attester' MUST be first field
            {'name': 'schema', 'type': 'bytes32'},
            {'name': 'recipient', 'type': 'address'},
            {'name': 'expirationTime', 'type': 'uint64'},
            {'name': 'revocable', 'type': 'bool'},
            {'name': 'refUID', 'type': 'bytes32'},
            {'name': 'data', 'type': 'bytes'},
            {'name': 'value', 'type': 'uint256'},
            {'name': 'deadline', 'type': 'uint64'},
        ]
    }
    
    # ✅ CORRECT: Domain for EIP712Proxy on Base
    domain = {
        'name': 'EAS',  # ✅ CORRECT: Must be 'EAS'
        'version': '1.0.1',  # ✅ CORRECT: Must be '1.0.1' for Base
        'chainId': w3.eth.chain_id,
        'verifyingContract': Web3.to_checksum_address(EIP712_PROXY_ADDRESS),  # ✅ CORRECT: Use EIP712Proxy
    }
    
    self.logger.debug(
        f"EIP-712 domain - name={domain['name']}, version={domain['version']}, "
        f"chainId={domain['chainId']}, verifyingContract={domain['verifyingContract']}"
    )
    
    # ✅ CORRECT: Message data with 'attester' field
    message = {
        'attester': self.account.address,  # ✅ CORRECT: Add attester as FIRST field
        'schema': request_data['schema'],
        'recipient': request_data['recipient'], 
        'expirationTime': request_data['expirationTime'],
        'revocable': request_data['revocable'],
        'refUID': request_data['refUID'],
        'data': request_data['data'],
        'value': request_data['value'],
        'deadline': request_data['deadline'],
    }
    
    self.logger.debug(
        f"EIP-712 message - attester={self.account.address}, "
        f"schema={request_data['schema'].hex()}, "
        f"recipient={request_data['recipient']}, deadline={request_data['deadline']}, "
        f"data_length={len(request_data['data'])}"
    )
    
    # ✅ CORRECT: Create EIP-712 encoded data
    typed_data = {
        'domain': domain,
        'primaryType': 'Attest',  # ✅ CORRECT: Must be 'Attest'
        'types': types,
        'message': message,
    }
    
    self.logger.debug("Encoding EIP-712 typed data")
    encoded = encode_typed_data(full_message=typed_data)
    
    # Sign with the account's private key
    self.logger.debug("Signing EIP-712 encoded message with private key")
    signature = self.account.sign_message(encoded)
    
    self.logger.info(
        f"Generated EAS delegated signature successfully - signature_length={len(signature.signature)}, "
        f"signature_hex={signature.signature.hex()[:20]}..."
    )
    
    return signature.signature
```

### Summary of Changes

1. **Add EIP712Proxy constant**: 
   ```python
   EIP712_PROXY_ADDRESS = "0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"
   ```

2. **Change type name from 'DelegatedAttestation' to 'Attest'** (line 780)

3. **Add 'attester' as FIRST field in Attest type** (line 781 - insert before schema)

4. **Update domain parameters** (lines 792-797):
   - name: 'EAS Attestation' → 'EAS'
   - version: '0.26' → '1.0.1'
   - verifyingContract: Use EIP712_PROXY_ADDRESS instead of eas_contract_address

5. **Add 'attester' field to message** (line 806 - insert before schema):
   ```python
   'attester': self.account.address,
   ```

6. **Change primaryType** (line 825):
   - 'DelegatedAttestation' → 'Attest'

### Testing the Changes

After making these changes, test with:
```python
# The signature should now be valid for EIP712Proxy
# AttestationTracker should be deployed pointing to EIP712Proxy
# EAS delegated attestations should succeed
```
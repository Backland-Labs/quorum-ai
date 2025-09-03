# QuorumStaking Integration Tests

This document describes the comprehensive integration tests for verifying the interaction between `QuorumStakingTokenActivityChecker` and `AttestationTracker` through the `IQuorumTracker` interface.

## Files

- `QuorumStakingIntegration.t.sol` - Comprehensive integration test suite
- `TestQuorumStakingIntegration.s.sol` - Local testnet deployment and testing script

## Test Coverage

### Core Integration Tests

1. **Setup and Constructor Tests**
   - Validates proper contract deployment with all dependencies
   - Tests error conditions (zero addresses, invalid parameters)

2. **Interface Integration**
   - Verifies `QuorumStakingTokenActivityChecker` can call `AttestationTracker.getVotingStats()`
   - Tests `getMultisigNonces()` returns correct 4-element array format
   - Validates real-time updates when attestations are made

3. **Liveness Ratio Calculations**
   - Tests `isRatioPass()` with various scenarios:
     - No multisig nonce changes (should fail)
     - Zero timestamp (should fail)
     - Successful voting scenarios
     - Failed voting scenarios (ratio too low)
     - Alternative attestation scenarios (no voting but opportunities available)
   - Tests different liveness ratio configurations

4. **Multi-Multisig Support**
   - Verifies independent tracking of multiple multisigs
   - Tests that attestations from one multisig don't affect another

5. **End-to-End Workflows**
   - Complete attestation progression testing
   - Realistic ratio calculation scenarios with timeline simulation
   - Integration of multisig nonce changes with attestation tracking

6. **Edge Cases and Error Handling**
   - Maximum value testing (overflow protection)
   - Gas optimization verification
   - Fuzz testing for various input combinations

## Running the Tests

### Unit Tests

```bash
# Run all integration tests
forge test --match-path test/QuorumStakingIntegration.t.sol -v

# Run specific test categories
forge test --match-path test/QuorumStakingIntegration.t.sol --match-test test_Integration -v
forge test --match-path test/QuorumStakingIntegration.t.sol --match-test test_IsRatioPass -v
forge test --match-path test/QuorumStakingIntegration.t.sol --match-test test_EndToEnd -v

# Run fuzz tests
forge test --match-path test/QuorumStakingIntegration.t.sol --match-test testFuzz -v
```

### Local Testnet Integration

```bash
# 1. Start local anvil testnet
anvil

# 2. Set environment variables
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80  # anvil default
export LIVENESS_RATIO=1000000000000000  # 1e15 (optional, has default)

# 3. Run the integration test script
forge script script/TestQuorumStakingIntegration.s.sol --tc TestQuorumStakingIntegrationScript --fork-url http://localhost:8545 --broadcast

# 4. Observe comprehensive output showing:
#    - Contract deployments
#    - Initial state verification
#    - Attestation creation
#    - Ratio calculations
#    - Edge case testing
```

## Test Scenarios Covered

### Attestation Tracking
- ✅ Zero attestations initial state
- ✅ Single attestation tracking
- ✅ Multiple attestations tracking
- ✅ Independent multisig tracking
- ✅ Real-time state updates

### Ratio Calculations
- ✅ Successful voting scenarios (casted votes increased)
- ✅ Failed voting scenarios (ratio too low)
- ✅ Alternative attestation scenarios (opportunities without votes)
- ✅ Different liveness ratio configurations
- ✅ Edge cases (zero timestamp, no nonce change)

### Interface Compatibility
- ✅ `IQuorumTracker.getVotingStats()` integration
- ✅ `IMultisig.nonce()` integration
- ✅ 4-element array format compliance
- ✅ Error handling for interface calls

### Performance
- ✅ Gas efficiency testing
- ✅ Large value handling (no overflow)
- ✅ Fuzz testing with random inputs

## Expected Results

All tests should pass, demonstrating:

1. **Successful Integration**: `QuorumStakingTokenActivityChecker` can successfully query `AttestationTracker` through the `IQuorumTracker` interface
2. **Correct Data Flow**: Attestations made through `AttestationTracker` are immediately visible to `QuorumStakingTokenActivityChecker`
3. **Accurate Calculations**: Liveness ratio calculations work correctly with various scenarios and edge cases
4. **Independent Tracking**: Multiple multisigs are tracked independently without interference
5. **Gas Efficiency**: All operations complete within reasonable gas limits

## Integration with Existing Tests

These integration tests complement the existing test suites:

- **AttestationTracker.t.sol**: Tests the core attestation tracking functionality
- **QuorumStakingIntegration.t.sol**: Tests the integration between both contracts
- **TestQuorumStakingIntegration.s.sol**: Provides a script for real deployment testing

## Troubleshooting

### Common Issues

1. **Environment Variables**: Ensure `PRIVATE_KEY` is set when running the test script
2. **Network Configuration**: Verify anvil is running on `http://localhost:8545`
3. **Gas Limits**: If tests fail due to gas, check that anvil has sufficient gas limits
4. **Compilation**: Ensure all dependencies are properly installed via `forge install`

### Debug Information

The test script provides comprehensive logging:
- Contract deployment addresses
- Initial and updated state information
- Ratio calculation details
- Gas usage statistics
- Final verification results

This allows for detailed debugging of any integration issues.
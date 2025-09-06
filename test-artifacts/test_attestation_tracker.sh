#!/bin/bash

# Test script for AttestationTracker contract
# Run this script to compile and test the new AttestationTracker contract

echo "=== AttestationTracker Test Suite ==="
echo "Testing the minimal attestation tracking contract..."

cd /Users/max/code/quorum-ai/contracts

echo "1. Building contracts..."
forge build

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
else
    echo "❌ Build failed!"
    exit 1
fi

echo "2. Running AttestationTracker tests..."
forge test --match-contract AttestationTrackerTest -vvv

if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed!"
    exit 1
fi

echo "3. Running gas report..."
forge test --match-contract AttestationTrackerTest --gas-report

echo "4. Testing fuzz tests with more runs..."
forge test --match-test testFuzz -vv --fuzz-runs 1000

echo "=== Test Complete ==="
echo "AttestationTracker contract successfully tested!"

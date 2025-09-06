#!/bin/bash

# Test private key from Anvil (account 0)
export PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Test owner address (account 1 from Anvil)
export QUORUM_TRACKER_OWNER="0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

# Deploy the contract
forge script script/Deploy.s.sol:DeployScript --rpc-url http://localhost:8545 --broadcast -vvv

# Extract the deployed address from broadcast logs
DEPLOYED_ADDRESS=$(cat broadcast/Deploy.s.sol/8453/run-latest.json 2>/dev/null | jq -r '.transactions[0].contractAddress // empty')

if [ -z "$DEPLOYED_ADDRESS" ]; then
    # Fallback: try to extract from different chain ID (31337 for local anvil)
    DEPLOYED_ADDRESS=$(cat broadcast/Deploy.s.sol/31337/run-latest.json 2>/dev/null | jq -r '.transactions[0].contractAddress // empty')
fi

if [ -n "$DEPLOYED_ADDRESS" ]; then
    echo "Contract deployed to: $DEPLOYED_ADDRESS"
    echo "QUORUM_TRACKER_ADDRESS=$DEPLOYED_ADDRESS" > ../.env
    echo "QUORUM_TRACKER_OWNER=$QUORUM_TRACKER_OWNER" >> ../.env
else
    echo "Failed to extract deployed address"
fi

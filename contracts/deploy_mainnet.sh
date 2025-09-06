#!/bin/bash

# AttestationTracker Mainnet Deployment Script
# This script handles the deployment of the AttestationTracker contract to Ethereum Mainnet

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AttestationTracker Mainnet Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with the following variables:"
    echo "  PRIVATE_KEY=<your_private_key>"
    echo "  ATTESTATION_TRACKER_OWNER=<owner_address>"
    echo "  MAINNET_RPC_URL=<your_mainnet_rpc_url>"
    echo "  ETHERSCAN_API_KEY=<your_etherscan_api_key>"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$PRIVATE_KEY" ]; then
    echo -e "${RED}Error: PRIVATE_KEY not set in .env${NC}"
    exit 1
fi

if [ -z "$ATTESTATION_TRACKER_OWNER" ]; then
    echo -e "${RED}Error: ATTESTATION_TRACKER_OWNER not set in .env${NC}"
    exit 1
fi

if [ -z "$MAINNET_RPC_URL" ]; then
    echo -e "${RED}Error: MAINNET_RPC_URL not set in .env${NC}"
    exit 1
fi

# Display deployment configuration
echo -e "${YELLOW}Deployment Configuration:${NC}"
echo "  Network: Ethereum Mainnet"
echo "  Owner: $ATTESTATION_TRACKER_OWNER"
echo "  EAS: 0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587 (Mainnet)"
echo "  RPC URL: ${MAINNET_RPC_URL:0:30}..."

# Safety confirmation
echo -e "\n${YELLOW}⚠️  WARNING: You are about to deploy to MAINNET!${NC}"
echo -e "${YELLOW}This will consume real ETH. Please confirm the details above.${NC}"
read -p "Type 'DEPLOY TO MAINNET' to continue: " confirmation

if [ "$confirmation" != "DEPLOY TO MAINNET" ]; then
    echo -e "${RED}Deployment cancelled.${NC}"
    exit 1
fi

# Optional dry run
echo -e "\n${GREEN}Would you like to perform a dry run first? (y/n)${NC}"
read -p "> " dry_run

if [ "$dry_run" == "y" ] || [ "$dry_run" == "Y" ]; then
    echo -e "\n${GREEN}Running dry run...${NC}"
    forge script script/DeployMainnet.s.sol:DeployMainnet --sig "dryRun()" \
        --rpc-url $MAINNET_RPC_URL \
        -vvv
    
    echo -e "\n${GREEN}Dry run complete. Proceed with actual deployment? (y/n)${NC}"
    read -p "> " proceed
    
    if [ "$proceed" != "y" ] && [ "$proceed" != "Y" ]; then
        echo -e "${RED}Deployment cancelled.${NC}"
        exit 1
    fi
fi

# Build the contracts
echo -e "\n${GREEN}Building contracts...${NC}"
forge build

# Run tests
echo -e "\n${GREEN}Running tests...${NC}"
forge test --match-contract AttestationTrackerTest

# Deploy to mainnet
echo -e "\n${GREEN}Deploying to Mainnet...${NC}"

# Set EAS address for mainnet
export EAS_CONTRACT_ADDRESS=0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587

# Deploy with verification
if [ -n "$ETHERSCAN_API_KEY" ]; then
    echo -e "${GREEN}Deploying with Etherscan verification...${NC}"
    forge script script/DeployMainnet.s.sol:DeployMainnet \
        --rpc-url $MAINNET_RPC_URL \
        --broadcast \
        --verify \
        --etherscan-api-key $ETHERSCAN_API_KEY \
        -vvv
else
    echo -e "${YELLOW}Deploying without verification (no ETHERSCAN_API_KEY)...${NC}"
    forge script script/DeployMainnet.s.sol:DeployMainnet \
        --rpc-url $MAINNET_RPC_URL \
        --broadcast \
        -vvv
fi

# Check if deployment was successful
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Deployment Successful!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Save deployment info
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    DEPLOYMENT_FILE="deployments/mainnet_${TIMESTAMP}.txt"
    
    mkdir -p deployments
    echo "Mainnet Deployment - $TIMESTAMP" > $DEPLOYMENT_FILE
    echo "Owner: $ATTESTATION_TRACKER_OWNER" >> $DEPLOYMENT_FILE
    echo "EAS: 0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587" >> $DEPLOYMENT_FILE
    echo "" >> $DEPLOYMENT_FILE
    echo "Check broadcast/DeployMainnet.s.sol/1/run-latest.json for contract address" >> $DEPLOYMENT_FILE
    
    echo -e "${GREEN}Deployment info saved to: $DEPLOYMENT_FILE${NC}"
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Find the contract address in broadcast/DeployMainnet.s.sol/1/run-latest.json"
    echo "2. Verify the contract on Etherscan (if not auto-verified)"
    echo "3. Test the contract functions"
    echo "4. Update any dependent systems with the new contract address"
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}❌ Deployment Failed!${NC}"
    echo -e "${RED}========================================${NC}"
    echo "Please check the error messages above."
    exit 1
fi
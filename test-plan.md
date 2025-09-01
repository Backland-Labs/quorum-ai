# Quorum AI Testing Plan

## Overview

This document outlines the comprehensive testing strategy for validating Quorum AI's autonomous voting agent functionality in a controlled local environment before production deployment on the Olas Pearl platform. ALWAYS DELEGATE TASKS TO SUBAGENTS.

## Testing Architecture

### Infrastructure Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                     │
├───────────────────┬────────────┬─────────────────────────────┤
│   Anvil Local     │  Backend   │  Frontend                   │
│   Blockchain      │  Container │  Container                  │
│   (Port 8545)     │  (8716)    │  (3000)                     │
└───────────────────┴────────────┴─────────────────────────────┘
                            │
                            ├── Real Snapshot API (GraphQL)
                            ├── Real OpenRouter (Gemini 2.0)
                            └── Real Base Network (for EAS reads)
```

**Local Services:**
- Anvil (Foundry): Local Ethereum blockchain forking Base mainnet
- Backend Container: Python FastAPI application with UV package manager
- Frontend Container: SvelteKit monitoring dashboard (optional)

**External Services:**
- Snapshot Testnet API: Test governance proposals from testnet
- OpenRouter API: Real AI model access (Gemini 2.0 Flash)

**Local Services:**
- Anvil: Local blockchain with deployed EAS contracts for attestations

## Test Environment Setup

### Prerequisites

1. **Required API Keys:**
   - OpenRouter API key from https://openrouter.ai/

2. **Environment Variables:**
   ```bash
   # Required
   OPENROUTER_API_KEY= # Accessed in .env
   
   # Snapshot Testnet Configuration
   SNAPSHOT_GRAPHQL_URL=https://testnet.hub.snapshot.org/graphql
   
   # Local Testnet Configuration (Anvil)
   RPC_URL=http://localhost:8545
   CHAIN_ID=8453  # Base chain ID for EAS compatibility
   
   # Agent's own Safe for attestations (on local testnet)
   BASE_SAFE_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
   BASE_RPC_URL=http://localhost:8545
   
   # Test wallet (from Anvil mnemonic)
   PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
   
   # EAS Configuration (deployed on local Anvil)
   EAS_CONTRACT_ADDRESS=0x4200000000000000000000000000000000000021
   EAS_SCHEMA_UID=0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
   ATTESTATION_TRACKER_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3  # First contract deployed by Anvil
   
   # Testing configuration (using real testnet space)
   MONITORED_DAOS=s-tn:defactor-engage.eth
   DRY_RUN_DEFAULT=false
   AGENT_CONFIDENCE_THRESHOLD=0.8
   MAX_PROPOSALS_PER_RUN=3
   VOTING_STRATEGY=conservative
   ```

### File Structure

```
test-data/
├── state/
│   ├── agent_state.json
│   ├── user_preferences.json
│   └── backups/
├── logs/
│   └── pearl/
│       └── log.txt
├── deployment.json
└── metrics/
    ├── 24h_test_YYYYMMDD_HHMMSS.log
    └── 24h_metrics_YYYYMMDD_HHMMSS.json
```
## Build the Backend Docker Container

Deploy the backend container and make sure that the networking is set up so that you can access the endpoint and the container can access the local testnet. Before starting the below, `exec` into the Docker container and confirm you can connect to the local testnet before continuing.

## Execute Test Steps
1. Query the agent run endpoint, and then monitor the logs to see if it successfully queries snapshot. Write evidence of success or failure to a file.
2. Monitor the logs to confirm that it successfully queries the OpenRouter API and makes a voting decision.
3. Make sure that the voting decision is correctly recorded per the application.
4. Confirm the voting decision is sent to the attestation tracker contract deployed on the local testnet.
5. Confirm that an attestation is made on the local testnet via the EAS contract that is local.

Provide supporting evidence for each of these steps.
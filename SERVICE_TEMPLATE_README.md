# Olas Service Template Configuration

This document explains the placeholders in `service-template.json` that need to be updated for deployment.

## Placeholders to Update

### 1. `hash` Field
- **Current Value**: `QmXwJ3VgFjQ2MNbkNYoCYqN4jCPdmngz3oYsRCcUi8GTAR`
- **Description**: IPFS hash of the agent package
- **How to Update**: After building and uploading your agent package to IPFS, replace this with the actual CIDv0 hash

### 2. `image` Field
- **Current Value**: `valory/oar-quorum-ai:QmXwJ3VgFjQ2MNbkNYoCYqN4jCPdmngz3oYsRCcUi8GTAR`
- **Description**: Docker image name with tag
- **Format**: `<registry>/<namespace>/oar-<agent-name>:<hash>`
- **How to Update**: 
  - Replace `valory` with your Docker registry namespace
  - Keep `oar-quorum-ai` as the image name
  - Update the tag to match the actual hash from step 1

## Environment Variables

The template includes all required environment variables:

### Computed Variables (Provided by Olas Pearl)
- `ETHEREUM_LEDGER_RPC`: Ethereum network RPC endpoint
- `GNOSIS_LEDGER_RPC`: Gnosis network RPC endpoint
- `AGENT_ADDRESS`: Agent's blockchain address
- `SAFE_ADDRESS`: Safe wallet address for the agent

### User Variables (Must be provided during deployment)
- `OPENROUTER_API_KEY`: API key for OpenRouter AI service

### Fixed Variables (Pre-configured)
- `STORE_PATH`: `/app/data` - Persistent data storage path
- `HEALTH_CHECK_PORT`: `8716` - Health check endpoint port
- `PORT`: `8716` - Main application port
- `DEBUG`: `false` - Debug mode flag

## Chain Configuration

The template is configured for Gnosis chain (ID: 100) with:
- **Staking Program**: `pearl_alpha`
- **Agent Fund Requirement**: 0.005 xDAI (5000000000000000 wei)
- **Total Fund Requirement**: 0.01 xDAI (10000000000000000 wei)

## Deployment Steps

1. Build your agent package and upload to IPFS
2. Update the `hash` field with the IPFS CIDv0
3. Build and push your Docker image with the same hash as tag
4. Update the `image` field with your Docker registry details
5. Deploy using the Olas Pearl platform

## Validation

Run the test suite to validate your configuration:
```bash
backend/.venv/bin/pytest test_service_template.py -v
```

All tests should pass before attempting deployment.
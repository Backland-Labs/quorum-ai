# Quorum AI

**IMPORTANT: This application currently only supports Base network due to the Ethereum Attestation Service (EAS) integration being locked to Base. All voting attestations will be recorded on Base, regardless of which network the DAO operates on.**

A sophisticated autonomous voting agent for DAO governance on the Olas Pearl platform. This full-stack application enables automated participation in decentralized governance through AI-powered proposal analysis and voting decisions, featuring integration with Snapshot and Google Gemini 2.5 Flash.

## Quick Start - Local Testing

Get Quorum AI running locally in minutes using our automated setup script.

### Prerequisites
- Docker installed
- Node.js and npm
- Foundry (`anvil` and `cast` commands)
- `curl` command-line tool
- At least 4GB of available RAM
- [OpenRouter](https://openrouter.ai/) API KEY
- Gnosis Safe Address (SAFE_CONTRACT_ADDRESSES)

### Automated Setup (Recommended)

The `local_run_service.sh` script automates the entire quickstart process:

```bash
# export env vars
export OPENROUTER_API_KEY=sk-....
export SAFE_CONTRACT_ADDRESSES='{"base": "0x..."}'

# Clone the repository (or just download the script)
git clone https://github.com/Backland-Labs/quorum-ai.git
cd quorum-ai

# Make the script executable
chmod +x local_run_service.sh

# Start all services
./local_run_service.sh start
```

**That's it!** The script will:
1. Check all prerequisites are installed
2. Start a local fork of Base mainnet using Anvil
3. Verify all smart contracts are deployed and accessible
4. Configure environment variables with secure defaults
5. Pull/build the Docker image
6. Fund the Safe multisig for transactions
7. Start the Quorum AI service
8. Verify everything is working

### Script Usage

The `local_run_service.sh` script supports multiple commands:

```bash
# Start all services (default command)
./local_run_service.sh start
./local_run_service.sh        # same as 'start'

# Stop all services (Anvil + Docker container)
./local_run_service.sh stop

# Show live application logs
./local_run_service.sh logs

# Show detailed status and verify attestations
./local_run_service.sh status
```

### Access Points

Once the script completes successfully:

- **Web UI**: http://localhost:8716
- **Health Check**: http://localhost:8716/healthcheck  
- **API Documentation**: http://localhost:8716/docs
- **RPC Endpoint**: http://localhost:8545 (Anvil fork)

### Environment Configuration

The script automatically configures these defaults:

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `MONITORED_DAOS` | `quorum-ai.eth` | DAO to monitor for testing |
| `EAS_CONTRACT_ADDRESS` | `0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6` | Base mainnet EAS contract |
| `ATTESTATION_TRACKER_ADDRESS` | `0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC` | Our deployed tracker |
| `CHAIN_ID` | `8453` | Base mainnet (preserved in fork) |
| `RPC_URL` | `http://host.docker.internal:8545` | Points to local Anvil |
| `PRIVATE_KEY` | `ac0974bec...` | Default Anvil test account |

To override any defaults, set environment variables before running:

```bash
# Set your own API key
export MONITORED_DAOS="uniswap.eth" # must be register space on Snapshot

# Start with your config
./local_run_service.sh start
```


## QA

[QA Checklist](QA_CHECKLIST.md)

## Required Contracts

Before running Quorum AI, you need access to the following smart contracts:

### Required Deployments


2. **AttestationTracker** - EAS wrapper contract for vote attestations
   - Location: `contracts/src/AttestationTracker.sol`
   - Deploy using: `forge script script/Deploy.s.sol`
   - Required for on-chain vote tracking


### Key Considerations

- **Network**: Base mainnet/testnet recommended for lower gas costs
- **Dependencies**: AttestationTracker requires EAS contract address
- **Order**: Deploy EAS Schema → AttestationTracker → QuorumStaking
- **Environment**: Update `.env` with all deployed contract addresses
- **Security**: Use dedicated deployment wallet with sufficient ETH

## Environment Variables

Quorum AI requires several environment variables for proper operation. Create a `.env` file in the root directory with the following configuration:

### Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | OpenRouter API key for Google Gemini 2.0 Flash |
| `EAS_CONTRACT_ADDRESS` | `0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6` | EAS EIP712Proxy contract address on Base mainnet |
| `EAS_SCHEMA_UID` | - | 32-byte hex string from EAS schema deployment |
| `ATTESTATION_TRACKER_ADDRESS` | - | Deployed AttestationTracker address (optional if using wrapper) |
| `BASE_RPC_URL` or `BASE_LEDGER_RPC` | `https://mainnet.base.org` | Base network RPC endpoint |
| `RPC_URL` | `https://mainnet.base.org` | Primary RPC endpoint |
| `CHAIN_ID` | `8453` | Base mainnet chain ID |
| `PRIVATE_KEY` or `EOA_PRIVATE_KEY` | - | Should be provided in `ethereum_private_key.txt`|
| `SAFE_CONTRACT_ADDRESSES` | - | JSON string of Safe addresses per chain |

**Note**: For production, use `ethereum_private_key.txt` file (permissions 600) instead of `PRIVATE_KEY` or `EOA_PRIVATE_KEY` environment variables.

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host address |
| `PORT` | `8716` | Server port |
| `HEALTH_CHECK_PORT` | `8716` | Health check endpoint port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE_PATH` | `log.txt` | Path to log file |
| `MONITORED_DAOS` | `compound.eth,nouns.eth,arbitrum.eth` | Comma-separated list of DAOs to monitor |
| `AGENT_CONFIDENCE_THRESHOLD` | `0.7` | Agent-specific confidence threshold |
| `MAX_PROPOSALS_PER_RUN` | `3` | Maximum proposals to analyze per run |
| `PROPOSAL_FETCH_TIMEOUT` | `30` | Seconds to wait for proposal fetching |
| `VOTE_EXECUTION_TIMEOUT` | `60` | Seconds to wait for vote execution |
| `MAX_RETRY_ATTEMPTS` | `3` | Maximum retry attempts for failed operations |
| `RETRY_DELAY_SECONDS` | `5` | Delay between retry attempts in seconds |
| `HEALTH_CHECK_PATH` | `/healthcheck` | Health check endpoint path |
| `FAST_TRANSITION_THRESHOLD` | `5` | Seconds threshold for fast state transitions |
| `SNAPSHOT_GRAPHQL_ENDPOINT` | `https://hub.snapshot.org/graphql` | Snapshot GraphQL API endpoint |
| `SNAPSHOT_HUB_URL` | `https://seq.snapshot.org/` | Snapshot Hub API for vote submissions |
| `SNAPSHOT_API_KEY` | - | Snapshot API key for enhanced rate limits |
| `VOTING_STRATEGY` | `balanced` | Voting strategy: balanced, conservative, or aggressive |
| `DRY_RUN_DEFAULT` | `false` | Default dry run mode for testing |
| `WITHDRAWAL_MODE` | `false` | Enable withdrawal mode for agent shutdown |
| `AGENT_ADDRESS` | - | The agent's EOA address (auto-detected from private key) |
| `STORE_PATH` | - | Path for persistent data storage |
| `ACTIVITY_CHECK_INTERVAL` | `3600` | Seconds between activity checks (1 hour) |
| `PROPOSAL_CHECK_INTERVAL` | `300` | Seconds between proposal checks (5 minutes) |
| `MIN_TIME_BEFORE_DEADLINE` | `1800` | Minimum seconds before proposal deadline (30 minutes) |
| `DECISION_OUTPUT_DIR` | `decisions` | Directory for voting decision files |
| `DECISION_FILE_FORMAT` | `json` | Format for decision files |
| `MAX_DECISION_FILES` | `100` | Maximum number of decision files to retain |
| `ATTESTATION_CHAIN` | `base` | Chain to use for attestation transactions |
| `STAKING_TOKEN_CONTRACT_ADDRESS` | - | Olas staking token contract |
| `ACTIVITY_CHECKER_CONTRACT_ADDRESS` | - | Olas activity checker contract |
| `SERVICE_REGISTRY_TOKEN_UTILITY_CONTRACT` | - | Olas service registry contract |
| `ETHEREUM_LEDGER_RPC` | - | Ethereum mainnet RPC endpoint |
| `GNOSIS_LEDGER_RPC` | - | Gnosis chain RPC endpoint |
| `MODE_LEDGER_RPC` | - | Mode chain RPC endpoint |
| `CELO_LEDGER_RPC` | - | Celo chain RPC endpoint |

# Quorum AI

**⚠️ IMPORTANT: This application currently only supports Base network due to the Ethereum Attestation Service (EAS) integration being locked to Base. All voting attestations will be recorded on Base, regardless of which network the DAO operates on.**

A sophisticated autonomous voting agent for DAO governance on the Olas Pearl platform. This full-stack application enables automated participation in decentralized governance through AI-powered proposal analysis and voting decisions, featuring integration with Snapshot and Google Gemini 2.0 Flash.

## 🚀 Quick Start - Local Testing

Get Quorum AI running locally in minutes with these steps:

### Prerequisites
- Docker and Docker Compose installed
- Node.js and npm (for local testnet)
- Foundry (`forge`) for smart contract deployment
- At least 4GB of available RAM

### Step 1: Get the Application

#### Option A: Pull Docker Image (Recommended)
```bash
docker pull backlandlabs/quorum:latest
```

#### Option B: Clone Repository
```bash
git clone https://github.com/yourusername/quorum-ai.git
cd quorum-ai
```

### Step 2: Set Up Local Fork of Base Mainnet

Start a local fork of Base mainnet using Anvil (from Foundry):
```bash
# Fork Base mainnet locally - this will include all deployed contracts
anvil --fork-url https://mainnet.base.org --host 0.0.0.0 --port 8545

# Or if you have a Base RPC endpoint (e.g., from QuickNode):
# anvil --fork-url YOUR_BASE_RPC_URL --host 0.0.0.0 --port 8545
```

Keep this terminal open. Anvil provides test accounts with ETH pre-funded. The forked chain includes all Base mainnet contracts, including the already-deployed AttestationTracker.

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Core Configuration
MONITORED_DAOS="quorum-ai.eth"  # Default DAO for testing
OPENROUTER_API_KEY="your_openrouter_api_key_here"  # Get from OpenRouter

# Contract Addresses (already deployed on Base mainnet)
EAS_CONTRACT_ADDRESS="0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"
ATTESTATION_TRACKER_ADDRESS="0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
EAS_SCHEMA_UID="0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4"

# Network Configuration (Local fork of Base mainnet)
RPC_URL="http://host.docker.internal:8545"  # For Docker to access host's Anvil fork
BASE_RPC_URL="http://host.docker.internal:8545"
CHAIN_ID="8453"  # Base mainnet chain ID (preserved in fork)

# Test Account (Anvil account - DO NOT use in production!)
PRIVATE_KEY="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
AGENT_ADDRESS="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# Safe Configuration
SAFE_CONTRACT_ADDRESSES='{"base":"0x"}'

# Server Configuration
HOST="0.0.0.0"
PORT="8716"
DEBUG="true"
LOG_LEVEL="DEBUG"

# Snapshot Configuration
SNAPSHOT_GRAPHQL_ENDPOINT=https://testnet.hub.snapshot.org/graphql
SNAPSHOT_HUB_URL=https://testnet.seq.snapshot.org/
DRY_RUN_DEFAULT="false"
```

### Step 4: Run with Docker Compose

```bash
# If using cloned repository:
docker-compose up --build

# If using pulled image, create docker-compose.yml:
cat > docker-compose.yml << 'EOF'
services:
  app:
    image: backlandlabs/quorum:latest
    container_name: quorum_app
    env_file:
      - .env
    environment:
      - PUBLIC_API_BASE_URL=http://localhost:8716
    ports:
      - "8716:8716"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8716/healthcheck || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"  # Allows Docker to access host's Anvil
EOF

# Then run:
docker-compose up
```

### Step 5: Access the Application

Once the container is running:

1. **Web UI**: Open http://localhost:8716 in your browser
2. **Health Check**: http://localhost:8716/healthcheck
3. **API Documentation**: http://localhost:8716/docs

### Step 6: Test the Setup

1. The agent will automatically start monitoring the configured DAO (`quorum-ai.eth`)
2. Check the logs to see the agent fetching proposals:
   ```bash
   docker logs quorum_app
   ```
3. The agent will analyze any active proposals and make voting decisions
4. Voting attestations will be recorded on your local testnet

### Troubleshooting

- **Container can't connect to Anvil**: Ensure you're using `host.docker.internal` in RPC_URL for Docker
- **Fork fails to start**: Make sure you have a valid Base RPC URL or use the public endpoint `https://mainnet.base.org`
- **Contract not found errors**: Verify Anvil is running with `--fork-url` to fork Base mainnet (not a regular Anvil instance)
- **API key errors**: Ensure you've added your OpenRouter API key to the `.env` file

### Stopping the Application

```bash
# Stop Docker container
docker-compose down

# Stop Anvil (Ctrl+C in the Anvil terminal)
```

---

## QA

[QA Checklist](QA_CHECKLIST.md)

## Required Contracts

Before running Quorum AI, you need access to the following smart contracts:

### 📋 Required Deployments


2. **AttestationTracker** - EAS wrapper contract for vote attestations
   - Location: `contracts/src/AttestationTracker.sol`
   - Deploy using: `forge script script/Deploy.s.sol`
   - Required for on-chain vote tracking


### 🔑 Key Considerations

- **Network**: Base mainnet/testnet recommended for lower gas costs
- **Dependencies**: AttestationTracker requires EAS contract address
- **Order**: Deploy EAS Schema → AttestationTracker → QuorumStaking
- **Environment**: Update `.env` with all deployed contract addresses
- **Security**: Use dedicated deployment wallet with sufficient ETH

## Environment Variables

Quorum AI requires several environment variables for proper operation. Create a `.env` file in the root directory with the following configuration:

### 🔑 Required Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | OpenRouter API key for Google Gemini 2.0 Flash |
| `EAS_CONTRACT_ADDRESS` | `0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6` | EAS EIP712Proxy contract address on Base mainnet |
| `EAS_SCHEMA_UID` | - | 32-byte hex string from EAS schema deployment |
| `ATTESTATION_TRACKER_ADDRESS` | - | Deployed AttestationTracker address (optional if using wrapper) |
| `BASE_RPC_URL` or `BASE_LEDGER_RPC` | `https://mainnet.base.org` | Base network RPC endpoint |
| `RPC_URL` | `https://mainnet.base.org` | Primary RPC endpoint |
| `CHAIN_ID` | `8453` | Base mainnet chain ID |
| `PRIVATE_KEY` or `EOA_PRIVATE_KEY` | - | Agent private key (without 0x prefix) - for testing only |
| `SAFE_CONTRACT_ADDRESSES` | - | JSON string of Safe addresses per chain |

**Note**: For production, use `ethereum_private_key.txt` file (permissions 600) instead of `PRIVATE_KEY` or `EOA_PRIVATE_KEY` environment variables.

### ⚙️ Optional Variables

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

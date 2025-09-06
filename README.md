# Quorum AI

**⚠️ IMPORTANT: This application currently only supports Base network due to the Ethereum Attestation Service (EAS) integration being locked to Base. All voting attestations will be recorded on Base, regardless of which network the DAO operates on.**

A sophisticated autonomous voting agent for DAO governance on the Olas Pearl platform. This full-stack application enables automated participation in decentralized governance through AI-powered proposal analysis and voting decisions, featuring integration with Snapshot and Google Gemini 2.0 Flash.

## Required Contracts

Before running Quorum AI, you need access to the following smart contracts:

### 📋 Required Deployments

1. **EAS Schema** - Register attestation schema on Base network
   - Schema: `address agent, string spaceId, string proposalId, uint8 voteChoice, string snapshotSig, uint256 timestamp, string runId, uint8 confidence`
   - Deploy via [EAS Schema Registry](https://base.easscan.org/schema/create)
   - Save the Schema UID for environment configuration

2. **AttestationTracker** - EAS wrapper contract for vote attestations
   - Location: `contracts/src/AttestationTracker.sol`
   - Deploy using: `forge script script/Deploy.s.sol`
   - Required for on-chain vote tracking

3. **QuorumStaking** *(Optional)* - Token activity monitoring
   - Location: `contracts/src/QuorumStaking.sol`
   - Deploy using: `forge script script/DeployQuorumStaking.s.sol`
   - Required only if using activity-based rewards

### 🔑 Key Considerations

- **Network**: Base mainnet/testnet recommended for lower gas costs
- **Dependencies**: AttestationTracker requires EAS contract address
- **Order**: Deploy EAS Schema → AttestationTracker → QuorumStaking
- **Environment**: Update `.env` with all deployed contract addresses
- **Security**: Use dedicated deployment wallet with sufficient ETH

## Environment Variables

Quorum AI requires several environment variables for proper operation. Create a `.env` file in the root directory with the following configuration:

### 🔑 Required Variables

**AI Service Configuration**
```bash
# OpenRouter API key for Google Gemini 2.0 Flash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

**Smart Contract Configuration**
```bash
# EAS (Ethereum Attestation Service) configuration
EAS_CONTRACT_ADDRESS=0x4200000000000000000000000000000000000021  # Base mainnet
EAS_SCHEMA_UID=0x...  # 32-byte hex string from EAS schema deployment

# AttestationTracker contract (optional - if using wrapper contract)
ATTESTATION_TRACKER_ADDRESS=0x...  # Deployed AttestationTracker address
```

**Network Configuration**
```bash
# Base network RPC (choose one)
BASE_RPC_URL=https://mainnet.base.org
# OR
BASE_LEDGER_RPC=https://mainnet.base.org

# Chain configuration
RPC_URL=https://mainnet.base.org  # Primary RPC endpoint
CHAIN_ID=8453  # Base mainnet
```

**Wallet Configuration**
```bash
# Agent wallet configuration (choose one method)

# Method 1: Private key file (recommended for production)
# Create file: ethereum_private_key.txt with private key (without 0x prefix)
# File permissions must be 600 (owner read/write only)

# Method 2: Environment variable (for testing)
EOA_PRIVATE_KEY=your_private_key_without_0x_prefix

# Gnosis Safe configuration (for multi-sig voting)
BASE_SAFE_ADDRESS=0x...  # Your Safe address on Base network
SAFE_CONTRACT_ADDRESSES={"base": "0x..."}  # JSON string format
```

### ⚙️ Optional Variables

**Application Configuration**
```bash
# Server configuration
DEBUG=false
HOST=0.0.0.0
PORT=8716
HEALTH_CHECK_PORT=8716

# Logging configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=log.txt

# DAO monitoring
MONITORED_DAOS=compound,nounsdao,arbitrum,aave  # Comma-separated list
TOP_ORGANIZATIONS=compound,nounsdao,arbitrum    # Default dashboard organizations
```

**Agent Behavior Configuration**
```bash
# Voting parameters
VOTE_CONFIDENCE_THRESHOLD=0.6        # Minimum confidence to execute vote (0.0-1.0)
AGENT_CONFIDENCE_THRESHOLD=0.7       # Agent-specific confidence threshold
MAX_PROPOSALS_PER_RUN=3              # Maximum proposals to analyze per run

# Timeout settings
PROPOSAL_FETCH_TIMEOUT=30            # Seconds to wait for proposal fetching
VOTE_EXECUTION_TIMEOUT=60            # Seconds to wait for vote execution

# Agent run intervals
AGENT_RUN_INTERVAL=300               # Seconds between automatic agent runs
```

**Health Check & Monitoring**
```bash
# Health check configuration
HEALTH_CHECK_PATH=/healthcheck
FAST_TRANSITION_THRESHOLD=5          # Seconds threshold for fast state transitions

# State management
STATE_FILE_PATH=agent_state.json     # Path to agent state persistence file
BACKUP_STATE_INTERVAL=60             # Seconds between state backups
```

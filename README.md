# Quorum AI

**⚠️ IMPORTANT: This application currently only supports Base network due to the Ethereum Attestation Service (EAS) integration being locked to Base. All voting attestations will be recorded on Base, regardless of which network the DAO operates on.**

A sophisticated autonomous voting agent for DAO governance on the Olas Pearl platform. This full-stack application enables automated participation in decentralized governance through AI-powered proposal analysis and voting decisions, featuring integration with Snapshot and Google Gemini 2.0 Flash.

## QA

[QA Checklist](QA_CHECKLIST.md)

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

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | OpenRouter API key for Google Gemini 2.0 Flash |
| `EAS_CONTRACT_ADDRESS` | `0x4200000000000000000000000000000000000021` | EAS contract address on Base mainnet |
| `EAS_SCHEMA_UID` | - | 32-byte hex string from EAS schema deployment |
| `ATTESTATION_TRACKER_ADDRESS` | - | Deployed AttestationTracker address (optional if using wrapper) |
| `BASE_RPC_URL` or `BASE_LEDGER_RPC` | `https://mainnet.base.org` | Base network RPC endpoint |
| `RPC_URL` | `https://mainnet.base.org` | Primary RPC endpoint |
| `CHAIN_ID` | `8453` | Base mainnet chain ID |
| `PRIVATE_KEY` or `EOA_PRIVATE_KEY` | - | Agent private key (without 0x prefix) - for testing only |
| `BASE_SAFE_ADDRESS` | - | Gnosis Safe address on Base network |
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

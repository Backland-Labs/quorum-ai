# Quorum AI Pearl Integration - Acceptance Checklist

## Repository Structure & Files

### Core Agent Files
- [ ] `main.py` - Agent orchestration logic
- [ ] `health_server.py` - Healthcheck endpoint implementation
- [ ] `requirements.txt` - Python dependencies
- [ ] `service.yaml` - Service configuration
- [ ] `Dockerfile` - Container configuration
- [ ] `entrypoint.sh` - Docker entrypoint script
- [ ] `log.txt` - Generated during runtime (verify format)

### Configuration Files
- [ ] `config.py` - Agent configuration
- [ ] `models.py` - Data models
- [ ] `governor_abi.json` - Smart contract ABI

### Service Components
- [ ] `services/snapshot_service.py` - Snapshot integration
- [ ] `services/ai_service.py` - Voting decision logic
- [ ] `services/safe_executor.py` - Gnosis Safe integration
- [ ] `services/staking_manager.py` - Staking logic

## Technical Requirements

### Health Check Endpoint
- [ ] Endpoint accessible at `http://127.0.0.1:8716/healthcheck`
- [ ] Returns valid JSON with required fields:
  - [ ] `seconds_since_last_transition`
  - [ ] `is_tm_healthy`
  - [ ] `is_transitioning_fast`
  - [ ] `period`
  - [ ] `agent_health` object with:
    - [ ] `is_making_on_chain_transactions`
    - [ ] `is_staking_kpi_met`
    - [ ] `has_required_funds`
  - [ ] `rounds` array
  - [ ] `rounds_info` object

### Logging
- [ ] Logs written to `log.txt` in working directory
- [ ] Format: `[YYYY-MM-DD HH:MM:SS,mmm] [LOG_LEVEL] [agent] Message`
- [ ] Log file created on startup
- [ ] Appropriate log levels used (INFO, WARNING, ERROR)

### Key Management
- [ ] Reads `ethereum_private_key.txt` from working directory
- [ ] Handles `SAFE_CONTRACT_ADDRESSES` environment variable
- [ ] Properly parses Safe addresses JSON format

### Environment Variables
- [ ] All variables defined in `service.yaml`
- [ ] Variables prefixed with `CONNECTION_CONFIGS_CONFIG_` when read
- [ ] Required computed variables:
  - [ ] `SAFE_CONTRACT_ADDRESSES`
  - [ ] `GNOSIS_LEDGER_RPC`
  - [ ] `STAKING_TOKEN_CONTRACT_ADDRESS`
  - [ ] `ACTIVITY_CHECKER_CONTRACT_ADDRESS`
  - [ ] `STORE_PATH`
- [ ] User-provided variables:
  - [ ] `SNAPSHOT_API_KEY`
  - [ ] `VOTING_STRATEGY`
  - [ ] `DAO_ADDRESSES`

### Persistence & Recovery
- [ ] Uses `STORE_PATH` for persistent data
- [ ] Saves state periodically (at least every epoch)
- [ ] Recovers gracefully after SIGKILL
- [ ] No data stored outside `STORE_PATH`

### Activity Requirements
- [ ] Performs at least 1 transaction per 24 hours
- [ ] Implements fallback dummy transaction if no proposals
- [ ] Transaction goes through multisig Safe
- [ ] Activity tracked for staking rewards

## Docker Requirements

### Dockerfile
- [ ] Uses appropriate base image (Python 3.10+)
- [ ] Installs all system dependencies
- [ ] Copies all required files
- [ ] Sets ENTRYPOINT (not CMD)
- [ ] Includes HEALTHCHECK directive
- [ ] Health check interval ≤ 30 seconds

### Docker Image
- [ ] Built successfully
- [ ] Tagged with format: `<author>/oar-quorum_ai:<ipfs_hash>`
- [ ] Pushed to Docker Hub
- [ ] Publicly accessible

## IPFS & Registry

### Package Management
- [ ] All packages locked (`autonomy packages lock`)
- [ ] Pushed to IPFS (`autonomy push-all`)
- [ ] IPFS hash recorded
- [ ] Hash matches in `packages/packages.json`

### Olas Registry
- [ ] Agent minted on Olas Protocol
- [ ] Agent ID recorded
- [ ] All components registered (not service)
- [ ] Dependencies set (minimum: 1)

## Smart Contracts

### Staking Contract
- [ ] Activity checker deployed
- [ ] Staking contract deployed via Olas factory
- [ ] Contract addresses recorded
- [ ] Minimum activity: 1 transaction/day
- [ ] Epoch length: 86400 seconds

## Service Template

### JSON Structure
- [ ] Valid JSON format
- [ ] All required fields present:
  - [ ] `name`, `hash`, `description`
  - [ ] `service_version`
  - [ ] `home_chain`
  - [ ] `configurations` object
  - [ ] `env_variables` object

### Configuration
- [ ] Correct IPFS hash
- [ ] Valid agent ID
- [ ] `use_staking: "true"`
- [ ] Appropriate fund requirements
- [ ] All environment variables defined

## Testing

### Local Testing
- [ ] Agent starts successfully
- [ ] Health check responds correctly
- [ ] Logs generated in correct format
- [ ] Connects to Gnosis Safe
- [ ] Can read Snapshot proposals
- [ ] Makes voting decisions
- [ ] Executes transactions

### Pearl Integration Testing
- [ ] Works with Pearl binary
- [ ] Handles start/stop via SIGKILL
- [ ] Environment variables properly passed
- [ ] Staking mechanism functional
- [ ] Daily activity requirement met

## Security & Code Quality

### Code Standards
- [ ] ASCII characters only (32-126)
- [ ] No hardcoded credentials
- [ ] Proper error handling
- [ ] Input validation
- [ ] No external dependencies beyond requirements

### Python Quality (if Open Autonomy)
- [ ] Passes Black formatter
- [ ] Passes isort
- [ ] Passes mypy type checking
- [ ] Passes Bandit security scan

## Documentation

### Required Documentation
- [ ] README with setup instructions
- [ ] Environment variable descriptions
- [ ] Voting strategy explanation
- [ ] Troubleshooting guide

### Pearl Submission
- [ ] Service template JSON ready
- [ ] PR prepared for Pearl repository
- [ ] Agent metadata provided:
  - [ ] Agent name
  - [ ] Description
  - [ ] Logo (if custom UI)

## Final Validation

### Deployment Ready
- [ ] All above items checked
- [ ] Tested on Gnosis testnet
- [ ] Fund requirements verified
- [ ] Activity tracking confirmed
- [ ] Staking rewards accumulating
- [ ] No critical issues in 24-hour test run

### Pearl Requirements Met
- [ ] Follows Pearl integration guide
- [ ] Compatible with Pearl binary
- [ ] Healthcheck fully functional
- [ ] Logging compliant
- [ ] SIGKILL recovery tested
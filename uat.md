# Quorum AI - User Acceptance Testing (UAT) Plan

## Overview
This UAT plan provides a comprehensive testing strategy for the Quorum AI application, including deployment of containers, smart contracts, and end-to-end testing with UI verification and blockchain interaction validation.

## Prerequisites

### Required Software
- Docker & Docker Compose
- Foundry (forge, cast, anvil) for smart contract deployment
- Playwright MCP for UI automation
- jq for JSON parsing
- curl for API testing

### Environment Setup

#### Container Architecture Overview
- **Combined Application Container**: 
  - Base: Multi-stage Dockerfile in project root
  - Backend: Python with uv package manager (port 8716)
  - Frontend: Static files served by backend
  - Both services run in single container with health checks
  - Non-root user for security

#### Smart Contract Setup
```bash
# Install Foundry dependencies
cd contracts && forge install && cd ..
```

## Test Execution Plan

### Phase 1: Local Blockchain Setup

#### 1.1 Start Anvil Test Network
```bash
# Terminal 1: Start Anvil with deterministic accounts
anvil --fork-url https://mainnet.base.org \
      --chain-id 8453 \
      --port 8545 \
      --accounts 10 \
      --balance 10000 \
      --block-time 2

# Expected Output:
# - 10 test accounts with private keys
# - RPC endpoint: http://localhost:8545
# - Chain ID: 8453
```

#### 1.2 Deploy Smart Contracts
```bash
# Terminal 2: Deploy contracts
cd contracts

# Export environment variables
export PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
export ATTESTATION_TRACKER_OWNER="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
export EAS_CONTRACT_ADDRESS="0x4200000000000000000000000000000000000021"
export LIVENESS_RATIO="1000000000000000"

# Deploy AttestationTracker
forge script script/Deploy.s.sol:DeployScript \
  --rpc-url http://localhost:8545 \
  --broadcast \
  -vvv

# Capture deployed address
export ATTESTATION_TRACKER_ADDRESS=$(cat broadcast/Deploy.s.sol/8453/run-latest.json | jq -r '.transactions[0].contractAddress')
echo "AttestationTracker deployed to: $ATTESTATION_TRACKER_ADDRESS"

# Deploy QuorumStaking (if needed)
forge script script/DeployQuorumStaking.s.sol \
  --rpc-url http://localhost:8545 \
  --broadcast

# Verify deployment
cast call $ATTESTATION_TRACKER_ADDRESS "owner()" --rpc-url http://localhost:8545
```

### Phase 2: Application Deployment

#### 2.1 Docker Container Deployment
```bash
# Terminal 3: Build and start containers
# Update .env with contract addresses
echo "ATTESTATION_TRACKER_ADDRESS=$ATTESTATION_TRACKER_ADDRESS" >> .env

# Update .env with Test Safe address for attestation testing
sed -i '' "s/SAFE_CONTRACT_ADDRESSES=.*/SAFE_CONTRACT_ADDRESSES='{\"base\": \"$TEST_SAFE_ADDRESS\"}'/" .env

# Verify configuration
echo "Updated .env with:"
echo "ATTESTATION_TRACKER_ADDRESS=$ATTESTATION_TRACKER_ADDRESS"
echo "SAFE_CONTRACT_ADDRESSES={\"base\": \"$TEST_SAFE_ADDRESS\"}"

# Build container
docker-compose build

# Start containers with logging
docker-compose up -d

# Verify containers are running
docker-compose ps

# Expected container:
# - quorum_app (combined backend and frontend on port 8716)
```

### Phase 3: Service Health Verification

#### 3.1 Backend Health Check
```bash
# Check backend health
curl -f http://localhost:8716/healthcheck

# Expected response:
# {
#   "status": "healthy",
#   "services": {
#     "database": "connected",
#     "blockchain": "connected",
#     "snapshot": "connected"
#   }
# }

# Check API documentation
curl http://localhost:8716/docs
```

#### 3.2 Frontend Health Check
```bash
# Check frontend is serving (served by backend at root)
curl -f http://localhost:8716/

# Should return HTML content
```

#### 3.3 Monitor Container Logs
```bash
# Terminal 4: Tail application logs (combined)
docker logs -f quorum_app

```

### Phase 4: UI Testing with Playwright MCP

#### 4.1 Initialize Playwright Browser
```python
# Using Playwright MCP commands
mcp__playwright__browser_navigate(url="http://localhost:8716")
mcp__playwright__browser_snapshot()  # Capture initial state
```

#### 4.2 Test User Onboarding Flow
```python
# Step 1: Navigate to Setup Page
mcp__playwright__browser_navigate(url="http://localhost:8716/setup")
mcp__playwright__browser_take_screenshot(filename="setup-page.png")

# Step 2: Fill Preference Form
mcp__playwright__browser_fill_form(fields=[
    {
        "name": "DAO Selection",
        "ref": "select#dao-selector",
        "type": "combobox",
        "value": "compound-governance.eth"
    },
    {
        "name": "Voting Strategy",
        "ref": "select#voting-strategy",
        "type": "combobox",
        "value": "conservative"
    },
    {
        "name": "Confidence Threshold",
        "ref": "input#confidence-threshold",
        "type": "textbox",
        "value": "0.8"
    }
])

# Step 3: Submit Form
mcp__playwright__browser_click(
    element="Submit Preferences Button",
    ref="button#submit-preferences"
)

# Step 4: Verify Redirect to Dashboard
mcp__playwright__browser_wait_for(text="Dashboard")
mcp__playwright__browser_take_screenshot(filename="dashboard-loaded.png")
```

#### 4.3 Test Dashboard Metrics Display
```python
# Capture dashboard state
mcp__playwright__browser_snapshot()

# Verify key metrics are displayed
mcp__playwright__browser_evaluate(
    function="""() => {
        const metrics = {
            totalProposals: document.querySelector('[data-testid="total-proposals"]')?.textContent,
            activeProposals: document.querySelector('[data-testid="active-proposals"]')?.textContent,
            votedProposals: document.querySelector('[data-testid="voted-proposals"]')?.textContent,
            agentStatus: document.querySelector('[data-testid="agent-status"]')?.textContent
        };
        return metrics;
    }"""
)

# Take screenshots of each section
mcp__playwright__browser_take_screenshot(
    element="Agent Status Widget",
    ref="[data-testid='agent-status-widget']",
    filename="agent-status.png"
)

mcp__playwright__browser_take_screenshot(
    element="Proposal Statistics",
    ref="[data-testid='proposal-stats']",
    filename="proposal-stats.png"
)

mcp__playwright__browser_take_screenshot(
    element="Recent Proposals",
    ref="[data-testid='recent-proposals']",
    filename="recent-proposals.png"
)
```

#### 4.4 Test Proposal Interaction
```python
# Click on a proposal
mcp__playwright__browser_click(
    element="First Proposal Card",
    ref=".proposal-card:first-child"
)

# Wait for proposal details to load
mcp__playwright__browser_wait_for(text="Proposal Details")

# Capture proposal page
mcp__playwright__browser_take_screenshot(filename="proposal-details.png")

# Test voting action (if available)
mcp__playwright__browser_click(
    element="Vote Button",
    ref="button[data-action='vote']"
)

# Verify transaction initiation
mcp__playwright__browser_wait_for(text="Transaction Pending")
```

### Phase 5: Blockchain Interaction Testing

#### 5.1 Test Attestation Creation
```bash
# Create a test attestation through the API
curl -X POST http://localhost:8716/api/attestations \
  -H "Content-Type: application/json" \
  -d '{
    "proposalId": "0x123...",
    "vote": "FOR",
    "reasoning": "Test attestation"
  }'

# Verify on-chain
cast call $ATTESTATION_TRACKER_ADDRESS \
  "getNumAttestations(address)" \
  "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266" \
  --rpc-url http://localhost:8545
```

#### 5.2 Test Agent Run Workflow
```bash
# Trigger agent run
curl -X POST http://localhost:8716/api/agent/run \
  -H "Content-Type: application/json" \
  -d '{"dao": "compound-governance.eth"}'

# Monitor agent execution in logs
docker logs -f quorum_app | grep "AGENT"

# Check agent run status
curl http://localhost:8716/api/agent/status
```

#### 5.3 Verify Smart Contract Interactions
```bash
# Check attestation tracker state
cast call $ATTESTATION_TRACKER_ADDRESS \
  "getMultisigInfo(address)" \
  "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266" \
  --rpc-url http://localhost:8545

# Monitor contract events
cast logs \
  --address $ATTESTATION_TRACKER_ADDRESS \
  --from-block latest \
  --rpc-url http://localhost:8545
```

### Phase 6: End-to-End Workflow Testing

#### 6.1 Complete Voting Cycle
1. **Fetch Active Proposals**
   ```bash
   curl http://localhost:8716/api/proposals?dao=compound-governance.eth&state=active
   ```

2. **Analyze Proposal with AI**
   ```bash
   curl -X POST http://localhost:8716/api/analyze \
     -H "Content-Type: application/json" \
     -d '{"proposalId": "<proposal-id>"}'
   ```

3. **Execute Vote**
   ```bash
   curl -X POST http://localhost:8716/api/vote \
     -H "Content-Type: application/json" \
     -d '{
       "proposalId": "<proposal-id>",
       "choice": "FOR",
       "reasoning": "AI analysis supports this proposal"
     }'
   ```

4. **Create Attestation**
   ```bash
   # Vote creates attestation automatically
   # Verify in logs and on-chain
   ```

#### 6.2 UI Workflow Verification
```python
# Complete user journey through UI
# 1. Navigate to dashboard
mcp__playwright__browser_navigate(url="http://localhost:8716")

# 2. Select a DAO
mcp__playwright__browser_click(
    element="DAO Dropdown",
    ref="select#dao-selector"
)
mcp__playwright__browser_select_option(
    element="DAO Option",
    ref="select#dao-selector",
    values=["compound-governance.eth"]
)

# 3. View proposals
mcp__playwright__browser_wait_for(text="Active Proposals")

# 4. Click on proposal
mcp__playwright__browser_click(
    element="Proposal Card",
    ref=".proposal-card"
)

# 5. Review AI analysis
mcp__playwright__browser_wait_for(text="AI Analysis")
mcp__playwright__browser_take_screenshot(filename="ai-analysis.png")

# 6. Execute vote
mcp__playwright__browser_click(
    element="Vote For Button",
    ref="button[data-vote='for']"
)

# 7. Confirm transaction
mcp__playwright__browser_wait_for(text="Vote Submitted")
mcp__playwright__browser_take_screenshot(filename="vote-confirmation.png")
```

### Phase 7: Test Cleanup

#### 8.1 Stop Services
```bash
# Stop Docker containers
docker-compose down

# Or stop local services
pkill -f "uv run"
pkill -f "npm run dev"

# Stop Anvil
pkill anvil
```

#### 8.2 Collect Test Artifacts
```bash
# Create test report directory
mkdir -p test-reports/$(date +%Y%m%d_%H%M%S)

# Copy logs
cp backend.log test-reports/*/
cp frontend.log test-reports/*/
cp backend/log.txt test-reports/*/pearl.log

# Copy screenshots
cp *.png test-reports/*/

# Generate summary report
echo "# UAT Execution Report - $(date)" > test-reports/*/REPORT.md
echo "## Test Results" >> test-reports/*/REPORT.md
echo "- Backend Health: PASS/FAIL" >> test-reports/*/REPORT.md
echo "- Frontend Load: PASS/FAIL" >> test-reports/*/REPORT.md
echo "- Contract Deploy: PASS/FAIL" >> test-reports/*/REPORT.md
echo "- UI Navigation: PASS/FAIL" >> test-reports/*/REPORT.md
echo "- Blockchain Interaction: PASS/FAIL" >> test-reports/*/REPORT.md
```

## Success Criteria

### ✅ Core Functionality
- [ ] Containers deploy successfully
- [ ] Health checks pass for all services
- [ ] Smart contracts deploy and verify correctly
- [ ] API endpoints respond within acceptable time
- [ ] Frontend loads without errors

### ✅ User Interface
- [ ] Dashboard displays all metrics correctly
- [ ] Proposal list populates with data
- [ ] Navigation between pages works
- [ ] Forms submit successfully
- [ ] Error states display appropriately

### ✅ Blockchain Integration
- [ ] Attestations are created on-chain
- [ ] Contract state updates correctly
- [ ] Events emit as expected
- [ ] Gas costs are reasonable
- [ ] Transaction confirmations work

### ✅ Agent Functionality
- [ ] Agent runs execute on schedule
- [ ] AI analysis completes successfully
- [ ] Voting decisions are recorded
- [ ] Pearl logging captures all activities
- [ ] State persistence works correctly

## Troubleshooting Guide

### Common Issues and Solutions

#### Port Already in Use
```bash
# Kill process on specific port
lsof -ti :8716 | xargs kill -9
lsof -ti :8545 | xargs kill -9
```

#### Contract Deployment Fails
```bash
# Reset Anvil state
pkill anvil
rm -rf contracts/broadcast/*
anvil --reset
```

#### Frontend Build Errors
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run generate-api
npm run dev
```

#### Backend Import Errors
```bash
cd backend
uv sync --force-reinstall
uv run python -m pytest tests/ -v
```

#### Docker Container Issues
```bash
# Rebuild containers
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Test Execution Checklist

### Pre-Test
- [ ] All prerequisites installed
- [ ] Environment variables configured
- [ ] Ports available (8545, 8716)
- [ ] Test data prepared

### During Test
- [ ] Monitor all log outputs
- [ ] Capture screenshots at key points
- [ ] Document any errors or issues
- [ ] Verify blockchain state changes

### Post-Test
- [ ] All services stopped cleanly
- [ ] Test artifacts collected
- [ ] Report generated
- [ ] Issues logged for resolution

## Automated Test Script

Save this as `run_uat.sh`:

```bash
#!/bin/bash
set -e

echo "Starting UAT Execution..."

# Phase 1: Start infrastructure
echo "Phase 1: Starting blockchain..."
anvil --fork-url https://mainnet.base.org --chain-id 8453 &
ANVIL_PID=$!
sleep 5

# Phase 2: Deploy contracts
echo "Phase 2: Deploying contracts..."
cd contracts
./deploy_local.sh
cd ..

# Phase 3: Start application
echo "Phase 3: Starting application..."
docker-compose up -d
sleep 10

# Phase 4: Run health checks
echo "Phase 4: Running health checks..."
curl -f http://localhost:8716/healthcheck || exit 1
curl -f http://localhost:8716 || exit 1

# Phase 5: Execute tests
echo "Phase 5: Executing UI tests..."
# Add Playwright MCP test commands here

# Phase 6: Cleanup
echo "Phase 6: Cleaning up..."
docker-compose down
kill $ANVIL_PID

echo "UAT Complete!"
```

## Conclusion

This UAT plan provides comprehensive coverage of the Quorum AI application, ensuring all components work together correctly. Execute each phase sequentially, documenting results and capturing evidence of successful operation.

For any issues encountered, refer to the troubleshooting guide or create detailed bug reports with:
- Error messages and stack traces
- Screenshots showing the issue
- Steps to reproduce
- Environment configuration
- Log excerpts from affected services
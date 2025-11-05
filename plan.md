# Quorum AI Testing & Deployment Improvement Plan

## Objective
Simplify deployment and testing with clear pass/fail signals while maintaining Pearl-compliant logging.

## Key Principles
- ✅ Keep Pearl-compliant logging unchanged (no structured JSON changes)
- ✅ Single container image for Pearl/Olas deployment
- ✅ Docker Compose for local development convenience only
- ✅ Clear automated verification endpoints for auditors
- ✅ One-command startup for testing

---

## Implementation Tasks

### 1. Environment Configuration Cleanup

**Goal**: Single source of truth for configuration with smart defaults.

#### 1.1 Create Environment Presets
Create `env/` directory with three preset files:

**`env/mock.env`** - Fastest testing, no external dependencies
```bash
# Mock mode - no RPC/API keys needed
MOCK_MODE=1
DRY_RUN_DEFAULT=1
MONITORED_DAOS=quorum-ai.eth
LOG_LEVEL=DEBUG
CHAIN_ID=8453
RPC_URL=http://localhost:8545
PORT=8716
HOST=0.0.0.0
```

**`env/fork.env`** - Local Anvil fork of Base
```bash
# Fork mode - local blockchain with real data
MOCK_MODE=0
DRY_RUN_DEFAULT=1
MONITORED_DAOS=quorum-ai.eth
LOG_LEVEL=DEBUG

# Blockchain config
CHAIN_ID=8453
RPC_URL=http://anvil:8545
BASE_RPC_URL=https://mainnet.base.org

# Contract addresses (Base mainnet)
EAS_CONTRACT_ADDRESS=0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6
ATTESTATION_TRACKER_ADDRESS=0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC
EAS_SCHEMA_UID=0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4

# Anvil default account (auto-funded)
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
AGENT_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
SAFE_CONTRACT_ADDRESSES={"base":"0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"}

# API config (optional for AI testing)
OPENROUTER_API_KEY=your_key_here

# Server config
PORT=8716
HOST=0.0.0.0
```

**`env/testnet.env`** - Real Base network
```bash
# Testnet/mainnet mode - real network
MOCK_MODE=0
DRY_RUN_DEFAULT=1
MONITORED_DAOS=quorum-ai.eth
LOG_LEVEL=INFO

# Blockchain config
CHAIN_ID=8453
RPC_URL=https://mainnet.base.org
BASE_RPC_URL=https://mainnet.base.org

# Contract addresses (Base mainnet)
EAS_CONTRACT_ADDRESS=0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6
ATTESTATION_TRACKER_ADDRESS=0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC
EAS_SCHEMA_UID=0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4

# Set your own keys
PRIVATE_KEY=
AGENT_ADDRESS=
SAFE_CONTRACT_ADDRESSES=

# API config
OPENROUTER_API_KEY=

# Server config
PORT=8716
HOST=0.0.0.0
```

#### 1.2 Unify Private Key Handling
- Use single env var: `ETH_PRIVATE_KEY_FILE=/agent_key/ethereum_private_key.txt`
- Fallback to `PRIVATE_KEY` env var if file not found
- Update `backend/config.py` to read from file first

---

### 2. Docker Compose Improvements

**Goal**: Manage Anvil + app together for local testing.

#### 2.1 Add Anvil Service to `docker-compose.yml`
```yaml
services:
  anvil:
    image: ghcr.io/foundry-rs/foundry:latest
    profiles: ["fork"]
    command: anvil --fork-url ${BASE_RPC_URL:-https://mainnet.base.org} --host 0.0.0.0 --port 8545 --block-time 2
    healthcheck:
      test: ["CMD-SHELL", "curl -sf -X POST http://localhost:8545 -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}' || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 20
      start_period: 5s
    ports:
      - "8545:8545"
    restart: unless-stopped
```

#### 2.2 Update App Service Dependencies
```yaml
services:
  app:
    # ... existing config ...
    depends_on:
      anvil:
        condition: service_healthy
        required: false  # Only required when fork profile is active
```

#### 2.3 Create `docker-compose.dev.yml` for Hot Reload
```yaml
services:
  app:
    command: uv run uvicorn main:app --host 0.0.0.0 --port 8716 --reload
    volumes:
      - ./backend:/app/backend
      - ./logs:/app/logs
      - ./store:/app/store
```

---

### 3. Backend Verification Endpoints

**Goal**: Provide clear pass/fail testing signals for auditors. Use existing `/agent-run` endpoint for testing.

#### 3.1 Add Mock Mode Support

**`backend/config.py`**
```python
# Mock mode - stubs AI and blockchain for testing without keys
MOCK_MODE = os.getenv("MOCK_MODE", "0") == "1"
```

**`backend/ai_service.py`**
```python
from backend.config import MOCK_MODE

async def summarize_proposal(proposal: Proposal) -> ProposalSummary:
    """Summarize proposal using AI or mock."""
    if MOCK_MODE or not OPENROUTER_API_KEY:
        logger.warning("AI in MOCK_MODE: returning stubbed summary")
        return ProposalSummary(
            proposal_id=proposal.id,
            summary="[MOCK] This is a test proposal summary",
            risk_level="low",
            recommendation="approve",
            confidence=0.85
        )
    # ... existing AI logic ...

async def get_voting_decision(proposal: Proposal, user_prefs: UserPreferences) -> VotingDecision:
    """Get autonomous voting decision or mock."""
    if MOCK_MODE or not OPENROUTER_API_KEY:
        logger.warning("AI in MOCK_MODE: returning stubbed decision")
        return VotingDecision(
            proposal_id=proposal.id,
            choice=proposal.choices[0] if proposal.choices else "For",
            confidence=0.85,
            reasoning="[MOCK] Auto-approved for testing"
        )
    # ... existing AI logic ...
```

**`backend/safe_service.py`**
```python
from backend.config import MOCK_MODE, DRY_RUN_DEFAULT

async def create_attestation(data: dict) -> str:
    """Create attestation or return mock UID."""
    if MOCK_MODE or DRY_RUN_DEFAULT:
        logger.info("MOCK/DRY_RUN: skipping on-chain attestation")
        return "0x" + "0" * 64  # Stub attestation UID
    # ... existing attestation logic ...
```

#### 3.2 Add `/self-test` Endpoint

**`backend/main.py`**
```python
class SelfTestResponse(BaseModel):
    """Response from self-test endpoint."""
    proposal_fetch_ok: bool
    ai_decision_ok: bool
    attestation_ok: bool
    onchain_count: Optional[int] = None
    details: dict = {}

@app.get("/self-test", response_model=SelfTestResponse)
async def self_test():
    """
    Run a comprehensive self-test of all system components.
    Returns explicit pass/fail for each component.
    """
    details = {}
    
    # Test 1: Proposal fetch from Snapshot
    try:
        from backend.snapshot_service import fetch_proposals
        proposals = await fetch_proposals(
            space_name=config.MONITORED_DAOS.split(",")[0],
            max_proposals=1
        )
        proposal_fetch_ok = len(proposals) > 0
        details["proposal_count"] = len(proposals)
    except Exception as e:
        proposal_fetch_ok = False
        details["proposal_error"] = str(e)
    
    # Test 2: AI decision (use mock or real)
    try:
        from backend.ai_service import get_voting_decision
        from backend.models import UserPreferences
        
        if proposal_fetch_ok:
            test_prefs = UserPreferences(voting_strategy="balanced")
            decision = await get_voting_decision(proposals[0], test_prefs)
            ai_decision_ok = decision.confidence > 0.5
            details["ai_confidence"] = decision.confidence
        else:
            ai_decision_ok = False
            details["ai_error"] = "No proposals to test"
    except Exception as e:
        ai_decision_ok = False
        details["ai_error"] = str(e)
    
    # Test 3: Attestation capability (check if we can connect)
    try:
        from backend.safe_service import get_multisig_info
        
        info = await get_multisig_info()
        attestation_ok = info is not None
        details["attestation_count"] = info.get("attestation_count") if info else None
    except Exception as e:
        attestation_ok = False
        details["attestation_error"] = str(e)
    
    return SelfTestResponse(
        proposal_fetch_ok=proposal_fetch_ok,
        ai_decision_ok=ai_decision_ok,
        attestation_ok=attestation_ok,
        onchain_count=details.get("attestation_count"),
        details=details
    )
```

#### 3.3 Add `/verify/attestation` Endpoint

**`backend/main.py`**
```python
class AttestationVerification(BaseModel):
    """Verification result for an attestation."""
    found: bool
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    error: Optional[str] = None

@app.get("/verify/attestation", response_model=AttestationVerification)
async def verify_attestation(uid: str):
    """
    Verify that an attestation exists on-chain.
    Queries EAS contract to confirm the attestation.
    """
    try:
        from backend.safe_service import verify_attestation_onchain
        
        result = await verify_attestation_onchain(uid)
        
        return AttestationVerification(
            found=result.get("found", False),
            tx_hash=result.get("tx_hash"),
            block_number=result.get("block_number")
        )
    except Exception as e:
        logger.error(f"Attestation verification failed: {e}")
        return AttestationVerification(
            found=False,
            error=str(e)
        )
```

#### 3.4 Add `/verify/count` Endpoint (for Anvil testing)

**`backend/main.py`**
```python
@app.get("/verify/count")
async def verify_attestation_count():
    """
    Get current attestation count from AttestationTracker contract.
    Useful for verifying attestations were recorded on local Anvil.
    """
    try:
        from backend.safe_service import get_multisig_info
        
        info = await get_multisig_info()
        
        return {
            "count": info.get("attestation_count", 0),
            "address": config.ATTESTATION_TRACKER_ADDRESS
        }
    except Exception as e:
        logger.error(f"Count verification failed: {e}")
        return {"count": 0, "error": str(e)}
```

#### 3.5 Add Helper Service Functions

**`backend/safe_service.py`**
```python
async def verify_attestation_onchain(uid: str) -> dict:
    """
    Verify an attestation exists on-chain by querying EAS contract.
    
    Args:
        uid: Attestation UID to verify
    
    Returns:
        dict with found, tx_hash, block_number
    """
    from web3 import Web3
    
    if config.MOCK_MODE:
        return {"found": True, "tx_hash": "0x" + "0" * 64, "block_number": 1}
    
    # Initialize web3 connection
    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    
    # Query EAS contract for attestation
    # This is a simplified example - adjust based on EAS contract ABI
    eas_contract = w3.eth.contract(
        address=config.EAS_CONTRACT_ADDRESS,
        abi=[...]  # Add EAS ABI here
    )
    
    try:
        attestation = eas_contract.functions.getAttestation(uid).call()
        
        # Check if attestation exists (non-zero values)
        found = attestation[0] != "0x0000000000000000000000000000000000000000"
        
        return {
            "found": found,
            "tx_hash": None,  # Would need to query events for tx hash
            "block_number": None  # Would need to query events for block
        }
    except Exception as e:
        logger.error(f"Error verifying attestation {uid}: {e}")
        return {"found": False, "error": str(e)}
```

---

### 4. Simple Wrapper Script

**Goal**: Single command interface for all operations.

#### 4.1 Create `scripts/quorum`
```bash
#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-mock}"
CMD="${2:-up}"
DEV_FLAG="${3:-}"

ENV_FILE="env/${PROFILE}.env"
COMPOSE_FILES="-f docker-compose.yml"
PROFILES=""

# Enable fork profile for anvil
if [[ "$PROFILE" == "fork" ]]; then 
    PROFILES="--profile fork"
fi

# Enable dev overrides
if [[ "$DEV_FLAG" == "--dev" ]]; then 
    COMPOSE_FILES="$COMPOSE_FILES -f docker-compose.dev.yml"
fi

case "$CMD" in
  up)
    echo "Starting Quorum AI in $PROFILE mode..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" $PROFILES up -d
    echo "Waiting for service to be ready..."
    sleep 5
    curl -sf http://localhost:8716/healthcheck && echo "✓ Service is healthy" || echo "✗ Service not responding"
    ;;
  down)
    echo "Stopping Quorum AI..."
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" $PROFILES down -v
    ;;
  logs)
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" $PROFILES logs -f app
    ;;
  status)
    echo "=== Service Status ==="
    docker compose $COMPOSE_FILES --env-file "$ENV_FILE" $PROFILES ps
    echo ""
    echo "=== Health Check ==="
    curl -sf http://localhost:8716/healthcheck | jq '.' || echo "Service not responding"
    echo ""
    if [[ "$PROFILE" == "fork" ]]; then
      echo "=== Anvil Status ==="
      curl -s -X POST http://localhost:8545 -H 'Content-Type: application/json' \
        -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' | jq '.'
    fi
    ;;
  test)
    echo "=== Running Self-Test ==="
    curl -sf http://localhost:8716/self-test | jq '.'
    ;;
  verify)
    echo "=== Verifying Attestation Count ==="
    curl -sf http://localhost:8716/verify/count | jq '.'
    ;;
  run)
    echo "=== Running Agent ==="
    curl -sf -X POST http://localhost:8716/agent-run | jq '.'
    ;;
  *)
    echo "Quorum AI Testing Script"
    echo ""
    echo "Usage: ./quorum [PROFILE] [COMMAND] [--dev]"
    echo ""
    echo "Profiles:"
    echo "  mock     - Fastest, no external dependencies (default)"
    echo "  fork     - Local Anvil fork of Base"
    echo "  testnet  - Real Base network"
    echo ""
    echo "Commands:"
    echo "  up       - Start services (default)"
    echo "  down     - Stop services"
    echo "  logs     - Show live logs"
    echo "  status   - Show service status"
    echo "  test     - Run self-test"
    echo "  verify   - Verify attestation count"
    echo "  run      - Run agent (existing endpoint)"
    echo ""
    echo "Examples:"
    echo "  ./quorum mock up         # Start in mock mode"
    echo "  ./quorum fork up --dev   # Start with hot reload"
    echo "  ./quorum fork test       # Run self-test"
    echo "  ./quorum fork verify     # Check attestation count"
    exit 1
    ;;
esac
```

Make executable: `chmod +x scripts/quorum`

#### 4.2 Create `Makefile`
```makefile
.PHONY: help up down logs status test verify run clean

PROFILE ?= fork

help:
	@echo "Quorum AI Testing Commands"
	@echo ""
	@echo "  make up         - Start services (default: fork mode)"
	@echo "  make down       - Stop services"
	@echo "  make logs       - Show live logs"
	@echo "  make status     - Show service status"
	@echo "  make test       - Run self-test"
	@echo "  make verify     - Verify attestation count"
	@echo "  make run        - Run agent (existing endpoint)"
	@echo "  make clean      - Stop and remove all data"
	@echo ""
	@echo "Set PROFILE=mock|fork|testnet to change mode"

up:
	./scripts/quorum $(PROFILE) up

down:
	./scripts/quorum $(PROFILE) down

logs:
	./scripts/quorum $(PROFILE) logs

status:
	./scripts/quorum $(PROFILE) status

test:
	./scripts/quorum $(PROFILE) test

verify:
	./scripts/quorum $(PROFILE) verify

run:
	./scripts/quorum $(PROFILE) run

clean: down
	rm -rf logs/* store/* .anvil.pid
```

---

### 5. Update AGENTS.md

Add testing commands section:
```markdown
## Rapid Testing Workflow

### Quick Start
```bash
# Fastest: Mock mode (no keys needed)
./scripts/quorum mock up
curl http://localhost:8716/self-test

# Full: Fork mode (local blockchain)
./scripts/quorum fork up
curl -X POST http://localhost:8716/agent-run-once
curl http://localhost:8716/verify/count

# Using Makefile
make up              # Start in fork mode
make test            # Run self-test
make verify          # Check attestation count
make down            # Stop services
```

### Testing Commands
- **Start services**: `./scripts/quorum [mock|fork|testnet] up`
- **Self-test**: `curl http://localhost:8716/self-test`
- **Run agent**: `curl -X POST http://localhost:8716/agent-run`
- **Verify attestations**: `curl http://localhost:8716/verify/count`
- **View logs**: `./scripts/quorum fork logs`
- **Stop services**: `./scripts/quorum fork down`

### Auditor Verification Steps
1. Start: `make up`
2. Test: `make test` (should show all checks passing)
3. Run: `make run` (triggers agent run)
4. Verify: `make verify` (confirms attestation on-chain)
5. Logs: `make logs` (Pearl-compliant audit trail)
```

---

## Implementation Order

1. **Environment Setup** (30 min)
   - Create `env/` directory and three preset files
   - Update `.gitignore` to exclude `env/*.local.env`

2. **Docker Compose** (30 min)
   - Add Anvil service to `docker-compose.yml`
   - Create `docker-compose.dev.yml`
   - Update app service dependencies

3. **Backend Mock Mode** (45 min)
   - Add `MOCK_MODE` to `config.py`
   - Update `ai_service.py` with mock stubs
   - Update `safe_service.py` with mock stubs

4. **Verification Endpoints** (1.5 hours)
   - Implement `/self-test` endpoint
   - Implement `/verify/attestation` endpoint
   - Implement `/verify/count` endpoint
   - Add helper functions to `safe_service.py`

5. **Wrapper Script** (30 min)
   - Create `scripts/quorum` with all commands
   - Make executable
   - Test all commands

6. **Makefile** (15 min)
   - Create `Makefile` with targets
   - Test all targets

7. **Documentation** (15 min)
   - Update `AGENTS.md` with testing workflow
   - Update `README.md` quick start section

8. **Testing & Validation** (1 hour)
   - Test mock mode: `./scripts/quorum mock up`
   - Test fork mode: `./scripts/quorum fork up`
   - Run self-test in both modes
   - Verify all endpoints work
   - Check Pearl-compliant logs

---

## Success Criteria

- ✅ `make up` starts all services in one command
- ✅ `make test` returns clear pass/fail for all components
- ✅ `make verify` confirms attestations on-chain (in fork mode)
- ✅ Mock mode works without any API keys or RPC
- ✅ Pearl-compliant logging remains unchanged
- ✅ Single Docker image works for local and Pearl deployment
- ✅ Clear auditor workflow documented

---

## Files Changed

### New Files
- `env/mock.env`
- `env/fork.env`
- `env/testnet.env`
- `scripts/quorum`
- `docker-compose.dev.yml`
- `Makefile`

### Modified Files
- `docker-compose.yml` - Add Anvil service
- `backend/config.py` - Add MOCK_MODE
- `backend/main.py` - Add verification endpoints
- `backend/ai_service.py` - Add mock stubs
- `backend/safe_service.py` - Add mock stubs and verification functions

- `AGENTS.md` - Add testing workflow section
- `README.md` - Update quick start

---

## Rollback Plan

If issues arise:
1. Keep existing `local_run_service.sh` functional during transition
2. Mark new system as "experimental" initially
3. Test thoroughly in mock mode before fork mode
4. Validate Pearl deployment separately before deprecating old workflow

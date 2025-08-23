# ActivityService Staking Contract Nonce Tracking Implementation Plan

## Overview

Extend the existing ActivityService to implement the IQuorumTracker interface and track 4 nonce values required for OLAS staking eligibility. The service will maintain persistent counters for multisig transactions, vote attestations, voting opportunities considered, and no-voting opportunities, integrating with existing OLAS compliance in a unified state file.

## Current State Analysis

The ActivityService currently provides basic OLAS compliance tracking:
- **State Persistence**: JSON file at `activity_tracker.json` with `last_activity_date` and `last_tx_hash`
- **Daily Compliance**: Tracks 24-hour activity requirement via `is_daily_activity_needed()`
- **Pearl Logging**: Full Pearl-compliant logging integration
- **Safe Integration**: Collaborates with SafeService for activity transactions

### Key Discoveries:
- SafeService already provides multi-chain Web3 connections (`backend/services/safe_service.py:75`)
- Configuration has staking contract addresses (`backend/config.py:138-147`)
- Existing atomic file operations for state persistence (`backend/services/activity_service.py:86-120`)
- Contract requires IQuorumTracker interface with `getVotingStats()` method

## Desired End State

The ActivityService will:
1. Track 4 nonce values locally (multisig_activity, vote_attestations, voting_considered, no_voting)
2. Implement IQuorumTracker interface with `getMultisigNonces()` and `isRatioPass()` methods
3. Calculate activity ratios to determine OLAS staking eligibility
4. Persist all activity data (OLAS compliance + nonces) in unified `activity_tracker.json`
5. Support multi-chain nonce tracking using Safe addresses from settings
6. Start fresh with nonce values at 0 (no migration needed)

### Verification:
- Unit tests pass with >90% coverage for new functionality
- Integration tests verify contract interaction
- State persistence includes all nonce data
- API endpoints return comprehensive activity status
- No regression in existing OLAS compliance features

## What We're NOT Doing

- Deploying the Activity Checker contract (handled separately)
- Reading nonces from on-chain contracts (tracking locally only)
- Implementing backward compatibility or migration (starting fresh)
- Managing contract addresses (will be configured separately)
- Creating new database tables (file-based persistence only)
- Modifying the staking contract itself

## Implementation Approach

Extend ActivityService to implement IQuorumTracker interface for local nonce tracking. Integrate all activity data into unified state file, implement eligibility checking logic, and provide methods that match the Activity Checker contract interface for OLAS staking eligibility determination.

## Phase 1: Unified Data Model and State Persistence

### Overview
Create unified state schema that integrates OLAS compliance and nonce tracking in single `activity_tracker.json` file.

### Changes Required:

#### 1. ActivityService State Schema Update
**File**: `backend/services/activity_service.py`
**Changes**: 
- Add nonce tracking data structures to class:
  ```python
  # Nonce type constants
  NONCE_MULTISIG_ACTIVITY = 0
  NONCE_VOTE_ATTESTATIONS = 1
  NONCE_VOTING_CONSIDERED = 2
  NONCE_NO_VOTING = 3
  
  # In __init__
  self.nonces: Dict[str, Dict[int, int]] = {}  # {chain: {nonce_type: value}}
  ```
- Update `_prepare_state_data()` to include nonces in unified format:
  ```python
  {
      "last_activity_date": "2024-01-15",
      "last_tx_hash": "0x123...",
      "nonces": {
          "ethereum": {0: 5, 1: 3, 2: 10, 3: 2},
          "gnosis": {0: 8, 1: 6, 2: 15, 3: 4}
      },
      "last_updated": "2024-01-15T10:30:00Z"
  }
  ```
- Modify `load_state()` to handle unified schema (no migration needed)

#### 2. Pydantic Models for Nonce Data
**File**: `backend/models.py`
**Changes**:
- Add models for type-safe nonce handling:
  ```python
  class ChainNonces(BaseModel):
      multisig_activity: int = Field(default=0, ge=0)
      vote_attestations: int = Field(default=0, ge=0)
      voting_considered: int = Field(default=0, ge=0)
      no_voting: int = Field(default=0, ge=0)
      last_updated: datetime = Field(default_factory=datetime.utcnow)
  
  class ActivityState(BaseModel):
      last_activity_date: Optional[date] = None
      last_tx_hash: Optional[str] = None
      nonces: Dict[str, ChainNonces] = Field(default_factory=dict)
  ```

### Success Criteria:

#### Automated Verification:
- [ ] Unit tests pass: `uv run pytest tests/test_activity_service.py -v`
- [ ] State persistence tests pass: `uv run pytest tests/test_state_persistence.py -v`
- [ ] Type checking passes: `cd frontend && npm run check`
- [ ] Linting passes: `pre-commit run --all-files`

#### Manual Verification:
- [ ] Existing state files load without errors
- [ ] New state files include nonce data
- [ ] Schema migration handles old format files
- [ ] No data loss during migration

---

## Phase 2: Nonce Increment Logic

### Overview
Implement logic to increment nonces based on agent activities and voting operations.

### Changes Required:

#### 1. Nonce Increment Methods
**File**: `backend/services/activity_service.py`
**Changes**:
- Add increment methods for each nonce type:
  ```python
  def increment_multisig_activity(self, chain: str) -> None:
      """Increment nonce for multisig transaction activity."""
      self._increment_nonce(chain, NONCE_MULTISIG_ACTIVITY)
      self.logger.info("Multisig activity incremented (chain=%s)", chain)
  
  def increment_vote_attestation(self, chain: str) -> None:
      """Increment nonce for vote attestation."""
      self._increment_nonce(chain, NONCE_VOTE_ATTESTATIONS)
      self.logger.info("Vote attestation incremented (chain=%s)", chain)
  
  def increment_voting_considered(self, chain: str) -> None:
      """Increment nonce when proposal considered but not voted."""
      self._increment_nonce(chain, NONCE_VOTING_CONSIDERED)
      self.logger.info("Voting opportunity considered (chain=%s)", chain)
  
  def increment_no_voting(self, chain: str) -> None:
      """Increment nonce when no voting opportunities available."""
      self._increment_nonce(chain, NONCE_NO_VOTING)
      self.logger.info("No voting opportunity recorded (chain=%s)", chain)
  ```

#### 2. Exception Classes for Validation
**File**: `backend/services/activity_service.py`
**Changes**:
- Add validation exception:
  ```python
  class NonceValidationError(Exception):
      """Exception for nonce validation failures."""
      def __init__(self, chain: str, nonce_type: int, message: str):
          self.chain = chain
          self.nonce_type = nonce_type
          super().__init__(f"Invalid nonce operation on {chain} for type {nonce_type}: {message}")
  ```

#### 3. Multi-chain Support
**File**: `backend/services/activity_service.py`
**Changes**:
- Add chain validation using Safe addresses:
  ```python
  @property
  def supported_chains(self) -> List[str]:
      """Get list of supported chains from Safe addresses."""
      return list(settings.safe_addresses.keys())
  
  def _validate_chain(self, chain: str) -> None:
      """Validate chain is supported."""
      if chain not in self.supported_chains:
          raise NonceValidationError(chain, -1, f"Chain not configured in Safe addresses")
  ```

### Success Criteria:

#### Automated Verification:
- [ ] Contract integration tests pass: `uv run pytest tests/test_activity_service_contract.py -v`
- [ ] Mock Web3 tests pass: `uv run pytest tests/test_activity_service.py::TestContractIntegration -v`
- [ ] Type checking passes: `cd frontend && npm run check`

#### Manual Verification:
- [ ] Successfully fetch nonces from testnet contracts
- [ ] Handle network errors gracefully
- [ ] Multi-chain queries work correctly
- [ ] Contract call timeouts handled properly

---

## Phase 3: IQuorumTracker Interface Implementation

### Overview
Implement the IQuorumTracker interface methods required by the Activity Checker contract for OLAS staking eligibility.

### Changes Required:

#### 1. Core Interface Methods
**File**: `backend/services/activity_service.py`
**Changes**:
- Add `getMultisigNonces()` method matching contract interface:
  ```python
  def getMultisigNonces(self, multisig_address: str) -> List[int]:
      """Get nonces for multisig address (IQuorumTracker interface).
      
      Returns array: [multisig_activity, vote_attestations, voting_considered, no_voting]
      """
      # Use Safe address to determine chain
      chain = self._get_chain_for_safe(multisig_address)
      if chain not in self.nonces:
          return [0, 0, 0, 0]
      
      chain_nonces = self.nonces[chain]
      return [
          chain_nonces.get(NONCE_MULTISIG_ACTIVITY, 0),
          chain_nonces.get(NONCE_VOTE_ATTESTATIONS, 0),
          chain_nonces.get(NONCE_VOTING_CONSIDERED, 0),
          chain_nonces.get(NONCE_NO_VOTING, 0)
      ]
  ```

#### 2. Eligibility Check Method
**File**: `backend/services/activity_service.py`
**Changes**:
- Add `isRatioPass()` method for eligibility determination:
  ```python
  def isRatioPass(self, multisig_address: str, liveness_ratio: float, period_seconds: int) -> bool:
      """Check if multisig passes activity ratio for staking eligibility.
      
      Args:
          multisig_address: Safe multisig address
          liveness_ratio: Required tx/s ratio (with 18 decimals)
          period_seconds: Time period to check
      
      Returns:
          True if activity ratio meets requirements
      """
      nonces = self.getMultisigNonces(multisig_address)
      # Calculate actual ratio based on nonce differences
      actual_ratio = self._calculate_activity_ratio(nonces, period_seconds)
      return actual_ratio >= liveness_ratio
  ```

#### 3. Helper Methods with Pearl Logging
**File**: `backend/services/activity_service.py`
**Changes**:
- Add helper methods for chain resolution and ratio calculation:
  ```python
  def _get_chain_for_safe(self, safe_address: str) -> Optional[str]:
      """Determine chain from Safe address."""
      for chain, address in settings.safe_addresses.items():
          if address.lower() == safe_address.lower():
              return chain
      return None
  
  def _calculate_activity_ratio(self, nonces: List[int], period_seconds: int) -> float:
      """Calculate activity ratio for staking eligibility.
      
      Formula: (nonce_differences * 1e18) / period_seconds
      """
      with log_span(self.logger, "activity_service.calculate_ratio") as span_data:
          # For now, use multisig activity as primary metric
          activity_count = nonces[NONCE_MULTISIG_ACTIVITY]
          ratio = (activity_count * 10**18) / period_seconds if period_seconds > 0 else 0
          
          self.logger.info(
              "Activity ratio calculated (activity=%s, period=%s, ratio=%s)",
              activity_count, period_seconds, ratio
          )
          span_data.update({"activity": activity_count, "period": period_seconds, "ratio": ratio})
          return ratio
  ```

### Success Criteria:

#### Automated Verification:
- [ ] Interface tests pass: `uv run pytest tests/test_activity_service.py::TestIQuorumTracker -v`
- [ ] Ratio calculation tests pass: `uv run pytest tests/test_activity_service.py::TestActivityRatio -v`
- [ ] Integration tests pass: `uv run pytest tests/test_service_integration.py -v`

#### Manual Verification:
- [ ] Voting stats match expected format
- [ ] Activity ratios calculate correctly
- [ ] Interface compatible with contract expectations
- [ ] Edge cases handled (zero time delta, no changes)

---

## Phase 4: Service Integration

### Overview
Integrate nonce tracking with existing services to automatically increment counters based on agent activities.

### Changes Required:

#### 1. VotingService Integration
**File**: `backend/services/voting_service.py`
**Changes**:
- Import and use ActivityService after successful vote:
  ```python
  async def vote_on_proposal(self, proposal_id: str, choice: int, chain: str):
      # Existing voting logic...
      if vote_result.success:
          # Increment vote attestation nonce
          self.activity_service.increment_vote_attestation(chain)
      return vote_result
  ```

#### 2. AgentRunService Integration
**File**: `backend/services/agent_run_service.py`
**Changes**:
- Track voting opportunities:
  ```python
  async def _process_proposals(self, proposals: List[Proposal], chain: str):
      if not proposals:
          # No voting opportunities available
          self.activity_service.increment_no_voting(chain)
          return
      
      for proposal in proposals:
          decision = await self.ai_service.decide_vote(proposal)
          if decision.should_vote:
              await self.voting_service.vote_on_proposal(proposal.id, decision.choice, chain)
              # vote_attestation incremented by VotingService
          else:
              # Proposal considered but not voted
              self.activity_service.increment_voting_considered(chain)
  ```

#### 3. SafeService Integration
**File**: `backend/services/safe_service.py`
**Changes**:
- Track multisig transactions:
  ```python
  async def perform_activity_transaction(self, chain: str):
      # Existing Safe transaction logic...
      if tx_result.success:
          # Increment multisig activity nonce
          self.activity_service.increment_multisig_activity(chain)
      return tx_result
  ```

### Success Criteria:

#### Automated Verification:
- [ ] Integration tests pass: `uv run pytest tests/test_service_integration.py -v`
- [ ] VotingService tests pass: `uv run pytest tests/test_voting_service.py -v`
- [ ] AgentRunService tests pass: `uv run pytest tests/test_agent_run_service.py -v`

#### Manual Verification:
- [ ] Nonces increment correctly after votes
- [ ] Multisig activities tracked properly
- [ ] No-voting scenarios recorded
- [ ] Considered proposals tracked

---

## Phase 5: API Endpoints

### Overview
Expose nonce tracking data and eligibility status through REST API endpoints.

### Changes Required:

#### 1. API Endpoints with Specification-Compliant Responses
**File**: `backend/main.py`
**Changes**:
- Add endpoints with proper error handling:
  ```python
  @app.get("/activity/nonces", response_model=NonceResponse)
  async def get_all_nonces():
      """Get nonce values for all configured chains."""
      try:
          nonces_data = {}
          for chain in activity_service.supported_chains:
              safe_address = settings.safe_addresses.get(chain)
              if safe_address:
                  nonces_data[chain] = {
                      "address": safe_address,
                      "nonces": activity_service.getMultisigNonces(safe_address)
                  }
          return {"data": nonces_data, "status": "success"}
      except Exception as e:
          raise HTTPException(
              status_code=500,
              detail={"error": "Internal Server Error", "message": str(e)}
          )
  ```
- Add eligibility check endpoint:
  ```python
  @app.get("/activity/eligibility/{chain}")
  async def check_eligibility(chain: str, liveness_ratio: float = 5e15):  # 5 tx per day default
      """Check OLAS staking eligibility for a chain."""
      safe_address = settings.safe_addresses.get(chain)
      if not safe_address:
          raise HTTPException(404, detail={"error": "Chain not configured"})
      
      is_eligible = activity_service.isRatioPass(safe_address, liveness_ratio, 86400)  # 24 hours
      nonces = activity_service.getMultisigNonces(safe_address)
      
      return {
          "data": {
              "chain": chain,
              "eligible": is_eligible,
              "nonces": nonces,
              "safe_address": safe_address
          },
          "status": "success"
      }
  ```
- Update `GET /activity/status` to include nonce summary:
  ```python
  status = activity_service.get_activity_status()
  status["nonces"] = {chain: activity_service.getMultisigNonces(addr) 
                       for chain, addr in settings.safe_addresses.items()}
  ```

#### 2. Response Models
**File**: `backend/models.py`
**Changes**:
- Add API response models:
  ```python
  class NonceData(BaseModel):
      address: str
      nonces: List[int]
  
  class NonceResponse(BaseModel):
      data: Dict[str, NonceData]
      status: Literal["success"]
  
  class EligibilityResponse(BaseModel):
      data: Dict[str, Any]
      status: Literal["success"]
  ```

### Success Criteria:

#### Automated Verification:
- [ ] API tests pass: `uv run pytest tests/test_main.py::TestNonceEndpoints -v`
- [ ] Model validation tests pass: `uv run pytest tests/test_models.py -v`
- [ ] Type checking passes: `cd frontend && npm run check`

#### Manual Verification:
- [ ] API endpoints return correct nonce data
- [ ] Eligibility endpoint calculates correctly
- [ ] Swagger documentation updated
- [ ] Response formats match specification

---

## Testing Strategy

### Unit Tests:
- Test nonce increment methods for all 4 types
- Test state persistence with unified schema
- Test IQuorumTracker interface methods
- Test activity ratio calculations
- Test chain resolution from Safe addresses

### Integration Tests:
- Test service integration (VotingService, AgentRunService, SafeService)
- Test nonce increments during agent operations
- Test API endpoint responses
- Test eligibility checking logic

### Manual Testing Steps:
1. Start the service with fresh state (nonces at 0)
2. Trigger various agent activities:
   - Submit a vote (increment vote_attestations)
   - Execute Safe transaction (increment multisig_activity)
   - Process proposals without voting (increment voting_considered)
   - Run agent with no proposals (increment no_voting)
3. Verify nonces increment correctly in `activity_tracker.json`
4. Test API endpoints return correct nonce values
5. Verify eligibility calculation with different liveness ratios

## Performance Considerations

- Nonce increments are local operations (no blockchain calls)
- State persistence uses atomic file operations
- Chain resolution uses in-memory Safe address lookup
- Activity ratio calculation is simple arithmetic
- No external API calls required for eligibility checks

## Implementation Notes

- Start with all nonces at 0 (no migration needed)
- Single `activity_tracker.json` file contains all data
- Uses existing Safe addresses from settings for multi-chain support
- Activity Checker contract deployment handled separately
- Contract address configuration will be added later

## References

- Original ticket: Task requirements provided
- Staking contract: https://github.com/valory-xyz/autonolas-staking-programmes/blob/quorum/contracts/externals/backland/QuorumStakingTokenActivityChecker.sol
- Current ActivityService: `backend/services/activity_service.py:18`
- SafeService integration: `backend/services/safe_service.py:43`
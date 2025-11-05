# Switch to Immediate Attestations (Remove Queue) Implementation Plan

## Overview

This plan details the migration from queued attestations to immediate attestation processing in the Quorum AI autonomous voting agent. Currently, vote attestations are queued in checkpoint state and processed at the start of subsequent agent runs. The new approach will create EAS attestations immediately after each successful vote submission, simplifying the architecture and providing faster on-chain auditability.

## Current State Analysis

### Existing Queue Mechanism

Based on code analysis of `backend/services/agent_run_service.py`:

**Queue Lifecycle (Lines 159-160, 927-1058)**:
- Line 159-160: `_process_pending_attestations()` called at start of each agent run
- Lines 927-1058: `_process_pending_attestations()` method loads checkpoint, retries failed attestations up to `MAX_ATTESTATION_RETRIES` (3 attempts)
- Lines 1059-1129: `_queue_attestation()` method stores attestation data in checkpoint's `pending_attestations` array
- Line 836-838: Called after each vote submission in `_execute_votes()` regardless of vote success/failure

**Checkpoint State (Lines 1131-1161)**:
- Line 1154: `pending_attestations` field initialized as empty array in checkpoint
- Lines 1143-1145: Vote decisions serialized with timestamps
- Line 1157-1159: Checkpoint saved to StateManager with pending attestations

**Retry Logic (Lines 978-983, 1039-1041)**:
- Lines 978-983: Max retries check, attestations exceeding limit are dropped
- Lines 1039-1041: Retry count incremented on failure, attestation re-queued
- Line 36: `MAX_ATTESTATION_RETRIES = 3` constant

### Key Discoveries

1. **Attestation Data Structure** (Lines 1096-1111):
   - Proposal ID, vote choice (mapped from VoteType enum)
   - Voter address, delegate address
   - Vote transaction hash (vote_id from Snapshot or 0x+64 zeros placeholder)
   - Reasoning, timestamp, retry_count
   - Uses `datetime.now(timezone.utc)` for timestamp

2. **Vote Execution Flow** (Lines 735-870):
   - Lines 788-843: Each vote submission extracts vote_id from Snapshot response
   - Line 820-821: Vote_id extracted from `submission_result.response.id`
   - Lines 834-843: Attestation queued regardless of vote success with proper vote_id or placeholder
   - Line 782-783: Dry run mode returns early, skipping both voting and attestation

3. **EAS Integration** (via SafeService):
   - SafeService.create_eas_attestation() expects EASAttestationData model
   - Returns dict with `success`, `safe_tx_hash` (optional)
   - Already handles config validation and error cases
   - Lines 1005-1031: Activity service marking happens after successful attestation

## Desired End State

### Immediate Attestation Flow

After this implementation:
1. Agent run starts → No queue processing
2. Proposal analyzed → Vote decision made
3. Vote submitted → Immediate attestation attempt
4. Attestation success → Activity marked complete (if tx hash present)
5. Attestation failure → Logged, execution continues
6. Checkpoint saved → No pending_attestations field

### Success Verification

#### Automated Verification:
- [ ] All unit tests pass: `uv run pytest backend/tests/test_agent_run_service.py -v`
- [ ] Integration tests pass: `uv run pytest backend/tests/ -k "integration" -v`
- [ ] No linting errors: `pre-commit run --all-files` (only on modified files)
- [ ] Type checking passes: `uv run mypy backend/services/agent_run_service.py`
- [ ] Code builds successfully: `docker build -t quorum-ai .`

#### Manual Verification:
- [ ] Agent run executes end-to-end without errors in dry run mode
- [ ] Immediate attestation occurs after vote with proper logging
- [ ] Checkpoint files contain no pending_attestations field
- [ ] Failed attestation does not block subsequent votes
- [ ] Mock mode produces expected stub attestation response
- [ ] Real attestation (testnet) creates on-chain record within same run

## What We're NOT Doing

Explicitly out of scope to prevent scope creep:
- Not changing EASAttestationData model schema
- Not modifying SafeService attestation creation logic (only adding error categorization in agent_run_service)
- Not refactoring existing error messages in SafeService, VotingService, or other components
- Not altering VoteDecision model or API response structure
- Not implementing parallel/concurrent attestations
- Not adding a separate attestation retry mechanism
- Not creating new database tables for attestation tracking
- Not modifying frontend components
- Not changing API endpoint signatures
- Not implementing attestation result aggregation in responses
- Not updating error messages throughout the entire codebase (only immediate attestation errors)

## Implementation Approach

### Rationale for Immediate Attestation

**Benefits**:
- **Simpler Architecture**: Eliminates queue state management, retry logic, and checkpoint complexity
- **Faster Auditability**: Attestations appear on-chain immediately after votes
- **Clearer Logging**: Attestation success/failure logged in context with vote execution
- **Reduced State**: No need to persist pending attestations across runs
- **Better Error Visibility**: Attestation failures visible immediately, not delayed

**Trade-offs**:
- **Longer Run Time**: Attestation latency extends per-proposal processing time
- **No Retry Mechanism**: Failed attestations are logged but not automatically retried
- **Config Dependency**: Missing EAS config causes failures during run (logged, not blocking)

**Mitigation Strategies**:
- Keep sequential execution for now (consider parallelization in future)
- Clear logging of attestation failures for manual investigation
- Graceful degradation when EAS config missing (log warning, continue)

## Phase 1: Remove Queue Infrastructure

### Overview
Remove all queue-related code, constants, and state management from agent_run_service.py.

### Changes Required

#### 1. Remove Queue Constants and Methods
**File**: `backend/services/agent_run_service.py`

**Delete**:
- Line 36: `MAX_ATTESTATION_RETRIES = 3` constant
- Lines 159-160: Call to `await self._process_pending_attestations(request.space_id)`
- Lines 927-1058: Entire `_process_pending_attestations()` method
- Lines 1059-1129: Entire `_queue_attestation()` method

**Rationale**: These components implement the queue lifecycle and retry mechanism, which are no longer needed with immediate attestation.

#### 2. Update Checkpoint State Structure
**File**: `backend/services/agent_run_service.py`

**Changes in `_save_checkpoint_state()` (Lines 1131-1161)**:
- Line 1154: Remove `"pending_attestations": []` from checkpoint_data dict
- Remove any queue-related aggregation logic if present

**Before**:
```python
checkpoint_data = {
    "space_id": response.space_id,
    "proposals_analyzed": response.proposals_analyzed,
    "votes_cast": votes_with_timestamps,
    "execution_time": response.execution_time,
    "timestamp": datetime.utcnow().isoformat(),
    "errors": response.errors,
    "pending_attestations": [],  # Remove this line
}
```

**After**:
```python
checkpoint_data = {
    "space_id": response.space_id,
    "proposals_analyzed": response.proposals_analyzed,
    "votes_cast": votes_with_timestamps,
    "execution_time": response.execution_time,
    "timestamp": datetime.utcnow().isoformat(),
    "errors": response.errors,
}
```

### Success Criteria

#### Automated Verification:
- [ ] Code compiles without import errors: `python -m py_compile backend/services/agent_run_service.py`
- [ ] No references to deleted methods: `rg "_process_pending_attestations|_queue_attestation" backend/services/`
- [ ] No references to MAX_ATTESTATION_RETRIES: `rg "MAX_ATTESTATION_RETRIES" backend/services/`
- [ ] Checkpoint structure simplified: `rg "pending_attestations" backend/services/agent_run_service.py` returns no results

#### Manual Verification:
- [ ] Review git diff to confirm only queue-related code removed
- [ ] Verify no unintended deletions of attestation-related imports
- [ ] Confirm checkpoint save logic still present and functional

---

## Phase 2: Implement Immediate Attestation

### Overview
Add immediate attestation logic to `_execute_votes()` method, called directly after each vote submission.

### Changes Required

#### 1. Add Immediate Attestation to Vote Execution Loop
**File**: `backend/services/agent_run_service.py`

**Location**: In `_execute_votes()` method (Lines 735-870), after vote submission

**Insert after Line 843** (after current attestation queue call):

```python
# Always attempt immediate attestation regardless of vote success/failure
# This creates an audit trail of all voting decisions
try:
    self.pearl_logger.info(
        f"Creating immediate EAS attestation (proposal={decision.proposal_id}, "
        f"vote_succeeded={vote_succeeded}, vote_id={vote_id or 'None'}, "
        f"agent={self.voting_service.account.address}, space={space_id})"
    )

    # Build EAS attestation data
    eas_data = EASAttestationData(
        agent=self.voting_service.account.address,
        space_id=space_id,
        proposal_id=decision.proposal_id,
        vote_choice=vote_choice,  # Already converted via VOTE_CHOICE_MAPPING
        snapshot_sig=vote_id if vote_id else "0x" + "0" * 64,
        timestamp=int(time.time()),
        run_id=run_id,
        confidence=int(decision.confidence * 100),  # Convert 0.0-1.0 to 0-100
    )

    # Submit attestation through Safe service
    attestation_result = await self.safe_service.create_eas_attestation(eas_data)

    if attestation_result.get("success"):
        safe_tx_hash = attestation_result.get("safe_tx_hash")
        self.pearl_logger.info(
            f"Successfully created EAS attestation (proposal={decision.proposal_id}, "
            f"safe_tx_hash={safe_tx_hash}, schema_uid={config.EAS_SCHEMA_UID})"
        )

        # Mark daily activity as completed for OLAS staking compliance
        if safe_tx_hash:
            self.activity_service.mark_activity_completed(safe_tx_hash)
            self.pearl_logger.info(
                f"Marked daily activity as completed (tx_hash={safe_tx_hash}, "
                f"proposal={decision.proposal_id})"
            )
    else:
        # Provide precise, actionable error messages based on failure type
        # Note: We're categorizing errors returned by SafeService, not modifying SafeService itself
        error_msg = attestation_result.get("error", "Unknown error")

        # Categorize error and provide specific guidance
        if "EAS_CONTRACT_ADDRESS" in error_msg or "contract address" in error_msg.lower():
            self.pearl_logger.error(
                f"Cannot create EAS attestation: EAS_CONTRACT_ADDRESS not configured. "
                f"Set EAS_CONTRACT_ADDRESS environment variable to the EAS contract address "
                f"on Base network (0x4200000000000000000000000000000000000021). "
                f"proposal={decision.proposal_id}, space={space_id}"
            )
        elif "EAS_SCHEMA_UID" in error_msg or "schema" in error_msg.lower():
            self.pearl_logger.error(
                f"Cannot create EAS attestation: EAS_SCHEMA_UID not configured. "
                f"Set EAS_SCHEMA_UID environment variable to your registered schema UID. "
                f"Register schema at https://base.easscan.org/schema/create. "
                f"proposal={decision.proposal_id}, space={space_id}"
            )
        elif "SAFE_CONTRACT_ADDRESSES" in error_msg or "safe address" in error_msg.lower():
            self.pearl_logger.error(
                f"Cannot create EAS attestation: SAFE_CONTRACT_ADDRESSES not configured. "
                f"Set SAFE_CONTRACT_ADDRESSES environment variable with Safe address JSON. "
                f"Example: SAFE_CONTRACT_ADDRESSES='{{\"base\":\"0xYourSafeAddress\"}}'. "
                f"proposal={decision.proposal_id}, space={space_id}"
            )
        elif "timeout" in error_msg.lower():
            self.pearl_logger.error(
                f"EAS attestation failed due to RPC timeout. "
                f"Check RPC_URL is responsive: {config.RPC_URL}. "
                f"Try increasing timeout or switching RPC provider. "
                f"proposal={decision.proposal_id}, error={error_msg}"
            )
        elif "insufficient funds" in error_msg.lower():
            safe_addr = config.SAFE_CONTRACT_ADDRESSES.get('base') if config.SAFE_CONTRACT_ADDRESSES else 'UNKNOWN'
            self.pearl_logger.error(
                f"EAS attestation failed: Safe has insufficient ETH for gas. "
                f"Fund Safe address with ETH: {safe_addr}. "
                f"Check balance at https://basescan.org/address/{safe_addr}. "
                f"proposal={decision.proposal_id}, error={error_msg}"
            )
        elif "nonce" in error_msg.lower():
            safe_addr = config.SAFE_CONTRACT_ADDRESSES.get('base') if config.SAFE_CONTRACT_ADDRESSES else 'UNKNOWN'
            self.pearl_logger.error(
                f"EAS attestation failed due to nonce mismatch. "
                f"This may indicate a pending transaction or concurrent execution. "
                f"Check Safe Transaction Service for pending txs: "
                f"https://safe-transaction-base.safe.global/api/v1/safes/{safe_addr}/multisig-transactions/. "
                f"proposal={decision.proposal_id}, error={error_msg}"
            )
        else:
            # Generic failure with full debugging context
            self.pearl_logger.error(
                f"Failed to create EAS attestation (proposal={decision.proposal_id}, "
                f"space={space_id}, agent={self.voting_service.account.address}, "
                f"eas_contract={config.EAS_CONTRACT_ADDRESS or 'NOT_SET'}, "
                f"schema_uid={config.EAS_SCHEMA_UID or 'NOT_SET'}, "
                f"rpc_url={config.RPC_URL}, error={error_msg}). "
                f"Check configuration and network connectivity."
            )
        # Do not raise - continue with other votes

except Exception as e:
    self.pearl_logger.exception(
        f"Unexpected exception during immediate attestation. "
        f"proposal={decision.proposal_id}, space={space_id}, "
        f"vote_id={vote_id or 'None'}, agent={self.voting_service.account.address}, "
        f"eas_contract={config.EAS_CONTRACT_ADDRESS or 'NOT_SET'}, "
        f"schema_uid={config.EAS_SCHEMA_UID or 'NOT_SET'}, "
        f"safe_address={config.SAFE_CONTRACT_ADDRESSES.get('base') if config.SAFE_CONTRACT_ADDRESSES else 'NOT_SET'}. "
        f"Exception: {str(e)}"
    )
    # Do not raise - attestation failures should not block voting
```

**Replace Lines 834-843** (remove old queue call):
```python
# Delete these lines:
# Always queue attestation regardless of vote success/failure
# This creates an audit trail of all voting decisions
await self._queue_attestation(
    decision, space_id, run_id, vote_id
)

self.pearl_logger.info(
    f"Attestation queued for vote attempt (proposal={decision.proposal_id}, "
    f"vote_succeeded={vote_succeeded}, vote_id={vote_id or 'None'})"
)
```

#### 2. Ensure Dry Run Skips Attestation
**File**: `backend/services/agent_run_service.py`

**Verification**: Lines 780-783 already handle dry run early return:
```python
if dry_run:
    self.pearl_logger.info("Dry run mode - simulating vote execution")
    # In dry run, we skip actual submission but still return decisions
    return decisions
```

**No changes needed** - this early return prevents both voting and attestation in dry run mode.

### Success Criteria

#### Automated Verification:
- [ ] Unit test passes for immediate attestation with vote success: `uv run pytest backend/tests/test_agent_run_service.py::test_immediate_attestation_success -v`
- [ ] Unit test passes for immediate attestation with vote failure: `uv run pytest backend/tests/test_agent_run_service.py::test_immediate_attestation_vote_failure -v`
- [ ] Unit test passes for attestation failure continuing execution: `uv run pytest backend/tests/test_agent_run_service.py::test_attestation_failure_continues -v`
- [ ] Dry run test confirms no attestation: `uv run pytest backend/tests/test_agent_run_service.py::test_dry_run_skips_attestation -v`
- [ ] Mock SafeService.create_eas_attestation called with correct data: Verified via mock assertions
- [ ] Mock ActivityService.mark_activity_completed called on success: Verified via mock assertions
- [ ] Code compiles without syntax errors: `python -m py_compile backend/services/agent_run_service.py`

#### Manual Verification:
- [ ] Immediate attestation logs appear with clear success/failure messages
- [ ] Vote execution continues after attestation failure
- [ ] Dry run mode produces expected behavior (no votes, no attestations)
- [ ] EAS data structure matches expected schema (agent, space_id, proposal_id, etc.)
- [ ] Error messages categorize failures correctly (config vs network vs blockchain)
- [ ] Error messages include actionable remediation steps
- [ ] Error logs include all debugging context (addresses, RPC URLs, config state)

---

## Phase 3: Update Tests

### Overview
Remove queue-related tests and add comprehensive tests for immediate attestation behavior.

### Changes Required

#### 1. Remove Queue-Related Tests
**File**: `backend/tests/test_agent_run_service.py` (or similar test files)

**Delete any tests that**:
- Test `_process_pending_attestations()` functionality
- Test `_queue_attestation()` functionality
- Test retry logic with MAX_ATTESTATION_RETRIES
- Verify pending_attestations in checkpoint state
- Test queue persistence across runs

#### 2. Add Immediate Attestation Tests
**File**: `backend/tests/test_agent_run_service.py`

**New Test Cases**:

```python
class TestImmediateAttestationFlow:
    """Test immediate attestation after vote submission."""

    @pytest.mark.asyncio
    async def test_immediate_attestation_after_successful_vote(
        self, agent_run_service, sample_proposal, user_preferences
    ):
        """Test that attestation is created immediately after successful vote.

        Importance: Verifies the core immediate attestation flow works correctly
        when votes succeed, ensuring on-chain audit trail is created promptly.
        """
        # Mock vote success
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": "0xabc123"}},
            }
        )

        # Mock successful attestation
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={"success": True, "safe_tx_hash": "0xdef456"}
        )

        # Mock activity marking
        agent_run_service.activity_service.mark_activity_completed = Mock()

        # Execute votes
        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test reasoning",
            strategy_used=VotingStrategy.BALANCED,
        )

        await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify attestation was called with correct data
        assert agent_run_service.safe_service.create_eas_attestation.called
        call_args = agent_run_service.safe_service.create_eas_attestation.call_args[0][0]
        assert isinstance(call_args, EASAttestationData)
        assert call_args.proposal_id == "test-proposal"
        assert call_args.vote_choice == 1  # FOR = 1
        assert call_args.snapshot_sig == "0xabc123"
        assert call_args.confidence == 85  # 0.85 * 100

        # Verify activity was marked
        agent_run_service.activity_service.mark_activity_completed.assert_called_once_with(
            "0xdef456"
        )

    @pytest.mark.asyncio
    async def test_immediate_attestation_after_failed_vote(
        self, agent_run_service, sample_proposal
    ):
        """Test that attestation still attempted after vote failure with placeholder sig.

        Importance: Ensures failed votes are also attested for complete audit trail,
        using placeholder signature when no vote_id available.
        """
        # Mock vote failure
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={"success": False, "error": "Snapshot API error"}
        )

        # Mock successful attestation
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={"success": True, "safe_tx_hash": "0xabc123"}
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test reasoning",
            strategy_used=VotingStrategy.BALANCED,
        )

        await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify attestation was called with placeholder signature
        assert agent_run_service.safe_service.create_eas_attestation.called
        call_args = agent_run_service.safe_service.create_eas_attestation.call_args[0][0]
        assert call_args.snapshot_sig == "0x" + "0" * 64  # Placeholder for failed vote

    @pytest.mark.asyncio
    async def test_attestation_failure_does_not_block_execution(
        self, agent_run_service, sample_proposal
    ):
        """Test that attestation failure does not prevent subsequent votes.

        Importance: Critical for resilience - attestation issues should not
        stop the agent from processing remaining proposals.
        """
        # Mock vote success
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": "0xabc123"}},
            }
        )

        # Mock attestation failure
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={"success": False, "error": "EAS contract not configured"}
        )

        # Create two decisions
        decisions = [
            VoteDecision(
                proposal_id="proposal-1",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="Test",
                strategy_used=VotingStrategy.BALANCED,
            ),
            VoteDecision(
                proposal_id="proposal-2",
                vote=VoteType.AGAINST,
                confidence=0.75,
                reasoning="Test",
                strategy_used=VotingStrategy.BALANCED,
            ),
        ]

        # Execute votes - should not raise exception
        result = await agent_run_service._execute_votes(
            decisions=decisions,
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify both votes were attempted
        assert agent_run_service.voting_service.vote_on_proposal.call_count == 2

        # Verify both attestations were attempted despite first failure
        assert agent_run_service.safe_service.create_eas_attestation.call_count == 2

        # Verify execution completed with both decisions
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_dry_run_skips_attestation(self, agent_run_service):
        """Test that dry run mode skips both voting and attestation.

        Importance: Ensures test mode doesn't create any on-chain transactions.
        """
        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test",
            strategy_used=VotingStrategy.BALANCED,
        )

        # Execute in dry run mode
        result = await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=True,
            run_id="test_run_123",
        )

        # Verify no vote was attempted
        agent_run_service.voting_service.vote_on_proposal.assert_not_called()

        # Verify no attestation was attempted
        agent_run_service.safe_service.create_eas_attestation.assert_not_called()

        # Verify decisions returned unchanged
        assert result == [decision]

    @pytest.mark.asyncio
    async def test_attestation_exception_handling(self, agent_run_service):
        """Test that exceptions during attestation are caught and logged.

        Importance: Ensures unexpected errors don't crash the agent run.
        """
        # Mock vote success
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": "0xabc123"}},
            }
        )

        # Mock attestation raising exception
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test",
            strategy_used=VotingStrategy.BALANCED,
        )

        # Execute votes - should not raise exception
        result = await agent_run_service._execute_votes(
            decisions=[decision],
            space_id="test.eth",
            dry_run=False,
            run_id="test_run_123",
        )

        # Verify vote was attempted
        assert agent_run_service.voting_service.vote_on_proposal.called

        # Verify execution completed despite exception
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_error_messages_are_actionable_config_missing(
        self, agent_run_service, caplog
    ):
        """Test that configuration error messages include actionable guidance.

        Importance: Verifies error messages help users resolve configuration issues
        without requiring code inspection or external documentation.
        """
        import logging

        # Mock vote success
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": "0xabc123"}},
            }
        )

        # Mock attestation failure with config error
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={
                "success": False,
                "error": "EAS_CONTRACT_ADDRESS not configured"
            }
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test",
            strategy_used=VotingStrategy.BALANCED,
        )

        with caplog.at_level(logging.ERROR):
            await agent_run_service._execute_votes(
                decisions=[decision],
                space_id="test.eth",
                dry_run=False,
                run_id="test_run_123",
            )

        # Verify error message contains actionable information
        error_logs = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_logs) > 0

        error_msg = error_logs[0]
        # Must contain the environment variable name
        assert "EAS_CONTRACT_ADDRESS" in error_msg
        # Must contain example or instruction
        assert "Set EAS_CONTRACT_ADDRESS" in error_msg or "0x42000000" in error_msg
        # Must contain proposal context
        assert "proposal=test-proposal" in error_msg

    @pytest.mark.asyncio
    async def test_error_messages_include_debugging_context(
        self, agent_run_service, caplog
    ):
        """Test that error messages include debugging context for investigation.

        Importance: Ensures operators have sufficient information to debug issues
        from log files without needing to reproduce the error.
        """
        import logging

        # Mock vote success
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": "0xabc123"}},
            }
        )

        # Mock generic attestation failure
        agent_run_service.safe_service.create_eas_attestation = AsyncMock(
            return_value={
                "success": False,
                "error": "Network timeout"
            }
        )

        decision = VoteDecision(
            proposal_id="test-proposal",
            vote=VoteType.FOR,
            confidence=0.85,
            reasoning="Test",
            strategy_used=VotingStrategy.BALANCED,
        )

        with caplog.at_level(logging.ERROR):
            await agent_run_service._execute_votes(
                decisions=[decision],
                space_id="test.eth",
                dry_run=False,
                run_id="test_run_123",
            )

        error_logs = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_logs) > 0

        error_msg = error_logs[0]
        # Must contain proposal ID for tracing
        assert "proposal=" in error_msg and "test-proposal" in error_msg
        # Must contain space ID for context
        assert "space=" in error_msg and "test.eth" in error_msg
        # Must suggest checking RPC or network
        assert "RPC" in error_msg or "timeout" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_error_messages_distinguish_failure_types(
        self, agent_run_service, caplog
    ):
        """Test that different failure types produce distinct error messages.

        Importance: Users should be able to quickly identify the type of problem
        from the error message without analyzing generic stack traces.
        """
        import logging

        # Mock vote success
        agent_run_service.voting_service.vote_on_proposal = AsyncMock(
            return_value={
                "success": True,
                "submission_result": {"success": True, "response": {"id": "0xabc123"}},
            }
        )

        # Test different error types
        error_scenarios = [
            ("EAS_SCHEMA_UID not set", ["schema", "EAS_SCHEMA_UID"]),
            ("insufficient funds for gas", ["insufficient", "fund", "ETH"]),
            ("nonce too low", ["nonce", "pending", "Safe Transaction Service"]),
            ("timeout", ["timeout", "RPC_URL"])
        ]

        for error_message, expected_keywords in error_scenarios:
            caplog.clear()

            agent_run_service.safe_service.create_eas_attestation = AsyncMock(
                return_value={"success": False, "error": error_message}
            )

            decision = VoteDecision(
                proposal_id="test-proposal",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="Test",
                strategy_used=VotingStrategy.BALANCED,
            )

            with caplog.at_level(logging.ERROR):
                await agent_run_service._execute_votes(
                    decisions=[decision],
                    space_id="test.eth",
                    dry_run=False,
                    run_id="test_run_123",
                )

            error_logs = [record.message for record in caplog.records if record.levelname == "ERROR"]
            assert len(error_logs) > 0

            error_msg = error_logs[0].lower()
            # Verify error message contains expected keywords for this error type
            keywords_found = [kw for kw in expected_keywords if kw.lower() in error_msg]
            assert len(keywords_found) > 0, \
                f"Error message for '{error_message}' should contain at least one of {expected_keywords}"


class TestCheckpointStateSimplification:
    """Test that checkpoint state no longer includes pending attestations."""

    @pytest.mark.asyncio
    async def test_checkpoint_excludes_pending_attestations(
        self, agent_run_service, state_manager
    ):
        """Test that saved checkpoint does not contain pending_attestations field.

        Importance: Verifies queue infrastructure fully removed from state persistence.
        """
        response = AgentRunResponse(
            space_id="test.eth",
            proposals_analyzed=2,
            votes_cast=[],
            user_preferences_applied=True,
            execution_time=1.5,
            errors=[],
        )

        await agent_run_service._save_checkpoint_state(response)

        # Load checkpoint and verify structure
        checkpoint = await state_manager.load_checkpoint("agent_checkpoint_test.eth")

        assert checkpoint is not None
        assert "pending_attestations" not in checkpoint
        assert "space_id" in checkpoint
        assert "votes_cast" in checkpoint
```

### Integration Test
**File**: `backend/tests/test_agent_run_integration.py`

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_run_with_immediate_attestation_integration(httpx_mock):
    """Integration test: complete agent run with immediate attestations.

    Importance: Validates end-to-end flow with immediate attestation after each vote,
    ensuring all components work together correctly.
    """
    # Mock Snapshot API for proposal fetch
    httpx_mock.add_response(
        method="POST",
        url="https://hub.snapshot.org/graphql",
        json={
            "data": {
                "proposals": [
                    AgentTestFixtures.create_sample_proposal().__dict__,
                ]
            }
        },
    )

    # Create agent run service with mocked dependencies
    agent_service = AgentRunService()

    # Mock SafeService attestation to succeed
    agent_service.safe_service.create_eas_attestation = AsyncMock(
        return_value={"success": True, "safe_tx_hash": "0xtest123"}
    )

    # Execute agent run
    request = AgentRunRequest(space_id="test.eth", dry_run=False)
    response = await agent_service.execute_agent_run(request)

    # Verify attestations were created immediately (no queue)
    assert agent_service.safe_service.create_eas_attestation.call_count > 0

    # Verify response successful
    assert len(response.votes_cast) > 0
    assert len(response.errors) == 0
```

### Success Criteria

#### Automated Verification:
- [ ] All new tests pass: `uv run pytest backend/tests/test_agent_run_service.py::TestImmediateAttestationFlow -v`
- [ ] Error message tests pass: `uv run pytest backend/tests/test_agent_run_service.py::TestImmediateAttestationFlow::test_error_messages -v -k "error_message"`
- [ ] Checkpoint test passes: `uv run pytest backend/tests/test_agent_run_service.py::TestCheckpointStateSimplification -v`
- [ ] Integration test passes: `uv run pytest backend/tests/test_agent_run_integration.py::test_agent_run_with_immediate_attestation_integration -v`
- [ ] No queue-related tests remain: `rg "test.*queue.*attestation|test.*pending.*attestation" backend/tests/` returns no results
- [ ] Overall test coverage maintained: `uv run pytest --cov=backend/services/agent_run_service --cov-report=term-missing` shows >90%

#### Manual Verification:
- [ ] Test names clearly describe what is being tested
- [ ] Test importance documented in docstrings
- [ ] All edge cases covered (vote success, vote failure, attestation failure, exceptions, dry run)
- [ ] Mock assertions verify correct method calls and arguments
- [ ] Error messages include environment variable names for config issues
- [ ] Error messages include remediation steps or links to relevant services
- [ ] Error messages include full context (proposal ID, space, agent address, config values)

---

## Phase 4: Documentation Updates

### Overview
Update all documentation to reflect immediate attestation workflow and remove queue references.

### Changes Required

#### 1. Update AGENTS.md
**File**: `AGENTS.md`

**Section**: "Autonomous Voting Agent" workflow description (around line 290-300)

**Changes**:
- Remove mentions of attestation queue
- Remove mentions of pending attestation processing
- Remove mentions of retry mechanism
- Add description of immediate attestation
- Note that failed attestations are logged but not retried

**Before** (example):
```markdown
### Autonomous Voting Agent
The application includes a comprehensive autonomous voting system:
- **Queue Processing**: Processes pending attestations from previous runs
- **Retry Mechanism**: Retries failed attestations up to 3 times
- **Checkpoint State**: Persists pending attestations across runs
```

**After**:
```markdown
### Autonomous Voting Agent
The application includes a comprehensive autonomous voting system:
- **Immediate Attestation**: Creates on-chain attestations immediately after each vote
- **Audit Trail**: All voting decisions attested on-chain for transparency
- **Graceful Degradation**: Attestation failures logged but do not block voting
- **Simplified State**: No queue state management or retry logic
```

#### 2. Update Architecture Documentation
**File**: `AGENTS.md`

**Section**: "Backend Architecture" service descriptions (around line 85-90)

**Changes**:
- Update agent_run_service description to reflect streamlined architecture
- Note immediate attestation as part of vote execution
- Remove any mention of queue processing or retry logic

**Before** (example):
```markdown
- `agent_run_service.py`: Orchestrates autonomous voting workflow with attestation queue
```

**After**:
```markdown
- `agent_run_service.py`: Orchestrates autonomous voting workflow with immediate attestation
```

#### 3. Update Code Comments
**File**: `backend/services/agent_run_service.py`

**Changes**:
- Update docstring of `_execute_votes()` method (around line 735) to mention immediate attestation
- Remove any comments referencing queue or pending attestations
- Add comments explaining immediate attestation flow

**Updated docstring**:
```python
async def _execute_votes(
    self, decisions: List[VoteDecision], space_id: str, dry_run: bool, run_id: str
) -> List[VoteDecision]:
    """Execute votes for the given decisions with immediate attestation.

    For each vote decision:
    1. Submit vote to Snapshot
    2. Immediately create EAS attestation (regardless of vote success)
    3. Mark activity completed if attestation succeeds
    4. Log errors but continue with remaining votes

    Args:
        decisions: List of VoteDecision objects to execute
        space_id: The space ID where votes will be cast
        dry_run: If True, simulate voting without actual execution
        run_id: Unique identifier for this agent run

    Returns:
        List of successfully executed VoteDecision objects

    Raises:
        VoteExecutionError: When vote execution fails critically

    Note:
        - In dry run mode, returns decisions without execution
        - Attestation failures are logged but do not block voting
        - Each attestation is attempted immediately after vote submission
    """
```

### Success Criteria

#### Automated Verification:
- [ ] No mentions of queue in AGENTS.md: `rg -i "queue.*attestation|attestation.*queue" AGENTS.md` returns no results
- [ ] No mentions of pending attestations: `rg "pending.*attestation" AGENTS.md` returns no results
- [ ] No mentions of retry in attestation context: `rg "retry.*attestation|attestation.*retry" AGENTS.md` returns no results
- [ ] Immediate attestation mentioned: `rg -i "immediate.*attestation" AGENTS.md` returns results

#### Manual Verification:
- [ ] Documentation accurately describes new immediate attestation flow
- [ ] No contradictory information about queue or retries
- [ ] Code comments are clear and accurate
- [ ] Workflow descriptions match actual implementation

---

## Logging and Error Handling

### Scope

This section applies **only to the immediate attestation implementation** added in this migration. Existing error messages in SafeService, VotingService, and other components are out of scope unless they directly relate to attestation failures.

### Error Message Standards

All error messages for immediate attestation must be **precise, actionable, and include debugging context**. Follow these principles:

1. **State the Problem Clearly**: What failed and why
2. **Provide Context**: Include relevant IDs, addresses, and state
3. **Suggest Solutions**: What the user should check or fix
4. **Include Debugging Info**: Configuration values, network details, etc.

### Logging Requirements

Following Pearl-compliant logging standards, all attestation operations must emit structured logs:

**Success Logs** (INFO level):
```python
self.pearl_logger.info(
    f"Creating immediate EAS attestation (proposal={decision.proposal_id}, "
    f"vote_succeeded={vote_succeeded}, vote_id={vote_id or 'None'}, "
    f"agent={self.voting_service.account.address}, space={space_id})"
)

self.pearl_logger.info(
    f"Successfully created EAS attestation (proposal={decision.proposal_id}, "
    f"safe_tx_hash={safe_tx_hash}, schema_uid={config.EAS_SCHEMA_UID})"
)

self.pearl_logger.info(
    f"Marked daily activity as completed (tx_hash={safe_tx_hash}, "
    f"proposal={decision.proposal_id})"
)
```

**Failure Logs with Actionable Guidance** (ERROR level):

```python
# Configuration errors - provide clear remediation steps
if not config.EAS_CONTRACT_ADDRESS:
    self.pearl_logger.error(
        f"Cannot create EAS attestation: EAS_CONTRACT_ADDRESS not configured. "
        f"Set EAS_CONTRACT_ADDRESS environment variable to the EAS contract address "
        f"on Base network (0x4200000000000000000000000000000000000021). "
        f"proposal={decision.proposal_id}, space={space_id}"
    )
elif not config.EAS_SCHEMA_UID:
    self.pearl_logger.error(
        f"Cannot create EAS attestation: EAS_SCHEMA_UID not configured. "
        f"Set EAS_SCHEMA_UID environment variable to your registered schema UID. "
        f"Register schema at https://base.easscan.org/schema/create. "
        f"proposal={decision.proposal_id}, space={space_id}"
    )
elif not config.SAFE_CONTRACT_ADDRESSES:
    self.pearl_logger.error(
        f"Cannot create EAS attestation: SAFE_CONTRACT_ADDRESSES not configured. "
        f"Set SAFE_CONTRACT_ADDRESSES environment variable with Safe address JSON. "
        f"Example: SAFE_CONTRACT_ADDRESSES='{{\"base\":\"0xYourSafeAddress\"}}'. "
        f"proposal={decision.proposal_id}, space={space_id}"
    )

# Network/blockchain errors - include debugging context
elif "timeout" in error_msg.lower():
    self.pearl_logger.error(
        f"EAS attestation failed due to RPC timeout. "
        f"Check RPC_URL is responsive: {config.RPC_URL}. "
        f"Try increasing timeout or switching RPC provider. "
        f"proposal={decision.proposal_id}, safe_tx_hash={safe_tx_hash or 'None'}, "
        f"error={error_msg}"
    )
elif "insufficient funds" in error_msg.lower():
    self.pearl_logger.error(
        f"EAS attestation failed: Safe has insufficient ETH for gas. "
        f"Fund Safe address with ETH: {config.SAFE_CONTRACT_ADDRESSES.get('base')}. "
        f"Check balance at https://basescan.org/address/{config.SAFE_CONTRACT_ADDRESSES.get('base')}. "
        f"proposal={decision.proposal_id}, error={error_msg}"
    )
elif "nonce" in error_msg.lower():
    self.pearl_logger.error(
        f"EAS attestation failed due to nonce mismatch. "
        f"This may indicate a pending transaction or concurrent execution. "
        f"Check Safe Transaction Service for pending txs: "
        f"https://safe-transaction-base.safe.global/api/v1/safes/{config.SAFE_CONTRACT_ADDRESSES.get('base')}/multisig-transactions/. "
        f"proposal={decision.proposal_id}, error={error_msg}"
    )

# Generic failure with full context
else:
    self.pearl_logger.error(
        f"Failed to create EAS attestation (proposal={decision.proposal_id}, "
        f"space={space_id}, agent={self.voting_service.account.address}, "
        f"eas_contract={config.EAS_CONTRACT_ADDRESS}, "
        f"schema_uid={config.EAS_SCHEMA_UID}, "
        f"rpc_url={config.RPC_URL}, error={error_msg}). "
        f"Check configuration and network connectivity."
    )
```

**Exception Logs with Debugging Context** (EXCEPTION level):
```python
self.pearl_logger.exception(
    f"Unexpected exception during immediate attestation. "
    f"proposal={decision.proposal_id}, space={space_id}, "
    f"vote_id={vote_id or 'None'}, agent={self.voting_service.account.address}, "
    f"eas_contract={config.EAS_CONTRACT_ADDRESS or 'NOT_SET'}, "
    f"schema_uid={config.EAS_SCHEMA_UID or 'NOT_SET'}, "
    f"safe_address={config.SAFE_CONTRACT_ADDRESSES.get('base') if config.SAFE_CONTRACT_ADDRESSES else 'NOT_SET'}. "
    f"Exception: {str(e)}"
)
```

### Error Message Examples

**Bad Error Message** (vague, not actionable):
```python
self.pearl_logger.error("Attestation failed")
```

**Good Error Message** (precise, actionable, contextual):
```python
self.pearl_logger.error(
    f"EAS attestation failed: Missing schema UID configuration. "
    f"Set EAS_SCHEMA_UID environment variable to your registered schema UID. "
    f"Register schema at https://base.easscan.org/schema/create with fields: "
    f"agent (address), space_id (string), proposal_id (string), vote_choice (uint8), "
    f"snapshot_sig (bytes32), timestamp (uint256), run_id (string), confidence (uint8). "
    f"proposal={decision.proposal_id}, space={space_id}"
)
```

### Error Handling Strategy

**Non-Blocking Errors**:
- Attestation creation failures do NOT raise exceptions
- Execution continues with remaining votes
- All errors logged with full context for debugging and auditing
- Each error log includes:
  - What failed (operation)
  - Why it failed (root cause)
  - How to fix it (remediation steps)
  - Debugging context (IDs, addresses, config values)

**Configuration Errors**:
- Missing EAS config (contract address, schema UID) logged with setup instructions
- SafeService handles missing config gracefully with clear error messages
- Agent run continues without attestations if config missing
- Error messages include:
  - Which config variable is missing
  - What value to set (with examples)
  - Where to get the value (links to Base Sepolia explorer, Safe UI, etc.)

**Network/Blockchain Errors**:
- Transient errors (timeouts, network issues) logged with RPC URL and suggestions
- Insufficient funds errors include Safe address and funding instructions
- Nonce errors include Safe Transaction Service URL for investigation
- No retry mechanism - failures logged for manual investigation
- Error messages include:
  - Network/chain being used
  - RPC endpoint URL
  - Transaction details if available
  - Links to block explorers or transaction services

**Safe/Multisig Errors**:
- Safe address validation errors include correct format examples
- Threshold/signer errors include current Safe configuration
- Pending transaction conflicts include Safe Transaction Service link
- Error messages include:
  - Safe address being used
  - Current Safe configuration (owners, threshold)
  - Link to Safe UI for manual inspection

### Graceful Degradation

When attestation fails:
1. Log detailed error message with:
   - Proposal context (ID, space, agent)
   - Failure reason with specific error details
   - Configuration state (what's set, what's missing)
   - Suggested remediation steps with examples
   - Links to relevant tools/explorers
2. Continue processing remaining proposals
3. Complete agent run successfully
4. Return standard AgentRunResponse (no attestation results in response)

When EAS config missing:
1. SafeService logs warning:
   ```python
   self.pearl_logger.warning(
       f"EAS attestation disabled: Configuration incomplete. "
       f"EAS_CONTRACT_ADDRESS: {'SET' if config.EAS_CONTRACT_ADDRESS else 'MISSING (set to 0x4200000000000000000000000000000000000021 for Base)'}, "
       f"EAS_SCHEMA_UID: {'SET' if config.EAS_SCHEMA_UID else 'MISSING (register schema at https://base.easscan.org)'}, "
       f"SAFE_CONTRACT_ADDRESSES: {'SET' if config.SAFE_CONTRACT_ADDRESSES else 'MISSING (set Safe address JSON)'}. "
       f"Agent will continue without on-chain attestations."
   )
   ```
2. Returns `{"success": False, "error": "EAS configuration incomplete. See logs for required environment variables."}`
3. Agent run logs failure but continues
4. User receives actionable guidance via logs with exact config variable names and example values

### Error Testing Requirements

Tests must verify error messages are actionable:
- Assert error logs contain configuration variable names
- Assert error logs include remediation steps or links
- Assert error logs include all relevant context (IDs, addresses)
- Assert error messages distinguish between different failure modes
- Verify users can resolve issues from error message alone

---

## Testing Strategy

### Unit Test Coverage

**Required Tests**:
- ✅ Immediate attestation after successful vote
- ✅ Immediate attestation after failed vote (with placeholder signature)
- ✅ Attestation failure does not block subsequent votes
- ✅ Exception during attestation caught and logged
- ✅ Dry run mode skips attestation
- ✅ Checkpoint excludes pending_attestations field
- ✅ EASAttestationData constructed with correct fields
- ✅ Activity marked completed when attestation succeeds

**Mock Strategy**:
- Mock `VotingService.vote_on_proposal()` for vote outcomes
- Mock `SafeService.create_eas_attestation()` for attestation results
- Mock `ActivityService.mark_activity_completed()` for activity tracking
- Use `AsyncMock` for all async methods
- Verify mock calls with assertions on arguments

### Integration Test Coverage

**Required Tests**:
- ✅ End-to-end agent run with immediate attestations
- ✅ Multiple proposals processed with attestations
- ✅ Mixed success/failure scenarios

**Integration Test Setup**:
- Use `httpx_mock` for Snapshot API responses
- Mock only external APIs (Snapshot, blockchain)
- Allow real service interactions internally
- Verify attestations created for each vote

### Manual Testing Checklist

**Mock Mode Testing**:
1. Set `MOCK_MODE=true` in environment
2. Run agent: `curl -X POST http://localhost:8716/agent-run -H "Content-Type: application/json" -d '{"space_id":"test.eth","dry_run":false}'`
3. Verify logs show "MOCK/DRY_RUN: skipping on-chain attestation"
4. Verify stub UID returned: `0x0000...`
5. Verify no actual blockchain transactions

**Dry Run Testing**:
1. Run agent with dry_run=true: `curl -X POST http://localhost:8716/agent-run -H "Content-Type: application/json" -d '{"space_id":"test.eth","dry_run":true}'`
2. Verify logs show "Dry run mode - simulating vote execution"
3. Verify no vote submissions to Snapshot
4. Verify no attestation attempts
5. Verify decisions returned in response

**Real Testnet Testing**:
1. Configure Base testnet RPC and Safe address
2. Fund Safe with testnet ETH
3. Run agent on testnet space
4. Verify attestation tx appears in Safe Transaction Service
5. Verify attestation on-chain via BaseScan
6. Verify activity marked completed
7. Check logs for successful attestation messages


## Migration Notes

### No Breaking Changes

**API Compatibility**:
- No changes to API endpoints or request/response schemas
- `POST /agent-run` works identically
- Frontend requires no updates
- Existing API consumers unaffected

**Configuration Compatibility**:
- Same environment variables required
- No new config needed for basic operation
- Attestation behavior transparent to users

### Deployment Strategy

**Zero-Downtime Deployment**:
1. Deploy new code with immediate attestation
2. Old checkpoints with pending_attestations ignored
3. New runs create immediate attestations
4. No migration script needed

**Rollback Plan**:
1. If issues arise, deploy previous version
2. System reverts to queue-based attestation
3. No data loss (checkpoints preserved)
4. Re-deploy after fixing issues

### Monitoring Post-Deployment

**Key Metrics**:
- Attestation success rate (log analysis)
- Average run time per proposal
- Attestation failure reasons
- Activity completion rate

**Log Analysis**:
- Monitor for "Failed to create EAS attestation" errors
- Check for exceptions during attestation
- Verify "Successfully created EAS attestation" frequency
- Track activity completion markers

---

## Risks and Mitigations

### Risk 1: Longer Run Time Per Proposal

**Impact**: Medium - Attestations add latency to each proposal processing

**Probability**: High - This is expected behavior

**Mitigation**:
- Accept longer run time as trade-off for simpler architecture
- Document expected run time increase
- Consider parallel attestations in future enhancement
- Monitor run time metrics

### Risk 2: Config Mis-Set (Missing EAS/Safe Settings)

**Impact**: Medium - Attestations will fail if config missing

**Probability**: Low - Config validated at service initialization

**Mitigation**:
- SafeService validates config early
- Clear error messages in logs
- Agent run continues without attestations
- Health endpoint reports config status
- Documentation updated with required config

### Risk 3: Audit Trail Gaps (Failed Attestations)

**Impact**: Low - Some votes may not have on-chain attestations

**Probability**: Medium - Network/blockchain issues can cause failures

**Mitigation**:
- All attestation attempts logged with details
- Failed attestations visible in logs for investigation
- Consider manual retry process for critical votes
- Future enhancement: retry mechanism

### Risk 4: Attestation Failures Accumulating Over Time

**Impact**: Low - Without retry, some attestations never succeed

**Probability**: Medium - Transient failures will occur

**Mitigation**:
- Monitor attestation failure rate
- Alert on high failure rates
- Manual investigation and correction process
- Consider future retry mechanism if failure rate too high

---

## References

### Original Code Analysis
- `backend/services/agent_run_service.py`: Lines 36, 159-160, 735-870, 927-1161
- `backend/models.py`: Lines 982-1048 (EASAttestationData)
- `backend/services/safe_service.py`: Lines 552-649 (create_eas_attestation)

### Related Specifications
- `specs/logging.md`: Pearl-compliant logging requirements
- `specs/error-handling.md`: Error handling patterns
- `specs/testing.md`: Testing strategies and coverage requirements
- `AGENTS.md`: Architecture overview and workflow documentation

### External References
- EAS Documentation: https://docs.attest.sh/
- Safe Transaction Service: https://safe-docs.safe.global/
- Snapshot API: https://docs.snapshot.box/

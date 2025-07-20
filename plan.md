# Implementation Plan: Agent Interface Layer (BAC-173)

## Overview

**Issue**: BAC-173 - Agent Interface Layer  
**Objective**: Implement core agent infrastructure for Pearl integration including state management, key handling, and blockchain integration.

This plan provides a comprehensive, TDD-driven approach to integrating Quorum AI with the Pearl platform while maintaining existing autonomous voting functionality.

## Priority Levels

- **P0 (Critical)**: Blocks Pearl deployment - must be done first
- **P1 (High)**: Core functionality - required for proper operation  
- **P2 (Medium)**: Important features - enhances reliability
- **P3 (Low)**: Nice-to-have - polish and optimization

## Implementation Status

### Completed Features ✅

#### P0: Signal Handling for Graceful Shutdowns (BAC-174)
- **Status**: ✅ IMPLEMENTED (2024-01-XX)
- **Files**: 
  - `backend/services/signal_handler.py` - Core signal handling and shutdown coordination
  - `backend/tests/test_signal_handler.py` - Comprehensive test suite (14 tests passing)
- **Integration**: Integrated into main.py and all services
- **Notes**: Full TDD implementation with 100% test coverage

#### P0: State Persistence with STORE_PATH (BAC-174) 
- **Status**: ✅ IMPLEMENTED (2024-01-XX)
- **Files**:
  - `backend/services/state_manager.py` - Atomic state persistence with corruption recovery
  - `backend/tests/test_state_manager.py` - Comprehensive test suite (12 tests passing)
- **Integration**: Integrated into UserPreferencesService and AgentRunService
- **Notes**: Supports atomic writes, corruption detection, backups, and version migration

### Pending Features ❌

#### P1: Private Key Management (BAC-175)
- Secure key file reading with permission checks
- Key manager service for centralized key handling
- Support for multiple key formats

#### P1: Safe Contract Integration (BAC-176)
- Multi-chain Safe support
- Parse SAFE_CONTRACT_ADDRESSES environment variable
- Integrate with existing voting flow

#### P2: Withdrawal Mode (BAC-177)
- Emergency fund recovery mechanism
- Integration with Safe contracts
- Withdrawal service implementation

#### P3: Enhanced Health Checks
- Comprehensive service health monitoring
- Pearl-compliant health reporting
- Service dependency health tracking

#### P3: Retry and Circuit Breaker Patterns
- External service reliability improvements
- Configurable retry policies
- Circuit breaker for failing services

## Features and Tasks

### P0: Signal Handling for Graceful Shutdowns (BAC-174) ✅

#### Task 1: Create Signal Handler Service
**Acceptance Criteria**:
- Service captures SIGTERM and SIGINT signals
- Triggers graceful shutdown of all services
- Prevents new operations during shutdown
- Logs shutdown events with Pearl format

**Test Cases**:
1. `test_signal_handler_captures_sigterm` - Verify SIGTERM triggers shutdown
2. `test_signal_handler_captures_sigint` - Verify SIGINT triggers shutdown  
3. `test_signal_handler_prevents_new_operations` - Ensure no new work during shutdown
4. `test_signal_handler_logs_events` - Verify Pearl-compliant logging

**Implementation Steps**:
1. Create `signal_handler_service.py` with asyncio signal handling
2. Implement shutdown event propagation system
3. Add is_shutting_down flag to prevent new operations
4. Integrate Pearl logging for all signal events

**Integration Points**:
- All services must register with signal handler
- Main application loop must respect shutdown flag

#### Task 2: Add Shutdown Methods to Services
**Acceptance Criteria**:
- Each service has async shutdown() method
- Services save state before shutdown
- Resources are properly released
- Shutdown completes within 30 seconds

**Test Cases**:
1. `test_agent_run_service_shutdown` - Verify clean agent shutdown
2. `test_voting_service_shutdown` - Ensure pending votes are saved
3. `test_snapshot_service_shutdown` - Verify cache persistence
4. `test_shutdown_timeout` - Ensure 30-second limit is enforced

**Implementation Steps**:
1. Add abstract base service with shutdown interface
2. Implement shutdown in each service
3. Add timeout decorator for 30-second limit
4. Create shutdown orchestrator in main.py

**Integration Points**:
- Signal handler calls shutdown orchestrator
- Each service must extend base service

### P0: State Persistence with STORE_PATH (BAC-174) ✅

#### Task 3: Create State Manager Service ✅
**Acceptance Criteria**:
- Centralized state management using STORE_PATH
- Atomic writes with corruption detection
- State recovery after crashes
- Version migration support

**Test Cases**:
1. `test_state_manager_uses_store_path` - Verify correct path usage
2. `test_state_atomic_writes` - Ensure no partial writes
3. `test_state_corruption_recovery` - Handle corrupted files
4. `test_state_version_migration` - Support schema changes

**Implementation Steps**:
1. Create `state_manager_service.py` with atomic file operations
2. Implement JSON schema validation
3. Add backup/restore mechanism
4. Create migration framework for version changes

**Integration Points**:
- Replace direct file I/O in all services
- UserPreferencesService migrates to state manager

#### Task 4: Implement State Checkpointing
**Acceptance Criteria**:
- Periodic state saves during long operations
- Checkpoint before risky operations
- Recovery from last checkpoint
- Minimal performance impact

**Test Cases**:
1. `test_periodic_checkpointing` - Verify automatic saves
2. `test_checkpoint_before_voting` - Save before blockchain ops
3. `test_checkpoint_recovery` - Restore from checkpoint
4. `test_checkpoint_performance` - Under 100ms overhead

**Implementation Steps**:
1. Add checkpoint() method to state manager
2. Implement time-based auto-checkpointing
3. Add checkpoint triggers in critical paths
4. Create recovery logic in startup

**Integration Points**:
- AgentRunService triggers checkpoints
- VotingService checkpoints before transactions

### P1: Private Key File Reading (BAC-175)

#### Task 5: Implement Secure Key Reader
**Acceptance Criteria**:
- Read ethereum_private_key.txt from working directory
- Validate file permissions (600 only)
- Secure key handling in memory
- Clear error messages without exposing paths

**Test Cases**:
1. `test_key_reader_finds_file` - Locate key file correctly
2. `test_key_reader_validates_permissions` - Reject insecure files
3. `test_key_reader_validates_content` - Check key format
4. `test_key_reader_secure_errors` - No sensitive data in errors

**Implementation Steps**:
1. Create `key_manager_service.py` with secure file reading
2. Implement permission validation (stat.S_IRUSR only)
3. Add key format validation (ethereum private key)
4. Create secure error messages

**Integration Points**:
- VotingService uses key manager for signing
- Remove hardcoded private key logic

#### Task 6: Integrate Key Manager with Services
**Acceptance Criteria**:
- VotingService uses key manager
- Lazy loading of private key
- Key caching with timeout
- Memory clearing after use

**Test Cases**:
1. `test_voting_service_uses_key_manager` - Integration test
2. `test_key_lazy_loading` - Load only when needed
3. `test_key_cache_timeout` - Expire after 5 minutes
4. `test_key_memory_clearing` - Secure cleanup

**Implementation Steps**:
1. Refactor VotingService to use key manager
2. Implement lazy loading pattern
3. Add TTL cache with secure storage
4. Use context manager for memory cleanup

**Integration Points**:
- VotingService constructor accepts key manager
- Configuration updated for key file path

### P1: Safe Contract Address Integration (BAC-176)

#### Task 7: Parse Multi-Chain Safe Addresses
**Acceptance Criteria**:
- Parse SAFE_CONTRACT_ADDRESSES environment variable
- Support chain_id:address format
- Validate ethereum addresses
- Default handling for missing chains

**Test Cases**:
1. `test_parse_safe_addresses_format` - Parse "1:0x123,42161:0x456"
2. `test_validate_ethereum_addresses` - Check address format
3. `test_handle_missing_chains` - Graceful degradation
4. `test_parse_malformed_input` - Error handling

**Implementation Steps**:
1. Add safe_addresses parser to config.py
2. Create SafeAddress dataclass with validation
3. Implement chain-specific lookup method
4. Add configuration validation on startup

**Integration Points**:
- VotingService uses Safe addresses
- Configuration validates on startup

#### Task 8: Integrate Safe with Voting Service
**Acceptance Criteria**:
- VotingService uses Safe for transactions
- Multi-chain support maintained
- Fallback to direct execution
- Transaction monitoring

**Test Cases**:
1. `test_voting_via_safe` - Execute through Safe
2. `test_multi_chain_safe_support` - Different chains
3. `test_safe_fallback` - Direct execution backup
4. `test_safe_transaction_monitoring` - Status tracking

**Implementation Steps**:
1. Update VotingService with Safe integration
2. Implement Safe SDK or contract calls
3. Add transaction queue management
4. Create monitoring for Safe transactions

**Integration Points**:
- VotingService enhanced with Safe support
- State manager tracks pending Safe transactions

### P2: Withdrawal Mode Implementation (BAC-177)

#### Task 9: Create Withdrawal Service
**Acceptance Criteria**:
- Detect WITHDRAWAL_MODE=true
- List all invested positions
- Calculate withdrawal amounts
- Execute withdrawal transactions

**Test Cases**:
1. `test_withdrawal_mode_detection` - Check env variable
2. `test_list_invested_positions` - Find all investments
3. `test_calculate_withdrawals` - Compute amounts
4. `test_execute_withdrawals` - Process transactions

**Implementation Steps**:
1. Create `withdrawal_service.py`
2. Implement position discovery logic
3. Add withdrawal calculation engine
4. Create transaction execution flow

**Integration Points**:
- Main.py checks withdrawal mode
- Uses VotingService for transactions

#### Task 10: Integrate Withdrawal with Agent
**Acceptance Criteria**:
- Agent skips voting in withdrawal mode
- Withdrawal runs instead of voting
- Progress tracking and reporting
- Safe integration for withdrawals

**Test Cases**:
1. `test_agent_withdrawal_mode` - Skip normal flow
2. `test_withdrawal_progress_tracking` - Monitor status
3. `test_withdrawal_via_safe` - Use Safe contracts
4. `test_withdrawal_completion` - Verify success

**Implementation Steps**:
1. Modify main.py for withdrawal mode
2. Create withdrawal orchestrator
3. Add progress tracking to state
4. Integrate with Safe for execution

**Integration Points**:
- Main application flow modification
- State manager tracks withdrawal progress

### P3: Performance and Reliability

#### Task 11: Implement Health Checks
**Acceptance Criteria**:
- Periodic self-health checks
- Service availability monitoring
- Resource usage tracking
- Pearl-compliant health reporting

**Test Cases**:
1. `test_health_check_all_services` - Monitor availability
2. `test_resource_monitoring` - Track memory/CPU
3. `test_health_reporting` - Pearl format output
4. `test_unhealthy_service_handling` - Recovery logic

**Implementation Steps**:
1. Add health check endpoint to each service
2. Create health monitor service
3. Implement resource tracking
4. Add Pearl health report generation

**Integration Points**:
- All services implement health interface
- Main loop includes health monitoring

#### Task 12: Add Retry and Circuit Breaker
**Acceptance Criteria**:
- Retry failed operations with backoff
- Circuit breaker for external services
- Configurable retry policies
- Failure tracking and reporting

**Test Cases**:
1. `test_retry_with_exponential_backoff` - Retry logic
2. `test_circuit_breaker_triggers` - Open on failures
3. `test_circuit_breaker_recovery` - Half-open state
4. `test_failure_reporting` - Track patterns

**Implementation Steps**:
1. Create retry decorator with policies
2. Implement circuit breaker pattern
3. Add failure tracking to state
4. Create failure analysis reports

**Integration Points**:
- All external service calls use retry
- Circuit breaker on Snapshot/blockchain calls

## Risk Assessment

### High Risks
1. **Signal Handling Complexity**: 
   - **Risk**: Async signal handling is complex
   - **Mitigation**: Extensive testing, timeout limits

2. **State Corruption**:
   - **Risk**: Corrupted state prevents startup
   - **Mitigation**: Backup/restore, validation, checksums

3. **Private Key Security**:
   - **Risk**: Key exposure via logs or errors
   - **Mitigation**: Secure coding practices, audit

### Medium Risks
1. **Safe Integration Delays**:
   - **Risk**: Safe transactions slower than direct
   - **Mitigation**: Async processing, timeout handling

2. **Multi-Chain Complexity**:
   - **Risk**: Chain-specific issues
   - **Mitigation**: Comprehensive testing per chain

### Low Risks
1. **Performance Overhead**:
   - **Risk**: New services slow down agent
   - **Mitigation**: Performance testing, optimization

## Success Criteria

- [ ] Agent handles SIGTERM gracefully with state preservation
- [ ] All state persisted to STORE_PATH with corruption recovery
- [ ] Private key read from ethereum_private_key.txt securely
- [ ] Safe addresses parsed and used for transactions
- [ ] Withdrawal mode executes when enabled
- [ ] Zero data loss during shutdowns
- [ ] All tests pass with >90% coverage
- [ ] Pearl compliance verified in test deployment
- [ ] Performance within 10% of baseline
- [ ] Security audit passed for key handling

## Resource Estimates

### Development Time
- **P0 Tasks**: 5-6 days
- **P1 Tasks**: 4-5 days  
- **P2 Tasks**: 2-3 days
- **P3 Tasks**: 2-3 days
- **Testing & Integration**: 3-4 days
- **Total**: 16-21 days

### Team Requirements
- 1 Senior Developer (full-time)
- 1 QA Engineer (50% allocation)
- Security review (2 days)
- Pearl platform access for testing

### Dependencies
- Pearl documentation and test environment
- Safe SDK or contract ABIs
- Multi-chain test infrastructure
- Security audit resources

## Implementation Order

1. **Week 1**: P0 Signal handling and state persistence
2. **Week 2**: P1 Key management and Safe integration  
3. **Week 3**: P2 Withdrawal mode and P3 enhancements
4. **Week 4**: Integration testing and Pearl deployment

This plan ensures systematic, test-driven development with minimal risk to existing functionality while achieving full Pearl platform compliance.
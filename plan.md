# Agent Interface Layer Implementation Plan

## Overview

**Linear Issue**: BAC-173 - Agent Interface Layer  
**Priority**: Urgent (P1)  
**Objective**: Implement core agent infrastructure for Pearl integration including state management, key handling, and blockchain integration.

This plan details the implementation of fundamental system-level integration requirements for Pearl platform compatibility, broken down into atomic, TDD-friendly tasks.

## Success Criteria

- [ ] Agent handles SIGTERM/SIGINT signals gracefully
- [ ] Agent recovers state after SIGKILL without corruption
- [ ] Private keys are loaded securely from `ethereum_private_key.txt`
- [ ] Safe contract addresses are parsed from environment
- [ ] Withdrawal mode can be triggered via environment variable
- [ ] All operations are logged in Pearl-compliant format
- [ ] State persistence works atomically with corruption recovery
- [ ] Multi-chain operations are supported

## Prioritized Features

### P0 - Critical Core Infrastructure

#### 1. Signal Handling & Graceful Shutdown (BAC-174)
Implement SIGKILL/SIGTERM signal handling for graceful shutdowns and state recovery.

**Task 1.1: Add Signal Handler Infrastructure**
- **Acceptance Criteria**: Application responds to SIGTERM/SIGINT by saving state before exit
- **Test Cases**:
  - `test_signal_handler_saves_state`: Verify state is saved when SIGTERM received
  - `test_signal_handler_completes_operations`: Verify in-flight operations complete
  - `test_signal_handler_timeout`: Verify forced shutdown after grace period
- **Implementation**:
  1. Create `backend/services/signal_handler.py`
  2. Add signal registration in `main.py` lifespan
  3. Implement graceful shutdown callback
  4. Add state save trigger on shutdown
- **Integration**: Integrates with FastAPI lifespan context

**Task 1.2: State Recovery After SIGKILL**
- **Acceptance Criteria**: Agent recovers last known state after unexpected termination
- **Test Cases**:
  - `test_state_recovery_after_crash`: Verify state loads correctly after simulated crash
  - `test_corrupted_state_recovery`: Verify fallback when state file is corrupted
  - `test_missing_state_initialization`: Verify clean start when no state exists
- **Implementation**:
  1. Create `backend/services/state_manager.py`
  2. Implement state validation and recovery logic
  3. Add startup state check in `main.py`
  4. Create state schema with versioning
- **Integration**: Called during application startup

#### 2. Centralized Key Management (BAC-175)
Implement secure private key file reading for blockchain access.

**Task 2.1: Create Key Manager Service**
- **Acceptance Criteria**: Single service manages all private key operations securely
- **Test Cases**:
  - `test_key_manager_loads_private_key`: Verify key loads from file
  - `test_key_manager_validates_format`: Verify invalid keys are rejected
  - `test_key_manager_file_permissions`: Verify security warnings for bad permissions
  - `test_key_manager_missing_file`: Verify appropriate error when file missing
- **Implementation**:
  1. Create `backend/services/key_manager.py`
  2. Implement secure file reading with validation
  3. Add caching to avoid repeated file reads
  4. Implement key format validation
- **Integration**: Replace direct file reads in voting_service, safe_service

**Task 2.2: Refactor Services to Use Key Manager**
- **Acceptance Criteria**: All services use centralized key management
- **Test Cases**:
  - `test_voting_service_uses_key_manager`: Verify voting service gets key from manager
  - `test_safe_service_uses_key_manager`: Verify safe service gets key from manager
  - `test_key_manager_dependency_injection`: Verify services receive key manager
- **Implementation**:
  1. Update `voting_service.py` to use KeyManager
  2. Update `safe_service.py` to use KeyManager
  3. Update `voter.py` and `voter_olas.py`
  4. Remove direct file reads
- **Integration**: Dependency injection in service initialization

### P1 - Safe Contract Integration

#### 3. Multi-Chain Safe Address Management (BAC-176)
Integrate Safe contract addresses for multi-chain operations.

**Task 3.1: Parse Safe Contract Addresses**
- **Acceptance Criteria**: Environment variable parsed into chain-specific addresses
- **Test Cases**:
  - `test_parse_safe_addresses_json`: Verify JSON parsing of addresses
  - `test_invalid_safe_address_format`: Verify error handling for malformed data
  - `test_missing_safe_addresses`: Verify graceful handling when not provided
- **Implementation**:
  1. Update `config.py` with SAFE_CONTRACT_ADDRESSES field
  2. Add JSON parsing with validation
  3. Create address mapping structure
  4. Add chain ID to address resolution
- **Integration**: Used by safe_service for multi-chain operations

**Task 3.2: Enhance Safe Service for Multi-Chain**
- **Acceptance Criteria**: Safe service handles operations across multiple chains
- **Test Cases**:
  - `test_safe_service_chain_selection`: Verify correct chain is selected
  - `test_safe_service_multi_chain_state`: Verify state tracked per chain
  - `test_safe_service_chain_fallback`: Verify fallback for unsupported chains
- **Implementation**:
  1. Update `safe_service.py` with chain routing
  2. Add per-chain RPC configuration
  3. Implement chain-specific transaction building
  4. Add multi-chain state tracking
- **Integration**: Used by voting and withdrawal operations

### P2 - Withdrawal Mode

#### 4. Withdrawal Mode Implementation (BAC-177)
Implement withdrawal mode for fund recovery via WITHDRAWAL_MODE environment variable.

**Task 4.1: Add Withdrawal Mode Detection**
- **Acceptance Criteria**: Agent detects withdrawal mode from environment
- **Test Cases**:
  - `test_withdrawal_mode_enabled`: Verify mode detected when env var true
  - `test_withdrawal_mode_disabled`: Verify normal operation when false/missing
  - `test_withdrawal_mode_logging`: Verify mode change is logged
- **Implementation**:
  1. Add WITHDRAWAL_MODE to `config.py`
  2. Create withdrawal mode check in `main.py`
  3. Add mode status to health endpoint
  4. Log mode on startup
- **Integration**: Affects agent_run_service behavior

**Task 4.2: Implement Fund Withdrawal Logic**
- **Acceptance Criteria**: Agent withdraws funds to Safe when in withdrawal mode
- **Test Cases**:
  - `test_withdrawal_identifies_funds`: Verify fund discovery across chains
  - `test_withdrawal_transaction_creation`: Verify correct withdrawal transactions
  - `test_withdrawal_safe_return`: Verify funds return to agent Safe
  - `test_withdrawal_error_recovery`: Verify handling of failed withdrawals
- **Implementation**:
  1. Create `backend/services/withdrawal_service.py`
  2. Implement fund discovery logic
  3. Add withdrawal transaction builder
  4. Integrate with safe_service
- **Integration**: Called instead of voting when mode enabled

### P3 - Enhanced Monitoring & Recovery

#### 5. State Persistence Framework
Extend state persistence beyond user preferences.

**Task 5.1: Create Comprehensive State Schema**
- **Acceptance Criteria**: All agent state is defined in versioned schema
- **Test Cases**:
  - `test_state_schema_validation`: Verify schema validates state data
  - `test_state_schema_migration`: Verify old versions upgrade correctly
  - `test_state_schema_defaults`: Verify missing fields get defaults
- **Implementation**:
  1. Define state schema in `models.py`
  2. Add version field for migrations
  3. Include: agent runs, pending votes, last check times
  4. Create migration logic
- **Integration**: Used by state_manager service

**Task 5.2: Implement Atomic State Operations**
- **Acceptance Criteria**: State saves are atomic with corruption recovery
- **Test Cases**:
  - `test_atomic_state_save`: Verify atomic writes with temp files
  - `test_concurrent_state_access`: Verify thread-safe operations
  - `test_state_backup_rotation`: Verify backup files are managed
- **Implementation**:
  1. Extend atomic write pattern from user_preferences
  2. Add file locking for concurrent access
  3. Implement backup rotation (keep last 3)
  4. Add corruption detection and recovery
- **Integration**: Used throughout application for state

#### 6. Pearl Platform Interface
Add Pearl-specific command processing and monitoring.

**Task 6.1: Add Pearl Command Endpoint**
- **Acceptance Criteria**: Pearl can send commands to agent via API
- **Test Cases**:
  - `test_pearl_command_vote`: Verify vote command processing
  - `test_pearl_command_status`: Verify status command returns state
  - `test_pearl_command_validation`: Verify invalid commands rejected
- **Implementation**:
  1. Add `/pearl/command` endpoint to `main.py`
  2. Create command schema in `models.py`
  3. Implement command router
  4. Add command logging
- **Integration**: New API endpoint for Pearl platform

**Task 6.2: Enhanced Health Monitoring**
- **Acceptance Criteria**: Health endpoint provides Pearl-required metrics
- **Test Cases**:
  - `test_health_includes_pearl_fields`: Verify Pearl fields in response
  - `test_health_performance`: Verify < 1 second response time
  - `test_health_during_operations`: Verify accurate during active work
- **Implementation**:
  1. Enhance `/health` endpoint
  2. Add: last activity, pending operations, mode status
  3. Include service health checks
  4. Add performance metrics
- **Integration**: Updates existing health endpoint

## Risk Assessment & Mitigation

### Technical Risks

1. **Signal Handling Complexity**
   - **Risk**: Platform differences in signal behavior
   - **Mitigation**: Use standard library signal module, test on target OS
   - **Fallback**: Implement polling-based shutdown if signals unreliable

2. **State Corruption During SIGKILL**
   - **Risk**: Partial writes leave corrupted state
   - **Mitigation**: Atomic writes with temp files, validation on load
   - **Fallback**: Multiple backup files with timestamps

3. **Private Key Security**
   - **Risk**: Key exposure through logs or memory dumps
   - **Mitigation**: Never log keys, validate file permissions, secure memory
   - **Fallback**: Support hardware wallet integration path

4. **Multi-Chain Complexity**
   - **Risk**: Chain-specific quirks cause failures
   - **Mitigation**: Comprehensive chain abstraction layer
   - **Fallback**: Limit initial support to well-tested chains

### Integration Risks

1. **Pearl Platform Changes**
   - **Risk**: Pearl API changes break integration
   - **Mitigation**: Version command interface, maintain compatibility
   - **Fallback**: Adapter pattern for version differences

2. **Existing Service Disruption**
   - **Risk**: Changes break current functionality
   - **Mitigation**: Interface layer pattern, extensive testing
   - **Fallback**: Feature flags for gradual rollout

## Resource Estimates

### Development Time (2 developers)
- **P0 Tasks**: 3-4 days (critical path)
- **P1 Tasks**: 2-3 days
- **P2 Tasks**: 2 days
- **P3 Tasks**: 2-3 days
- **Testing & Integration**: 2 days
- **Total**: 11-15 days

### Testing Requirements
- **Unit Tests**: ~50 new tests across all tasks
- **Integration Tests**: ~15 tests for service interactions
- **E2E Tests**: 5 tests for Pearl platform scenarios
- **Performance Tests**: Response time and resource usage

### Documentation
- **Technical Docs**: 2 days
- **Operational Guide**: 1 day
- **API Updates**: Automated from OpenAPI

## Implementation Order

1. **Week 1**: P0 tasks (signal handling, key management)
2. **Week 2**: P1 tasks (Safe integration) + P2 tasks (withdrawal)
3. **Week 3**: P3 tasks (monitoring) + testing + documentation

This order ensures critical infrastructure is in place first, followed by feature implementation, and finally enhanced monitoring and polish.
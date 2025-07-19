# Agent Interface Layer Implementation Plan

## Overview

**Linear Parent Issue**: BAC-173 - Agent Interface Layer  
**Objective**: Implement core agent infrastructure for Pearl integration including state management, key handling, and blockchain integration.

This implementation plan provides a comprehensive roadmap for integrating the Quorum AI agent with the Olas Pearl App store platform. The plan is structured for Test-Driven Development (TDD) with atomic tasks suitable for one red-green-refactor cycle each.

### Key Deliverables
1. Graceful shutdown with signal handling (SIGKILL/SIGTERM)
2. Centralized private key management system
3. Multi-chain Safe contract integration
4. Withdrawal mode for emergency fund recovery
5. Comprehensive state persistence and recovery

## Prioritized Feature List

### P0 - Critical Foundation (Week 1)

#### 1. Centralized Private Key Management (BAC-175)
**Priority**: P0 - Blocks all blockchain operations  
**Effort**: 1 day

##### Task 1.1: Create KeyManager Service
- **Acceptance Criteria**:
  - Service loads private key from `ethereum_private_key.txt`
  - Validates key format (64 hex characters)
  - Checks file permissions (must be 600)
  - Provides secure key access interface
  
- **Test Cases**:
  - `test_key_manager_loads_valid_key`: Verify successful key loading
  - `test_key_manager_validates_format`: Test hex format validation
  - `test_key_manager_checks_permissions`: Ensure permission verification
  - `test_key_manager_handles_missing_file`: Test graceful error handling
  - `test_key_manager_handles_invalid_key`: Test malformed key rejection
  
- **Implementation Steps**:
  1. Create `backend/services/key_manager.py`
  2. Implement file reading with permission checks
  3. Add key validation logic
  4. Create secure getter method
  5. Add Pearl-compliant logging
  
- **Integration Points**:
  - Used by `VotingService` for EIP-712 signatures
  - Used by `SafeService` for transaction signing
  - Configuration via `settings.key_file_path`

##### Task 1.2: Refactor Existing Services to Use KeyManager
- **Acceptance Criteria**:
  - Remove duplicate key loading from `safe_service.py`
  - Remove duplicate key loading from `voter_olas.py`
  - All services use centralized KeyManager
  - No regression in functionality
  
- **Test Cases**:
  - `test_safe_service_uses_key_manager`: Verify SafeService integration
  - `test_voting_service_uses_key_manager`: Verify VotingService integration
  - `test_key_manager_singleton_pattern`: Ensure single instance
  
- **Implementation Steps**:
  1. Update `SafeService.__init__` to inject KeyManager
  2. Update `VotingService.__init__` to inject KeyManager
  3. Remove hardcoded key loading logic
  4. Update service initialization in `main.py`

#### 2. Safe Contract Address Configuration (BAC-176)
**Priority**: P0 - Required for multi-chain support  
**Effort**: 0.5 days

##### Task 2.1: Enhance Configuration Parsing
- **Acceptance Criteria**:
  - Parse `SAFE_CONTRACT_ADDRESSES` environment variable
  - Support format: `ethereum:0x123...,gnosis:0x456...`
  - Validate Ethereum addresses
  - Handle missing chains gracefully
  
- **Test Cases**:
  - `test_config_parses_safe_addresses`: Test parsing logic
  - `test_config_validates_addresses`: Test address validation
  - `test_config_handles_malformed_input`: Test error cases
  - `test_config_provides_chain_mapping`: Test data structure
  
- **Implementation Steps**:
  1. Enhance `backend/config.py` parsing logic
  2. Add address validation using web3
  3. Create `SafeAddressMapping` type
  4. Add environment variable documentation

##### Task 2.2: Update SafeService for Dynamic Addresses
- **Acceptance Criteria**:
  - SafeService uses configured addresses per chain
  - Falls back gracefully if chain not configured
  - Logs address usage for debugging
  
- **Test Cases**:
  - `test_safe_service_uses_configured_addresses`: Verify address usage
  - `test_safe_service_handles_missing_chain`: Test fallback behavior
  - `test_safe_service_logs_address_selection`: Verify logging
  
- **Implementation Steps**:
  1. Update `SafeService.get_safe_address()` method
  2. Add chain-specific address lookup
  3. Implement fallback logic
  4. Add debug logging

#### 3. Signal Handling System (BAC-174)
**Priority**: P0 - Critical for production  
**Effort**: 2 days

##### Task 3.1: Create SignalHandler Service
- **Acceptance Criteria**:
  - Captures SIGTERM and SIGINT signals
  - Provides shutdown event for coordination
  - Implements 30-second timeout
  - Logs signal reception
  
- **Test Cases**:
  - `test_signal_handler_captures_sigterm`: Test SIGTERM handling
  - `test_signal_handler_captures_sigint`: Test SIGINT handling
  - `test_signal_handler_shutdown_event`: Test event propagation
  - `test_signal_handler_timeout`: Test 30-second timeout
  - `test_signal_handler_multiple_signals`: Test signal queuing
  
- **Implementation Steps**:
  1. Create `backend/services/signal_handler.py`
  2. Implement signal registration with asyncio
  3. Create shutdown event mechanism
  4. Add timeout logic
  5. Integrate Pearl logging

##### Task 3.2: Implement Graceful Shutdown in Services
- **Acceptance Criteria**:
  - All services implement `shutdown()` method
  - Long-running operations can be cancelled
  - State is saved before shutdown
  - Shutdown completes within timeout
  
- **Test Cases**:
  - `test_agent_run_service_graceful_shutdown`: Test agent run cancellation
  - `test_safe_service_transaction_rollback`: Test transaction safety
  - `test_voting_service_completes_active_vote`: Test vote completion
  - `test_all_services_shutdown_within_timeout`: Integration test
  
- **Implementation Steps**:
  1. Add `shutdown()` to base service interface
  2. Implement in `AgentRunService` with state save
  3. Implement in `SafeService` with transaction handling
  4. Implement in `VotingService` with vote completion
  5. Update `main.py` shutdown sequence

##### Task 3.3: Create StateManager for Persistence
- **Acceptance Criteria**:
  - Atomic save operations with temporary files
  - JSON serialization of service states
  - Corruption detection and recovery
  - Uses `STORE_PATH` environment variable
  
- **Test Cases**:
  - `test_state_manager_atomic_save`: Test atomic operations
  - `test_state_manager_corruption_recovery`: Test recovery logic
  - `test_state_manager_concurrent_access`: Test thread safety
  - `test_state_manager_serialization`: Test data serialization
  
- **Implementation Steps**:
  1. Create `backend/services/state_manager.py`
  2. Implement atomic file operations
  3. Add corruption detection
  4. Create recovery mechanism
  5. Add checkpoint system

### P1 - Core Integration (Week 2)

#### 4. Pearl Command Handler
**Priority**: P1 - Required for Pearl integration  
**Effort**: 1 day

##### Task 4.1: Create Command Processing System
- **Acceptance Criteria**:
  - Dedicated endpoint for Pearl commands
  - Command validation and routing
  - Structured response format
  - Error handling with clear messages
  
- **Test Cases**:
  - `test_command_handler_routing`: Test command dispatch
  - `test_command_handler_validation`: Test input validation
  - `test_command_handler_error_responses`: Test error cases
  - `test_command_handler_unknown_command`: Test fallback
  
- **Implementation Steps**:
  1. Create `backend/services/pearl_command_handler.py`
  2. Define command interface and types
  3. Implement routing logic
  4. Add validation layer
  5. Create API endpoint in `main.py`

##### Task 4.2: Implement Core Commands
- **Acceptance Criteria**:
  - `status` command returns service health
  - `run` command triggers agent execution
  - `stop` command initiates shutdown
  - `config` command shows configuration
  
- **Test Cases**:
  - `test_status_command_returns_health`: Test health reporting
  - `test_run_command_starts_agent`: Test agent execution
  - `test_stop_command_graceful_shutdown`: Test shutdown trigger
  - `test_config_command_shows_settings`: Test config display
  
- **Implementation Steps**:
  1. Implement status command with health checks
  2. Implement run command with AgentRunService
  3. Implement stop command with SignalHandler
  4. Implement config command with settings display

#### 5. Health Monitoring System
**Priority**: P1 - Required for production monitoring  
**Effort**: 1 day

##### Task 5.1: Create HealthMonitor Service
- **Acceptance Criteria**:
  - Tracks service status (running/stopped/error)
  - Monitors resource usage (memory/CPU)
  - Provides aggregated health status
  - Logs health metrics periodically
  
- **Test Cases**:
  - `test_health_monitor_tracks_services`: Test service tracking
  - `test_health_monitor_resource_metrics`: Test resource monitoring
  - `test_health_monitor_aggregation`: Test status aggregation
  - `test_health_monitor_periodic_logging`: Test logging behavior
  
- **Implementation Steps**:
  1. Create `backend/services/health_monitor.py`
  2. Implement service registry
  3. Add resource monitoring
  4. Create health aggregation logic
  5. Add periodic logging task

##### Task 5.2: Integrate Health Checks
- **Acceptance Criteria**:
  - All services register with HealthMonitor
  - Services report status changes
  - Health endpoint returns detailed status
  - Unhealthy services trigger alerts
  
- **Test Cases**:
  - `test_service_registration`: Test auto-registration
  - `test_service_status_updates`: Test status reporting
  - `test_health_endpoint_response`: Test API response
  - `test_unhealthy_service_alerts`: Test alert mechanism
  
- **Implementation Steps**:
  1. Add health registration to base service
  2. Update all services to report status
  3. Create `/health/detailed` endpoint
  4. Implement alert logging

### P2 - Advanced Features (Week 3)

#### 6. Withdrawal Mode Implementation (BAC-177)
**Priority**: P2 - Emergency recovery feature  
**Effort**: 2 days

##### Task 6.1: Create WithdrawalService
- **Acceptance Criteria**:
  - Detects `WITHDRAWAL_MODE=true` environment variable
  - Identifies invested funds across chains
  - Builds withdrawal transactions
  - Returns funds to Agent Safe
  
- **Test Cases**:
  - `test_withdrawal_mode_detection`: Test env var detection
  - `test_withdrawal_fund_identification`: Test fund discovery
  - `test_withdrawal_transaction_building`: Test tx creation
  - `test_withdrawal_multi_chain_support`: Test all chains
  
- **Implementation Steps**:
  1. Create `backend/services/withdrawal_service.py`
  2. Implement mode detection logic
  3. Add fund discovery across protocols
  4. Create withdrawal transaction builders
  5. Integrate with SafeService

##### Task 6.2: Implement Withdrawal Strategies
- **Acceptance Criteria**:
  - Support different DeFi protocols
  - Handle partial withdrawals
  - Implement retry logic for failures
  - Track withdrawal progress
  
- **Test Cases**:
  - `test_withdrawal_defi_protocols`: Test protocol support
  - `test_withdrawal_partial_amounts`: Test partial withdrawals
  - `test_withdrawal_retry_logic`: Test failure handling
  - `test_withdrawal_progress_tracking`: Test progress updates
  
- **Implementation Steps**:
  1. Define withdrawal strategy interface
  2. Implement protocol-specific strategies
  3. Add retry mechanism with backoff
  4. Create progress tracking system
  5. Add withdrawal activity logging

#### 7. Performance Optimization
**Priority**: P2 - Production readiness  
**Effort**: 1 day

##### Task 7.1: Implement Metrics Collection
- **Acceptance Criteria**:
  - Track operation timings
  - Monitor memory usage
  - Count API calls and errors
  - Export metrics for analysis
  
- **Test Cases**:
  - `test_metrics_timing_collection`: Test timing metrics
  - `test_metrics_memory_tracking`: Test memory monitoring
  - `test_metrics_error_counting`: Test error metrics
  - `test_metrics_export_format`: Test export functionality
  
- **Implementation Steps**:
  1. Create metrics collection framework
  2. Add timing decorators
  3. Implement memory tracking
  4. Create metrics aggregation
  5. Add export endpoint

##### Task 7.2: Optimize Critical Paths
- **Acceptance Criteria**:
  - Reduce startup time by 50%
  - Optimize database queries
  - Implement connection pooling
  - Add caching where appropriate
  
- **Test Cases**:
  - `test_startup_time_optimization`: Test startup speed
  - `test_query_optimization`: Test query performance
  - `test_connection_pooling`: Test pool efficiency
  - `test_cache_effectiveness`: Test cache hit rates
  
- **Implementation Steps**:
  1. Profile startup sequence
  2. Lazy-load non-critical services
  3. Optimize database queries
  4. Implement connection pools
  5. Add strategic caching

### P3 - Production Hardening (Week 4)

#### 8. Comprehensive Testing Suite
**Priority**: P3 - Quality assurance  
**Effort**: 2 days

##### Task 8.1: Integration Tests
- **Acceptance Criteria**:
  - Test complete agent lifecycle
  - Simulate Pearl platform environment
  - Test multi-chain scenarios
  - Verify error recovery
  
- **Test Cases**:
  - `test_agent_full_lifecycle`: End-to-end test
  - `test_pearl_environment_simulation`: Platform test
  - `test_multi_chain_operations`: Chain integration
  - `test_error_recovery_scenarios`: Failure handling
  
- **Implementation Steps**:
  1. Create integration test framework
  2. Mock Pearl environment
  3. Implement lifecycle tests
  4. Add failure injection
  5. Create test documentation

##### Task 8.2: Load and Stress Testing
- **Acceptance Criteria**:
  - Handle 100+ concurrent proposals
  - Process votes within SLA
  - Maintain stability under load
  - Graceful degradation
  
- **Test Cases**:
  - `test_concurrent_proposal_handling`: Load test
  - `test_vote_processing_sla`: Performance test
  - `test_system_stability`: Stress test
  - `test_graceful_degradation`: Overload test
  
- **Implementation Steps**:
  1. Create load testing framework
  2. Generate test data
  3. Implement performance tests
  4. Add monitoring
  5. Document results

## Risk Assessment

### High-Risk Areas

1. **Signal Handling Complexity**
   - **Risk**: Async coordination failures
   - **Mitigation**: Extensive testing, timeout mechanisms
   - **Contingency**: Manual shutdown procedures

2. **Private Key Security**
   - **Risk**: Key exposure or loss
   - **Mitigation**: Permission checks, secure storage
   - **Contingency**: Key rotation procedures

3. **State Corruption**
   - **Risk**: Data loss during shutdown
   - **Mitigation**: Atomic operations, checksums
   - **Contingency**: Recovery from backups

### Medium-Risk Areas

1. **Multi-Chain Failures**
   - **Risk**: Chain-specific issues
   - **Mitigation**: Fallback mechanisms
   - **Contingency**: Single-chain operation

2. **Performance Under Load**
   - **Risk**: Degraded performance
   - **Mitigation**: Load testing, optimization
   - **Contingency**: Rate limiting

## Success Criteria Checklist

### Technical Requirements
- [ ] All tests pass with >90% coverage
- [ ] Pearl-compliant logging throughout
- [ ] Graceful shutdown completes in <30 seconds
- [ ] Private key loaded securely
- [ ] Multi-chain Safe operations work
- [ ] Withdrawal mode functions correctly
- [ ] State persists across restarts
- [ ] Health monitoring active
- [ ] Metrics collected and exportable
- [ ] Load tests pass SLA requirements

### Integration Requirements
- [ ] Works in Pearl container environment
- [ ] Responds to Pearl commands
- [ ] Handles all signals properly
- [ ] Recovers from failures gracefully
- [ ] Maintains backward compatibility
- [ ] Documentation complete
- [ ] Deployment guide updated
- [ ] Monitoring alerts configured

### Production Readiness
- [ ] Security audit completed
- [ ] Performance benchmarks met
- [ ] Error handling comprehensive
- [ ] Logging provides full observability
- [ ] Recovery procedures documented
- [ ] Operator guide created
- [ ] Support runbook available

## Resource Estimates

### Development Time
- **P0 Features**: 5 days
- **P1 Features**: 2 days  
- **P2 Features**: 3 days
- **P3 Features**: 2 days
- **Total**: 12 days (2.5 weeks)

### Testing Time
- **Unit Tests**: Included in development
- **Integration Tests**: 2 days
- **Load Testing**: 1 day
- **UAT with Pearl**: 2 days
- **Total**: 5 days (1 week)

### Documentation
- **Technical Docs**: 1 day
- **Operator Guide**: 1 day
- **Total**: 2 days

**Project Total**: 19 days (~4 weeks)

## Notes

1. This plan follows TDD principles with tests defined before implementation
2. Each task is atomic and completable in one development cycle
3. Priority levels ensure critical functionality is delivered first
4. Integration points are clearly defined to avoid conflicts
5. Risk mitigation strategies are built into the plan
6. Resource estimates include buffer for unexpected issues
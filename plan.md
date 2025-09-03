# Implementation Plan

## Overview
Comprehensive verification and setup of the test environment prerequisites for Quorum AI testing as outlined in test-plan.md. This plan addresses identified configuration issues, missing components, and provides actionable tasks to ensure the environment is fully prepared for testing the autonomous voting agent functionality.

## Feature 1: Environment Configuration Alignment

#### Task 1.1: Synchronize Environment Variables Between Files
- Acceptance Criteria:
  * Backend .env file uses real OpenRouter API key from main .env
  * SNAPSHOT_GRAPHQL naming is consistent across files
  * Docker networking addresses use host.docker.internal where appropriate
- Test Cases:
  * Verify backend container can access OpenRouter API with configured key
- Integration Points:
  * Main .env and backend/.env synchronization
  * Docker container environment variable injection
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/backend/.env

#### Task 1.2: Update Attestation Tracker Address
- Acceptance Criteria:
  * ATTESTATION_TRACKER_ADDRESS matches latest local deployment
  * Address corresponds to chain ID 31337 for local Anvil
  * Configuration is consistent across all environment files
- Test Cases:
  * Verify contract exists at configured address on local testnet
- Integration Points:
  * Contract deployment output
  * Environment variable configuration
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/.env

## Feature 2: Test Data Structure Initialization

#### Task 2.1: Create Agent State File
- Acceptance Criteria:
  * agent_state.json exists with valid initial structure
  * File contains required fields for agent operation
  * Permissions allow read/write from Docker container
- Test Cases:
  * Verify file can be read and written by backend service
- Integration Points:
  * State management service
  * Agent run service
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/test-data/state/agent_state.json

#### Task 2.2: Create User Preferences File
- Acceptance Criteria:
  * user_preferences.json exists with default preferences
  * File structure matches backend expectations
  * Contains test DAO monitoring configuration
- Test Cases:
  * Verify preferences can be loaded by backend service
- Integration Points:
  * User preferences service
  * DAO monitoring configuration
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/test-data/state/user_preferences.json

#### Task 2.3: Create Deployment Configuration File
- Acceptance Criteria:
  * deployment.json contains contract deployment information
  * Includes attestation tracker address and deployment block
  * Documents network configuration used
- Test Cases:
  * Verify deployment information is accurate and readable
- Integration Points:
  * Contract deployment tracking
  * Test execution evidence
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/test-data/deployment.json

## Feature 3: Docker Environment Enhancement

#### Task 3.1: Add Anvil Service to Docker Compose
- Acceptance Criteria:
  * Anvil service defined in docker-compose.yml
  * Service configured with Base mainnet fork
  * Port 8545 exposed for RPC access
  * Proper network configuration for container communication
- Test Cases:
  * Verify Anvil container starts and is accessible from backend
- Integration Points:
  * Docker network bridge
  * Backend RPC configuration
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/docker-compose.yml

#### Task 3.2: Configure Container Network Access
- Acceptance Criteria:
  * Backend can access Anvil via Docker network
  * Backend can reach external APIs (Snapshot, OpenRouter)
  * Frontend can communicate with backend API
- Test Cases:
  * Test connectivity from backend container to all required endpoints
- Integration Points:
  * Docker network configuration
  * Service discovery
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/docker-compose.yml

## Feature 4: Contract Deployment Automation

#### Task 4.1: Enhance Deployment Script
- Acceptance Criteria:
  * Script correctly identifies chain ID (31337 vs 8453)
  * Automatically updates environment with deployed address
  * Provides clear deployment status output
- Test Cases:
  * Test script successfully deploys and updates configuration
- Integration Points:
  * Foundry forge deployment
  * Environment variable management
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/contracts/deploy_local.sh

#### Task 4.2: Create Anvil Startup Script
- Acceptance Criteria:
  * Script starts Anvil with Base mainnet fork
  * Configures correct chain ID and test accounts
  * Provides persistent state option for testing
- Test Cases:
  * Verify Anvil starts with expected configuration
- Integration Points:
  * Local blockchain service
  * Test account management
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/scripts/start-anvil.sh

## Feature 5: Testing Infrastructure Validation

#### Task 5.1: Create Environment Validation Script
- Acceptance Criteria:
  * Checks all required environment variables
  * Validates API key formats and connectivity
  * Tests RPC endpoint accessibility
  * Verifies contract deployment status
- Test Cases:
  * Script correctly identifies configuration issues
- Integration Points:
  * All environment dependencies
  * External service endpoints
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/scripts/validate-test-env.sh

#### Task 5.2: Create Test Execution Helper
- Acceptance Criteria:
  * Script executes test steps from test-plan.md
  * Captures evidence for each test step
  * Generates test execution report
- Test Cases:
  * Script successfully runs through all test scenarios
- Integration Points:
  * Backend API endpoints
  * Log file monitoring
  * Contract interaction
- Files to Modify/Create:
  * /Users/max/code/quorum-ai/scripts/run-test-suite.sh

## Success Criteria
- [ ] Environment variables synchronized and consistent across all configuration files
- [ ] OpenRouter API key properly configured and accessible from backend container
- [ ] Test data directory structure complete with all required JSON files
- [ ] Attestation Tracker contract deployed to local testnet with correct address configuration
- [ ] Docker Compose includes Anvil service with proper networking
- [ ] Backend container can access local Anvil, Snapshot API, and OpenRouter API
- [ ] Deployment and validation scripts created and functional
- [ ] All prerequisites from test-plan.md satisfied and verified
- [ ] Test execution can proceed without configuration issues
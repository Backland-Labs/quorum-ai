# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-09-08

### Added
- **Continuous Integration**: GitHub Actions workflow for cross-platform binary builds
  - Automated building of agent_runner binaries for macOS and Windows (x64/ARM64)
  - PyInstaller integration for standalone executable creation
  - Automatic upload to GitHub releases and artifacts
- **EAS Schema Management**: Automated schema registration and validation scripts
- **Contract Deployment**: Mainnet deployment scripts with environment configuration
- **Smart Contract Infrastructure**: Complete AttestationTracker and QuorumStaking contract system
  - AttestationTracker.sol: EAS-based vote attestation tracking with IQuorumTracker interface
  - QuorumStaking.sol: Token activity monitoring with configurable liveness ratios
  - Foundry deployment scripts and comprehensive test suites
  - Multi-chain deployment support (Base, Ethereum, Gnosis, Mode)
- **Frontend UI Enhancements**:
  - Instructions tab and dedicated page in navigation system
  - Streamlined Dashboard navigation (replaced 'Organizations' label)
  - Removed confidence/success rate cards for simplified metrics display
  - Complete removal of unused Proposals/Activity tabs and tab infrastructure
- **AI Agent Architecture Improvements**:
  - Separated voting and summarization agents for better modularity (#180)
  - Enhanced AI reasoning integration with decision data
  - Improved agent orchestration and error handling
- **Repository Organization**:
  - Dedicated test-artifacts/ directory for organized development files
  - Comprehensive CLAUDE.md documentation for AI assistant context
  - Enhanced development tooling with ast-grep integration
- **Docker & Deployment**:
  - Combined Docker container implementation for frontend and backend
  - Improved containerization with proper environment setup
  - Enhanced Dockerfile with security improvements (removed API key logging)

### Changed
- **AttestationTracker Contract**: Refactored from AttestationTrackerFixed to standardized AttestationTracker
- **EAS Interface Integration**: Updated contract interface to match deployed EAS attestation standards
- **Base RPC Rate Limiting**: Added 1-second delays to prevent 429 Too Many Requests errors
- **CI/CD Pipeline**: Enhanced testing and deployment automation with standardized contract usage
- **Blockchain Integration Fixes**: Resolved signature validation issues in EAS attestation
- **Frontend Architecture**: Complete tab system removal and navigation simplification
- **User Interface**: Removed blacklisted/whitelisted proposers UI from settings page
- **AI Decision Making**: Enhanced summary section with AI reasoning from decision data
- **Development Workflow**: Improved Docker entrypoint with graceful shutdown handling

### Fixed
- **EAS Delegated Attestation**: Resolved EIP-712 signature parameter validation issues
- **AttestationTracker Interface**: Fixed contract method calls to match deployed interface
- **CI Test Integration**: Updated tests to use standard AttestationTracker.sol contract
- **Signature Generation**: Improved signature extraction and validation for blockchain transactions
- **EAS Integration**: Fixed attestation validation by properly capturing Snapshot vote IDs
- **Blockchain Signatures**: Resolved signature format issues in contract interactions
- **Environment Handling**: Corrected empty string validation in env_helper.py
- **Container Security**: Removed API key exposure in container logging
- **Build Process**: Various Docker and container configuration improvements

### Removed
- **UI Complexity**: Eliminated unused tab components and navigation complexity
- **Deprecated Metrics**: Removed confidence and success rate cards from dashboard
- **Legacy Code**: Cleaned up remaining tab infrastructure and unused components

## [0.5.0] - 2025-07-23
### Added
- EAS (Ethereum Attestation Service) integration for on-chain vote attestation
- Complete SafeService implementation with multi-chain support (Ethereum, Gnosis, Base, Mode, Celo)
- EAS contract ABI and attestation creation functionality
- Multi-chain Safe wallet configuration and transaction support
- Enhanced VoteDecision model with attestation tracking fields
- EASAttestationData model for structured attestation records
- Comprehensive blockchain specification documentation
- Environment validation for EAS and multi-chain configuration
- Dedicated test suite for EAS attestation and SafeService operations

### Changed
- Enhanced voting service with EAS attestation integration
- Updated agent run service to track attestation status
- Improved configuration with multi-chain RPC endpoints and Safe addresses
- Enhanced README with EAS configuration and deployment instructions

## [0.4.0] - 2025-07-20
### Added
- Pearl-compliant health check endpoint for monitoring agent status (BAC-178)
- State persistence and recovery functionality for agent lifecycle management
- State transition tracking with fast transition detection
- Graceful shutdown signal handling (SIGTERM/SIGINT)
- Pearl-compliant structured logging to local files
- Comprehensive test coverage for health check and state management

### Changed
- Enhanced configuration with health check parameters (port, path, thresholds)
- Improved agent run logging with Pearl-compliant format

## [0.3.0] - 2025-07-20
### Added
- Agent Interface Layer for Pearl Platform integration (BAC-173)
- Standardized governor ABI system for DAO voting
- Comprehensive agent run system implementation

### Changed
- Applied code quality improvements to Pearl logging migration
- Consolidated validation methods in ModelValidationHelper

## [0.2.0] - 2025-07-17
### Added
- Snapshot GraphQL integration for spaces, proposals, and votes (BAC-152)
- Snapshot API service with comprehensive GraphQL queries
- AI summarization support for Snapshot proposals (BAC-157)
- Snapshot-specific Pydantic models and data structures
- Agent-specific models VoteDecision and AgentState (BAC-135)
- Claude Code GitHub Workflow for automated CI/CD

### Changed
- Updated AI service for voting decision making (BAC-138)
- Updated config.py for Olas Agent Architecture (BAC-134)
- Split voter_olas.py into three focused services for better modularity

### Removed
- Removed all Tally-specific code and dependencies (BAC-155)
- Removed 1,100+ lines of unused infrastructure code

## [0.1.0] - 2025-07-08
### Added
- Initial project setup with FastAPI backend and SvelteKit frontend
- Docker and Docker Compose configuration for development
- PostgreSQL and Redis service integration
- Basic proposal management endpoints
- Top voters endpoint (GET /proposals/{id}/top-voters) with caching
- ProposalVoter data models for top voters feature (BAC-126)
- TopVoters component with proposal detail pages (BAC-129)
- Health check endpoint for service monitoring
- Vote history tracking with has_voted() method (BAC-145)
- Proposal fetching for specific DAOs with governor IDs (BAC-146)

### Changed
- Transformed Tally Service for autonomous agent operation (BAC-137)

### Fixed
- Docker service healthcheck and port configuration issues

[Unreleased]: https://github.com/quorum-ai/quorum-ai/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/quorum-ai/quorum-ai/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/quorum-ai/quorum-ai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/quorum-ai/quorum-ai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/quorum-ai/quorum-ai/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/quorum-ai/quorum-ai/releases/tag/v0.1.0

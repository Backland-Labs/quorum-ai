# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/quorum-ai/quorum-ai/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/quorum-ai/quorum-ai/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/quorum-ai/quorum-ai/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/quorum-ai/quorum-ai/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/quorum-ai/quorum-ai/releases/tag/v0.1.0
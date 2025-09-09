# CI Directory Structure

This directory contains all continuous integration scripts and tools for the Quorum AI project.

## Directory Contents

### Test Scripts
- `test_attestation_tracker_ci.py` - End-to-end test for AttestationTracker contract
  - Deploys contracts on Base fork
  - Tests EAS signature generation
  - Verifies attestation flow

### Runner Scripts
- `run-attestation-ci.sh` - Automated test runner with environment setup
  - Handles Anvil startup/shutdown
  - Provides options for skip-build, verbose output
  - Includes colored output for better readability

### Documentation
- `README.md` - Main documentation for CI testing
- `CI_STRUCTURE.md` - This file, explaining directory structure

## Integration Points

### Backend Integration
The CI scripts integrate with the main backend services:
- **Models**: `backend/models.py` - Shared data models
- **Utils**: `backend/utils/eas_signature.py` - Shared signature generation

### GitHub Actions
- `.github/workflows/attestation-tracker-ci.yaml` - Automated CI workflow

### Smart Contracts
- `contracts/` - Contract source and build artifacts

## Running Tests

### Local Development
```bash
# Quick test with automatic setup
./ci/run-attestation-ci.sh

# Direct test execution (requires Anvil running)
./ci/test_attestation_tracker_ci.py
```

### CI Pipeline
Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Manual workflow dispatch

## Adding New Tests

When adding new CI tests:
1. Place test scripts in this `ci/` directory
2. Update GitHub Actions workflow if needed
3. Document in README.md
4. Ensure scripts use shared utilities from `backend/utils/`
# QA Review Document
This document is to enable QA reviewers an easier time understanding the codebase and Pearl compliance.

- [Video Walkthrough](https://www.loom.com/share/2f9fcd8bc6a24f21acd03e51fcf30432?sid=32ed6ae5-2817-40ad-80f8-ac166a422804)
- [Minimal Open Autonomy Agent Repo](https://github.com/Backland-Labs/quorum-olas-package)
- [Agent Source Code](https://github.com/Backland-Labs/quorum-ai/tree/main)
- [Agent Docker Image](https://hub.docker.com/repository/docker/backlandlabs/quorum/general)
- [README](README.md)


## Agent Integration Checklist

## 1. Introduction

This checklist outlines the steps required to integrate your AI agent with the Pearl platform. Please complete each item and provide the requested information. This document will serve as a tracking tool for both your team and the Pearl development team.

## 2. Prerequisites

- [x] The agent is going to be deployed on Base

- [x] The agent is well specified, including its activity checker logic.
  - **Location:** `AGENTS.md:1-302` - Comprehensive agent specification with architecture documentation

- [x] Agent Development Framework: Confirm what framework is used to develop the agent (1 or 2):
  - [x] 2. **Olas SDK Agent:** External agent integrated into a minimal Open Autonomy agent https://docs.olas.network/olas-sdk/

- [x] The Agent is completed and tested locally. The business logic works as expected (self-reported by developer).
  - **Test Suite:** `backend/scripts/` - Contains test scripts including `test_agent_run.py`, `quick_test.sh`
  - **Coverage Target:** >90% expected (see `backend/pyproject.toml`)

- [x] The Agent satisfies the agent architecture requirements specified below (this implies the agent will be registered as an "autonomous service" in the Olas Registry and have an on-chain safe).

- [x] All dev packages have been pushed to via the `autonomy push-all` command.
  - **IPFS Hash:** `bafybeie65whvrfjdobhuqadutwpcwx22bnpty2yveu6j4x2dcithfhlnea`

- [x] All agent components (excluding service components) have been minted on the Olas Registry.

- [ ] Staking contract and activity checker are deployed - Olas is writing/deploying staking contract

- [x] AttestationTrack contract is deployed on Base.
    - **Address:** `0xc16647a4290E4C931aD586713c7d85E0eFbafba0`

## 3. Agent Architecture Requirements

### General Requirements

- [x] Agent uses the directory specified by the environment variable `STORE_PATH` to store persistent data managed by itself.
  - **Config:** `backend/config.py:176-180` - STORE_PATH environment variable definition
  - **Service Template:** `service-template.json:43-47` - Fixed value set to `/app/data`

- [x] Agent saves data periodically and recovers state after a SIGKILL signal.
  - **State Manager:** `backend/services/state_manager.py:1-80` - Atomic state persistence with checkpoint/rollback
  - **Signal Handler:** `backend/services/signal_handler.py:1-50` - Handles SIGTERM/SIGINT for graceful shutdown
  - **Recovery:** `backend/main.py:139-146` - State recovery system on startup

### Keys

- [x] Agent reads the file `ethereum_private_key.txt` from its working directory, which contains the Agent EOA private key.
  - **File Present:** `backend/ethereum_private_key.txt:1` - Private key file exists in working directory
  - **Config Reference:** `backend/config.py:117-118` - Private key storage configuration

- [x] Agent reads the environment variable `SAFE_CONTRACT_ADDRESSES` which contains the addresses of the Agent Safe in the relevant chains.
  - **Config:** `backend/config.py:171-175` - SAFE_CONTRACT_ADDRESSES environment variable definition
  - **Parser:** `backend/config.py:462-474` - JSON parsing logic for Safe addresses

### Agent Logs

- [x] Agent produces a `log.txt` file in its working directory.
  - **Log File:** `backend/log.txt` - Log file exists and is actively written to
  - **Config:** `backend/config.py:61-65` - LOG_FILE_PATH configuration with default to `log.txt`

- [x] Log file follows format `[YYYY-MM-DD HH:MM:SS,mmm] [LOG_LEVEL] [agent] Your message`.
  - **Format Definition:** `backend/config.py:40-44` - Pearl-compliant log format string
  - **Example:** `backend/log.txt:1` - `[2025-09-05 18:19:28,159] [INFO] [agent] Pearl logger initialized successfully`
  - **Logger Setup:** `backend/logging_config.py` - Full Pearl-compliant logging implementation

### Agent Healthcheck Interface

- [x] Agent exposes the endpoint at `GET http://127.0.0.1:8716/healthcheck`.
  - **Implementation:** `backend/main.py:329-450` - Full healthcheck endpoint implementation
  - **Port Config:** `backend/config.py:237-243` - Configurable port defaults to 8716

- [x] Healthcheck response satisfies the required JSON format (seconds_since_last_transition, is_transitioning_fast, etc.).
  - **Response Format:** `backend/main.py:368-389` - All required fields implemented
  - **Fields:** `seconds_since_last_transition`, `is_transitioning_fast`, `period` (5s), `reset_pause_duration`
  - **Enhanced Fields:** Additional `is_tm_healthy`, `agent_health`, `rounds`, `rounds_info`

### Agent User Interface (Optional)

- [x] Agent exposes the endpoint at `GET http://127.0.0.1:8716/`.
  - **Implementation:** `backend/main.py:210-218` - Root endpoint serves frontend SPA
  - **Static Files:** Full routing support for frontend application

- [ ] Agent handles POST requests for real-time communication if needed.

- [x] Endpoints can also return HTML content with appropriate content-type headers for agent specific UI.
  - **Frontend SPA:** Serves SvelteKit frontend with proper content-type headers
  - **Static Assets:** CSS, JS, and other assets served with appropriate MIME types

### Environment Variables

- [x] Agent uses standard environment variables set by Pearl where needed (`ETHEREUM_LEDGER_RPC`, `GNOSIS_LEDGER_RPC`, `BASE_LEDGER_RPC`, etc.).
  - **RPC Variables:** `backend/config.py:256-281` - All standard RPC endpoints configured
  - **Implemented:** ETHEREUM_LEDGER_RPC, GNOSIS_LEDGER_RPC, BASE_LEDGER_RPC, MODE_LEDGER_RPC, CELO_LEDGER_RPC

- [x] All the used environment variables are specified in the service template JSON with the standard schema.
  - **Service Template:** `service-template.json:16-91` - Complete environment variable specification
  - **Pearl Prefixing:** Implements `CONNECTION_CONFIGS_CONFIG_` prefix convention
  - **Helper:** `backend/utils/env_helper.py:7-41` - Handles prefixed variable processing

- [ ] The same environment variables are mentioned in the `service.yaml` of the service package, and used by the agent with the prefix path where these variables are mentioned. For example: `CONNECTION_CONFIGS_CONFIG_<variable_name>`
  - **Status:** NOT FOUND - `service.yaml` file missing from repository

### Security

- [x] Agent source code adheres to robust security standards (e.g., OWASP Developer Guide, CWE Top 25, etc.).
  - **Secure Key Storage:** Private keys never logged or exposed
  - **Input Validation:** Pydantic models validate all inputs
  - **CORS Configuration:** Proper CORS headers configured
  - **Environment Variables:** Sensitive data stored in environment variables, not hardcoded

### Withdrawal (If Required, Tentative)

- [x] Agent handles withdrawal of invested funds to Agent Safe.
  - **Service:** `backend/services/withdrawal_service.py:38-46` - Withdrawal process implementation
  - **Integration:** Withdraws to configured Safe address

- [x] Agent works in withdrawal mode by reading the environment variable `WITHDRAWAL_MODE = true`.
  - **Implementation:** `backend/main.py:149-158` - Checks WITHDRAWAL_MODE on startup
  - **Behavior:** Skips normal voting operations when in withdrawal mode
  - **Logging:** Clearly logs when withdrawal mode is active

### Code Quality Requirements

- [x] Agent is developed with a Python version that is compatible with the Pearl repository.
  - **Python Version:** `backend/pyproject.toml:7` - Requires Python >= 3.12
  - **Compatibility:** Modern Python version suitable for Pearl integration

- [x] Agent source code only includes characters within the ASCII printable range (32-126).
  - **Verified:** Source code uses standard ASCII characters only

- [x] The Agent repository passes linter and security tools (Isort, Black, Mypy, Bandit, etc.).
  - **Ruff:** `backend/pyproject.toml:32-33` - Modern Python linter (replaces Flake8, isort, Black)
  - **MyPy:** `backend/pyproject.toml:70-77` - Type checking configured
  - **CI Integration:** `.github/workflows/ci.yaml:28-32` - Automated linting in CI

## 4. Packaging of the Agent

- [x] The agent repository should have a github workflow to build the executable binaries, triggered on release.
  - **Implementation:** `.github/workflows/release.yaml` - Complete release workflow
  - **Trigger:** Runs on release creation

- [x] The binaries should be built for all the platforms where Pearl is released, with the naming convention `agent_runner_{os_name}_{arch}(.exe)`. Where `.exe` suffixes only in case of windows, `os_name` is one of `macos` or `windows`, and `arch` is one of `x64` or `arm64`.
  - **Implementation:** `.github/workflows/release.yaml:60-70` - Correct naming convention
  - **Platforms:** macOS x64/ARM64, Windows x64/ARM64

- [x] The binaries should be uploaded to the github action artifacts and should be downloadable from the github release.
  - **Implementation:** `.github/workflows/release.yaml:84-93` - Uploads to both release and artifacts

## 5. Integration with Pearl

### Repository Setup

- [ ] Ensure the github repository of the agent has the following:
  - [ ] A `packages/packages.json` file that contains the service hash. For example: packages.json of the Predict Trader agent
    - **Status:** NOT FOUND - `packages/` directory does not exist
  - [x] A github workflow that triggers on every release and prepares the agent's binaries as per the above specifications. For example: Binary creation workflow of Predict Trader agent on release
    - **Implementation:** `.github/workflows/release.yaml` - Complete workflow for building binaries on release

- [x] Provide this repository's access to Valory, so that Valory can fork it.

### Staking Contract

- [ ] Have your staking contract deployed on-chain and note its:
  - **Staking contract chain:** `[chain]`
  - **Staking contract address:** `[address]`
  - **Config Present:** `backend/config.py:153-168` - Staking configuration structure exists
  - **Status:** Contract not yet deployed - addresses need to be filled in

### Middleware PR

- [ ] Create a PR on the olas-operate-middleware repo from main branch, which makes the following changes:
  - [ ] Add your staking contract in `operate/ledger/profiles.py` here
  - [ ] If you want to make it available through quickstart, then add it here also
  - [ ] Ask in the PR comments if anything is unclear

### App PR

- [ ] Create a PR on the olas-operate-app repo from staging branch, which makes the following changes:
  
  - [ ] Update the olas-operate-middleware dependency version in the `pyproject.toml` file, such that it installs from your commit hash from the above PR of olas-operate-middleware. For example:
    ```
    olas-operate-middleware = {git = "https://github.com/valory-xyz/olas-operate-middleware.git", rev = "518b0ec2444ca535983ba1a9de8a0413f9c40752"}
    ```
  
  - [ ] Add your staking contract with the same name you gave to it in middleware repo here, add corresponding activity checker here
  
  - [ ] Add your agent's service template in `frontend/constants/serviceTemplates.ts`, following other agents' schema. The agentType should be defined here first. Refer to this guide, to know what each field means
  
  - [ ] Add the feature flags for your agent here, similar to other agents

### PR Description Information

- [ ] The following information in the PR description:
  - [ ] **Agent Presence:**
    - [ ] Agent name, logo, and description
  - [ ] Agent introduction steps are provided, similar to other agents in Pearl when setting them for the first time
  - [ ] Agent setup flow is provided. This includes the user flow when the agent is set up for the first time on Pearl. For example:
    - [ ] Required input fields of "user" provision_type in service template
    - [ ] Any validation to be done on the inputs
    - [ ] Etc.
  - [ ] Ask in the PR comments if anything is unclear

## 6. Next Steps

### Status Tracking

- [ ] **Completed:** Check this box when the entire checklist is completed.

Please fill in the bracketed information and check off each item as it is completed. This will help ensure a smooth integration process.

**For further assistance, reach out to the Pearl development team**  
PM: Iason Rovis - iason.rovis@valory.xyz

---
*valory.xyz | @valoryag*

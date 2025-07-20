# Olas SDK Agent Technical Specification

## Overview

This document defines the technical requirements for implementing an autonomous agent compatible with the Olas SDK. Agents can be built with any framework and integrated into the Olas Protocol.

[Docs](https://docs.olas.network/olas-sdk/)

## Agent Architecture

### Agent Type
- **Category**: Olas SDK Agent (external agent wrapped in minimal Open Autonomy agent)
- **Deployment**: Docker container or standalone binary
- **Supported Chains**: Ethereum, Arbitrum, Base, Celo, Gnosis, Mode, Optimism, Polygon

## Docker Requirements

### Container Specifications

#### Required Docker Directives
- **ENTRYPOINT**: Must specify a script file to start agent execution
- **HEALTHCHECK**: Must be defined or agent won't execute via Olas Agent Quickstart

#### Image Naming Convention
```
<author_name>/oar-<agent_name>:<agent_package_hash>
```

## Environment Variables

### Standard Variables (Backend-Computed)
Automatically provided by Olas Agent Quickstart with prefix `CONNECTION_CONFIGS_CONFIG_`:

- `CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES` - JSON dictionary with chain as key
- `CONNECTION_CONFIGS_CONFIG_GNOSIS_LEDGER_RPC` - Gnosis RPC endpoint
- `CONNECTION_CONFIGS_CONFIG_ETHEREUM_LEDGER_RPC` - Ethereum RPC endpoint
- `CONNECTION_CONFIGS_CONFIG_[CHAIN]_LEDGER_RPC` - Other chain RPCs as needed

### Custom Variables
Define in service configuration with provision types:
- **user**: Prompted from user during setup
- **fixed**: Uses predefined value
- **computed**: Automatically calculated by backend

## Key Management

### Agent EOA Private Key
- **Location**: `/agent_key/ethereum_private_key.txt`
- **Format**: Plain text private key
- **Access**: Read-only by agent

### Safe Contract Address
- **Source**: `CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES` environment variable
- **Format**: JSON dictionary, e.g., `{"gnosis": "0xE7CA89..."}`

## Required Endpoints

### Health Check
- **URL**: `http://127.0.0.1:8716/healthcheck`
- **Method**: GET
- **Response Format**:
```json
{
  "healthy": true,
  "seconds_since_last_transition": 120,
  "is_transitioning_fast": false,
  "agent_state": "active",
  "timestamp": 1234567890
}
```

### Optional User Interface
- **URL**: `http://127.0.0.1:8716/`
- **Methods**: GET, POST
- **Purpose**: Agent-specific UI or real-time communication

## Persistent Storage

### Storage Directory
- **Environment Variable**: `STORE_PATH`
- **Default**: `./storage`
- **Purpose**: Agent-managed persistent data

### State Management
- Periodically save state to storage directory
- Recover state after SIGKILL signal
- Handle graceful shutdown on SIGTERM

## Logging

### Log File
- **Location**: `log.txt` in working directory
- **Format**: `[YYYY-MM-DD HH:MM:SS,mmm] [LOG_LEVEL] [agent] Message`
- **Example**: `[2025-01-20 14:30:45,123] [INFO] [agent] Started successfully`

## Service Configuration

### service.yaml Structure
```yaml
name: agent_name
author: organization_name
version: 0.1.0
description: Agent description
aea_version: ">=1.0.0, <2.0.0"
license: Apache-2.0
fingerprint: {}
fingerprint_ignore_patterns: []
connections: []
contracts: []
protocols: []
skills:
  - valory/abstract_round_abci:0.1.0:<hash>
models:
  params:
    args:
      setup:
        safe_contract_addresses:
          $ref: ${SAFE_CONTRACT_ADDRESSES:list}
        gnosis_ledger_rpc:
          $ref: ${GNOSIS_LEDGER_RPC:str}
      tendermint_config:
        max_msg_size: 104857600
type: skill
```

### config.json Template
```json
{
  "name": "<agent_name>",
  "hash": "<service_hash>",
  "description": "Agent description",
  "image": "",
  "service_version": "v0.1.0",
  "home_chain": "gnosis",
  "configurations": {
    "gnosis": {
      "agent_id": <agent_id>,
      "nft": "<service_nft_hash>",
      "threshold": 1,
      "use_staking": true,
      "staking_program_id": "<program_id>",
      "use_mech_marketplace": false,
      "fund_requirements": {
        "0x0000000000000000000000000000000000000000": {
          "agent": 5000000000000000,
          "safe": 5000000000000000
        }
      }
    }
  },
  "env_variables": {
    "SAFE_CONTRACT_ADDRESSES": {
      "name": "Safe contract addresses",
      "value": "",
      "provision_type": "computed"
    },
    "GNOSIS_LEDGER_RPC": {
      "name": "Gnosis ledger RPC",
      "value": "",
      "provision_type": "computed"
    },
    "CUSTOM_VAR": {
      "name": "Custom Variable",
      "description": "Description for user",
      "value": "",
      "provision_type": "user"
    }
  }
}
```

## Activity Requirements

### Withdrawal Mode
- Check environment variable `WITHDRAWAL_MODE`
- If `true`, handle withdrawal of invested funds to Agent Safe

### Activity Tracking
- Agent must perform trackable on-chain or off-chain activities
- Activities verified by Olas activity checker contract


## Integration Workflow

1. **Build**: Create agent following specifications
2. **Package**: Push Docker image to Docker Hub
3. **Mint**: Register agent on Olas Protocol web app
4. **Deploy**: Run via Olas Agent Quickstart with config.json

## Deployment Process

Olas Agent Quickstart handles:
- Prompting for user-provided environment variables
- Setting up service Safe and agent wallet
- Minting service in registry to DEPLOYED state
- Downloading and starting Docker container
- Configuring all environment variables with proper prefixes
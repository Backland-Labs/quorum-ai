# Olas SDK Integration Guide

## Overview

The Olas SDK allows you to bring autonomous agents built with **any framework** to the Olas Protocol. This enables:
- **Monetization** through Dev Rewards
- **Wallet abstraction** for on-chain transactions
- **Easy deployment** via Olas Agent Quickstart

## Integration Steps

### Step 1: Build Olas Agent Configuration

Create the minimal Open Autonomy agent wrapper for your existing agent. Check the [Olas SDK Starter guide](https://docs.olas.network/olas-sdk/).

**Key files to create:**
- `service.yaml` - Service configuration
- `agent.yaml` - Agent configuration
- `packages/packages.json` - Package registry

### Step 2: Publish Docker Image

Push your Docker image to Docker Hub with specific requirements:

#### Docker Image Requirements

| Requirement | Description |
|------------|-------------|
| **ENTRYPOINT** | Script file to start agent execution |
| **HEALTHCHECK** | Required for Olas Agent Quickstart compatibility |
| **Image Name** | Must follow format: `<author_name>/oar-<agent_name>:<agent_package_hash>` |

**Image naming components:**
- `author_name` - Your Docker Hub username
- `agent_name` - Must match name in service configuration
- `agent_package_hash` - Hash from `packages/packages.json`

### Step 3: Mint Your Agent

Register on the [Olas Protocol web app](https://registry.olas.network/):
1. Set dependencies to at least `1` (default value)
2. Use the agent hash from `packages/packages.json`
3. Complete the minting process to get your `agent_id`

### Step 4: Configure and Execute

1. **Clone Olas Agent Quickstart:**
   ```bash
   git clone https://github.com/valory-xyz/quickstart
   ```

2. **Create `config.json` in the `configs` folder:**
   ```json
   {
     "name": "<agent_name>",
     "hash": "<service_hash>",
     "description": "My awesome agent service",
     "image": "",
     "service_version": "v0.1.0",
     "home_chain": "gnosis",
     "configurations": {
       "gnosis": {
         "agent_id": <agent_id>,
         "nft": "bafybeifgj3kackzfoq4fxjiuousm6epgwx7jbc3n2gjwzjgvtbbz7fc3su",
         "threshold": 1,
         "use_mech_marketplace": false,
         "fund_requirements": {
           "0x0000000000000000000000000000000000000000": {
             "agent": 0,
             "safe": 0
           }
         }
       }
     },
     "env_variables": {
       "SAFE_CONTRACT_ADDRESSES": {
         "name": "Safe contract addresses",
         "description": "",
         "value": "",
         "provision_type": "computed"
       },
       "GNOSIS_LEDGER_RPC": {
         "name": "Gnosis ledger RPC",
         "description": "",
         "value": "",
         "provision_type": "computed"
       },
       "<YOUR_ENV_VAR>": {
         "name": "<YOUR_ENV_VAR>",
         "description": "",
         "value": "",
         "provision_type": "user"
       }
     }
   }
   ```

3. **Start the service:**
   ```bash
   ./run_service.sh <agent_config.json>
   ```

## Environment Variables

Environment variables are prefixed with `CONNECTION_CONFIGS_CONFIG_` when passed to your agent.

### Provision Types
- **`user`** - Prompts user for value during setup
- **`fixed`** - Uses value from config file
- **`computed`** - Automatically calculated by Olas

### Available Resources in Container

| Resource | Location/Variable |
|----------|------------------|
| Agent EOA Private Key | `/agent_key/ethereum_private_key.txt` |
| Safe Contract Address | `CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES` |
| Chain RPCs | `CONNECTION_CONFIGS_CONFIG_<CHAIN>_LEDGER_RPC` |

## Building a Binary (Alternative to Docker)

You can create a standalone executable instead of using Docker:
- Must meet same requirements as Docker images
- Must include HEALTHCHECK functionality
- Follow framework-specific build process

## Supported Chains

- Ethereum
- Gnosis
- Base
- Celo
- Mode
- Arbitrum
- Optimism
- Polygon

## Key Configuration Fields

### service.yaml Requirements
- Define all environment variables used by your agent
- Specify chain configurations
- Set funding requirements

### Agent Metadata
- `agent_name` - Unique identifier for your agent
- `agent_id` - Obtained after minting on Olas Protocol
- `service_hash` - Generated when pushing to IPFS
- `home_chain` - Primary chain for deployment

## Service Template Specification

The service template is a JSON configuration file required for Pearl integration. This must be submitted via PR to the Pearl repository.

### Complete Service Template Structure

```json
{
  "name": "<agent_name>",
  "hash": "<service_hash>",
  "description": "<description>",
  "image": "",
  "service_version": "v0.1.0",
  "home_chain": "<home_chain>",
  "configurations": {
    "<chain_1>": {
      "nft": "<service_nft>",
      "threshold": 1,
      "agent_id": <agent_id>,
      "use_staking": "true",
      "staking_program_id": "<staking_program_id>",
      "use_mech_marketplace": false,
      "fund_requirements": {
        "0x0000000000000000000000000000000000000000": {
          "agent": 5000000000000000,
          "safe": 5000000000000000
        },
        "0x1234567890123456789012345678901234567890": {
          "agent": 0,
          "safe": 5000000000000000
        }
      }
    },
    "<chain_2>": {
      ...
    }
  },
  "env_variables": {
    "<ENV_VAR_1>": {
      "name": "Fixed environment variable",
      "description": "",
      "value": "42",
      "provision_type": "fixed"
    },
    "<ENV_VAR_2>": {
      "name": "User environment variable",
      "description": "",
      "value": "",
      "provision_type": "user"
    },
    "<ENV_VAR_3>": {
      "name": "Computed environment variable",
      "description": "",
      "value": "",
      "provision_type": "computed"
    }
  }
}
```

### Field Descriptions

#### Top Level Fields
- **`name`**: Your agent's display name
- **`hash`**: IPFS hash of the agent service
- **`description`**: Brief description of agent functionality
- **`image`**: Currently unused, leave empty
- **`service_version`**: Semantic version (e.g., "v0.1.0")
- **`home_chain`**: Primary chain ID (e.g., "gnosis", "ethereum")

#### Configuration Fields (per chain)
- **`nft`**: Service NFT identifier
- **`threshold`**: Number of signers required (typically 1)
- **`agent_id`**: On-chain agent ID from minting process
- **`use_staking`**: Currently only "true" is supported
- **`staking_program_id`**: ID of the staking program
- **`use_mech_marketplace`**: Set to false (currently unused)

#### Fund Requirements
Define minimum balances for each token:
- **Native token** (address: `0x0000...0000`):
  - `agent`: Funds for agent EOA (gas fees)
  - `safe`: Funds for agent Safe (business logic)
- **ERC20 tokens**: Same structure with token contract address

#### Environment Variables
Three provision types:
- **`fixed`**: Static values defined in template
- **`user`**: User provides during setup
- **`computed`**: Pearl calculates automatically (e.g., RPC URLs, Safe addresses)

### Standard Computed Variables
These should be included if your agent needs them:
```json
"SAFE_CONTRACT_ADDRESSES": {
  "name": "Safe contract addresses",
  "description": "",
  "value": "",
  "provision_type": "computed"
},
"ETHEREUM_LEDGER_RPC": {
  "name": "Ethereum ledger RPC",
  "description": "",
  "value": "",
  "provision_type": "computed"
},
"STAKING_TOKEN_CONTRACT_ADDRESS": {
  "name": "Staking token contract address",
  "description": "",
  "value": "",
  "provision_type": "computed"
},
"ACTIVITY_CHECKER_CONTRACT_ADDRESS": {
  "name": "Activity checker contract address",
  "description": "",
  "value": "",
  "provision_type": "computed"
}
```

### Important Notes
- All environment variables must match those in `service.yaml`
- Fund requirements trigger automatic fund distribution from Master Safe
- Pearl monitors when funds drop below 50% of specified values
- Submit template updates via PR to Pearl repository for agent updates

## Best Practices

1. **Test locally** before pushing to IPFS
2. **Document all environment variables** in service.yaml
3. **Handle SIGKILL gracefully** - agent may be restarted
4. **Use standard logging** to `/logs/` directory
5. **Implement health checks** at `http://127.0.0.1:8716/healthcheck`

## Examples

- [Langchain Hello World Agent](https://github.com/valory-xyz/olas-sdk-langchain)
- [Eliza Memeooorr Agent](https://github.com/valory-xyz/olas-sdk-eliza)

## Troubleshooting

### Common Issues
- **Docker image not found**: Ensure image name follows exact format
- **Environment variables not accessible**: Check for `CONNECTION_CONFIGS_CONFIG_` prefix
- **Agent not starting**: Verify HEALTHCHECK is implemented
- **Minting fails**: Ensure at least one dependency is specified

### Support
For assistance, contact the Pearl development team or refer to the [Olas Developer Documentation](https://docs.olas.network/).

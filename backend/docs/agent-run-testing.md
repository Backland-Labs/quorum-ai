# Agent Run Testing Guide

This guide provides a simple and robust approach to testing the `/agent-run` endpoint with real Snapshot data.

## Overview

The agent-run endpoint executes an autonomous voting agent that:
1. Fetches active proposals from Snapshot spaces
2. Analyzes proposals using AI (Google Gemini 2.0 Flash)
3. Makes voting decisions based on configured strategies
4. Executes votes (or simulates in dry-run mode)

## Key Points

- **No Testnet Required**: Snapshot uses off-chain EIP-712 signatures, so voting is gasless
- **Dry-Run Mode**: Test without actually submitting votes
- **Real Data**: Uses mainnet Snapshot spaces for realistic testing

## Prerequisites

1. **Environment Setup**
   ```bash
   cd backend
   uv sync  # or pip install -e .
   ```

2. **Required Environment Variables**
   Create a `.env` file:
   ```bash
   # Required for AI analysis
   OPENROUTER_API_KEY=your_openrouter_api_key
   
   # Optional
   LOG_LEVEL=INFO
   ```

3. **Private Key Setup**
   Create `ethereum_private_key.txt` in the backend directory:
   ```
   0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
   ```
   Note: Use a test wallet, not your main wallet!

## Quick Start Testing

### 1. Start the Backend
```bash
uv run main.py
```

### 2. Test with cURL (Dry-Run)

Test with an active Snapshot space:
```bash
# Test with ENS DAO (usually has active proposals)
curl -X POST http://localhost:8000/agent-run \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": "ens.eth",
    "dry_run": true
  }'
```

### 3. Test with Python Script

Create and run `test_agent.py`:
```python
import requests
import json

# Test configuration
API_URL = "http://localhost:8000"
TEST_SPACES = [
    "ens.eth",          # ENS DAO
    "arbitrumfoundation.eth",  # Arbitrum
    "aave.eth",         # Aave
    "compound.eth"      # Compound
]

def test_agent_run(space_id, dry_run=True):
    """Test the agent-run endpoint."""
    print(f"\n🔍 Testing space: {space_id}")
    print(f"   Dry run: {dry_run}")
    
    response = requests.post(
        f"{API_URL}/agent-run",
        json={
            "space_id": space_id,
            "dry_run": dry_run
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"   Proposals analyzed: {data['proposals_analyzed']}")
        print(f"   Votes cast: {len(data['votes_cast'])}")
        print(f"   Execution time: {data['execution_time']:.2f}s")
        
        # Show voting decisions
        for vote in data['votes_cast']:
            print(f"\n   📊 Proposal: {vote['proposal_id'][:10]}...")
            print(f"      Vote: {vote['vote']}")
            print(f"      Confidence: {vote['confidence']:.2%}")
            print(f"      Risk: {vote['risk_assessment']['risk_level']}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")

# Run tests
for space in TEST_SPACES:
    test_agent_run(space, dry_run=True)
```

## User Preferences Configuration

Create `user_preferences.txt` to customize voting behavior:
```json
{
  "voting_strategy": "balanced",
  "confidence_threshold": 0.7,
  "max_proposals_per_run": 3,
  "blacklisted_proposers": [],
  "whitelisted_proposers": []
}
```

### Voting Strategies:
- **conservative**: Vote only on low-risk proposals with high confidence
- **balanced**: Default strategy, moderate risk tolerance
- **aggressive**: Vote on more proposals with lower confidence threshold

## Test Scenarios

### Scenario 1: Basic Dry-Run Test
Test the agent without submitting any votes:
```bash
curl -X POST http://localhost:8000/agent-run \
  -H "Content-Type: application/json" \
  -d '{"space_id": "ens.eth", "dry_run": true}'
```

Expected: Agent analyzes proposals and returns decisions without voting

### Scenario 2: Test Different Voting Strategies
1. Update `user_preferences.txt` with different strategies
2. Run the agent and observe decision changes:
```bash
# Conservative strategy
echo '{"voting_strategy": "conservative", "confidence_threshold": 0.8}' > user_preferences.txt

# Aggressive strategy  
echo '{"voting_strategy": "aggressive", "confidence_threshold": 0.6}' > user_preferences.txt
```

### Scenario 3: Test Proposal Filtering
Configure preferences to filter proposals:
```json
{
  "voting_strategy": "balanced",
  "confidence_threshold": 0.7,
  "max_proposals_per_run": 1,
  "blacklisted_proposers": ["0x123..."],
  "whitelisted_proposers": []
}
```

### Scenario 4: Live Voting Test (Careful!)
To test actual voting (submits real votes):
```bash
curl -X POST http://localhost:8000/agent-run \
  -H "Content-Type: application/json" \
  -d '{"space_id": "ens.eth", "dry_run": false}'
```

⚠️ **Warning**: This will submit real votes using your private key!

## Validation Steps

1. **Check Logs**
   ```bash
   tail -f log.txt | grep -E "(agent_run|voting_decision|proposal_analysis)"
   ```

2. **Verify API Response**
   - `proposals_analyzed`: Number of proposals examined
   - `votes_cast`: Array of voting decisions
   - `user_preferences_applied`: Should be `true`
   - `errors`: Should be empty for successful runs

3. **Validate Vote Decisions**
   Each vote should include:
   - `proposal_id`: Valid Snapshot proposal ID
   - `vote`: One of "FOR", "AGAINST", "ABSTAIN"
   - `confidence`: Between 0.0 and 1.0
   - `risk_assessment`: Risk level and factors

## Finding Active Spaces

To find Snapshot spaces with active proposals:

1. Visit https://snapshot.org
2. Look for spaces with "Active" proposals
3. Common active spaces:
   - `ens.eth` - ENS DAO
   - `arbitrumfoundation.eth` - Arbitrum
   - `aave.eth` - Aave Protocol
   - `gitcoindao.eth` - Gitcoin
   - `compound.eth` - Compound Finance

## Troubleshooting

### No Active Proposals
- Try different spaces from the list above
- Check https://snapshot.org for currently active proposals

### AI Service Errors
- Verify `OPENROUTER_API_KEY` is set correctly
- Check API key has credits available

### Private Key Issues
- Ensure `ethereum_private_key.txt` exists
- Format: 64 hex characters (with or without 0x prefix)
- File permissions should be 600 (read by owner only)

### Network Timeouts
- Snapshot API might be slow; increase timeout in config
- Check internet connectivity

## Example Output

Successful dry-run response:
```json
{
  "space_id": "ens.eth",
  "proposals_analyzed": 3,
  "votes_cast": [
    {
      "proposal_id": "0x1234...",
      "vote": "FOR",
      "confidence": 0.85,
      "reasoning": "Proposal aligns with protocol growth...",
      "risk_assessment": {
        "risk_level": "LOW",
        "risk_factors": []
      }
    }
  ],
  "user_preferences_applied": true,
  "execution_time": 4.23,
  "errors": []
}
```

## Next Steps

1. Start with dry-run tests on active spaces
2. Adjust user preferences to see different behaviors
3. Monitor logs to understand decision-making process
4. Only enable live voting after thorough testing
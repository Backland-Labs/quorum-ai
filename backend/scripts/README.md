# Agent Run Testing Scripts

This directory contains scripts for testing the `/agent-run` endpoint.

## Quick Start

1. **Ensure backend is running:**
   ```bash
   cd backend
   uv run main.py
   ```

2. **Run quick test:**
   ```bash
   ./quick_test.sh
   ```

## Available Scripts

### quick_test.sh
Simple bash script for quick testing:
```bash
./quick_test.sh              # Test ENS DAO
./quick_test.sh aave.eth     # Test specific space
./quick_test.sh --all        # Test multiple spaces
./quick_test.sh --help       # Show help
```

### test_agent_run.py
Comprehensive Python test script:
```bash
python test_agent_run.py                    # Test ENS DAO with details
python test_agent_run.py compound.eth       # Test specific space
python test_agent_run.py --all              # Test all popular spaces
python test_agent_run.py --live ens.eth     # Live voting (careful!)
```

## Example Output

```json
{
  "space_id": "ens.eth",
  "proposals_analyzed": 3,
  "votes_cast": [
    {
      "proposal_id": "0x123...",
      "vote": "FOR",
      "confidence": 0.85,
      "risk_assessment": {
        "risk_level": "LOW"
      }
    }
  ],
  "user_preferences_applied": true,
  "execution_time": 4.23,
  "errors": []
}
```

## Testing Tips

1. **No Active Proposals?** Try different spaces - ENS, Arbitrum, and Aave often have active proposals
2. **Always use dry_run=true** for testing unless you want to submit real votes
3. **Check logs** in `log.txt` for detailed execution information
4. **Test different strategies** by modifying `user_preferences.txt`

## Safety Note

These scripts default to dry-run mode. Only use live voting (`dry_run=false`) if you:
- Understand the proposals
- Want to submit real votes
- Are using a test wallet

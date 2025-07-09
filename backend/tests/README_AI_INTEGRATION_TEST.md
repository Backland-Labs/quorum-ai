# AI Voting Integration Test Script

This script tests the AI voting decision functionality with realistic DAO proposal data.

## Features

- ✅ **5 Realistic Proposals**: Development funding, security measures, experimental features, infrastructure improvements, and controversial decisions
- ✅ **3 Voting Strategies**: Conservative, Balanced, and Aggressive approaches  
- ✅ **Real AI Integration**: Tests against OpenRouter/Claude API
- ✅ **Demo Mode**: Mock responses for testing without API costs
- ✅ **Comprehensive Results**: JSON export with detailed analysis

## Usage

### Demo Mode (No API Key Required)
```bash
uv run python test_ai_integration.py --demo
```

### Real AI Integration
```bash
# Set your OpenRouter API key
export OPENROUTER_API_KEY="your-api-key-here"

# Run the test
uv run python test_ai_integration.py
```

## Sample Output

```
🚀 Starting AI Voting Integration Test
============================================================
✅ OpenRouter API key configured: sk-or-v1...
✅ AI Service initialized successfully
✅ Generated 5 fake proposals

📋 Testing Proposal 1: Increase Development Funding by 500,000 USDC
DAO: Compound Finance
Current votes: FOR 2500000.0K, AGAINST 800000.0K

  🤖 Testing CONSERVATIVE strategy...
    ✅ Vote: FOR
    📊 Confidence: 0.84
    🟡 Risk: MEDIUM
    💭 Reasoning: Conservative approach: Approving low-risk initiative

📈 STRATEGY ANALYSIS
CONSERVATIVE: FOR:3 AGAINST:2 ABSTAIN:0 (avg conf: 0.79)
BALANCED    : FOR:2 AGAINST:3 ABSTAIN:0 (avg conf: 0.77)  
AGGRESSIVE  : FOR:5 AGAINST:0 ABSTAIN:0 (avg conf: 0.71)
```

## Generated Proposals

1. **Development Funding** - 500K USDC allocation for protocol improvements
2. **Emergency Pause Mechanism** - Security feature for protocol protection
3. **NFT Marketplace Integration** - Experimental DeFi-NFT crossover
4. **L2 Migration** - Gas cost reduction through Arbitrum deployment
5. **Bitcoin Treasury Allocation** - Controversial 50% treasury diversification

## Strategy Behaviors

- **Conservative**: Rejects high-risk/experimental proposals, favors proven initiatives
- **Balanced**: Follows community consensus, moderate risk tolerance
- **Aggressive**: Supports innovation and growth opportunities, accepts higher risk

## Output Files

- `ai_voting_test_results.json` - Complete test results with timestamps and analysis
- Console output with real-time voting decisions and strategy comparisons

## Testing Real Integration

To test with the actual OpenRouter API:

1. Get an API key from [OpenRouter](https://openrouter.ai/)
2. Set the environment variable: `export OPENROUTER_API_KEY="your-key"`
3. Run: `uv run python test_ai_integration.py`

The script will make real API calls to Claude 3.5 Sonnet and provide genuine AI voting decisions based on the proposal content and selected strategy.

## Cost Estimation

Real API calls cost approximately:
- ~$0.01-0.03 per voting decision
- ~$0.15-0.45 for complete test (15 decisions)
- Demo mode is completely free
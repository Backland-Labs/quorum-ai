# Quorum AI

A sophisticated autonomous voting agent for DAO governance on the Olas Pearl platform. This full-stack application enables automated participation in decentralized governance through AI-powered proposal analysis and voting decisions, featuring integration with Snapshot and Google Gemini 2.0 Flash.

## Quick Start

### 🚀 One-Command Launch

```bash
./startup.sh
```

This will start both backend and frontend services automatically.

### Manual Setup

#### Prerequisites
- Python 3.8+ with `uv` package manager
- Node.js 18+ with npm
- OpenRouter API key (for AI summarization)

#### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Required for AI summarization
OPENROUTER_API_KEY=your_openrouter_api_key

# Optional configuration
TOP_ORGANIZATIONS=compound,nounsdao,arbitrum  # Default organizations

# Note: Observability is handled by Pearl-compliant logging to local files
# Log files are written to ./logs/ directory following Pearl standards
```

#### Backend Setup

```bash
cd backend
uv sync
uv run main.py
```

#### Frontend Setup

```bash
cd frontend
npm install
npm run generate-api  # Generate API client from backend
npm run dev
```

## Features

### 🎯 Core Functionality
- **Pearl Platform Integration**: Designed for deployment on Olas Pearl App Store
- **Autonomous Voting Agent**: Fully automated DAO governance participation
- **Snapshot Integration**: Direct integration with Snapshot GraphQL API
- **AI-Powered Analysis**: Google Gemini 2.0 Flash for proposal summarization and decision making
- **Risk Assessment**: Intelligent risk evaluation (LOW, MEDIUM, HIGH)
- **Multiple Voting Strategies**: Conservative, Balanced, and Aggressive approaches
- **State Management**: Persistent state tracking with recovery capabilities
- **Pearl-Compliant Logging**: Structured logging following Pearl standards
- **Health Monitoring**: Real-time health checks with state transition tracking

### 🔗 API Endpoints

- `GET /health` - Basic health check endpoint
- `GET /healthcheck` - Pearl-compliant health check with state metrics
- `GET /proposals` - Fetch proposals from Snapshot spaces with filtering
- `GET /proposals/{id}` - Get specific proposal details
- `POST /proposals/summarize` - AI-powered proposal summarization
- `GET /proposals/{id}/top-voters` - Analyze top voters for a proposal
- `POST /agent-run` - Execute autonomous voting agent
- `GET /docs` - Interactive OpenAPI documentation

### 🏗️ Architecture

**Backend (Python/FastAPI)**
- FastAPI with async/await for high performance
- Pydantic AI integration with Google Gemini 2.0 Flash via OpenRouter
- Direct Snapshot GraphQL API integration
- Service-oriented architecture with clear separation of concerns
- Pearl-compliant logging to local files
- State persistence and recovery mechanisms
- Signal handling for graceful shutdown (SIGTERM/SIGINT)
- Comprehensive test coverage (>90% target)

**Frontend (SvelteKit/TypeScript)**
- SvelteKit with Svelte 5 and runes
- TypeScript for full type safety
- TailwindCSS v4.x for utility-first styling
- OpenAPI TypeScript generation for type-safe API client
- Vitest with Testing Library for component testing
- Organization-based routing with dynamic routes

## Autonomous Voting Agent

The application includes an autonomous voting agent that can analyze proposals and make voting decisions based on user preferences.

### Agent Features
- **Automatic Proposal Analysis**: Fetches and analyzes active proposals from Snapshot spaces
- **Configurable Voting Strategies**: Balanced, conservative, or aggressive approaches
- **User Preference Management**: Persistent configuration via `user_preferences.txt`
- **Proposal Filtering**: Whitelist/blacklist proposers, confidence thresholds
- **Dry Run Mode**: Test voting decisions without executing actual votes
- **Comprehensive Logging**: Full audit trail of all agent decisions

### Using the Agent

```bash
# Execute agent run via API
curl -X POST http://localhost:8000/agent-run \
  -H "Content-Type: application/json" \
  -d '{
    "space_id": "yam.eth",
    "dry_run": true
  }'
```

### User Preferences Configuration

Create a `user_preferences.txt` file in the backend directory:

```json
{
  "voting_strategy": "BALANCED",
  "confidence_threshold": 0.7,
  "max_proposals_per_run": 3,
  "blacklisted_proposers": [],
  "whitelisted_proposers": []
}
```

## Development

### Commands

**Backend:**
```bash
uv run main.py              # Start dev server
uv run pytest              # Run tests
uv run ruff check .         # Lint code
uv run mypy .              # Type checking
uv run black .             # Format code
```

**Frontend:**
```bash
npm run dev                 # Start dev server
npm run build              # Build for production
npm run preview            # Preview production build
npm run check              # Type checking
npm run generate-api       # Generate API client
npm run test               # Run tests
npm run test:watch         # Run tests in watch mode
```

### Project Structure

```
quorum-ai/
├── backend/
│   ├── main.py                    # FastAPI application with health checks
│   ├── config.py                  # Pearl-compliant configuration
│   ├── models.py                  # Pydantic data models
│   ├── logging_config.py          # Pearl logging setup
│   ├── river.py                   # River framework interface
│   ├── services/
│   │   ├── ai_service.py          # AI summarization & voting logic
│   │   ├── snapshot_service.py    # Snapshot GraphQL integration
│   │   ├── voting_service.py      # EIP-712 vote submission
│   │   ├── agent_run_service.py   # Autonomous agent orchestration
│   │   ├── state_manager.py       # State persistence
│   │   ├── state_transition_tracker.py  # Health monitoring
│   │   ├── signal_handler.py      # Graceful shutdown
│   │   └── user_preferences_service.py  # User configuration
│   └── tests/                     # Comprehensive test suite
├── frontend/
│   ├── src/
│   │   ├── routes/               # SvelteKit pages
│   │   └── lib/                  # Shared components & utilities
│   └── package.json
├── specs/                        # Technical specifications
├── startup.sh                    # Launch script
├── CLAUDE.md                     # AI assistant instructions
└── README.md
```

## Configuration

### Environment Variables

**Required:**
| Variable | Description | Required |
|----------|-------------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key for Google Gemini 2.0 Flash | Yes |

**Optional Configuration:**
| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `LOG_LEVEL` | Pearl-compliant log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `LOG_FILE_PATH` | Path to Pearl-compliant log file | `log.txt` |
| `MONITORED_DAOS` | Comma-separated list of DAO spaces to monitor | - |
| `VOTE_CONFIDENCE_THRESHOLD` | Default confidence threshold for voting | `0.6` |

**Health Check Configuration:**
| Variable | Description | Default |
|----------|-------------|---------|
| `HEALTH_CHECK_PORT` | Port for Pearl health check endpoint | `8716` |
| `HEALTH_CHECK_PATH` | Path for Pearl health check endpoint | `/healthcheck` |
| `FAST_TRANSITION_THRESHOLD` | Seconds threshold for fast state transitions | `5` |

### AI Model Configuration

The application uses Google Gemini 2.0 Flash via OpenRouter by default. You can modify the AI service configuration in `backend/services/ai_service.py` to use different models or providers.

### Agent Run Configuration

The autonomous voting agent can be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_PROPOSALS_PER_RUN` | Maximum proposals to analyze per run | `3` |
| `AGENT_CONFIDENCE_THRESHOLD` | Minimum confidence for voting | `0.7` |
| `PROPOSAL_FETCH_TIMEOUT` | Timeout for fetching proposals (seconds) | `30` |
| `VOTE_EXECUTION_TIMEOUT` | Timeout for vote execution (seconds) | `60` |

## Vote Attestation Setup (Manual Step)

To enable on-chain vote attestations using the Ethereum Attestation Service (EAS), you must first manually register a schema on the Base network. This is a one-time setup process.

1.  **Connect to Base Network**: Use a tool like Remix, Foundry, or the [EAS Schema Registry UI](https://base.easscan.org/schema/create).
2.  **Register the Schema**: Register a new schema with the following definition:
    ```
    address agent, string spaceId, string proposalId, uint8 voteChoice, string snapshotSig, uint256 timestamp, string runId, uint8 confidence
    ```
3.  **Get the Schema UID**: After registration, you will receive a unique schema UID (a `bytes32` value).
4.  **Set Environment Variable**: Set the `EAS_SCHEMA_UID` environment variable in your `.env` file to this new UID.

The agent will use this schema to record all its voting activities on-chain.

## Voting Flow: From Decision to On-Chain Vote

Quorum AI implements a sophisticated voting system that bridges AI decision-making with on-chain governance. Here's how votes flow through the system:

### 🔄 Complete Voting Flow

```
User Request → Agent Run → Fetch Proposals → AI Analysis → Vote Decision → Submit Vote
                  ↓              ↓                ↓              ↓              ↓
           AgentRunService  SnapshotService   AIService    VoteDecision  VotingService/SafeService
```

### 📋 Step-by-Step Process

#### 1. **Vote Initiation**
- Agent run triggered via `/agent-run` endpoint
- Fetches active proposals from Snapshot spaces
- Applies user preferences (filtering, strategies)
- Ranks proposals by urgency and importance

#### 2. **AI Decision Making**
- Google Gemini 2.0 Flash analyzes each proposal
- Considers voting strategy (Conservative/Balanced/Aggressive)
- Returns structured decision with:
  - Vote choice: FOR, AGAINST, or ABSTAIN
  - Confidence score (0-1)
  - Risk assessment (LOW/MEDIUM/HIGH)
  - Detailed reasoning

#### 3. **Vote Submission Paths**

**Direct Voting (EOA)**:
- Creates EIP-712 typed message for Snapshot
- Signs with agent's private key
- Submits to Snapshot Hub API
- No gas fees required (off-chain)

**Multi-Sig Voting (Gnosis Safe)**:
- Builds Safe transaction for governor contract
- Encodes vote using governor ABI
- Signs and executes through Safe
- Requires on-chain gas fees

### 🔐 Security & Signatures

**EIP-712 Signature Structure**:
```json
{
  "from": "0xVoterAddress",
  "space": "compound.eth",
  "timestamp": 1234567890,
  "proposal": "0xProposalId",
  "choice": 1,  // 1=For, 2=Against, 3=Abstain
  "reason": "",
  "app": "",
  "metadata": "{}"
}
```

### ⛓️ Supported Blockchains
- **Ethereum** (Chain ID: 1)
- **Gnosis Chain** (Chain ID: 100)
- **Base** (Chain ID: 8453)
- **Mode** (Chain ID: 34443)
- **Sepolia Testnet** (Chain ID: 11155111)

### 🏛️ Governor Contract Support
- Compound Bravo
- Nouns Governor
- OpenZeppelin (Uniswap-style)
- Arbitrum Governor

### 🔍 State Tracking
The system tracks vote progression through states:
```
IDLE → STARTING → LOADING_PREFERENCES → FETCHING_PROPOSALS
→ FILTERING_PROPOSALS → ANALYZING_PROPOSAL → DECIDING_VOTE
→ SUBMITTING_VOTE → COMPLETED
```

### 🛡️ Key Security Features
- Private keys stored with 600 permissions
- Keys cached in memory (5-minute expiration)
- All votes cryptographically signed
- Comprehensive error handling
- Audit trail via Pearl-compliant logging

## Pearl Platform Integration

Quorum AI is designed specifically for deployment on the Olas Pearl App Store:

### Pearl-Compliant Features
- **Logging Format**: `[YYYY-MM-DD HH:MM:SS,mmm] [LEVEL] [agent] Message`
- **Health Check Endpoint**: Available at port 8716 by default
- **State Persistence**: Survives container restarts
- **Graceful Shutdown**: Handles SIGTERM/SIGINT properly
- **Local File Logging**: Writes to `log.txt` following Pearl standards
- **State Transition Tracking**: Monitors agent health and detects anomalies

### Pearl Deployment Requirements
- Container-based deployment
- Local file system for state persistence
- Access to Ethereum private key file
- Network access to Snapshot GraphQL API

## Deployment

### Docker

```bash
docker build -t quorum-ai .
docker run -p 8000:8000 -p 8716:8716 --env-file .env quorum-ai
```

### Docker Compose

The application includes a complete Docker Compose setup with PostgreSQL and Redis:

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d postgres redis
docker-compose up -d backend frontend

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

### Production Considerations

- Set `DEBUG=false` in production
- Configure proper CORS origins
- Use environment-specific `.env` files
- Set up reverse proxy (nginx/caddy) for frontend if needed
- Enable HTTPS with SSL certificates
- Configure rate limiting and monitoring
- Ensure Pearl health check endpoint is accessible
- Monitor `log.txt` for Pearl-compliant logging
- Set up appropriate volume mounts for state persistence
- Configure MONITORED_DAOS for specific DAO spaces
- Review and adjust voting confidence thresholds

## Startup Script Features

The `startup.sh` script provides:

- ✅ **Dependency Checking**: Verifies `uv` and `npm` are installed
- ✅ **Port Availability**: Checks if ports 8000 and 5173 are free
- ✅ **Graceful Shutdown**: Handles Ctrl+C to stop all services
- ✅ **Process Monitoring**: Automatically restarts if services crash
- ✅ **Logging**: Separate log files for backend and frontend
- ✅ **Status Display**: Shows service URLs and process IDs

### Usage

```bash
# Make executable (first time only)
chmod +x startup.sh

# Start all services
./startup.sh

# Services will be available at:
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Frontend: http://localhost:5173
```

## Testing

### Backend Testing
- **Framework**: pytest with async support (`pytest-asyncio`)
- **Coverage**: Target >90% with HTML reporting
- **Mocking**: pytest-mock and pytest-httpx for external APIs
- **Run Tests**: `uv run pytest`
- **With Coverage**: `uv run pytest --cov=. --cov-report=html`
- **Specific Test**: `uv run pytest tests/test_models.py -v`

### Frontend Testing
- **Framework**: Vitest with jsdom environment
- **Component Testing**: @testing-library/svelte
- **Run Tests**: `npm run test`
- **Watch Mode**: `npm run test:watch`

### Key Test Areas
- Pearl-compliant logging validation
- State persistence and recovery
- Health check endpoint functionality
- AI service integration
- Snapshot API interaction
- Signal handling and graceful shutdown

## Technical Specifications

The `specs/` directory contains detailed technical documentation:

- **[AI Service](specs/ai-service.md)**: AI integration, prompt engineering, autonomous voting logic
- **[API](specs/api.md)**: RESTful API design, endpoints, and data contracts
- **[Authentication](specs/authentication.md)**: Authentication mechanisms and security
- **[Database](specs/database.md)**: Database schema and data modeling
- **[Deployment](specs/deployment.md)**: Deployment strategies and infrastructure
- **[Error Handling](specs/error-handling.md)**: Error handling patterns and best practices
- **[Logging](specs/logging.md)**: Logging standards and Pearl-compliant implementation
- **[State Management](specs/state_management.md)**: State persistence and recovery mechanisms
- **[Testing](specs/testing.md)**: Testing strategies and coverage requirements

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

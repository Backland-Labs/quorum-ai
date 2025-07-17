# Quorum AI

A full-stack DAO proposal summarization and autonomous voting application with Python FastAPI backend and SvelteKit frontend, featuring AI-powered analysis using Google Gemini 2.0 Flash via OpenRouter and integration with Snapshot for decentralized governance.

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
LOGFIRE_TOKEN=your_logfire_token  # For observability
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
- **Snapshot Integration**: Direct integration with Snapshot for DAO proposal data
- **Active Proposals**: Fetches active proposals from Snapshot spaces
- **AI Summarization**: Uses Google Gemini 2.0 Flash via OpenRouter for proposal analysis
- **Risk Assessment**: AI-powered risk evaluation for each proposal
- **Autonomous Voting**: Agent-based system for automated voting decisions
- **User Preferences**: Configurable voting strategies and confidence thresholds

### 🔗 API Endpoints

- `GET /proposals` - Proposal search and filtering by Snapshot space
- `GET /proposals/{id}` - Get specific proposal by ID
- `POST /proposals/summarize` - AI summarization for specific proposals
- `GET /proposals/{id}/top-voters` - Top voters for a proposal
- `POST /agent-run` - Execute autonomous voting agent
- `GET /health` - Health check endpoint
- `GET /docs` - Interactive API documentation

### 🏗️ Architecture

**Backend (Python FastAPI)**
- Async/await for high performance
- Pydantic AI integration with OpenRouter
- Snapshot GraphQL API integration
- Service-oriented architecture
- Comprehensive error handling and logging

**Frontend (SvelteKit)**
- TypeScript for type safety
- TailwindCSS for styling
- Auto-generated API client
- Responsive design
- Real-time proposal updates

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
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration management
│   ├── models.py         # Pydantic data models
│   └── services/
│       ├── ai_service.py     # AI summarization
│       ├── snapshot_service.py  # Snapshot data fetching
│       ├── voting_service.py    # Vote submission
│       ├── agent_run_service.py # Autonomous agent
│       └── user_preferences_service.py  # User config
├── frontend/
│   ├── src/
│   │   ├── routes/           # SvelteKit pages
│   │   └── lib/             # Shared components
│   └── package.json
├── startup.sh           # Launch script
└── README.md
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API key for Claude 3.5 Sonnet | - | Yes |
| `TOP_ORGANIZATIONS` | Comma-separated organization slugs | `compound,nounsdao,arbitrum` | No |
| `LOGFIRE_TOKEN` | Logfire token for observability | - | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |

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

## Deployment

### Docker

```bash
docker build -t quorum-ai .
docker run -p 8000:8000 --env-file .env quorum-ai
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
- Set up reverse proxy (nginx/caddy) for frontend
- Enable HTTPS with SSL certificates
- Configure rate limiting and monitoring

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

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

# Quorum AI

A full-stack DAO proposal summarization application with Python FastAPI backend and SvelteKit frontend, featuring AI-powered analysis using Claude 3.5 Sonnet via OpenRouter.

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
TALLY_API_KEY=your_tally_api_key  # For higher rate limits
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
- **Top Organizations**: Automatically fetches top 3 DAO organizations
- **Active Proposals**: Gets 3 most active proposals per organization
- **AI Summarization**: Uses Claude 3.5 Sonnet via OpenRouter for proposal analysis
- **Risk Assessment**: AI-powered risk evaluation for each proposal
- **Recommendations**: Smart voting recommendations based on proposal analysis

### 🔗 API Endpoints

- `GET /organizations` - Top 3 organizations with summarized proposals
- `GET /organizations/list` - Full organization listing
- `GET /proposals` - Proposal search and filtering
- `POST /proposals/summarize` - AI summarization for specific proposals
- `GET /docs` - Interactive API documentation

### 🏗️ Architecture

**Backend (Python FastAPI)**
- Async/await for high performance
- Pydantic AI integration with OpenRouter
- Tally GraphQL API integration
- Service-oriented architecture
- Comprehensive error handling and logging

**Frontend (SvelteKit)**
- TypeScript for type safety
- TailwindCSS for styling
- Auto-generated API client
- Responsive design
- Real-time proposal updates

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
│       └── tally_service.py  # DAO data fetching
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
| `TALLY_API_KEY` | Tally API key for higher rate limits | - | No |
| `LOGFIRE_TOKEN` | Logfire token for observability | - | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `HOST` | Server host | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |

### AI Model Configuration

The application uses Claude 3.5 Sonnet via OpenRouter by default. You can modify the AI service configuration in `backend/services/ai_service.py` to use different models or providers.

## Deployment

### Docker

```bash
docker build -t quorum-ai .
docker run -p 8000:8000 --env-file .env quorum-ai
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

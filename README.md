# Quorum AI - DAO Proposal Summarization Backend

A modern, production-ready backend for sorting and summarizing DAO proposals using AI. Built with FastAPI, Pydantic AI, and following 12-factor app principles.

## Features

- **DAO Management**: Fetch and browse available DAOs from Tally
- **Proposal Filtering**: Advanced filtering and sorting of governance proposals
- **AI Summarization**: Generate plain-English summaries of complex proposals
- **Risk Assessment**: AI-powered risk analysis of proposals
- **Scalable Architecture**: Built with async/await and designed for high performance
- **Comprehensive Testing**: Full test coverage with pytest
- **Production Ready**: Observability with Logfire, health checks, and error handling

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic AI**: Type-safe AI integration with multiple model providers
- **Logfire**: Advanced observability and logging
- **UV**: Fast Python package installer and resolver
- **Docker**: Containerized deployment
- **Tally API**: Governance data source

## Quick Start

### Prerequisites

- Python 3.12+
- [UV](https://docs.astral.sh/uv/) (recommended) or pip
- Docker (optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd quorum-ai
   ```

2. **Install dependencies**
   ```bash
   # With UV (recommended)
   uv sync

   # Or with pip
   pip install -e .
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Configure your environment**
   
   Required environment variables:
   ```bash
   # AI Provider (choose one)
   OPENAI_API_KEY=your_openai_api_key
   # OR
   ANTHROPIC_API_KEY=your_anthropic_api_key

   # Optional but recommended
   TALLY_API_KEY=your_tally_api_key
   LOGFIRE_TOKEN=your_logfire_token
   ```

### Running the Application

**Development Mode:**
```bash
uv run main.py
```

**Production Mode:**
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

**With Docker:**
```bash
docker build -t quorum-ai .
docker run -p 8000:8000 --env-file .env quorum-ai
```

## API Documentation

Once running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

### Key Endpoints

#### DAOs
- `GET /daos` - List available DAOs
- `GET /daos/{dao_id}` - Get specific DAO details

#### Proposals
- `GET /proposals` - List proposals with filtering
- `GET /proposals/{proposal_id}` - Get specific proposal
- `POST /proposals/summarize` - Generate AI summaries

#### Example Usage

**Get DAOs:**
```bash
curl "http://localhost:8000/daos?limit=10"
```

**Get Proposals with Filters:**
```bash
curl "http://localhost:8000/proposals?dao_id=erc20:1:0x123&state=ACTIVE&limit=5"
```

**Summarize Proposals:**
```bash
curl -X POST "http://localhost:8000/proposals/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_ids": ["prop1", "prop2"],
    "include_risk_assessment": true,
    "include_recommendations": true
  }'
```

## Configuration

The application follows 12-factor app principles with all configuration through environment variables:

### Core Settings
- `APP_NAME`: Application name (default: "Quorum AI")
- `DEBUG`: Enable debug mode (default: false)
- `HOST`: Server host (default: "0.0.0.0")
- `PORT`: Server port (default: 8000)

### External Services
- `TALLY_API_BASE_URL`: Tally GraphQL endpoint
- `TALLY_API_KEY`: Optional API key for higher rate limits
- `AI_MODEL`: AI model to use (e.g., "openai:gpt-4o-mini")

### AI Configuration
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key
- Choose the appropriate key based on your `AI_MODEL` setting

### Observability
- `LOGFIRE_TOKEN`: Logfire authentication token
- `LOGFIRE_PROJECT`: Logfire project name

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py -v
```

### Code Quality

```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Development Workflow

This project follows Test-Driven Development (TDD):

1. Write tests first
2. Implement functionality to pass tests
3. Refactor with confidence

### Project Structure

```
quorum-ai/
├── config.py              # Configuration management
├── models.py               # Pydantic data models
├── main.py                 # FastAPI application
├── services/               # Business logic services
│   ├── tally_service.py    # Tally API integration
│   └── ai_service.py       # AI summarization service
├── tests/                  # Test suite
├── pyproject.toml          # Project configuration
├── Dockerfile              # Container configuration
└── README.md               # This file
```

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t quorum-ai .

# Run container
docker run -d \
  --name quorum-ai \
  -p 8000:8000 \
  --env-file .env \
  quorum-ai
```

### Environment Variables for Production

Ensure these are set in your production environment:

```bash
DEBUG=false
OPENAI_API_KEY=your_production_key
TALLY_API_KEY=your_production_key
LOGFIRE_TOKEN=your_production_token
```

### Health Checks

The application provides a health check endpoint at `/health` that returns:
- Application status
- Timestamp
- Version information

## Monitoring and Observability

The application integrates with Logfire for comprehensive observability:

- **Structured Logging**: All operations are logged with context
- **Distributed Tracing**: Request tracing across services
- **Performance Metrics**: Timing and performance data
- **Error Tracking**: Detailed error capture and analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for your changes
4. Implement the feature
5. Run the test suite
6. Submit a pull request

### Code Style

- Follow PEP 8
- Use type hints throughout
- Write comprehensive docstrings
- Maintain test coverage above 90%
- Prefer small, focused functions

## License

[MIT License](LICENSE)

## Support

For issues and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs`
- Review the test suite for usage examples

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
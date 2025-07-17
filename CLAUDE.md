# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
This application is an AI agent that will run on the Olas Pearl App store. Importantly, this will be deployed in a container on a local machine. Consider this deployment environment when making update or changes to the code.

## Development Commands

### Backend (Python/FastAPI)
- **Install dependencies**: `uv sync` (or `pip install -e .`)
- **Run development server**: `uv run main.py`
- **Run production server**: `uv run uvicorn main:app --host 0.0.0.0 --port 8000`
- **Run tests**: `uv run pytest`
- **Run tests with coverage**: `uv run pytest --cov=. --cov-report=html`
- **Run specific test**: `uv run pytest tests/test_models.py -v`
- **Lint code**: `pre-commit run --all-files`
- **Only run pre-commit against the files you're working on**

### Frontend (SvelteKit/TypeScript)
- **Install dependencies**: `npm install` (in `frontend/` directory)
- **Run development server**: `npm run dev`
- **Build for production**: `npm run build`
- **Preview production build**: `npm run preview`
- **Type checking**: `npm run check`
- **Generate API client**: `npm run generate-api` (requires backend running on localhost:8000)
- **Run tests**: `npm run test`
- **Run tests in watch mode**: `npm run test:watch`

### Docker
- **Build image**: `docker build -t quorum-ai .`
- **Run container**: `docker run -p 8000:8000 --env-file .env quorum-ai`

### Docker Compose Services
- **Start all services**: `docker-compose up -d`
- **Start specific services**: `docker-compose up -d postgres redis` or `docker-compose up -d backend frontend`
- **Stop all services**: `docker-compose down`
- **View service logs**: `docker-compose logs -f [service_name]`
- **Check service health**: `docker-compose ps`
- **Remove volumes**: `docker-compose down -v`
- **Rebuild services**: `docker-compose up -d --build`

#### Service Configuration
- **PostgreSQL**:
  - Port: 5432
  - Default credentials: `quorum/quorum`
  - Database: `quorum`
  - Volume: `postgres_data`
- **Redis**:
  - Port: 6379
  - Memory limit: 256MB with LRU eviction
  - Default password: `quorum`
  - Persistence: AOF enabled
  - Volume: `redis_data`
- **Backend (FastAPI)**:
  - Port: 8000
  - Health check: `/health` endpoint
  - Depends on: PostgreSQL, Redis
- **Frontend (SvelteKit)**:
  - Port: 3000
  - Depends on: Backend
  - API Base URL: `http://backend:8000`

#### Environment Variables for Docker Services
```bash
# PostgreSQL
POSTGRES_USER=quorum          # Database user
POSTGRES_PASSWORD=quorum      # Database password
POSTGRES_DB=quorum           # Database name

# Redis
REDIS_PASSWORD=quorum        # Redis password
```

## Architecture Overview

This is a full-stack DAO proposal summarization application with a Python FastAPI backend and SvelteKit frontend.

### Backend Architecture (`backend/`)
- **FastAPI application** with async/await patterns for high performance
- **Pydantic AI integration** with Claude 3.5 Sonnet via OpenRouter for AI-powered proposal summarization
- **Snapshot GraphQL API integration** for fetching DAO proposal data from Snapshot spaces
- **Service-oriented architecture**:
  - `snapshot_service.py`: Handles Snapshot space and proposal data fetching
  - `ai_service.py`: Manages AI summarization and risk assessment
  - `voting_service.py`: Handles vote submission to Snapshot
- **Pydantic models** for type-safe data validation (`models.py`)
- **Configuration management** via environment variables (`config.py`)
- **Logfire integration** for observability and distributed tracing

### Frontend Architecture (`frontend/`)
- **SvelteKit** with TypeScript for type safety and Svelte 5 with runes
- **TailwindCSS v4.x** for utility-first styling
- **OpenAPI TypeScript generation** for type-safe API client (`openapi-fetch`)
- **Vitest** with Testing Library for component testing
- **Vite** for build tooling and development server
- **Organization-based routing** with dynamic routes (`/organizations/[id]`)

### Key Integration Points
- Backend exposes OpenAPI schema at `/openapi.json`
- Frontend generates TypeScript client from OpenAPI schema
- API documentation available at `/docs` when backend is running

### Key API Endpoints
- `GET /proposals` - Proposal search and filtering by Snapshot space
- `GET /proposals/{id}` - Get specific proposal by ID
- `POST /proposals/summarize` - AI summarization for specific proposals
- `GET /proposals/{id}/top-voters` - Top voters for a proposal
- `GET /health` - Health check endpoint

## Environment Setup

### Required Environment Variables
```bash
# AI Provider (Required)
OPENROUTER_API_KEY=your_openrouter_api_key  # For Claude 3.5 Sonnet via OpenRouter

# Optional but recommended
LOGFIRE_TOKEN=your_logfire_token  # For observability
DEBUG=false  # Enable debug mode
HOST=0.0.0.0  # Server host
PORT=8000  # Server port
```

### Development Workflow
1. **Quick Start**: `./startup.sh` (starts both backend and frontend automatically)
2. **Manual Setup**:
   - Start backend: `cd backend && uv run main.py`
   - Generate API client: `cd frontend && npm run generate-api`
   - Start frontend: `cd frontend && npm run dev`
3. **Access Applications**:
   - Backend API: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Frontend: http://localhost:5173

## Code Style Guidelines

### Backend Python
- Follow FastAPI best practices from `.cursor/rules/backend.mdc`
- Use async/await for I/O operations
- Prefer functional programming over classes
- Use type hints throughout
- Keep methods under 60 lines
- Use early returns for error handling
- Implement proper error logging

### Frontend SvelteKit
- Follow Svelte best practices from `.cursor/rules/frontend.mdc`
- Use TailwindCSS classes exclusively for styling
- Use `class:` directive instead of ternary operators when possible
- Prefix event handlers with "handle" (e.g., `handleClick`)
- Use `const` for function definitions
- Implement accessibility features (aria-label, tabindex, etc.)

## Testing

- When writing tests, write out the meaning and the importance of the test explaining what it's trying to do.

### Backend Testing
- **Framework**: pytest with async support (`pytest-asyncio`)
- **Coverage**: pytest-cov with HTML reporting (`--cov=. --cov-report=html`)
- **Mocking**: pytest-mock and pytest-httpx for external API mocking
- **Test Structure**:
  - Test files in `tests/` directory following pattern: `test_*.py`
  - Fixtures in `conftest.py` for common test data
  - Integration tests for services and APIs
- **Configuration**: Strict settings in `pyproject.toml`
- **Target Coverage**: >90% expected

### Frontend Testing
- **Framework**: Vitest with jsdom environment
- **Testing Library**: @testing-library/svelte for component testing
- **Setup**: test-setup.ts for jest-dom integration
- **Commands**: `npm run test` (run once), `npm run test:watch` (watch mode)
- **Configuration**: vitest.config.ts with SvelteKit integration

### Code Clarity

    Class and method names must be self-documenting, short, and descriptive
    Remove all hardcoded values - use configuration or constants instead
    If you have a complicated expression, put the result of the expression or parts of the expression, in a temporary variable with a name that explains the purpose of the expression.

### Code Organization

    Eliminate duplicate code through extraction or abstraction
    If you have a code fragment that can be grouped together, turn the fragment into a method whose name explains the purpose of the method.
    Enforce maximum method length of 60 lines
    Decompose complex methods into smaller, single-purpose functions
    Break down large classes with excessive instance variables (>7-10)

### Code Quality

    Add runtime assertions to critical methods (minimum 2 per critical method)
    Assertions should validate key assumptions about state and parameters
    Consider consolidating scattered minor changes into cohesive classes
    Code needs to be easy for a human to read and understand. Make sure the code is explicit and clear.

### Design Priorities (in order)

    Readability - Code should be immediately understandable
    Simplicity - Choose the least complex solution
    Maintainability - Optimize for future changes
    Performance - Only optimize after the above are satisfied


## API Integration Changes (BAC-157)

### Migration from Tally to Snapshot
This application has been migrated from using Tally to Snapshot for DAO proposal data. Key changes include:

- **Data Source**: All proposal data now comes from Snapshot GraphQL API instead of Tally
- **Models**: Updated all Pydantic models to match Snapshot's data structures
- **Service Architecture**: Replaced `tally_service.py` with `snapshot_service.py`
- **GraphQL Queries**: Implemented Snapshot-specific queries for spaces, proposals, and votes
- **Vote Submission**: Updated voting mechanism to work with Snapshot's EIP-712 signatures

### Snapshot Integration Details
- **API Documentation**: https://docs.snapshot.box/tools/api
- **GraphQL Endpoint**: https://hub.snapshot.org/graphql
- **Key Services**:
  - `snapshot_service.py`: Fetches spaces, proposals, and votes from Snapshot
  - `voting_service.py`: Handles EIP-712 signature creation for vote submission
  - `ai_service.py`: Provides AI-powered summarization of Snapshot proposals

### Important Snapshot Concepts
- **Spaces**: DAO organizations on Snapshot (replaces Tally's governors)
- **Proposals**: Voting items within a space
- **Strategies**: Voting power calculation methods specific to each space
- **IPFS**: Proposal content is stored on IPFS, requiring special handling

### AI Service Updates
The AI service has been updated to work with Snapshot's data structure:
- Parses IPFS-stored proposal descriptions
- Handles Snapshot's voting choices format
- Provides risk assessment based on Snapshot proposal data
- Supports both single-choice and multiple-choice voting
# API Specification

## Overview

This document specifies the RESTful API for the Quorum AI autonomous voting agent application. All endpoints follow REST conventions and return JSON responses.

### Base URL
- Development: `http://localhost:8716`
- Production: Configured via environment variables

### Authentication
Currently, the API does not require authentication. Future iterations may add API key or OAuth2 authentication.

### Common Response Formats

#### Success Response
```json
{
  "data": {...},
  "status": "success"
}
```

#### Error Response
```json
{
  "detail": "Error message",
  "status": "error"
}
```

### HTTP Status Codes
- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Core Endpoints

### Health Check

#### GET /healthcheck
Returns comprehensive health status required for Olas Pearl integration.

This endpoint provides real-time information about agent state transitions, transaction manager health, agent operational status, and consensus rounds to help the Pearl platform monitor agent health and responsiveness.

**Response:**
```json
{
  "seconds_since_last_transition": 42.5,
  "is_transitioning_fast": false,
  "period": 5,
  "reset_pause_duration": 0.5,
  "is_tm_healthy": true,
  "agent_health": {
    "is_making_on_chain_transactions": true,
    "is_staking_kpi_met": true,
    "has_required_funds": true
  },
  "rounds": [
    {
      "round_id": 1,
      "from_state": "idle",
      "to_state": "starting",
      "timestamp": "2025-01-30T10:00:00.000Z",
      "metadata": {}
    }
  ],
  "rounds_info": {
    "total_rounds": 1,
    "latest_round": {
      "round_id": 1,
      "from_state": "idle",
      "to_state": "starting",
      "timestamp": "2025-01-30T10:00:00.000Z",
      "metadata": {}
    },
    "average_round_duration": 10.5
  }
}
```

**Field Descriptions:**

**Basic State Transition Fields:**
- `seconds_since_last_transition` (float): Time elapsed since the last state transition
- `is_transitioning_fast` (boolean): Whether the agent is transitioning between states too rapidly
- `period` (integer, optional): Time window in seconds used for fast transition detection
- `reset_pause_duration` (float, optional): Threshold in seconds for considering transitions as "fast"

**Transaction Manager Health:**
- `is_tm_healthy` (boolean): Overall transaction manager health status based on recent activity and stability

**Agent Health Object:**
- `agent_health.is_making_on_chain_transactions` (boolean): Whether the agent has made recent on-chain transactions
- `agent_health.is_staking_kpi_met` (boolean): Whether staking KPI requirements are being met (daily activity)
- `agent_health.has_required_funds` (boolean): Whether the agent has sufficient funds in Safe addresses

**Consensus Rounds:**
- `rounds` (array): Recent state transitions formatted as consensus rounds
  - `round_id` (integer): Sequential round identifier
  - `from_state` (string): Previous agent state
  - `to_state` (string): New agent state
  - `timestamp` (string): ISO 8601 timestamp of the transition
  - `metadata` (object): Additional transition metadata
- `rounds_info` (object): Metadata about consensus rounds
  - `total_rounds` (integer): Total number of recent rounds
  - `latest_round` (object|null): Most recent round data, or null if no rounds
  - `average_round_duration` (float): Average time between rounds in seconds

**Performance Requirements:**
- Response time must be under 100ms for real-time monitoring
- Uses 10-second caching to optimize performance
- Graceful error handling with safe default values

**Error Handling:**
If any component fails, the endpoint returns safe default values rather than failing:
- `is_tm_healthy`: false
- All `agent_health` fields: false  
- `rounds`: empty array
- `rounds_info`: zero/null values

---

## Proposal Endpoints

### Search Proposals

#### GET /proposals
Search and filter proposals from Snapshot spaces.

**Query Parameters:**
- `space_id` (required): The Snapshot space ID
- `state` (optional): Filter by proposal state (active, closed, pending)
- `limit` (optional, default: 20): Number of results to return
- `offset` (optional, default: 0): Pagination offset

**Response:**
```json
{
  "proposals": [
    {
      "id": "0x123...",
      "title": "Proposal Title",
      "space": {
        "id": "space.eth",
        "name": "Space Name"
      },
      "state": "active",
      "start": 1234567890,
      "end": 1234567890,
      "snapshot": "12345678",
      "author": "0xabc...",
      "choices": ["For", "Against", "Abstain"],
      "scores": [100.5, 50.2, 10.1],
      "scores_total": 160.8,
      "quorum": 100.0
    }
  ],
  "total": 100,
  "has_more": true
}
```

### Get Proposal Details

#### GET /proposals/{proposal_id}
Get detailed information about a specific proposal.

**Path Parameters:**
- `proposal_id`: The proposal ID

**Response:**
```json
{
  "id": "0x123...",
  "title": "Proposal Title",
  "body": "Full proposal description...",
  "space": {
    "id": "space.eth",
    "name": "Space Name"
  },
  "state": "active",
  "author": "0xabc...",
  "created": 1234567890,
  "start": 1234567890,
  "end": 1234567890,
  "snapshot": "12345678",
  "choices": ["For", "Against", "Abstain"],
  "scores": [100.5, 50.2, 10.1],
  "scores_total": 160.8,
  "quorum": 100.0,
  "votes": 42
}
```

### Summarize Proposals

#### POST /proposals/summarize
Generate AI summaries for multiple proposals.

**Request Body:**
```json
{
  "proposal_ids": ["0x123...", "0x456..."],
  "space_id": "space.eth"
}
```

**Response:**
```json
{
  "summaries": [
    {
      "proposal_id": "0x123...",
      "title": "Proposal Title",
      "summary": "AI-generated summary...",
      "key_points": ["Point 1", "Point 2"],
      "risk_assessment": "Low risk proposal that...",
      "recommendation": "Consider voting FOR because..."
    }
  ]
}
```

### Get Top Voters

#### GET /proposals/{proposal_id}/top-voters
Get the top voters for a specific proposal.

**Path Parameters:**
- `proposal_id`: The proposal ID

**Query Parameters:**
- `limit` (optional, default: 10): Number of top voters to return

**Response:**
```json
{
  "voters": [
    {
      "voter": "0xabc...",
      "voting_power": 1000.5,
      "choice": 1,
      "reason": "I support this because..."
    }
  ],
  "total_voters": 150
}
```

---

## Agent Run Endpoints

### Execute Agent Run

#### POST /agent-run
Trigger the autonomous voting agent to analyze and vote on proposals.

**Request Body:**
```json
{
  "space_id": "space.eth",
  "dry_run": false
}
```

**Response:**
```json
{
  "message": "Agent run completed successfully",
  "run_id": "run_123456",
  "proposals_analyzed": 15,
  "votes_cast": 3,
  "dry_run": false
}
```

### Get Agent Status

#### GET /agent-run/status
Get the current status of the autonomous voting agent.

**Response:**
```json
{
  "current_state": "idle",
  "last_run_timestamp": "2025-01-30T10:00:00Z",
  "is_active": false,
  "current_space_id": "space.eth"
}
```

**Status Values:**
- `current_state`: One of `idle`, `fetching_proposals`, `analyzing`, `voting`, `error`
- `is_active`: Boolean indicating if agent is currently running
- `last_run_timestamp`: ISO 8601 timestamp of last completed run
- `current_space_id`: The space ID from the most recent run

### Get Agent Decisions

#### GET /agent-run/decisions
Get recent voting decisions made by the agent.

**Query Parameters:**
- `limit` (optional, default: 10): Number of decisions to return

**Response:**
```json
{
  "decisions": [
    {
      "proposal_id": "0x123...",
      "proposal_title": "Proposal Title",
      "vote": "FOR",
      "confidence": 0.85,
      "timestamp": "2025-01-30T10:00:00Z",
      "space_id": "space.eth",
      "reasons": ["Aligns with DAO goals", "Low risk"]
    }
  ]
}
```

### Get Agent Statistics

#### GET /agent-run/statistics
Get aggregated statistics about the agent's performance.

**Response:**
```json
{
  "total_runs": 42,
  "total_proposals_reviewed": 256,
  "total_votes_cast": 89,
  "average_confidence": 0.78,
  "success_rate": 0.95
}
```

**Statistics Definitions:**
- `total_runs`: Total number of agent runs executed
- `total_proposals_reviewed`: Sum of all proposals analyzed
- `total_votes_cast`: Sum of all votes submitted
- `average_confidence`: Average confidence score across all votes
- `success_rate`: Percentage of runs completed without errors

---

## User Preferences Endpoints

### Get User Preferences

#### GET /user-preferences
Retrieve the current user preferences for the autonomous voting agent.

**Response:**
```json
{
  "voting_strategy": "balanced",
  "confidence_threshold": 0.7,
  "max_proposals_per_run": 10,
  "blacklisted_proposers": ["0x123...", "0x456..."],
  "whitelisted_proposers": ["0x789..."]
}
```

**Status Codes:**
- `200 OK`: Preferences found and returned
- `404 Not Found`: No preferences configured (new user)

### Update User Preferences

#### PUT /user-preferences
Update all user preferences. This is a full replacement operation.

**Request Body:**
```json
{
  "voting_strategy": "conservative",
  "confidence_threshold": 0.8,
  "max_proposals_per_run": 5,
  "blacklisted_proposers": ["0x123..."],
  "whitelisted_proposers": []
}
```

**Response:**
```json
{
  "voting_strategy": "conservative",
  "confidence_threshold": 0.8,
  "max_proposals_per_run": 5,
  "blacklisted_proposers": ["0x123..."],
  "whitelisted_proposers": []
}
```

**Validation Rules:**
- `voting_strategy`: Must be one of `conservative`, `balanced`, `aggressive`
- `confidence_threshold`: Must be between 0.0 and 1.0
- `max_proposals_per_run`: Must be between 1 and 10
- Proposer addresses must be valid Ethereum addresses

---

## Error Handling

All endpoints follow a consistent error response format:

```json
{
  "detail": "Descriptive error message",
  "status": "error",
  "code": "ERROR_CODE"
}
```

### Common Error Codes
- `VALIDATION_ERROR`: Invalid request parameters
- `NOT_FOUND`: Resource not found
- `INTERNAL_ERROR`: Server error
- `RATE_LIMITED`: Too many requests
- `SERVICE_UNAVAILABLE`: External service unavailable

### Example Error Responses

#### 400 Bad Request
```json
{
  "detail": "Invalid space_id format",
  "status": "error",
  "code": "VALIDATION_ERROR"
}
```

#### 404 Not Found
```json
{
  "detail": "Proposal not found",
  "status": "error",
  "code": "NOT_FOUND"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Failed to connect to Snapshot API",
  "status": "error",
  "code": "SERVICE_UNAVAILABLE"
}
```

---

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Default: 100 requests per minute per IP
- Agent runs: 10 requests per hour
- Bulk operations: 20 requests per hour

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Webhooks (Future)

Future versions may support webhooks for real-time notifications:
- Agent run completed
- Vote cast
- Error occurred

---

## OpenAPI Schema

The complete OpenAPI schema is available at `/openapi.json` and can be viewed interactively at `/docs` (Swagger UI) or `/redoc` (ReDoc).

### Generating TypeScript Client

Frontend developers can generate a type-safe client:
```bash
cd frontend
npm run generate-api
```

This uses the OpenAPI schema to create TypeScript types and a client in `src/lib/api/`.

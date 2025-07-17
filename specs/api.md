# API Specification

## Overview

This document defines the API standards and patterns for the Quorum AI backend service. All API endpoints must follow these guidelines to ensure consistency, security, and maintainability.

## Technology Stack

- **Framework**: FastAPI 0.115.0+
- **Server**: Uvicorn with standard extensions
- **Documentation**: OpenAPI 3.1.0 (auto-generated)
- **Validation**: Pydantic v2 for request/response validation

## API Design Principles

### 1. RESTful Design
- Use HTTP verbs appropriately (GET, POST, PUT, DELETE)
- Resource-based URLs
- Stateless operations
- Proper status codes

### 2. Consistency
- Uniform response formats
- Consistent naming conventions
- Predictable behavior

### 3. Performance
- Async/await for all I/O operations
- Efficient pagination
- Response caching where appropriate

## Application Configuration

```python
app = FastAPI(
    title="Quorum AI",
    description="Backend for sorting and summarizing DAO proposals using AI",
    version="0.1.0",
    lifespan=lifespan  # Async context manager for startup/shutdown
)
```

## API Endpoints

### Health Check

```
GET /health
```

**Purpose**: Monitor service health and availability

**Response Model**:
```python
{
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z",
    "version": "0.1.0"
}
```

**Status Codes**:
- `200 OK`: Service is healthy
- `503 Service Unavailable`: Service is unhealthy

**Implementation Requirements**:
- Must respond within 1 second
- No external dependencies
- Include version information

### Proposals API

#### List Proposals

```
GET /proposals
```

**Purpose**: Retrieve proposals from Snapshot spaces with filtering

**Query Parameters**:
| Parameter | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `space_id` | string | Yes | Snapshot space identifier | Valid space ID |
| `state` | enum | No | Proposal state filter | `pending`, `active`, `closed` |
| `limit` | integer | No | Results per page (default: 20) | 1-100 |
| `skip` | integer | No | Pagination offset (default: 0) | >= 0 |

**Response Model**:
```python
{
    "proposals": [
        {
            "id": "string",
            "title": "string",
            "body": "string",
            "state": "active",
            "space": { /* Space object */ },
            "author": "0x...",
            "created": 1234567890,
            "start": 1234567890,
            "end": 1234567890,
            "choices": ["For", "Against"],
            "scores": [100.5, 50.2],
            "scores_total": 150.7,
            "votes": 25,
            "discussion": "https://...",
            "snapshot": "12345678"
        }
    ],
    "next_cursor": "string"  // For pagination
}
```

**Status Codes**:
- `200 OK`: Success
- `422 Unprocessable Entity`: Invalid parameters
- `500 Internal Server Error`: Server error

#### Get Proposal by ID

```
GET /proposals/{proposal_id}
```

**Purpose**: Retrieve detailed information for a specific proposal

**Path Parameters**:
- `proposal_id` (string, required): Unique proposal identifier

**Response Model**: Single Proposal object (same as list item)

**Status Codes**:
- `200 OK`: Success
- `404 Not Found`: Proposal doesn't exist
- `422 Unprocessable Entity`: Invalid ID format
- `500 Internal Server Error`: Server error

#### Summarize Proposals

```
POST /proposals/summarize
```

**Purpose**: Generate AI-powered summaries for multiple proposals

**Request Body**:
```python
{
    "proposal_ids": ["id1", "id2"],  # 1-50 items
    "include_risk_assessment": true,  # default: true
    "include_recommendations": true   # default: true
}
```

**Response Model**:
```python
{
    "summaries": [
        {
            "proposal_id": "string",
            "summary": "string",
            "key_points": ["point1", "point2"],
            "risk_assessment": {
                "level": "low|medium|high",
                "factors": ["factor1", "factor2"]
            },
            "voting_recommendation": {
                "recommendation": "for|against|abstain",
                "reasoning": "string"
            }
        }
    ],
    "processing_time": 1.23,
    "model_used": "claude-3-5-sonnet"
}
```

**Status Codes**:
- `200 OK`: Success
- `422 Unprocessable Entity`: Invalid request
- `500 Internal Server Error`: Server or AI service error

#### Get Top Voters

```
GET /proposals/{proposal_id}/top-voters
```

**Purpose**: Retrieve voters with highest voting power for a proposal

**Path Parameters**:
- `proposal_id` (string, required): Proposal identifier

**Query Parameters**:
- `limit` (integer, optional): Number of voters (default: 10, max: 50)

**Response Model**:
```python
{
    "proposal_id": "string",
    "voters": [
        {
            "address": "0x...",
            "voting_power": 1000.5,
            "choice": "For",
            "reason": "Optional reason text"
        }
    ]
}
```

**Caching**:
- Active proposals: 5-minute cache
- Completed proposals: 1-hour cache
- ETag support for cache validation

**Status Codes**:
- `200 OK`: Success with Cache-Control headers
- `304 Not Modified`: ETag matches (no body)
- `404 Not Found`: Proposal doesn't exist
- `422 Unprocessable Entity`: Invalid parameters
- `500 Internal Server Error`: Server error

## Request/Response Models

### Model Design Principles

1. **Type Safety**: All fields must have explicit types
2. **Validation**: Use Pydantic validators for business rules
3. **Documentation**: Include field descriptions
4. **Examples**: Provide example values

### Base Model Configuration

```python
from pydantic import BaseModel, ConfigDict

class BaseAPIModel(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=False,
        extra="forbid"  # Reject unknown fields
    )
```

### Common Field Validations

```python
from pydantic import field_validator, Field

class ProposalRequest(BaseAPIModel):
    space_id: str = Field(..., min_length=3, max_length=100)
    limit: int = Field(default=20, ge=1, le=100)
    
    @field_validator('space_id')
    def validate_space_id(cls, v):
        if not v.replace('-', '').replace('.', '').isalnum():
            raise ValueError('Invalid space ID format')
        return v
```


### Documentation Requirements

1. **Endpoint Descriptions**:
```python
@app.get(
    "/proposals",
    summary="List proposals",
    description="Retrieve proposals from a Snapshot space with optional filtering",
    response_description="List of proposals with pagination"
)
```

2. **Model Documentation**:
```python
class Proposal(BaseModel):
    """Represents a governance proposal"""
    
    id: str = Field(..., description="Unique proposal identifier")
    title: str = Field(..., description="Proposal title", example="Fund Development")
```

3. **Example Values**:
```python
class Config:
    json_schema_extra = {
        "example": {
            "id": "0x123...",
            "title": "Increase Treasury Allocation"
        }
    }
```


## Security Best Practices

### Input Validation

1. **Sanitize All Inputs**: Use Pydantic's validators
2. **Limit Input Size**: Set maximum lengths
3. **Validate Formats**: Check patterns (addresses, IDs)

### Output Security

1. **Never Expose Sensitive Data**: Private keys, tokens
2. **Sanitize Error Messages**: Don't leak system details
3. **Use HTTPS**: Enforce TLS in production

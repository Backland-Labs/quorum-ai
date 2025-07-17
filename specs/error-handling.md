# Error Handling Specification

## Overview

This document defines the error handling standards and practices for the Quorum AI application. Consistent error handling ensures reliability, maintainability, and a good user experience across all components.

## Error Handling Philosophy

### Core Principles

1. **Fail Gracefully**: Never crash the application
2. **Inform Users**: Provide clear, actionable error messages
3. **Log Everything**: Capture detailed error context for debugging
4. **Recover When Possible**: Implement fallback mechanisms
5. **Security First**: Never expose sensitive information in errors

## Error Categories

### 1. Validation Errors (400-level)

**Description**: User input or request validation failures

**Examples**:
- Invalid Ethereum address format
- Missing required fields
- Out-of-range values

**Handling**:
```python
from pydantic import ValidationError
from fastapi import HTTPException

try:
    proposal = Proposal(**request_data)
except ValidationError as e:
    logfire.error("Validation failed", errors=e.errors())
    raise HTTPException(
        status_code=422,
        detail={
            "error": "Validation Error",
            "message": "Invalid request data",
            "details": e.errors()
        }
    )
```

### 2. Business Logic Errors

**Description**: Domain-specific rule violations

**Examples**:
- Voting on closed proposals
- Insufficient voting power
- Strategy constraints violated

**Handling**:
```python
class BusinessRuleError(Exception):
    """Custom exception for business rule violations."""
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)

# Usage
if proposal.state != ProposalState.ACTIVE:
    raise BusinessRuleError(
        message="Cannot vote on closed proposal",
        code="PROPOSAL_CLOSED"
    )
```

### 3. External Service Errors

**Description**: Third-party API failures

**Examples**:
- Snapshot API timeout
- OpenRouter rate limit
- Network connectivity issues

**Handling**:
```python
class ExternalServiceError(Exception):
    """Base exception for external service failures."""
    def __init__(self, service: str, message: str, status_code: Optional[int] = None):
        self.service = service
        self.status_code = status_code
        super().__init__(f"{service}: {message}")

# Snapshot service example
try:
    response = await self.client.post(url, json=payload)
    response.raise_for_status()
except httpx.TimeoutException:
    raise ExternalServiceError(
        service="Snapshot",
        message="Request timeout",
        status_code=None
    )
except httpx.HTTPStatusError as e:
    raise ExternalServiceError(
        service="Snapshot",
        message=f"HTTP {e.response.status_code}",
        status_code=e.response.status_code
    )
```

### 4. System Errors

**Description**: Internal application failures

**Examples**:
- File I/O errors
- Memory issues
- Unexpected states

**Handling**:
```python
try:
    with open("ethereum_private_key.txt", "r") as f:
        private_key = f.read().strip()
except FileNotFoundError:
    logfire.error("Private key file not found")
    raise SystemError("Critical configuration missing")
except IOError as e:
    logfire.error("Failed to read private key", error=str(e))
    raise SystemError("Configuration read error")
```

## Best Practices Summary

1. **Always Log Errors**: Include context, stack traces, and request IDs
2. **User-Friendly Messages**: Never expose technical details to users
3. **Fail Fast**: Validate early and provide immediate feedback
4. **Graceful Degradation**: Implement fallbacks for critical features
6. **Test Error Paths**: Ensure error handling works as expected
8. **Security First**: Never log sensitive data or expose system details
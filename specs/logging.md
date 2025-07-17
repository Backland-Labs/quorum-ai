# Logging Specification

## Overview

This document outlines the logging standards and practices for the Quorum AI application. All developers must follow these guidelines to ensure consistent, secure, and useful logging across the codebase.

## Logging Framework

### Primary Framework: Logfire

The application uses [Logfire](https://pydantic.dev/logfire) as the primary logging and observability framework.

**Configuration:**
```python
# backend/config.py
logfire_token: Optional[str] = None      # Authentication token (from environment)
logfire_project: Optional[str] = None    # Project identifier (from environment)
logfire_ignore_no_config: bool = False   # Ignore missing configuration
```

**Initialization:**
```python
# In application lifespan context (backend/main.py)
if settings.logfire_token:
    logfire.configure(
        token=settings.logfire_token,
        project_name=settings.logfire_project
    )
```

## Log Levels and Usage

### INFO Level
Use for normal application operations and state changes.

**When to use:**
- Application startup/shutdown
- Service initialization
- Successful operations
- State transitions
- Configuration changes

**Example:**
```python
logfire.info(
    "VotingService initialized",
    eoa_address=self.account.address,
    safe_addresses=self.safe_addresses
)
```

### ERROR Level
Use for system failures and unrecoverable errors.

**When to use:**
- API call failures
- Unhandled exceptions
- Critical service failures
- Data corruption or invalid states

**Example:**
```python
logfire.error(
    "Failed to fetch proposals",
    space_id=space_id,
    error=str(e),
    error_type=type(e).__name__
)
```

### WARN Level
Use for recoverable issues and non-critical problems.

**When to use:**
- Fallback behavior activated
- Deprecated feature usage
- Performance degradation
- Non-critical configuration issues

**Example:**
```python
logfire.warn(f"Could not load activity state: {e}")
```

### DEBUG Level
Use for detailed debugging information (development only).

**Configuration:** Controlled via `settings.debug` flag
**Usage:** Set server log level to "debug" when debug mode is enabled

## Structured Logging Patterns

### Context-Rich Logging

Always include relevant context parameters with log messages:

```python
logfire.info(
    "Starting vote decision making",
    proposal_id=proposal.id,
    proposal_title=proposal.title,
    strategy=strategy.value,
    model_type=str(type(self.model)),
)
```

### Consistent Field Naming

Use these standard field names across all log entries:

| Field Name | Description | Example |
|------------|-------------|---------|
| `error` | Error message string | `str(e)` |
| `error_type` | Exception class name | `type(e).__name__` |
| `count` | Number of items | `len(proposals)` |
| `status_code` | HTTP status code | `response.status_code` |
| `duration` | Time duration in seconds | `time.time() - start_time` |
| `user_id` | User identifier | `user.id` |
| `request_id` | Request correlation ID | `request.headers.get("X-Request-ID")` |


## Security and Privacy

### Sensitive Data Handling

**NEVER log:**
- Private keys
- API keys or tokens
- Passwords
- Full blockchain signatures
- Personal identifiable information (PII)

**Safe logging patterns:**
```python
# Log public addresses only
logfire.info("Account initialized", address=account.address)

# Truncate sensitive data
logfire.info(
    "Signature created",
    signature_preview=f"{signature[:10]}...{signature[-10:]}"
)

# Log data presence, not content
logfire.info("Private key loaded", has_private_key=bool(private_key))
```

### Error Message Sanitization

Ensure error messages don't leak sensitive information:

```python
try:
    # Operation
except Exception as e:
    # Sanitize error message before logging
    safe_error = str(e).replace(api_key, "***")
    logfire.error("Operation failed", error=safe_error)
```

## Best Practices

### 1. Use Runtime Assertions

Combine assertions with logging for critical invariants:

```python
assert proposal is not None, "Proposal cannot be None"
logfire.info("Processing proposal", proposal_id=proposal.id)
```

### 2. Log at Service Boundaries

Always log when:
- Entering/exiting service methods
- Making external API calls
- Processing user requests
- Handling background tasks

### 3. Include Request Context

Maintain request context throughout operations:

```python
class RequestContext:
    request_id: str
    user_id: Optional[str]

# Include in all log calls within request
logfire.info("Operation", request_id=context.request_id)
```

# Pearl Logging Infrastructure Guide

This guide documents the Pearl-compliant logging infrastructure used in the Quorum AI backend.

## Overview

The Pearl logging system provides a structured, compliant logging framework for autonomous AI agents deployed on the Pearl platform. It replaces Logfire and ensures all logs follow Pearl's specific format requirements.

## Pearl Log Format

All logs must follow this exact format:
```
[YYYY-MM-DD HH:MM:SS,mmm] [LOG_LEVEL] [agent] Message
```

Example:
```
[2025-01-18 10:30:45,123] [INFO] [agent] Starting vote decision making
```

## Core Components

### 1. **logging_config.py**
The main module containing Pearl logging infrastructure:

- **`PearlFormatter`**: Custom formatter that ensures Pearl-compliant log format
- **`StructuredAdapter`**: Adapter for structured logging while maintaining Pearl compliance
- **`setup_pearl_logger()`**: Main function to configure Pearl-compliant logger
- **`log_span()`**: Context manager for operation logging (replaces Logfire spans)
- **`validate_log_format()`**: Utility to validate log format compliance
- **`ensure_log_file_exists()`**: Ensures log.txt file exists and is writable

### 2. **config.py**
Configuration management for Pearl logging:

- **Pearl logging constants**:
  - `VALID_LOG_LEVELS`: ["DEBUG", "INFO", "WARNING", "ERROR"]
  - `DEFAULT_LOG_LEVEL`: "INFO"
  - `DEFAULT_LOG_FILE_PATH`: "log.txt"

- **Environment variables**:
  - `LOG_LEVEL`: Sets the logging level
  - `LOG_FILE_PATH`: Path to the log file (default: log.txt)
  - `STORE_PATH`: Pearl-provided path for persistent storage

## Import Requirements

To use Pearl logging in any module:

```python
from logging_config import setup_pearl_logger, log_span

# Initialize logger for your module
logger = setup_pearl_logger(__name__)
```

## API Functions and Usage

### 1. **setup_pearl_logger()**

```python
logger = setup_pearl_logger(
    name='agent',                    # Logger name (default: 'agent')
    level=logging.INFO,              # Logging level
    log_file_path=None,              # Custom log file path
    store_path=None                  # Pearl STORE_PATH environment variable
)
```

### 2. **log_span() Context Manager**

Provides structured operation logging with automatic timing and error handling:

```python
with log_span(logger, "operation_name", key1=value1, key2=value2) as span_data:
    # Your operation code here
    span_data['result'] = 'success'  # Add operation-specific data
```

Features:
- Logs operation start with context
- Automatically logs duration on completion
- Handles exceptions and logs failures
- Allows adding span-specific data

### 3. **Basic Logging Methods**

```python
# Info level logging
logger.info("Operation completed successfully")
logger.info("Processing proposal, proposal_id=%s, title=%s", proposal_id, title)

# Warning level logging
logger.warning("No AI API keys configured, using default model")

# Error level logging with exception info
logger.error("Failed to create model, error=%s, error_type=%s", str(e), type(e).__name__)

# Debug level logging
logger.debug("Detailed debug information")
```

## Logging Patterns and Conventions

### 1. **Structured Logging with Key-Value Pairs**

Always include relevant context as key-value pairs:

```python
logger.info(
    "Starting vote decision making, proposal_id=%s, proposal_title=%s, strategy=%s",
    proposal.id,
    proposal.title,
    strategy.value
)
```

### 2. **Error Logging Pattern**

Include error details and type:

```python
try:
    # operation
except Exception as e:
    logger.error(
        "Failed to process proposal, proposal_id=%s, error=%s, error_type=%s",
        proposal_id,
        str(e),
        type(e).__name__
    )
```

### 3. **Using log_span for Operations**

```python
with log_span(logger, "ai_vote_decision", proposal_id=proposal.id, strategy=strategy.value):
    logger.info("Starting vote decision making")
    
    # Perform operation
    result = await make_decision()
    
    logger.info(
        "Successfully generated vote decision, vote=%s, confidence=%s",
        result.vote,
        result.confidence
    )
```

### 4. **Service Initialization Pattern**

```python
class MyService:
    def __init__(self):
        # Initialize Pearl-compliant logger
        self.pearl_logger = setup_pearl_logger(name='my_service')
        self.pearl_logger.info("MyService initialized successfully")
```

## Migration from Logfire

When migrating from Logfire to Pearl logging:

1. **Replace imports**:
   ```python
   # Old
   import logfire
   
   # New
   from logging_config import setup_pearl_logger, log_span
   ```

2. **Replace logger initialization**:
   ```python
   # Old
   logfire.configure(service_name="agent")
   
   # New
   logger = setup_pearl_logger(__name__)
   ```

3. **Replace spans**:
   ```python
   # Old
   with logfire.span("operation"):
       # code
   
   # New
   with log_span(logger, "operation"):
       # code
   ```

4. **Replace structured logging**:
   ```python
   # Old
   logfire.info("Message", key=value)
   
   # New
   logger.info("Message, key=%s", value)
   ```

## Log Levels

Pearl uses standard log levels with one exception:
- **DEBUG**: Detailed debugging information
- **INFO**: General informational messages
- **WARN**: Warning messages (Pearl uses WARN, not WARNING)
- **ERROR**: Error messages (CRITICAL is mapped to ERROR)

## Best Practices

1. **Always use structured logging** with key-value pairs for context
2. **Use log_span** for operations that have a start/end and might fail
3. **Include relevant IDs** (proposal_id, space_id, etc.) in log messages
4. **Log at appropriate levels** - don't overuse ERROR or DEBUG
5. **Keep messages concise** but informative
6. **Use consistent naming** for context keys across the codebase
7. **Handle exceptions properly** and log them with full context

## Testing Pearl Compliance

Use the `validate_log_format()` function to ensure logs are Pearl-compliant:

```python
from logging_config import validate_log_format

log_line = "[2025-01-18 10:30:45,123] [INFO] [agent] Test message"
assert validate_log_format(log_line) == True
```

## Environment Configuration

Pearl logging respects these environment variables:
- `LOG_LEVEL`: Set to DEBUG, INFO, WARNING, or ERROR
- `LOG_FILE_PATH`: Path to log file (default: log.txt)
- `STORE_PATH`: Pearl-provided storage path (auto-detected)

## File Location

By default, logs are written to `log.txt` in:
1. The `STORE_PATH` directory if provided by Pearl
2. The current working directory otherwise

The log file is created automatically if it doesn't exist.
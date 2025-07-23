# Logging & Telemetry Specification

## Overview
This specification defines the logging system for Pearl-compliant AI agents, ensuring full compatibility with the OLAS network and Pearl platform requirements.

## Pearl Compliance Requirements

### Log File Location
- **Mandatory**: Agent must produce `log.txt` file in its working directory
- Working directory is set by Pearl platform during agent execution
- File must be accessible for Pearl monitoring and debugging

### Log Format
**Required Format**: `[YYYY-MM-DD HH:MM:SS,mmm] [LOG_LEVEL] [agent] Your message`

Example:
```
[2024-03-14 10:30:00,123] [INFO] [agent] Starting command execution
[2024-03-14 10:30:01,456] [DEBUG] [agent] Command parameters: {...}
[2024-03-14 10:30:02,789] [ERROR] [agent] Failed to connect to service
```

### Log Levels
- `ERROR`: Critical errors preventing agent execution
- `WARN`: Warning messages about potential issues
- `INFO`: General operational information
- `DEBUG`: Detailed debugging information
- `TRACE`: Verbose execution traces

## Required Packages

### Core Logging Dependencies
```bash
# Python standard library (no installation required)
import logging
import logging.handlers
from datetime import datetime
import re
import os
```

## Implementation

### Logger Configuration
```python
import logging
from datetime import datetime

def setup_pearl_logger():
    """Configure logging for Pearl compliance."""
    logger = logging.getLogger('agent')
    logger.setLevel(logging.INFO)

    # Create file handler for log.txt
    handler = logging.FileHandler('log.txt', mode='a')

    # Pearl-compliant formatter
    formatter = PearlFormatter()
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger

class PearlFormatter(logging.Formatter):
    """Custom formatter for Pearl compliance."""

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        return f"[{timestamp}] [{record.levelname}] [agent] {record.getMessage()}"
```

### Usage in Agent Code
```python
logger = setup_pearl_logger()

# Standard logging calls
logger.info("Agent initialized successfully")
logger.debug("Processing transaction: %s", tx_hash)
logger.error("Connection failed: %s", error_msg)
logger.warn("Retrying operation after timeout")
```

## Integration with Pearl Platform

### Environment Variables
The agent must respect Pearl-provided environment variables:
- `STORE_PATH`: Persistent data storage location

### Key Events to Log
1. **Agent Lifecycle**
   - Initialization and startup
   - Shutdown and cleanup
   - State recovery after SIGKILL

2. **Transaction Operations**
   - Safe contract interactions
   - EOA transactions
   - Gas estimation and execution

3. **Data Persistence**
   - State saves to STORE_PATH
   - Recovery operations
   - Data validation checks

### Compliance Validation
```python
import re

def validate_log_format(log_line):
    """Validate log line matches Pearl format."""
    pattern = r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\] \[(ERROR|WARN|INFO|DEBUG|TRACE)\] \[agent\] .*'
    return bool(re.match(pattern, log_line))
```

### Error Recovery
```python
def ensure_log_file_exists():
    """Ensure log.txt exists and is writable."""
    try:
        with open('log.txt', 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]}] [INFO] [agent] Log file initialized\n")
        return True
    except Exception as e:
        print(f"Failed to initialize log file: {e}")
        return False
```

## Best Practices

1. **Log Early and Often**: Log all significant agent operations
2. **Use Appropriate Levels**: Reserve ERROR for actual failures
3. **Include Context**: Add transaction hashes, addresses, amounts
4. **Handle Failures**: Ensure logging doesn't crash the agent
5. **Performance**: Avoid excessive DEBUG logging in production

This specification ensures full compliance with Pearl platform requirements while providing comprehensive observability for autonomous AI agent operations.

# Database Specification

## Overview

This document defines the data persistence and storage patterns for the Quorum AI application. The current implementation uses a lightweight, file-based persistence approach suitable for agent-based deployment on local machines.

## Current Architecture

### Storage Strategy

The application uses **file-based JSON storage** for persistent state management:

- **No traditional database**: No PostgreSQL, MySQL, MongoDB, or Redis
- **JSON file persistence**: State stored in local JSON files
- **Minimal persistence requirements**: Only activity tracking requires persistence
- **Stateless design**: Most operations fetch data from external APIs

### Rationale

This architecture is designed for:
1. **Container deployment**: Runs on Olas Pearl App store in local containers
2. **Minimal dependencies**: No database server required
3. **Agent autonomy**: Self-contained operation without external services
4. **Simple deployment**: No database migration or setup needed

## Data Storage Patterns

### 1. Activity State Persistence

**File**: `activity_tracker.json`

**Location**: Configurable via `settings.store_path`, defaults to application root

**Schema**:
```json
{
    "last_activity_date": "2024-01-15",
    "last_tx_hash": "0x123..."
}
```

**Implementation**:
```python
class ActivityService:
    def __init__(self):
        if settings.store_path:
            self.persistent_file = os.path.join(
                settings.store_path, "activity_tracker.json"
            )
        else:
            self.persistent_file = "activity_tracker.json"
```

### 2. Private Key Storage

**File**: `ethereum_private_key.txt`

**Security Requirements**:
- Plain text file (encrypted at rest by container)
- Never committed to version control
- Read once on service initialization
- File permissions: 600 (read/write owner only)

**Best Practices**:
```python
# Read private key securely
def load_private_key():
    key_path = os.environ.get("PRIVATE_KEY_PATH", "ethereum_private_key.txt")
    if not os.path.exists(key_path):
        raise ValueError("Private key file not found")
    
    with open(key_path, "r") as f:
        private_key = f.read().strip()
    
    # Validate key format
    if not private_key.startswith("0x"):
        private_key = f"0x{private_key}"
    
    return private_key
```

## Data Models

### Transient Data (Not Persisted)

The following data is fetched from external APIs and not persisted:

1. **Proposals**: Retrieved from Snapshot API
2. **Spaces**: DAO information from Snapshot
3. **Votes**: Voting data from Snapshot
4. **AI Summaries**: Generated on-demand
5. **Voting Decisions**: Calculated in real-time

### Persistent Data

Only the following data requires persistence:

1. **Activity Tracking**:
   - Last activity date
   - Last transaction hash
   - OLAS compliance status

2. **Configuration** (via environment):
   - API keys
   - Network settings
   - Service endpoints

## File I/O Patterns

### Safe File Writing

Always use atomic writes to prevent corruption:

```python
def save_state(self) -> None:
    """Save state with atomic write operation."""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.persistent_file), exist_ok=True)
        
        # Write to temporary file first
        temp_file = f"{self.persistent_file}.tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        
        # Atomic rename
        os.replace(temp_file, self.persistent_file)
        
        logfire.info("State saved successfully")
    except Exception as e:
        logfire.error(f"Failed to save state: {e}")
        # Clean up temp file if exists
        if os.path.exists(temp_file):
            os.remove(temp_file)
```

## Data Validation

### JSON Schema Validation

Define schemas for persistent data:

```python
ACTIVITY_SCHEMA = {
    "type": "object",
    "properties": {
        "last_activity_date": {
            "type": "string",
            "format": "date"
        },
        "last_tx_hash": {
            "type": "string",
            "pattern": "^0x[a-fA-F0-9]{64}$"
        }
    },
    "required": ["last_activity_date"]
}

def validate_activity_data(data: dict) -> bool:
    """Validate activity data against schema."""
    try:
        jsonschema.validate(data, ACTIVITY_SCHEMA)
        return True
    except jsonschema.ValidationError:
        return False
```

## Best Practices Summary

1. **Keep It Simple**: File-based storage is sufficient for current needs
2. **Handle Errors Gracefully**: Always fallback to defaults
3. **Atomic Operations**: Prevent partial writes
8. **Test Thoroughly**: Include corruption and concurrency scenarios

# State Management Specification

This specification defines the state persistence system for the Quorum AI agent, ensuring reliable data storage across agent restarts and providing atomic operations for data integrity within the Pearl/Olas environment.

## Overview

The State Management system provides a robust, file-based persistence layer that handles all persistent data storage for the agent. It ensures data integrity through atomic operations, supports state versioning for compatibility, and provides automatic backup and recovery mechanisms. The system is designed to be resilient against corruption, handle concurrent access safely, and integrate seamlessly with the Pearl platform's storage requirements.

## Architecture

### System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  AgentRunService    │  UserPreferencesService  │  Other Services │
└────────────────────┴───────────────────────────┴─────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                         StateManager                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Atomic Save │  │ Schema Valid │  │ Version Management     │ │
│  │ Operations  │  │ & Migration  │  │ & Compatibility        │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Corruption  │  │ Concurrent   │  │ Backup & Recovery      │ │
│  │ Detection   │  │ Access Lock  │  │ System                 │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Storage Backend                            │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ State Files │  │ Backup Files │  │ Temporary Files        │ │
│  │ (.json)     │  │ (.backup)    │  │ (.tmp)                 │ │
│  └─────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Storage Organization

```
$STORE_PATH/
├── state/
│   ├── agent_config.json
│   ├── user_preferences.json
│   ├── agent_checkpoint_*.json
│   └── backups/
│       ├── agent_config.20240115_120000_123456.backup
│       └── user_preferences.20240115_121500_654321.backup
└── logs/
    └── pearl/
```

## State Categories

### 1. Configuration State

**Purpose**: Store agent configuration parameters that persist across restarts

**Examples**:
- Agent polling intervals
- Retry configurations
- Feature flags
- API endpoints

**Characteristics**:
- Low write frequency
- Critical for agent operation
- Requires validation on load

### 2. User Preferences State

**Purpose**: Store user-defined voting strategies and preferences

**Examples**:
- Voting strategies (balanced, conservative, aggressive)
- Risk thresholds
- Auto-vote settings
- Space-specific overrides

**Characteristics**:
- Medium write frequency
- User-modifiable
- Requires schema validation

### 3. Operational State

**Purpose**: Track agent runtime state for recovery and monitoring

**Examples**:
- Active voting operations
- Processing checkpoints
- Error recovery state
- Service health status

**Characteristics**:
- High write frequency during operations
- Used for crash recovery
- May contain transient data

### 4. Sensitive State

**Purpose**: Store sensitive information with enhanced security

**Examples**:
- Private keys (when managed locally)
- API credentials
- Authentication tokens

**Characteristics**:
- Requires restricted file permissions (0600)
- Enhanced validation on access
- Optional encryption support

## Core Components

### StateManager Class

**Purpose**: Central manager for all state persistence operations

**Responsibilities**:
- Atomic file operations
- Schema validation
- Version migration
- Backup management
- Concurrent access control
- Corruption detection and recovery

**Implementation**:

```python
class StateManager:
    """Manages persistent state storage for the Quorum AI agent."""
    
    def __init__(self):
        """Initialize the state manager with configured storage paths."""
        # Set up Pearl-compliant logging
        self.logger = setup_pearl_logger("state_manager")
        
        # Get store path from environment or use default
        store_path_env = os.environ.get("STORE_PATH")
        if store_path_env:
            self.store_path = Path(store_path_env)
        else:
            self.store_path = Path.home() / ".quorum_ai" / "state"
        
        # Ensure store path exists
        self.store_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for organization
        self.backups_dir = self.store_path / "backups"
        self.backups_dir.mkdir(exist_ok=True)
        
        # File locks for concurrent access protection
        self._locks: Dict[str, asyncio.Lock] = {}
        
        # Maximum number of backups to keep
        self.max_backups = 5
```

### StateSchema Class

**Purpose**: Define and validate state data structure

**Implementation**:

```python
@dataclass
class StateSchema:
    """Defines the schema for validating state data."""
    
    required_fields: List[str]
    field_types: Dict[str, type]
    validators: Dict[str, Callable[[Any], bool]]

# Example usage
preferences_schema = StateSchema(
    required_fields=['voting_strategy', 'risk_threshold'],
    field_types={
        'voting_strategy': str,
        'risk_threshold': float,
        'auto_vote_enabled': bool
    },
    validators={
        'risk_threshold': lambda x: 0.0 <= x <= 1.0,
        'voting_strategy': lambda x: x in ['balanced', 'conservative', 'aggressive']
    }
)
```

### StateVersion Class

**Purpose**: Manage semantic versioning for state compatibility

**Implementation**:

```python
@dataclass(frozen=True)
class StateVersion:
    """Represents a semantic version for state schemas."""
    
    major: int
    minor: int
    patch: int
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __lt__(self, other: "StateVersion") -> bool:
        return (self.major, self.minor, self.patch) < (
            other.major, other.minor, other.patch
        )
```

## Implementation Details

### Atomic Save Operations

**Purpose**: Ensure state saves are atomic to prevent corruption

**Process**:
1. Create temporary file with new data
2. Write complete state with metadata
3. Set appropriate permissions
4. Atomic rename to final location
5. Clean up on failure

**Implementation**:

```python
async def save_state(
    self,
    name: str,
    data: Dict[str, Any],
    sensitive: bool = False,
    schema: Optional[StateSchema] = None,
    version: Optional[StateVersion] = None,
) -> Path:
    """Save state data atomically."""
    # Validate schema if provided
    if schema:
        self._validate_schema(data, schema)
    
    # Get or create lock for this state file
    if name not in self._locks:
        self._locks[name] = asyncio.Lock()
    
    async with self._locks[name]:
        state_file = self.store_path / f"{name}.json"
        
        # Create backup of existing file
        if state_file.exists():
            await self._create_backup(name, state_file)
        
        # Prepare state data with metadata
        state_data = {
            "version": str(version) if version else "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "checksum": self._calculate_checksum(data),
        }
        
        # Write atomically using temporary file
        temp_fd, temp_path = tempfile.mkstemp(dir=self.store_path, suffix=".tmp")
        try:
            with os.fdopen(temp_fd, "w") as f:
                json.dump(state_data, f, indent=2)
            
            # Set permissions for sensitive files
            if sensitive:
                os.chmod(temp_path, 0o600)
            
            # Atomic rename
            Path(temp_path).replace(state_file)
            
            self.logger.info(f"Successfully saved state: {name}")
            return state_file
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            self.logger.error(f"Failed to save state {name}: {e}")
            raise
```

### Corruption Detection

**Purpose**: Detect and recover from corrupted state files

**Methods**:
1. SHA256 checksum validation
2. JSON structure validation
3. Schema conformance checking
4. Automatic backup recovery

**Implementation**:

```python
def _calculate_checksum(self, data: Dict[str, Any]) -> str:
    """Calculate SHA256 checksum of data."""
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()

async def _load_and_validate_state(
    self, state_file: Path, name: str, target_version: Optional[StateVersion]
) -> Dict[str, Any]:
    """Load state data and validate integrity."""
    with open(state_file, "r") as f:
        state_data = json.load(f)
    
    # Verify checksum
    if "checksum" in state_data:
        expected_checksum = state_data["checksum"]
        actual_checksum = self._calculate_checksum(state_data["data"])
        if expected_checksum != actual_checksum:
            raise StateCorruptionError(f"State file {name} has checksum mismatch")
    
    return state_data.get("data", state_data)
```

### Version Migration

**Purpose**: Upgrade state data structures between versions

**Process**:
1. Detect current state version
2. Find applicable migrations
3. Apply migrations in order
4. Update version metadata

**Implementation**:

```python
async def _apply_migrations(
    self, data: Dict[str, Any], from_version: StateVersion, to_version: StateVersion
) -> Dict[str, Any]:
    """Apply migrations to upgrade data to target version."""
    current_data = data
    
    # Find and apply migrations in order
    for (from_v, to_v), migration_func in sorted(self._migrations.items()):
        if from_v >= from_version and to_v <= to_version:
            if asyncio.iscoroutinefunction(migration_func):
                current_data = await migration_func(current_data)
            else:
                current_data = migration_func(current_data)
            
            self.logger.info(f"Applied migration from {from_v} to {to_v}")
    
    return current_data

# Example migration
async def migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate strategy field to voting_strategy."""
    if 'preferences' in data and 'strategy' in data['preferences']:
        data['preferences']['voting_strategy'] = data['preferences'].pop('strategy')
    return data
```

## State Persistence Patterns

### Service Integration Pattern

**Purpose**: Standard pattern for services to integrate with state management

**Implementation**:

```python
class MyService:
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager
        self.logger = setup_pearl_logger(__name__)
    
    async def save_service_state(self) -> None:
        """Save current service state."""
        if not self.state_manager:
            return
        
        state_data = {
            "version": "1.0.0",
            "last_update": datetime.now(timezone.utc).isoformat(),
            "service_data": self._get_current_state()
        }
        
        await self.state_manager.save_state(
            'my_service',
            state_data,
            schema=self._get_state_schema()
        )
    
    async def load_service_state(self) -> Optional[Dict[str, Any]]:
        """Load saved service state."""
        if not self.state_manager:
            return None
        
        return await self.state_manager.load_state(
            'my_service',
            schema=self._get_state_schema(),
            allow_recovery=True
        )
```

### Checkpoint Pattern

**Purpose**: Save intermediate state during long-running operations

**Implementation**:

```python
async def process_with_checkpoints(self, items: List[Any]) -> None:
    """Process items with checkpoint saves."""
    checkpoint_interval = 10
    
    for i, item in enumerate(items):
        # Process item
        result = await self._process_item(item)
        
        # Save checkpoint periodically
        if i % checkpoint_interval == 0 and self.state_manager:
            checkpoint_data = {
                "processed": i + 1,
                "total": len(items),
                "last_item_id": item.id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.state_manager.save_state(
                f'checkpoint_{self.operation_id}',
                checkpoint_data
            )
```

## Concurrency and Safety

### Lock Management

**Purpose**: Prevent concurrent modifications to state files

**Implementation**:

```python
# Per-file locks prevent race conditions
if name not in self._locks:
    self._locks[name] = asyncio.Lock()

async with self._locks[name]:
    # Perform state operations
    pass
```

### Atomic Operations

**Requirements**:
- All writes must be atomic (temp file + rename)
- No partial writes allowed
- Rollback on any failure
- Maintain backup before overwrite

### Thread Safety

**Guarantees**:
- AsyncIO locks for coroutine safety
- File-level locking for process safety
- Atomic filesystem operations
- No shared mutable state

## Error Handling

### Error Types

```python
class StateCorruptionError(Exception):
    """Raised when state file corruption is detected."""
    pass

class StateMigrationError(Exception):
    """Raised when state migration fails."""
    pass

class StatePermissionError(Exception):
    """Raised when file permissions are insufficient."""
    pass
```

### Recovery Strategies

**1. Corruption Recovery**:
```python
try:
    data = await state_manager.load_state("config")
except StateCorruptionError:
    # Attempt automatic recovery from backup
    data = await state_manager.load_state("config", allow_recovery=True)
    if not data:
        # Use defaults if no backup available
        data = get_default_config()
```

**2. Permission Recovery**:
```python
try:
    data = await state_manager.load_state("keys", sensitive=True)
except StatePermissionError:
    logger.error("State file has incorrect permissions")
    # Fix permissions and retry
    fix_file_permissions(state_file)
    data = await state_manager.load_state("keys", sensitive=True)
```

**3. Migration Recovery**:
```python
try:
    data = await state_manager.load_state("prefs", target_version=v2)
except StateMigrationError:
    # Load without migration and handle manually
    data = await state_manager.load_state("prefs")
    data = manual_migration(data)
```

## Security Considerations

### File Permissions

**Requirements**:
- Sensitive files: 0600 (owner read/write only)
- Regular files: 0644 (owner write, others read)
- Directories: 0755 (owner full, others read/execute)

**Implementation**:

```python
def _validate_file_permissions(self, state_file: Path, name: str) -> None:
    """Validate file permissions for sensitive files."""
    stat_info = os.stat(state_file)
    permissions = stat_info.st_mode & 0o777
    if permissions != 0o600:
        raise StatePermissionError(
            f"State file {name} has insufficient permissions: {oct(permissions)}"
        )
```

### Sensitive Data Handling

**Best Practices**:
1. Always mark sensitive state with `sensitive=True`
2. Never log sensitive data contents
3. Use restricted permissions automatically
4. Consider encryption for highly sensitive data
5. Clean up temporary files on errors

### Path Traversal Prevention

**Safeguards**:
- Validate state names (alphanumeric + underscore only)
- No directory separators in state names
- All paths resolved relative to `STORE_PATH`
- No symlink following for state files

## Best Practices

### 1. State Design

- **Keep state minimal**: Only persist what's necessary for recovery
- **Use schemas**: Always define schemas for structured data
- **Version from start**: Include version info even for v1.0.0
- **Separate concerns**: Different state files for different purposes

### 2. Error Handling

- **Always handle corruption**: Use `allow_recovery=True` for critical state
- **Log all failures**: Include state name and error details
- **Provide defaults**: Have sensible defaults for missing state
- **Test recovery paths**: Ensure backup recovery works

### 3. Performance

- **Batch operations**: Save state at checkpoints, not every change
- **Async operations**: Use async/await for all I/O
- **Limit backup count**: Rotate old backups (default: 5)
- **Compress large state**: Consider compression for >1MB state

### 4. Integration

- **Dependency injection**: Pass StateManager to services that need it
- **Graceful degradation**: Services should work without state manager
- **Shutdown hooks**: Save state during graceful shutdown
- **Migration planning**: Design state changes to be backward compatible

### 5. Testing

```python
@pytest.fixture
async def state_manager(tmp_path):
    """Create isolated state manager for testing."""
    with patch.dict(os.environ, {'STORE_PATH': str(tmp_path)}):
        manager = StateManager()
        yield manager
        await manager.cleanup()

async def test_service_with_state(state_manager):
    """Test service state persistence."""
    service = MyService(state_manager=state_manager)
    
    # Test save
    await service.save_service_state()
    
    # Test load
    loaded = await service.load_service_state()
    assert loaded is not None
```

## Example Usage

### Basic State Operations

```python
# Initialize state manager
state_manager = StateManager()

# Save simple configuration
await state_manager.save_state("agent_config", {
    "poll_interval": 300,
    "max_retries": 3,
    "enabled": True
})

# Save with schema validation
schema = StateSchema(
    required_fields=['voting_strategy'],
    field_types={'voting_strategy': str},
    validators={'voting_strategy': lambda x: x in ['balanced', 'conservative']}
)

await state_manager.save_state("preferences", {
    "voting_strategy": "balanced"
}, schema=schema)

# Load with recovery
config = await state_manager.load_state(
    "agent_config",
    allow_recovery=True
)

# Save sensitive data
await state_manager.save_state("api_keys", {
    "openrouter": "sk-..."
}, sensitive=True)
```

### Service Integration

```python
class AgentRunService:
    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager
    
    async def save_checkpoint(self, run_id: str, progress: Dict[str, Any]):
        """Save execution checkpoint."""
        if not self.state_manager:
            return
        
        await self.state_manager.save_state(
            f'checkpoint_{run_id}',
            {
                "progress": progress,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    async def resume_from_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Resume from saved checkpoint."""
        if not self.state_manager:
            return None
        
        checkpoint = await self.state_manager.load_state(
            f'checkpoint_{run_id}',
            allow_recovery=True
        )
        
        return checkpoint.get("progress") if checkpoint else None
```

### Migration Example

```python
# Define migration function
def migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add default risk_threshold to v1 data."""
    if 'risk_threshold' not in data:
        data['risk_threshold'] = 0.7
    return data

# Register migration
state_manager.register_migration(
    StateVersion(1, 0, 0),
    StateVersion(2, 0, 0),
    migrate_v1_to_v2
)

# Load with automatic migration
data = await state_manager.load_state(
    "user_config",
    target_version=StateVersion(2, 0, 0)
)
```
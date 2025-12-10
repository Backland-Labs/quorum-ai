## Overview

Implement support for V3 Ethereum Keystore format to securely store encrypted agent EOA private keys, enabling Pearl V1 compatibility while maintaining backwards compatibility with the current plaintext key format used by Quickstart.

The implementation will:
1. Add `--password` CLI argument support to the agent startup
2. Modify `KeyManager` to detect and decrypt V3 Keystore JSON format
3. Support `KEY_PASSWORD` environment variable as a fallback
4. Maintain full backwards compatibility with plaintext keys

## Implementation Task List:
1. **CLI Argument Handling** - Add argparse for `--password` to main.py and pass through entrypoint.sh
2. **KeyManager V3 Detection** - Add V3 Keystore JSON format detection in KeyManager
3. **KeyManager Decryption** - Implement V3 keystore decryption using eth_account.Account.decrypt()
4. **Service Updates** - Update service consumers to support optional password parameter
5. **Unit Tests** - Add comprehensive unit tests for V3 keystore support
6. **Script Updates** - Update checkpoint.py to accept password argument

## Current State Analysis

### Key Management Architecture
- **KeyManager** (`backend/services/key_manager.py:32-194`): Central service for private key access
  - Reads plaintext keys from `ethereum_private_key.txt`
  - 5-minute memory caching with expiration
  - Validates format with regex: `^(0x)?[a-fA-F0-9]{64}$`
  - File located at `/agent_key/ethereum_private_key.txt` (configurable via `AGENT_KEY_DIR`)

### Key Consumers
- **SafeService** (`backend/services/safe_service.py:82-84`): Loads key at init, stores as instance variable
- **VotingService** (`backend/services/voting_service.py:41-58`): Accepts optional KeyManager, lazy-loads key
- **checkpoint.py** (`backend/scripts/checkpoint.py:75-77`): Script creates own KeyManager instance

### Agent Startup
- **Entry point**: `backend/entrypoint.sh:103` runs `uv run --no-sync python -O main.py`
- **No CLI argument parsing** currently exists - all config via environment variables
- Docker mounts `ethereum_private_key.txt` to `/agent_key/ethereum_private_key.txt`

### Dependencies Available
- `eth-account>=0.13.7` already in pyproject.toml - provides `Account.decrypt()`

## Desired End State

After implementation:
1. **V3 Keystore Detection**: `KeyManager` automatically detects if `ethereum_private_key.txt` contains V3 Keystore JSON (by checking for `"version": 3`)
2. **Password Decryption**: When `--password` CLI argument or `KEY_PASSWORD` environment variable is provided, encrypted keys are decrypted using `eth_account.Account.decrypt()`
3. **Clear Error Messages**: If encrypted key found but no password provided, raise `KeyManagerError` with clear message
4. **Backwards Compatibility**: Plaintext keys continue to work without any password
5. **All tests pass**: Existing tests unaffected, new tests cover V3 keystore functionality

### Verification:
```bash
# Test plaintext key (existing behavior)
echo "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" > /tmp/ethereum_private_key.txt
AGENT_KEY_DIR=/tmp uv run pytest backend/tests/test_key_manager.py -v

# Test V3 keystore with password
# (Create V3 keystore file, then test with --password)
uv run python -O main.py --password "test_password"

# Test V3 keystore error without password
# (Should fail with clear error message)
```

### Key Discoveries:
- `eth_account.Account.decrypt()` takes keystore JSON (as dict or string) and password - `backend/pyproject.toml:19`
- `VotingService` already accepts optional `key_manager` parameter - `backend/services/voting_service.py:38-43`
- `SafeService` creates its own `KeyManager` in `__init__` - needs modification - `backend/services/safe_service.py:82`
- No existing KeyManager tests found - need to create `backend/tests/test_key_manager.py`

## What We're NOT Doing

1. **NOT** implementing key generation/encryption - only decryption support
2. **NOT** modifying the Docker compose or Dockerfile - password passed via CLI/env
3. **NOT** changing file permissions handling - existing 600 permissions remain
4. **NOT** adding GUI password input - CLI only
5. **NOT** implementing password storage/caching - password used once at startup
6. **NOT** changing the key file location or naming conventions
7. **NOT** adding password rotation or change functionality

## Implementation Approach

### Architecture Decision: Global Password Storage
Since the password is provided at application startup and services are initialized in the lifespan context, we'll:
1. Parse `--password` argument in `main.py` before FastAPI app creation
2. Store password in a module-level variable accessible to services
3. Pass password to `KeyManager` constructor
4. `KeyManager` handles detection and decryption internally

### V3 Keystore Detection Logic
```python
def _is_v3_keystore(self, content: str) -> bool:
    try:
        keystore = json.loads(content)
        return isinstance(keystore, dict) and keystore.get("version") == 3
    except json.JSONDecodeError:
        return False
```

### Decryption Flow
1. Read file content
2. Check if V3 keystore format
3. If V3 and password provided: decrypt using `Account.decrypt()`
4. If V3 and no password: raise `KeyManagerError`
5. If plaintext: validate with existing regex

## Files to Edit

| File | Lines | Changes |
|------|-------|---------|
| `backend/main.py` | 1-10, 1393-1402 | Add argparse, module-level password storage |
| `backend/services/key_manager.py` | 8-23, 42-65, 124-193 | Add json import, password param, V3 detection and decryption |
| `backend/services/safe_service.py` | 82-84 | Pass password to KeyManager |
| `backend/services/voting_service.py` | 41-43 | Pass password when creating KeyManager |
| `backend/scripts/checkpoint.py` | 1-30, 74-77 | Add argparse, pass password to KeyManager |
| `backend/entrypoint.sh` | 103 | Pass --password from env var if set |
| `backend/tests/test_key_manager.py` | (new file) | Comprehensive unit tests |

---

## Task 1: Add CLI Argument Handling to main.py

**File**: `backend/main.py`

**Description of Changes**:

1. Add imports at top of file (after line 7):
   - `import argparse`
   - `import sys` (if not present)

2. Add module-level variable after imports (around line 52):
   - `_key_password: Optional[str] = None`

3. Add function to get password:
   ```python
   def get_key_password() -> Optional[str]:
       """Get the key password for encrypted keystore files."""
       return _key_password
   ```

4. Add early argument parsing before FastAPI app creation (around line 230):
   - Parse `--password` from sys.argv
   - Check `KEY_PASSWORD` environment variable as fallback
   - Store in module-level `_key_password`
   - Use `parse_known_args` to avoid conflicts with uvicorn args

5. Modify the `if __name__ == "__main__":` block (lines 1393-1402):
   - Remove duplicate parsing since it's done at module level

### Success Criteria:

#### Automated Verification:
- [ ] `python main.py --help` shows `--password` argument
- [ ] `python main.py --password test` starts without argument error
- [ ] Unit tests pass: `uv run pytest backend/tests/ -v`
- [ ] Type checking passes: `cd backend && uv run mypy main.py --ignore-missing-imports`

#### Manual Verification:
- [ ] Application starts with `--password` argument
- [ ] Application starts without `--password` argument (backwards compatible)
- [ ] `KEY_PASSWORD` environment variable is used when `--password` not provided

---

## Task 2: Add V3 Keystore Detection and Decryption to KeyManager

**File**: `backend/services/key_manager.py`

**Description of Changes**:

1. Add import at top (line 9):
   - `import json`

2. Add import for Account (after line 12):
   - `from eth_account import Account`

3. Modify `__init__` method (lines 42-65):
   - Add optional `password: Optional[str] = None` parameter
   - Store as `self._password = password`
   - Log (without exposing password) whether password was provided

4. Add new private method `_is_v3_keystore`:
   - Takes content string as parameter
   - Attempts to parse as JSON
   - Returns True if valid JSON with `"version": 3`
   - Returns False on JSONDecodeError or if not V3

5. Modify `_read_file_content` method (lines 151-167):
   - After reading content, check if it's V3 keystore
   - If V3 and password provided: decrypt and return hex private key
   - If V3 and no password: raise KeyManagerError with clear message
   - If not V3: return content as-is (existing behavior)

6. Add new private method `_decrypt_v3_keystore`:
   - Takes keystore dict and password
   - Uses `Account.decrypt(keystore, password)`
   - Returns decrypted private key as hex string with 0x prefix
   - Handles decryption errors (wrong password) with clear error message

7. Update docstrings to document V3 keystore support

### Success Criteria:

#### Automated Verification:
- [ ] Unit tests pass for plaintext keys (existing behavior)
- [ ] Unit tests pass for V3 keystore with correct password
- [ ] Unit tests pass for V3 keystore with wrong password (error)
- [ ] Unit tests pass for V3 keystore without password (error)
- [ ] Type checking passes: `cd backend && uv run mypy services/key_manager.py --ignore-missing-imports`

#### Manual Verification:
- [ ] Plaintext key file works without password
- [ ] V3 keystore file works with correct `--password`
- [ ] V3 keystore file fails with clear error without password
- [ ] V3 keystore file fails with clear error with wrong password

---

## Task 3: Update Service Consumers to Support Password

**Files**:
- `backend/services/safe_service.py`
- `backend/services/voting_service.py`

**Description of Changes for safe_service.py**:

1. Modify `__init__` method (lines 81-84):
   - Import get_key_password inside method to avoid circular import
   - Get password from `get_key_password()`
   - Pass password to KeyManager constructor:
     ```python
     from main import get_key_password
     self.key_manager = KeyManager(password=get_key_password())
     ```

**Description of Changes for voting_service.py**:

1. Modify `__init__` method (lines 41-43):
   - When creating new KeyManager (not passed in), pass password:
     ```python
     from main import get_key_password
     self.key_manager = key_manager or KeyManager(password=get_key_password())
     ```

### Success Criteria:

#### Automated Verification:
- [ ] Existing tests pass: `uv run pytest backend/tests/test_safe_service.py -v`
- [ ] Type checking passes for both files

#### Manual Verification:
- [ ] SafeService initializes correctly with V3 keystore and password
- [ ] VotingService initializes correctly with V3 keystore and password
- [ ] Both services work with plaintext keys (backwards compatible)

---

## Task 4: Update checkpoint.py Script

**File**: `backend/scripts/checkpoint.py`

**Description of Changes**:

1. Add argparse import at top of file (if not present)
2. Add argument parsing at the beginning of the script:
   - Add `--password` argument for key decryption
   - Check `KEY_PASSWORD` environment variable as fallback

3. Modify KeyManager instantiation (line 75):
   - Pass password to KeyManager constructor

4. Ensure the script can be called with password:
   ```bash
   uv run --script scripts/checkpoint.py --password "test"
   ```

### Success Criteria:

#### Automated Verification:
- [ ] `python scripts/checkpoint.py --help` shows `--password` argument
- [ ] Script syntax is valid: `python -m py_compile scripts/checkpoint.py`

#### Manual Verification:
- [ ] Script works with plaintext key (no password)
- [ ] Script works with V3 keystore and `--password`

---

## Task 5: Update entrypoint.sh

**File**: `backend/entrypoint.sh`

**Description of Changes**:

1. Modify line 103 to pass `--password` from environment variable if set:
   ```bash
   # Build command with optional password
   if [ -n "$KEY_PASSWORD" ]; then
       uv run --no-sync python -O main.py --password "$KEY_PASSWORD" &
   else
       uv run --no-sync python -O main.py &
   fi
   ```

2. Update checkpoint cron job (line 60) to pass password:
   ```bash
   # Add password to checkpoint script if KEY_PASSWORD is set
   if [ -n "$KEY_PASSWORD" ]; then
       echo "$FUTURE_MINUTE $FUTURE_HOUR * * * cd /app && timeout 300 uv run --quiet --script scripts/checkpoint.py --password \"\$KEY_PASSWORD\" >> /app/logs/checkpoint.log 2>&1" >> "$CRON_FILE"
   else
       echo "$FUTURE_MINUTE $FUTURE_HOUR * * * cd /app && timeout 300 uv run --quiet --script scripts/checkpoint.py >> /app/logs/checkpoint.log 2>&1" >> "$CRON_FILE"
   fi
   ```

### Success Criteria:

#### Automated Verification:
- [ ] Shellcheck passes: `shellcheck backend/entrypoint.sh` (or no critical errors)
- [ ] Script syntax is valid: `bash -n backend/entrypoint.sh`

#### Manual Verification:
- [ ] Container starts with `KEY_PASSWORD` environment variable
- [ ] Container starts without `KEY_PASSWORD` (backwards compatible)

---

## Task 6: Create Comprehensive Unit Tests

**File**: `backend/tests/test_key_manager.py` (new file)

**Description of Changes**:

Create new test file with the following test cases:

1. **Test plaintext key loading (existing behavior)**
   - Valid plaintext key with 0x prefix
   - Valid plaintext key without 0x prefix
   - Invalid format key (error case)

2. **Test V3 keystore detection**
   - Valid V3 keystore JSON is detected
   - Invalid JSON is not detected as V3
   - JSON without version field is not detected as V3
   - JSON with version != 3 is not detected as V3

3. **Test V3 keystore decryption**
   - Decryption with valid password succeeds
   - Decryption with wrong password raises error with clear message
   - V3 keystore without password raises error with clear message

4. **Test caching behavior**
   - Key is cached after first load
   - Cache expires after timeout
   - Cache can be cleared manually

5. **Test file not found error**
   - Missing file raises KeyManagerError

6. **Test backwards compatibility**
   - Plaintext key works without password parameter
   - Password parameter is ignored for plaintext keys

### Success Criteria:

#### Automated Verification:
- [ ] All new tests pass: `uv run pytest backend/tests/test_key_manager.py -v`
- [ ] Coverage for key_manager.py >= 90%: `uv run pytest backend/tests/test_key_manager.py --cov=services.key_manager --cov-report=term-missing`

#### Manual Verification:
- [ ] Test output is clear and descriptive
- [ ] Test names describe what they're testing

---

## Migration Notes

### For Pearl V1 Users
1. Generate V3 keystore file using eth-account or web3.py
2. Place V3 keystore JSON in `ethereum_private_key.txt`
3. Set `KEY_PASSWORD` environment variable or pass `--password` to agent

### For Quickstart Users
- No changes required - plaintext keys continue to work
- Password parameters are optional and ignored for plaintext keys

### Docker Deployment
```yaml
services:
  quorum:
    environment:
      - KEY_PASSWORD=${KEY_PASSWORD}  # Optional for encrypted keys
```

## References

- V3 Keystore Spec: https://github.com/ethereum/wiki/wiki/Web3-Secret-Storage-Definition
- eth-account decrypt: https://eth-account.readthedocs.io/en/stable/eth_account.html#eth_account.account.Account.decrypt
- Pearl V1 Requirements: Issue description
- Similar implementation: `backend/services/voting_service.py:35-62` (lazy key loading pattern)

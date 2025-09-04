.PHONY: clean clean-all clean-python clean-frontend clean-contracts clean-logs clean-state clean-artifacts help

help:
	@echo "Available targets:"
	@echo "  clean           - Clean all cache and temporary files"
	@echo "  clean-all       - Alias for clean"
	@echo "  clean-python    - Clean Python cache files"
	@echo "  clean-frontend  - Clean frontend build files and node_modules"
	@echo "  clean-contracts - Clean Solidity build artifacts"
	@echo "  clean-logs      - Clean log files"
	@echo "  clean-state     - Clean state and runtime files"
	@echo "  clean-artifacts - Clean test artifacts"

clean: clean-python clean-frontend clean-contracts clean-logs clean-state clean-artifacts
	@echo "✅ All cache and temporary files cleaned"

clean-all: clean

clean-python:
	@echo "🧹 Cleaning Python cache files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f backend/uv.lock
	@echo "✅ Python cache files cleaned"

clean-frontend:
	@echo "🧹 Cleaning frontend files..."
	rm -rf frontend/node_modules/
	rm -rf frontend/build/
	rm -f frontend/bun.lockb
	rm -f frontend/package-lock.json
	@echo "✅ Frontend cache files cleaned"

clean-contracts:
	@echo "🧹 Cleaning Solidity build artifacts..."
	rm -rf contracts/out/
	rm -rf contracts/cache/
	rm -rf contracts/broadcast/
	rm -f contracts/foundry.lock
	@echo "✅ Solidity build artifacts cleaned"

clean-logs:
	@echo "🧹 Cleaning log files..."
	find . -name "log.txt" -delete
	find . -name "*.log" -delete
	rm -rf test-data/logs/
	@echo "✅ Log files cleaned"

clean-state:
	@echo "🧹 Cleaning state and runtime files..."
	rm -f backend/agent_state.json
	rm -f backend/shutdown_state.json
	rm -f backend/user_preferences.txt
	rm -f backend/ethereum_private_key.txt
	rm -rf backend/agent_state/
	rm -rf test-data/state/
	@echo "✅ State and runtime files cleaned"

clean-artifacts:
	@echo "🧹 Cleaning test artifacts..."
	rm -rf test-artifacts/
	@echo "✅ Test artifacts cleaned"
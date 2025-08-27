#!/bin/bash
cd /Users/max/code/quorum-ai/backend
echo "Running Configuration Tests..."
uv run pytest tests/test_config.py::TestAttestationTrackerConfiguration -v
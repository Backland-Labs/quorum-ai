#!/bin/bash
cd /Users/max/code/quorum-ai/backend
uv run main.py &
echo $! > backend.pid
echo "Backend started with PID: $(cat backend.pid)"
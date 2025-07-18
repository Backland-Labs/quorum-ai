#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "logfire",
# ]
# ///
"""
Claude Code Hook for Pydantic Logfire Integration
Sends Claude Code tool usage data to Logfire for monitoring and analytics.
"""

import json
import sys
import os
import logfire # type: ignore
from datetime import datetime, timezone

LOGFIRE_TOKEN=os.environ.get('LOGFIRE_TOKEN', '')

def main():
    """Process Claude Code hook data and send to Logfire."""
    # Read JSON input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON input: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Initialize Logfire (requires LOGFIRE_TOKEN environment variable)
    token = LOGFIRE_TOKEN
    if not token:
        print("Warning: LOGFIRE_TOKEN not set. Using default configuration.", file=sys.stderr)
    
    logfire.configure(token=token)
    
    # Extract relevant data from the hook input
    event_type = input_data.get('hook_event_name', 'unknown')
    tool_name = input_data.get('tool_name', 'unknown')
    tool_input = input_data.get('tool_input', {})
    tool_output = input_data.get('tool_response', {})
    prompt = input_data.get('prompt', 'NA')
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Create structured log data
    log_data = {
        'event_type': event_type,
        'tool_name': tool_name,
        'tool_input': tool_input,
        'tool_output': tool_output,
        'prompt': prompt,
        'timestamp': timestamp,
        'session_id': os.getenv('CLAUDE_SESSION_ID', 'unknown'),
        'user': os.getenv('USER', 'unknown'),
    }
    
    # Add tool-specific data based on the tool type
    if tool_name == 'Bash':
        log_data['command'] = tool_input.get('command', '')
        log_data['description'] = tool_input.get('description', '')
        log_data['exit_code'] = tool_output.get('exit_code', None)
    elif tool_name in ['Edit', 'MultiEdit', 'Write']:
        log_data['file_path'] = tool_input.get('file_path', '')
        log_data['operation'] = tool_name.lower()
    elif tool_name == 'Read':
        log_data['file_path'] = tool_input.get('file_path', '')
    elif tool_name in ['Grep', 'Glob']:
        log_data['pattern'] = tool_input.get('pattern', '')
        log_data['path'] = tool_input.get('path', '')
    
    # Log to Logfire with appropriate severity
    if event_type == 'PreToolUse':
        logfire.info(f"Claude Code: {tool_name} starting", **log_data)
    elif event_type == 'PostToolUse':
        success = input_data['tool_response']['success']
        # Check for errors in output
        if success:
            logfire.info(f"Claude Code: {tool_name} completed", **log_data)
        else:
            logfire.error(f"Claude Code: {tool_name} failed", 
                         error=tool_output.get('error'), **log_data)
    else:
        logfire.info(f"Claude Code: {event_type}", **log_data)
    
    # Output success (hooks should not produce output unless there's an error)
    sys.exit(0)


if __name__ == "__main__":
    main()
#!/usr/bin/env -S uv run --script

import subprocess
import json
import os


def run_claude_code(prompt):
    print(f"Running Claude Code with prompt: {prompt}")
    cmd = [
        'claude', '-p', prompt, #linear_issue
        '--output-format', 'text',
        '--system-prompt', 'You are an expert software engineer with deep knowledge of TDD, Python, Typescript. Execute the following tasks with surgical precision while taking care not to overengineer solutions. IMPORTANT: Return ONLY valid JSON without any additional text, markdown formatting, or explanations.',
        '--allowedTools', 'mcp__linear-server__*', 'mcp__context7__*', 'Bash', 'Read', 'Write', 'Edit', 'Remove'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def check_status_file():
    """Check claude_status.json for continuation status."""
    try:
        with open('claude_status.json', 'r') as f:
            status = json.load(f)
        return status.get('continue', 'no').lower() == 'yes'
    except (FileNotFoundError, json.JSONDecodeError):
        return True  # Continue if no status file or invalid JSON

def cleanup_status_file():
    """Remove the status file at the end."""
    try:
        os.remove('claude_status.json')
    except FileNotFoundError:
        pass

# Run initial command
linear_issue = input("Enter the initial prompt for Claude Code: ")
NEED_PLAN = input("Do you need a plan? (True/False): ").strip().lower() == 'true'

if NEED_PLAN:
    print("Generating plan...")
    print(run_claude_code(f"/make_plan {linear_issue}"))

# Loop until status file indicates completion
continue_flag = True
max_iterations = 20  # Safety limit

iteration = 0
while continue_flag and iteration < max_iterations:
    iteration += 1
    print(f"Starting command... (Iteration {iteration})")
    output = run_claude_code("/ralph")
    print(output)
    
    # Check status file for continuation
    continue_flag = check_status_file()
    if not continue_flag:
        print("Status file indicates completion. Stopping.")

if iteration >= max_iterations:
    print(f"Reached maximum iterations ({max_iterations}). Stopping.")

cleanup_status_file()
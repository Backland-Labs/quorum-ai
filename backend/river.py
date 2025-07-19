#!/usr/bin/env -S uv run --script

import subprocess

def run_claude_code(prompt):
    cmd = [
        'claude', '-p', f"/make_plan {prompt}", #linear_issue
        '--output-format', 'json',
        '--system-prompt', 'You are an expert software engineer with deep knowledge of TDD, Python, Typescript. Execute the following tasks with surgical precision while taking care not to overengineer solutions. IMPORTANT: Return ONLY valid JSON without any additional text, markdown formatting, or explanations.',
        '--allowedTools', 'mcp__linear-server__*', 'mcp__context7__*', 'Bash', 'Read', 'Write', 'Edit', 'Remove'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def parse_continue(output):
    return 'continue=true' in output.lower()

# Run initial command
linear_issue = input("Enter the initial prompt for Claude Code: ")
print(run_claude_code(linear_issue))

# Loop until continue=false
continue_flag = True
while continue_flag:
    output = run_claude_code("/ralph")
    print(output)
    continue_flag = parse_continue(output)
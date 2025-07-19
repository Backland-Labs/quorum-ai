#!/usr/bin/env -S uv run --script

import subprocess
import json

def run_claude_code(prompt):
    print(f"Running Claude Code with prompt: {prompt}")
    cmd = [
        'claude', '-p', prompt, #linear_issue
        '--output-format', 'json',
        '--system-prompt', 'You are an expert software engineer with deep knowledge of TDD, Python, Typescript. Execute the following tasks with surgical precision while taking care not to overengineer solutions. IMPORTANT: Return ONLY valid JSON without any additional text, markdown formatting, or explanations.',
        '--allowedTools', 'mcp__linear-server__*', 'mcp__context7__*', 'Bash', 'Read', 'Write', 'Edit', 'Remove'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def parse_continue(result_dict):
    # Check if the result contains a continue flag
    if isinstance(result_dict, dict):
        result_text = result_dict.get('result', '')
        # Look for explicit continue flag in the result text
        if 'continue=true' in result_text.lower():
            return True
        elif 'continue=false' in result_text.lower():
            return False
    # Default to False if no explicit continue flag found
    return False

# Run initial command
linear_issue = input("Enter the initial prompt for Claude Code: ")
print(run_claude_code(f"/make_plan {linear_issue}"))

# Loop until continue=false
continue_flag = True
while continue_flag:
    print("Starting Ralph command...")
    output = run_claude_code("/ralph")
    print(output)
    try:
        output_dict = json.loads(output)
        continue_flag = parse_continue(output_dict)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        continue_flag = False


'''{"type":"result","subtype":"success","is_error":false,"duration_ms":469812,"duration_api_ms":416822,"num_turns":18,"result":"I've successfully created a comprehensive implementation plan for BAC-173 (Agent Interface Layer) in `plan.md`. Here's a summary of what the plan includes:\n\n## Plan Overview\n\nThe plan provides a detailed, TDD-friendly breakdown of implementing the Pearl Agent Interface Layer with:\n\n### Key Sections:\n\n1. **Overview & Objectives**\n   - Implement core agent infrastructure for Pearl platform integration\n   - Focus on state management, key handling, and blockchain integration\n\n2. **Prioritized Features (P0-P3)**\n   - P0: Critical requirements like signal handling, state persistence\n   - P1: Core features like Safe contract management, health monitoring\n   - P2: Advanced features like withdrawal mode, metrics\n   - P3: Nice-to-have enhancements\n\n3. **Detailed Task Breakdown**\n   - 8 phases of implementation\n   - Each task includes:\n     - Specific test cases to write first (TDD)\n     - Implementation steps\n     - Integration points\n     - Justification for testing\n\n4. **Risk Assessment**\n   - Technical risks (signal handling, state corruption, security)\n   - Integration risks (Pearl platform changes, service coordination)\n   - Mitigation strategies for each risk\n\n5. **Success Criteria**\n   - Functional requirements checklist\n   - Non-functional requirements (performance, reliability)\n   - Testing requirements (>90% coverage)\n   - Documentation requirements\n\n6. **Resource Estimates**\n   - 10-14 days total development effort\n   - Week-by-week implementation schedule\n   - Required technical resources\n\n### Key Implementation Highlights:\n\n- **Signal Handling**: Graceful shutdown with SIGTERM/SIGINT support\n- **State Persistence**: Atomic saves with corruption recovery\n- **Private Key Security**: Enhanced validation and secure loading\n- **Pearl Interface**: Command processing and event streaming\n- **Multi-chain Support**: Safe wallet integration across chains\n- **Withdrawal Mode**: Emergency fund recovery capability\n\nEach task is designed to be completed in one TDD cycle (red-green-refactor) with clear boundaries and testable outcomes. The plan emphasizes Pearl platform compliance while maintaining the existing service architecture.","session_id":"369014cf-51ef-48f3-88e6-60313791a9db","total_cost_usd":6.5635146,"usage":{"input_tokens":34,"cache_creation_input_tokens":39201,"cache_read_input_tokens":152633,"output_tokens":5978,"server_tool_use":{"web_search_requests":0},"service_tier":"standard"}}'''
#!/bin/bash

# Prompt definitions
GET_NEXT_SUBISSUE_PROMPT='Use Linear MCP to:
1. Get parent issue $PARENT_ISSUE_ID and all sub-issues
2. Find the next sub-issue that is NOT "Done" or "In Review"
3. Return the first unprocessed sub-issue

Return JSON format:
{
  "has_next": true | false,
  "issue": {"id": "issue_id", "title": "title", "description": "desc"} | null
}'

CREATE_PLAN_PROMPT='Create a detailed implementation plan for the Linear sub-issue provided. The plan should break down the work into granular, TDD-friendly tasks.

Issue id: $ISSUE_ID
Issue Title: $TITLE
Issue Description: $DESCRIPTION

Steps:
1. **Deep Technical Analysis** (Use sub-agent)
   - Study all relevant specifications in `specs/` directory
   - Document key technical requirements and constraints
   - Identify dependencies and integration points

2. **Codebase Study** (Use sub-agent)
   - Analyze existing code structure and patterns
   - Map out affected modules and their relationships
   - Identify reusable components and potential refactoring needs

3. **Create Detailed plan.md**
   Generate a plan.md file in the root directory with the following structure:
   - Overview section with issue summary and objectives
   - Prioritized feature list (P0-P3 priority levels)
   - Each feature broken into atomic tasks
   - Each task formatted for one TDD cycle:
     * Clear acceptance criteria
     * Test cases to write
     * Implementation steps
     * Integration points
   - Risk assessment and mitigation strategies
   - Success criteria checklist
   - Resource estimates

Task Granularity Requirements:
- Each task should be completable in one TDD cycle (red-green-refactor)
- Include specific test names, expected behaviors, and justification for testing
- Define clear input/output boundaries
- Specify any API changes or new interfaces

Return JSON format:
{
  "status": "complete" | "incomplete"
}'

IMPLEMENT_FEATURE_PROMPT='## Context
- Current directory: !`pwd`
- plan.md location: !`find . -name "plan.md"`

## Primary Task
You are a very senior engineer. Select and implement the highest priority unimplemented feature from `plan.md` using Test-Driven Development (TDD) methodology.

## Step-by-Step Process

### 1. Analysis Phase
- Use a subagent to read `plan.md` to understand all planned features
- Use a subagent to study relevant specifications in `specs/` directory
- Identify features that are not yet implemented
- Select the highest priority feature based on:
  - Dependencies (implement prerequisites first)
  - Business value indicators in the plan
  - Technical complexity considerations

### 2. Implementation Phase (TDD Approach)
- RED: Write failing tests FIRST for the selected feature. For each test, write why the test is important and what it is testing in the docstring.
- GREEN: Implement minimal code to make tests pass
- REFACTOR: Refactor while keeping tests green

### 3. Completion Phase
- Update `plan.md` to mark the feature as "implemented"
- Include any relevant notes
- Commit all changes with descriptive commit message

## Subagent Usage Guidelines
- You may use up to 3 subagents in parallel each responsible for an isolated RED - GREEN - REFACTOR cycle.

## Success Criteria
- [ ] Feature is fully implemented with passing tests
- [ ] `plan.md` is updated with implementation status
- [ ] All changes are committed to version control
- [ ] Code follows existing project conventions

## Commit Message Format
```
feat: Implement [feature name] from plan.md

- Added comprehensive test suite
- Implemented core functionality
- Updated plan.md status to '"'"'implemented'"'"'
- Follows TDD methodology
```

Return JSON format:
{
  "status": "complete" | "incomplete",
  "feature_implemented": "feature name",
  "all_features_complete": true | false
}'

COMPLETE_ISSUE_PROMPT='Complete the current Linear issue implementation:

Context: Execute these steps ONLY after all tasks in plan.md are implemented. If implementation is incomplete, continue working on the remaining tasks first.

Steps:
1. Verify all tasks in plan.md are complete
2. Read the contents of plan.md file from root directory
3. Add plan.md contents as a comment to the current Linear sub-issue using the Linear MCP
4. Update Linear issue status to "In Review" using the Linear MCP
5. Remove plan.md file from root directory
6. Commit the plan.md removal with message: "chore: remove plan.md after issue completion"
7. Fetch next available issue from Linear backlog

Return JSON format:
{
  "status": "complete" | "incomplete"
}'

execute_claude() {
    local prompt="$1"
    claude -p "$prompt" \
        --output-format json \
        --system-prompt "You are an expert software engineer with deep knowledge of TDD, Python, Typescript. Execute the following tasks with surgical precision while taking care not to overengineer solutions." \
        --allowedTools "mcp__linear__*" "mcp__context7__*" "Bash" "Read" "Write" "Edit" "Remove"
}

get_next_subissue() {
    local parent_issue_id="$1"
    local prompt=$(PARENT_ISSUE_ID="$parent_issue_id" envsubst <<< "$GET_NEXT_SUBISSUE_PROMPT")
    execute_claude "$prompt"
}

create_plan() {
    local issue_id="$1"
    local title="$2"
    local description="$3"
    local prompt=$(ISSUE_ID="$issue_id" TITLE="$title" DESCRIPTION="$description" envsubst <<< "$CREATE_PLAN_PROMPT")
    execute_claude "$prompt"
}

implement_next_feature() {
    execute_claude "$IMPLEMENT_FEATURE_PROMPT"
}

complete_issue() {
    local issue_id="$1"
    local prompt=$(ISSUE_ID="$issue_id" envsubst <<< "$COMPLETE_ISSUE_PROMPT")
    execute_claude "$prompt"
}

main() {
    echo "Enter Linear parent issue ID:"
    read parent_issue_id
    
    while true; do
        echo "Getting next sub-issue..."
        
        next_issue_json=$(get_next_subissue "$parent_issue_id")
        has_next=$(echo "$next_issue_json" | jq -r '.has_next // false')
        
        if [[ "$has_next" != "true" ]]; then
            echo "No more sub-issues to process!"
            break
        fi
        
        issue_id=$(echo "$next_issue_json" | jq -r '.issue.id')
        issue_title=$(echo "$next_issue_json" | jq -r '.issue.title')
        issue_desc=$(echo "$next_issue_json" | jq -r '.issue.description')
        
        echo "=== Processing Issue: $issue_title ==="
        
        echo "Creating implementation plan..."
        plan_json=$(create_plan "$issue_id" "$issue_title" "$issue_desc")
        plan_status=$(echo "$plan_json" | jq -r '.status // "incomplete"')
        
        if [[ "$plan_status" != "complete" ]]; then
            echo "Failed to create plan, skipping issue"
            continue
        fi
        
        echo "Plan created successfully"
        
        while true; do
            echo "Implementing next feature..."
            
            impl_json=$(implement_next_feature)
            impl_status=$(echo "$impl_json" | jq -r '.status // "incomplete"')
            
            if [[ "$impl_status" != "complete" ]]; then
                echo "Feature implementation failed"
                break
            fi
            
            feature_name=$(echo "$impl_json" | jq -r '.feature_implemented // "Unknown"')
            echo "✓ Implemented: $feature_name"
            
            all_complete=$(echo "$impl_json" | jq -r '.all_features_complete // false')
            if [[ "$all_complete" == "true" ]]; then
                echo "All features in plan completed!"
                break
            fi
        done
        
        echo "Completing issue..."
        complete_json=$(complete_issue "$issue_id")
        complete_status=$(echo "$complete_json" | jq -r '.status // "incomplete"')
        
        if [[ "$complete_status" == "complete" ]]; then
            echo "✓ Issue $issue_title completed and updated in Linear"
        else
            echo "Failed to complete issue cleanup"
        fi
        
        echo "Finished processing: $issue_title"
    done
    
    echo "All sub-issues processed!"
}

if ! command -v claude &> /dev/null; then
    echo "Error: Claude Code not found"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: jq not found"
    exit 1
fi

main "$@"
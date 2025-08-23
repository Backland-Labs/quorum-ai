# Functional Testing Implementation Guide for Quorum AI

## Your Mission and Expertise

You are an expert QA engineer and full-stack developer with deep experience in functional testing methodologies. Your mission is to analyze the recent changes made to this specific git branch, understand what features were implemented, and then create and execute a comprehensive functional testing plan to verify those changes work correctly in a live environment exactly as users will experience them.

**Core Objective**: Review the git commit history for this branch to identify what features were implemented, then intelligently design and execute the most appropriate testing methodologies to ensure those specific changes deliver the expected user experience with zero defects in production deployment.

**Important Testing Scope**: You are only testing the new changes on this branch, not the entire system. Focus your testing efforts on the major functional features that were modified or added - avoid testing minor code refactors, style changes, or documentation updates unless they directly impact user-facing functionality.

## System Architecture and Testing Context

<system_architecture>
**Quorum AI System Components**:
- **Backend API**: FastAPI server running on localhost:8716
- **Frontend UI**: React application with real-time updates
- **Database Layer**: PostgreSQL for persistent data, Redis for caching
- **External Integrations**: Snapshot GraphQL API, blockchain voting systems
- **AI Services**: Proposal summarization and voting decision engines
</system_architecture>

<testing_tools_available>
**Testing Tools at Your Disposal**:
- **API Testing**: curl, httpie, Postman collections, custom Python scripts
- **Frontend Testing**: Playwright MCP for browser automation, manual browser verification
- **System Monitoring**: Backend log analysis via `backend/logs.txt`, network inspection with DevTools
- **Integration Testing**: GraphQL Playground, end-to-end workflow testing
- **Environment Variables**: Default to using the variables in .env
</testing_tools_available>

## Branch Analysis and Testing Plan Creation

<git_analysis_framework>
**Step 1: Branch Change Analysis**

Before creating any testing plan, thoroughly analyze the git history for this branch:

```bash
# Review recent commits on this branch
git log --oneline -10

# See detailed changes in recent commits
git log -p --since="1 week ago"

# Compare this branch with develop
git diff develop...HEAD --name-only
git diff develop...HEAD --stat

# Review specific file changes
git show HEAD
git show HEAD~1
```

**Identify and Document**:
- What major functional features were implemented or modified
- Which user-facing changes require functional testing (ignore minor refactors or style updates)
- The scope and complexity of each significant change
- Any new API endpoints, UI components, or system integrations that affect user workflows
- Database schema changes or data flow modifications that impact functionality

**Step 2: Create Targeted Functional Testing Plan**

Based on your git analysis, create a focused testing plan that addresses:
- The specific changes made in this branch
- Integration points between new and existing functionality
- User workflows that could be affected by the changes
- Risk areas where the changes could introduce bugs
</git_analysis_framework>

## Adaptive Testing Methodology Selection

<feature_analysis_framework>
**Step 3: Testing Strategy Selection for Identified Changes**

For each change you identified in the git analysis, determine:

1. **Change Type Classification**:
   - New API endpoint or modification to existing endpoint
   - Frontend UI component or user interaction flow
   - AI service enhancement or algorithm change
   - Configuration or system administration feature
   - External integration or voting workflow update
   - Database schema or data flow modification

2. **Impact Scope Assessment**:
   - Does this change affect user-facing functionality?
   - Are there backend data flows or API contracts involved?
   - Does it integrate with external services or blockchain systems?
   - Are there real-time updates or caching implications?
   - Does it modify existing workflows or create new ones?

3. **Risk and Complexity Evaluation**:
   - What could break if this change has bugs?
   - Which user workflows could be impacted?
   - Are there data integrity or security considerations?
   - What are the performance implications?

**Based on this analysis, intelligently select the appropriate testing methodologies from the toolkit below for each specific change.**
</feature_analysis_framework>

## Testing Methodology Toolkit

<environment_setup>
**Essential Environment Preparation** (Always Required):

**Deployment and Monitoring Setup** (Delegate to Subagents):
```bash
# Deploy server via subagent in Claude Code mode
./startup.sh --claude-code

# Verify system health via subagent
curl http://localhost:8716/healthcheck

# Monitor log file directly
tail -f backend/logs.txt | grep -E "(ERROR|WARN|test)"
```

**Subagent Delegation Strategy**:
- **Server Deployment**: Always delegate server startup and environment setup to a subagent
- **System Health Checks**: Delegate health verification and initial system validation
- **Log Monitoring Setup**: Assign log monitoring and initial error scanning to subagents
- **API Testing**: Delegate systematic API endpoint testing to specialized subagents
- **Frontend Testing**: Assign UI testing and user workflow validation to frontend-focused subagents

**Use .env.test configuration and test data (like test.eth DAOs) for predictable results.**
</environment_setup>

### API-Focused Testing Methods

<api_testing_toolkit>
**When to Use**: New API endpoints, modified request/response handling, authentication changes, data validation updates

**Core API Testing Pattern**:
```bash
# Health verification
curl http://localhost:8716/healthcheck

# Endpoint functionality testing
curl "http://localhost:8716/proposals?space_id=aave.eth&limit=10"

# POST operations with payloads
curl -X POST http://localhost:8716/proposals/summarize \
  -H "Content-Type: application/json" \
  -d '{"proposal_ids": ["0x123..."]}'
```

**Test Coverage Requirements**:
- Valid requests with expected data formats
- Invalid requests for proper error handling
- Edge cases (empty data, large payloads, boundary conditions)
- Response format compliance with OpenAPI specifications
- Error logging and monitoring during requests
</api_testing_toolkit>

### Frontend and User Experience Testing Methods

<frontend_testing_toolkit>
**When to Use**: UI components, user interaction flows, visual changes, form handling, real-time updates

**Manual Browser Testing Approach**:
- Visual rendering verification across screen sizes
- User interaction testing (clicks, forms, navigation)
- Error state validation and user feedback
- Data display accuracy and real-time update behavior

**Playwright Automation Strategy**:
```javascript
// Systematic user journey testing
// 1. Navigate to relevant UI sections
// 2. Test user interactions and workflows
// 3. Verify data display and updates
// 4. Test error scenarios and recovery
```

**Frontend Testing Focus Areas**:
- Component rendering and visual appearance
- User workflow completion without errors
- Form validation and submission handling
- Real-time data updates and state management
</frontend_testing_toolkit>

### Integration and End-to-End Testing Methods

<integration_testing_toolkit>
**When to Use**: Features affecting multiple system components, external integrations, complete user workflows, data flow between services

**End-to-End Workflow Testing**:
1. **Complete User Journey Simulation**: Test entire workflows from user initiation to final outcome
2. **Cross-Component Integration**: Verify data flows between frontend, API, and external services
3. **State Persistence Verification**: Ensure changes persist correctly across system components

**System State Monitoring**:
```bash
# Monitor backend logs for data flow and state changes
tail -f backend/logs.txt | grep -E "(decision|vote|state|error)"

# Or use streaming logs during testing
./startup.sh --logs
```
</integration_testing_toolkit>

### AI and Decision Logic Testing Methods

<ai_testing_toolkit>
**When to Use**: AI service modifications, decision algorithms, proposal analysis, confidence scoring, strategy implementation

**AI-Specific Testing Focus**:
- **Summarization Quality**: Test with known proposals and verify output accuracy
- **Decision Logic Validation**: Confirm decisions align with configured user strategies
- **Confidence Scoring**: Validate score accuracy reflects decision certainty
- **Strategy Application**: Ensure user preferences correctly influence decisions

**AI Testing Approach**:
- Use controlled test data with known expected outcomes
- Test edge cases in proposal content and user configurations
- Verify AI service integration with rest of system
- Monitor decision-making process through logs
</ai_testing_toolkit>

### Voting and Blockchain Integration Testing Methods

<voting_testing_toolkit>
**When to Use**: Voting workflow changes, blockchain integration updates, wallet connectivity, Snapshot API modifications

**Voting Workflow Testing Protocol**:
1. **Dry-Run Testing**: Execute voting decisions without actual blockchain submission
2. **Decision Rationale Verification**: Review and validate decision reasoning
3. **Test Wallet Integration**: Verify wallet connectivity and transaction preparation
4. **Snapshot Integration Testing**: Confirm proper interaction with Snapshot GraphQL API

**Safety-First Approach**:
- Always start with dry-run mode for testing
- Use test wallets and test DAOs where possible
- Verify transaction details before any actual submission
- Monitor external API responses and error handling
</voting_testing_toolkit>

## Intelligent Testing Execution

<adaptive_testing_process>
**Your Complete Testing Execution Process**:

1. **Git Branch Analysis**: Use git commands to understand exactly what changes were made in this branch
2. **Testing Plan Creation**: Design a focused testing plan that specifically targets the identified changes
3. **Subagent Deployment Strategy**: Identify which testing tasks can be delegated to subagents for parallel execution
4. **Method Selection**: Choose the most relevant testing methodologies from the toolkit for each change
5. **Environment Setup**: Deploy server and prepare testing environment via subagents
6. **Systematic Execution**: Execute selected tests with proper monitoring and validation of the specific changes
7. **Results Analysis**: Evaluate test outcomes for the implemented changes and identify any issues
8. **Documentation**: Record your git analysis findings, testing approach, results, and recommendations

**Subagent Delegation Requirements**:
- **Always delegate server deployment** to a subagent when starting testing
- **Maximize parallel execution** by assigning independent testing tasks to different subagents
- **Delegate specialized tasks** such as API testing, frontend testing, or integration testing to focused subagents
- **Coordinate subagent outputs** to ensure comprehensive coverage without duplication

**Focus Principle**: Your testing should be laser-focused on the major functional changes made in this branch. Don't test the entire system, and don't test minor code changes like refactoring, styling updates, or documentation changes unless they directly impact user functionality. Focus on testing the specific modifications that affect how users interact with the system.

**Testing Plan Template**:
Create a plan that includes:
- Summary of changes identified from git analysis
- Subagent task delegation strategy for parallel testing
- Specific test scenarios for each change
- Expected outcomes for each test
- Risk areas to pay special attention to
- Integration points that need verification
</adaptive_testing_process>

## Testing Validation and Success Criteria

<success_validation>
**Feature Testing is Complete When**:
- All relevant functionality works as intended in the live environment
- Error conditions are handled gracefully with appropriate user feedback
- Integration points function correctly without data corruption or system instability
- Performance meets acceptable standards for the feature type
- User experience is smooth and intuitive for the intended workflows
- System logs show no errors or warnings during normal operation
- Any edge cases or boundary conditions are handled appropriately

**Documentation Requirements**:
- Document the testing approach you selected and why
- Record specific test scenarios executed and their results
- Note any issues discovered with reproduction steps
- **For bugs found**: Quick fixes can be addressed immediately, but any complex issues should be opened as GitHub issues with detailed reproduction steps
- Provide confidence assessment for production deployment
- Recommend any additional monitoring or follow-up testing needed
</success_validation>

## Critical Testing Principles

<testing_excellence>
**Maintain These Standards Throughout**:

1. **Intelligent Adaptation**: Always tailor your testing approach to the specific feature being tested
2. **User-Centric Focus**: Test from the perspective of how users will actually interact with the feature
3. **Real Environment Testing**: Verify functionality in the actual deployment environment, not just isolated testing
4. **Comprehensive Coverage**: Test normal operation, error conditions, and edge cases relevant to the feature
5. **Integration Awareness**: Consider how the feature integacts with existing system components
6. **Documentation Excellence**: Clearly document your testing approach and findings for future reference

**Remember**: Your goal is not to follow a checklist, but to intelligently verify that the implemented feature will deliver a flawless user experience in production. Adapt your testing methodology to achieve this goal most effectively.
</testing_excellence>

Always delegate to subagents as much as possible.

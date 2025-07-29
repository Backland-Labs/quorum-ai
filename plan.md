# Autonomous Voting Dashboard - Implementation Plan

## 1. Overview

**Issue**: The application's core feature, the autonomous voting agent, is fully functional but lacks visibility on the main dashboard. Users cannot monitor the agent's status, review its decisions, or trigger runs easily.

**Objective**: Elevate the autonomous voting agent to be the central feature of the dashboard by creating dedicated UI components that display the agent's status, recent decisions, and performance statistics, backed by a new set of backend APIs. This plan outlines the minimal implementation required to achieve this.

**Guiding Principle**: This plan follows a strict Test-Driven Development (TDD) methodology. For each task, tests will be written first to define the expected behavior (Red), then code will be written to pass those tests (Green), and finally, the code will be refactored for clarity and maintainability.

---

## 2. Prioritized Feature Implementation

### P0: Core Agent Visibility (Backend)

#### Task 1.1: Create `GET /agent-run/status` Endpoint ✅ IMPLEMENTED

*   **Why**: To provide the frontend with real-time agent status, enabling the Agent Status Widget. This is the most critical piece of information for the user.
*   **Acceptance Criteria**:
    *   Endpoint returns the current state from `StateTransitionTracker`. ✅
    *   Endpoint returns the timestamp of the last completed run from the latest checkpoint. ✅
    *   Endpoint returns an `is_active` flag based on `/healthcheck` logic. ✅
*   **Test Cases (Red)**:
    *   `test_get_status_returns_correct_structure()`: Verify response contains `current_state`, `last_run_timestamp`, `is_active`, `current_space_id`. ✅
    *   `test_get_status_when_no_runs_have_occurred()`: Ensure it returns a default "never run" state gracefully. ✅
    *   `test_get_status_reflects_latest_checkpoint()`: Ensure the timestamp is from the most recent checkpoint file. ✅
*   **Implementation (Green)**: ✅ COMPLETED
    1.  Add a new route `GET /agent-run/status` in `backend/main.py`. ✅
    2.  Create a new method in `AgentRunService` to read the latest `agent_checkpoint_{space_id}.json` file using `StateManager`. ✅
    3.  Integrate with `StateTransitionTracker` to get the `current_state`. ✅
    4.  Reuse logic from the `/healthcheck` endpoint to determine the `is_active` status. ✅
    5.  **Regenerate OpenAPI Client**: Run `cd frontend && npm run generate-api` to update TypeScript client with new endpoint. ⚠️ (Pending)
*   **Integration Points**:
    *   `StateManager`: To read checkpoint files. ✅
    *   `StateTransitionTracker`: To get the current state. ✅
    *   `main.py`: To expose the new endpoint. ✅
*   **Implementation Date**: 2025-07-29
*   **Implementation Notes**:
    *   Added comprehensive test suite with 7 endpoint tests and 8 service-level tests
    *   Refactored to extract common checkpoint pattern logic
    *   Added AgentRunStatus model to models.py
    *   All tests passing with >90% coverage for new code

#### Task 1.2: Create `GET /agent-run/decisions` Endpoint ✅

*   **Why**: To provide the frontend with the agent's most recent voting decisions, populating the Recent Decisions Panel. This directly exposes the agent's primary function.
*   **Acceptance Criteria**:
    *   Endpoint returns a list of the `N` most recent `VoteDecision` objects.
    *   Each decision object is enriched with the proposal title.
    *   The list is sorted in reverse chronological order.
*   **Test Cases (Red)**:
    *   `test_get_decisions_returns_correct_structure()`: Verify response contains a `decisions` array with correctly structured objects.
    *   `test_get_decisions_respects_limit_parameter()`: Ensure `?limit=N` works as expected.
    *   `test_get_decisions_enriches_with_proposal_title()`: Verify it calls the proposal service to get the title.
    *   `test_get_decisions_returns_empty_list_when_no_history()`: Handle the case with no prior decisions gracefully.
*   **Implementation (Green)**:
    1.  Add a new route `GET /agent-run/decisions` in `backend/main.py`.
    2.  Create a new method in `AgentRunService` to scan all `agent_checkpoint_*.json` files.
    3.  Aggregate `votes_cast` from all checkpoints, sort them by timestamp, and take the top `N`.
    4.  For each decision, call `SnapshotService.get_proposal()` to fetch the title and add it to the response object.
    5.  **Regenerate OpenAPI Client**: Run `cd frontend && npm run generate-api` to update TypeScript client with new endpoint.
*   **Integration Points**:
    *   `StateManager`: To read checkpoint files.
    *   `SnapshotService`: To fetch proposal details.
    *   `main.py`: To expose the new endpoint.

---

### P1: Core Agent Visibility (Frontend)

#### Task 2.1: Create `AgentStatusWidget.svelte` Component

*   **Why**: To display the real-time status of the agent, giving users immediate insight into its activity.
*   **Acceptance Criteria**:
    *   Component polls `GET /agent-run/status` every 30 seconds.
    *   Displays the `current_state` (e.g., "Idle", "Fetching Proposals").
    *   Displays the `last_run_timestamp` in a human-readable format (e.g., "2 minutes ago").
    *   Shows a visual indicator (e.g., a green dot) if `is_active` is true.
*   **Test Cases (Red)**:
    *   `test_widget_displays_loading_state_initially()`
    *   `test_widget_displays_correct_state_and_timestamp_on_load()`
    *   `test_widget_shows_active_indicator_correctly()`
    *   `test_widget_handles_api_error_gracefully()`
*   **Implementation (Green)**:
    1.  Create `src/lib/components/dashboard/AgentStatusWidget.svelte`.
    2.  Use `onMount` and `setInterval` to poll the `/agent-run/status` endpoint.
    3.  Use Svelte state (`$state`) to store and reactively display the status data.
    4.  Implement conditional rendering for the `is_active` indicator.
*   **Integration Points**:
    *   `OverviewTab.svelte`: The new widget will be placed here.
    *   `apiClient`: To make calls to the new backend endpoint.

#### Task 2.2: Create `AgentDecisionsPanel.svelte` Component

*   **Why**: To show the user the tangible output of the agent's work, building trust and transparency.
*   **Acceptance Criteria**:
    *   Component fetches data from `GET /agent-run/decisions`.
    *   Displays a list of the last 5 decisions.
    *   For each decision, it shows the proposal title, vote (`FOR`/`AGAINST`), and confidence score.
    *   The proposal title is a link to the proposal details page.
*   **Test Cases (Red)**:
    *   `test_panel_displays_loading_state()`
    *   `test_panel_renders_a_list_of_decisions()`
    *   `test_panel_displays_correct_data_for_each_decision()`
    *   `test_panel_shows_empty_state_when_no_decisions_are_available()`
*   **Implementation (Green)**:
    1.  Create `src/lib/components/dashboard/AgentDecisionsPanel.svelte`.
    2.  Fetch data from `/agent-run/decisions` in `onMount`.
    3.  Use an `#each` block to render the list of decisions.
    4.  Use TailwindCSS for styling the list items.
*   **Integration Points**:
    *   `OverviewTab.svelte`: The new panel will be placed here.
    *   `apiClient`: To fetch decision data.

---

### P2: Agent Statistics & Actions

#### Task 3.1: Create `GET /agent-run/statistics` Endpoint

*   **Why**: To provide users with an aggregated overview of agent performance over time.
*   **Acceptance Criteria**:
    *   Endpoint returns aggregated statistics as defined in the feature request.
    *   Calculations correctly sum totals and compute averages from all checkpoint files.
    *   `success_rate` is calculated as `(runs_with_no_errors / total_runs)`.
*   **Test Cases (Red)**:
    *   `test_statistics_returns_correct_structure()`
    *   `test_statistics_aggregates_data_from_multiple_checkpoints()`
    *   `test_statistics_handles_division_by_zero_when_no_runs()`
    *   `test_statistics_calculates_success_rate_correctly()`
*   **Implementation (Green)**:
    1.  Add a new route `GET /agent-run/statistics` in `backend/main.py`.
    2.  Create a new method in `AgentRunService` to scan and aggregate data from all `agent_checkpoint_*.json` files.
    3.  Implement the logic for calculating totals, averages, and success rate.
    4.  **Regenerate OpenAPI Client**: Run `cd frontend && npm run generate-api` to update TypeScript client with new endpoint.
*   **Integration Points**:
    *   `StateManager`: To read all checkpoint files.
    *   `main.py`: To expose the new endpoint.

#### Task 3.2: Create `AgentStatistics.svelte` and `AgentQuickActions.svelte`

*   **Why**: To complete the dashboard view with performance metrics and give the user control over the agent.
*   **Acceptance Criteria**:
    *   `AgentStatistics` displays all metrics from the `/agent-run/statistics` endpoint.
    *   `AgentQuickActions` has a "Run Now" button that triggers a `POST` to `/agent-run`.
    *   Actions are disabled when a run is already active.
*   **Test Cases (Red)**:
    *   `test_statistics_displays_all_metrics()`
    *   `test_quick_actions_run_now_button_calls_api()`
    *   `test_quick_actions_buttons_are_disabled_when_agent_is_active()`
*   **Implementation (Green)**:
    1.  Create `src/lib/components/dashboard/AgentStatistics.svelte` to fetch and display stats.
    2.  Create `src/lib/components/dashboard/AgentQuickActions.svelte`.
    3.  The "Run Now" button will use `apiClient` to call `POST /agent-run`. It will get the `current_space_id` from the shared dashboard store.
    4.  Integrate all new components into `OverviewTab.svelte`.
*   **Integration Points**:
    *   `OverviewTab.svelte`: To place the new components.
    *   `apiClient`: For both `GET` (stats) and `POST` (run now) calls.
    *   Dashboard Store: To get the `current_space_id` for the "Run Now" action.

---

---

### P3: Documentation & Deployment

#### Task 4.1: Update All Relevant Documentation

*   **Why**: Ensure all project documentation reflects the new autonomous voting dashboard features and API endpoints.
*   **Acceptance Criteria**:
    *   Update OpenAPI schema documentation for all new endpoints
    *   Add API usage examples to relevant spec files
    *   Update CLAUDE.md with new component locations and usage patterns
    *   Document new dashboard components in frontend architecture docs
*   **Implementation**:
    1.  Update `specs/api.md` with new endpoint documentation
    2.  Add component documentation to `specs/frontend.md`
    3.  Update `CLAUDE.md` with new development workflow steps
    4.  Add troubleshooting guide for agent dashboard issues

---

## 3. Acceptance Criteria

### Backend API Requirements
- [x] **GET /agent-run/status** endpoint returns structured JSON with `current_state`, `last_run_timestamp`, `is_active`, `current_space_id` ✅
- [ ] **GET /agent-run/decisions** endpoint returns paginated list of recent voting decisions with proposal titles
- [ ] **GET /agent-run/statistics** endpoint returns aggregated performance metrics from all checkpoint files
- [ ] All endpoints handle error cases gracefully with appropriate HTTP status codes
- [ ] OpenAPI schema is updated and TypeScript client regenerated for all new endpoints

### Frontend Component Requirements
- [ ] **AgentStatusWidget** displays real-time agent status with 30-second polling interval
- [ ] **AgentDecisionsPanel** shows last 5 voting decisions with proposal links and confidence scores
- [ ] **AgentStatistics** displays performance metrics from statistics endpoint
- [ ] **AgentQuickActions** provides "Run Now" button that triggers agent execution
- [ ] All components handle loading states and API errors gracefully
- [ ] Components are fully responsive and accessible on mobile devices

### Integration Requirements
- [ ] All new components are integrated into `OverviewTab.svelte`
- [ ] Dashboard updates in near real-time (30-second intervals)
- [ ] Agent run status is reflected across all dashboard components
- [ ] "Run Now" action is disabled when agent is already active

### Testing Requirements
- [ ] All backend endpoints have comprehensive unit tests with >90% coverage
- [ ] All frontend components have unit tests using Vitest and Testing Library
- [ ] Integration tests verify end-to-end data flow from API to UI
- [ ] Error handling scenarios are thoroughly tested

### Documentation Requirements
- [ ] OpenAPI documentation includes all new endpoints with examples
- [ ] Component usage is documented in relevant specification files
- [ ] CLAUDE.md is updated with new development workflow steps
- [ ] Troubleshooting guide covers common dashboard issues

---

## 4. Files to be Changed

### Backend Files
- [x] `backend/main.py` - Add new API routes for status, decisions, and statistics (status endpoint ✅)
- [x] `backend/services/agent_run_service.py` - Add methods for checkpoint aggregation and status retrieval ✅
- [x] `backend/models.py` - Add AgentRunStatus model ✅
- [x] `backend/tests/test_agent_run_service.py` - Add comprehensive tests for new methods ✅ (created test_agent_run_service_status.py)
- [x] `backend/tests/test_main.py` - Add API endpoint tests ✅ (created test_agent_run_status.py)

### Frontend Files
- [ ] `frontend/src/lib/components/dashboard/AgentStatusWidget.svelte` - New component
- [ ] `frontend/src/lib/components/dashboard/AgentDecisionsPanel.svelte` - New component
- [ ] `frontend/src/lib/components/dashboard/AgentStatistics.svelte` - New component
- [ ] `frontend/src/lib/components/dashboard/AgentQuickActions.svelte` - New component
- [ ] `frontend/src/routes/organizations/[id]/OverviewTab.svelte` - Integrate new components
- [ ] `frontend/src/lib/api/` - Generated OpenAPI client files (via `npm run generate-api`)
- [ ] `frontend/src/lib/components/dashboard/AgentStatusWidget.test.ts` - Component tests
- [ ] `frontend/src/lib/components/dashboard/AgentDecisionsPanel.test.ts` - Component tests
- [ ] `frontend/src/lib/components/dashboard/AgentStatistics.test.ts` - Component tests
- [ ] `frontend/src/lib/components/dashboard/AgentQuickActions.test.ts` - Component tests

### Documentation Files
- [ ] `specs/api.md` - Document new endpoints
- [ ] `specs/frontend.md` - Document new components
- [ ] `CLAUDE.md` - Update development workflow
- [ ] `specs/testing.md` - Update testing examples if needed

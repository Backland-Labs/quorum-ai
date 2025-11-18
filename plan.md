# Consolidate Proposals on Main Dashboard - Implementation Plan

## Overview

Remove the dedicated proposal detail page (`/proposals/[id]`) and AI summarization system, consolidating all proposal information into an expandable card interface on the main dashboard. Each proposal card will display the agent's voting decision (FOR/AGAINST/ABSTAIN) with reasoning in an expandable format. Only proposals with voting decisions will be displayed (proposals without decisions are filtered out).

## Implementation Phases

1. **Backend Cleanup** - Remove AI summarization endpoints, models, and services
2. **Frontend Data Layer** - Refactor dashboard hook to fetch agent decisions instead of summaries
3. **ProposalCard Enhancement** - Transform into expandable component with agent decision display
4. **Dashboard Updates** - Show all proposals (not just top 3) with decision integration
5. **Navigation Cleanup** - Remove proposal detail page and all navigation links
6. **Testing & Validation** - Verify all changes work correctly

## Current State Analysis

### Existing Architecture

**Proposal Detail Page:**
- Location: `frontend/src/routes/proposals/[id]/+page.svelte`
- Fetches individual proposal + agent decision from API
- Displays: proposal title, voting decision badge, agent reasoning
- Used by: Navigation from ProposalCard "View Details" link

**AI Summarization System:**
- Backend endpoint: `POST /proposals/summarize` (`backend/main.py:522-576`)
- Service layer: `backend/services/ai_service.py` (summarize methods)
- Data models: `backend/models.py:300-333` (ProposalSummary, SummarizeRequest, SummarizeResponse)
- Frontend integration: `useDashboardData.ts:73-95` (auto-fetches summaries after loading proposals)
- Display: ProposalCard shows summary text and risk level badge

**Current Dashboard Display:**
- Shows top 3 recent proposals only (`RecentProposals.svelte:28`)
- Uses compact variant of ProposalCard
- Navigation via `onProposalClick` callback that routes to detail page

**Agent Decisions:**
- Backend: `GET /agent-run/decisions?limit={n}` (`backend/main.py:715-768`)
- Stored as: JSON files in `decisions/` directory (`decision_*.json`)
- Service: `agent_run_service.py:1372-1443` reads and parses decision files
- Frontend store: `agentStatus.ts` polls decisions but NOT used on dashboard currently
- Current limitation: No proposal_id filtering supported (fetches all, filters client-side)

### Key Discoveries

1. **ProposalCard already has variant system** (`ProposalCard.svelte:11`) - can leverage for expansion
2. **VotingIndicator component exists** (`VotingIndicator.svelte`) - can reuse for vote display
3. **OrganizationDropdown provides expandable pattern** - use as reference for toggle/animation
4. **Decision files include all needed data** - proposal_id, vote, reasoning, confidence, strategy
5. **No tests exist** for ProposalCard, RecentProposals, or useDashboardData (must add)

## Desired End State

### User Experience
Users see all proposals with voting decisions on the main dashboard in a card grid. Each card displays:
- **Compact state:** Proposal title, agent vote badge (FOR/AGAINST/ABSTAIN)
- **Expanded state (on click):** Full agent reasoning, confidence level, strategy used
- **Filtering:** Only proposals with voting decisions are shown (proposals without decisions are hidden)

### Technical State
- No proposal detail route (`/proposals/[id]`)
- No AI summarization (endpoints, services, models removed)
- Dashboard fetches decisions alongside proposals and filters proposals to only show those with decisions
- ProposalCard handles expand/collapse with keyboard accessibility
- All proposal data accessible without navigation

### Verification
- Dashboard loads and displays only proposals with voting decisions
- Clicking a proposal card expands it inline (no page navigation)
- Agent decisions display correctly for each proposal
- Frontend tests pass: `cd frontend && npm run test`
- Frontend linting passes: `cd frontend && npm run lint`
- Type checking passes: `cd frontend && npm run check`
- Backend tests pass: `cd backend && uv run pytest tests/ -v`
- Backend linting passes: `cd backend && ruff check .`

## What We're NOT Doing

- NOT modifying backend agent decision service logic (file reading, parsing)
- NOT changing how decisions are generated or stored
- NOT implementing advanced proposal filtering/sorting beyond decision filtering (e.g., by date, state)
- NOT adding pagination (showing all proposals with decisions, likely < 20 active at once)
- NOT displaying Snapshot voting data (top voters, vote percentages) - only agent decision
- NOT implementing search functionality
- NOT creating E2E tests (only unit tests)
- NOT running frontend tests in CI (out of scope)

## Implementation Approach

**Strategy:** Bottom-up, test-driven approach starting with backend cleanup (safest), then data layer, then UI components, ending with navigation removal.

**Why this order:**
1. Backend cleanup has no frontend dependencies - safe to do first
2. Data layer changes enable all frontend work - must come before UI
3. ProposalCard enhancement is isolated - can be developed/tested independently
4. Dashboard integration brings it all together
5. Navigation cleanup is final step - only after new flow works

**Risk mitigation:**
- Each phase is independently testable
- No database migrations required (file-based storage)
- All changes are additions/removals, not complex refactoring
- Can validate each phase before proceeding

## Files to Edit

### Backend (Removal)
- `backend/main.py:522-576` - Delete `POST /proposals/summarize` endpoint
- `backend/services/ai_service.py` - Delete `summarize_proposal()` and `summarize_multiple_proposals()` methods
- `backend/models.py:300-333` - Delete ProposalSummary, SummarizeRequest, SummarizeResponse models

### Frontend Data Layer
- `frontend/src/lib/hooks/useDashboardData.ts` - Entire file refactor:
  - Remove: Lines 11, 29, 85-94 (proposalSummaries state and fetching)
  - Remove: Lines 73-95 (POST /proposals/summarize call)
  - Add: Decision fetching logic
  - Add: Decision Map creation (`Map<string, AgentDecisionResponse>`)

### Frontend Components
- `frontend/src/lib/components/dashboard/ProposalCard.svelte` - Major refactor:
  - Remove: Lines 9, 15, 51-57 (summary prop and parsing)
  - Remove: Lines 78-80, 85-87 (risk badge, summary text)
  - Remove: Lines 122-146 (footer with "View Details" link)
  - Add: `decision` prop (AgentDecisionResponse | undefined)
  - Add: `isExpanded` state with toggle handler
  - Add: Agent vote badge in header (compact view)
  - Add: Expandable section with reasoning (expanded view)
  - Add: Keyboard accessibility (Enter, Space, Escape)

- `frontend/src/lib/components/dashboard/RecentProposals.svelte` - Updates:
  - Remove: Line 8 (`onProposalClick` prop)
  - Remove: Line 28 (`.slice(0, 3)` - show all proposals)
  - Remove: Line 45 (`onClick` prop passing)
  - Change: Line 7 to accept `decisions` Map instead of `proposalSummaries`
  - Change: Line 37 heading to "All Proposals" or similar
  - Add: Pass `decision` to each ProposalCard

- `frontend/src/lib/components/dashboard/DashboardContent.svelte` - Updates:
  - Remove: Lines 15, 19, 22 (`onProposalClick` prop)
  - Remove: Line 81 (prop passing to RecentProposals)
  - Add: Access decisions from dashboard store
  - Change: Pass `decisions` Map to RecentProposals

- `frontend/src/routes/+page.svelte` - Updates:
  - Remove: Line 2 (`import { goto }`)
  - Remove: Lines 79-84 (`handleProposalClick` function)
  - Remove: Line 129 (`onProposalClick` prop)

### Frontend Routes (Deletion)
- `frontend/src/routes/proposals/[id]/+page.svelte` - Delete entire file/directory

### Frontend Types
- `frontend/src/lib/types/dashboard.ts` - Review and potentially remove unused ProposalSummary type references

---

## Phase 1: Backend Cleanup - Remove AI Summarization

### Overview
Remove all AI summarization functionality from backend (endpoint, service methods, data models). This is safe to do first as we'll remove frontend consumers immediately after.

### Changes Required

#### 1. Remove Summarization Endpoint

**File:** `backend/main.py`

**Lines to Delete:** 522-577

```python
# Delete entire block:
@app.post("/proposals/summarize", response_model=SummarizeResponse)
async def summarize_proposals(request: SummarizeRequest):
    # ... entire method ...
```

**Also delete helper functions** if they exist later in the file:
- `_fetch_proposals_for_summarization()`
- `_generate_proposal_summaries()`

Search file for these functions and remove if found.

#### 2. Remove Summarization Models

**File:** `backend/models.py`

**Lines to Delete:** 300-333 (approximate - verify exact line numbers)

```python
# Delete these model definitions:
class ProposalSummary(BaseModel):
    # ...

class SummarizeRequest(BaseModel):
    # ...

class SummarizeResponse(BaseModel):
    # ...
```

#### 3. Remove AI Service Methods

**File:** `backend/services/ai_service.py`

**Methods to Delete:**
- `summarize_proposal(self, proposal) -> ProposalSummary`
- `summarize_multiple_proposals(self, proposals) -> List[ProposalSummary]`

**Note:** Do NOT delete the entire `ai_service.py`. Only remove summarization methods.

**Search strategy:**
```bash
ast-grep run --lang python -p 'def summarize_proposal'
ast-grep run --lang python -p 'def summarize_multiple_proposals'
```

#### 4. Remove Summarization Tests

**Search for test files:**
```bash
cd backend && grep -r "summarize" tests/ --include="*.py"
```

**Tests to remove:**
- Any test functions that test `POST /proposals/summarize` endpoint
- Any test functions that test `summarize_proposal()` or `summarize_multiple_proposals()` methods
- Any fixtures or mocks specifically for summarization

**Common test patterns to look for:**
- `test_summarize_proposals`
- `test_summarize_proposal`
- `test_proposal_summary`
- Mock objects like `mock_summarize_response`

**Note:** Do NOT remove tests for other AI service functionality (if any exists).

### Success Criteria

#### Automated Verification:
- [ ] Backend starts without errors: `cd backend && export $(cat ../.env | xargs) && uv run uvicorn main:app --host 0.0.0.0 --port 8000`
- [ ] Backend tests pass: `cd backend && uv run pytest tests/ -v`
- [ ] Backend linting passes: `cd backend && ruff check .` (or applicable linter)
- [ ] Type checking passes (if using mypy): `cd backend && uv run mypy .`
- [ ] Summarization endpoint no longer exists: `curl -X POST http://localhost:8000/proposals/summarize -d '{"proposal_ids":["test"]}' -H "Content-Type: application/json"` returns 404
- [ ] No test failures related to summarization

#### Manual Verification:
- [ ] API docs (`http://localhost:8000/docs`) no longer show `/proposals/summarize` endpoint
- [ ] No import errors when starting backend
- [ ] Backend logs show clean startup
- [ ] No orphaned test files remain

---

## Phase 2: Frontend Data Layer - Replace Summaries with Decisions

### Overview
Refactor `useDashboardData` hook to fetch agent decisions instead of proposal summaries. Create a Map for efficient decision lookup by proposal_id.

### Changes Required

#### 1. Update DashboardState Interface

**File:** `frontend/src/lib/hooks/useDashboardData.ts`

**Lines 6-17:** Update interface

**Old:**
```typescript
interface DashboardState {
  loading: boolean;
  error: string | null;
  currentSpaceId: string;
  allProposals: components['schemas']['Proposal'][];
  proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;  // REMOVE
  proposalsLoading: boolean;
  proposalsError: string | null;
  proposalFilters: {
    state?: components['schemas']['ProposalState'];
  };
}
```

**New:**
```typescript
interface DashboardState {
  loading: boolean;
  error: string | null;
  currentSpaceId: string;
  allProposals: components['schemas']['Proposal'][];
  agentDecisions: Map<string, components['schemas']['AgentDecisionResponse']>;  // ADD
  decisionsLoading: boolean;  // ADD
  decisionsError: string | null;  // ADD
  proposalsLoading: boolean;
  proposalsError: string | null;
  proposalFilters: {
    state?: components['schemas']['ProposalState'];
  };
}
```

#### 2. Update Initial State

**Lines 24-33:** Update initialState

**Old:**
```typescript
const initialState: DashboardState = {
  loading: true,
  error: null,
  currentSpaceId: 'quorum-ai.eth',
  allProposals: [],
  proposalSummaries: new Map(),  // REMOVE
  proposalsLoading: false,
  proposalsError: null,
  proposalFilters: {}
};
```

**New:**
```typescript
const initialState: DashboardState = {
  loading: true,
  error: null,
  currentSpaceId: 'quorum-ai.eth',
  allProposals: [],
  agentDecisions: new Map(),  // ADD
  decisionsLoading: false,  // ADD
  decisionsError: null,  // ADD
  proposalsLoading: false,
  proposalsError: null,
  proposalFilters: {}
};
```

#### 3. Replace Summary Fetching with Decision Fetching

**Lines 73-95:** Delete entire summary fetching block

**Delete:**
```typescript
// Load summaries for proposals
const proposalIds = data.proposals.map(p => p.id);
if (proposalIds.length > 0) {
  const { data: summaryData } = await apiClient.POST("/proposals/summarize", {
    body: {
      proposal_ids: proposalIds,
      include_risk_assessment: true,
      include_recommendations: true
    }
  });

  if (summaryData) {
    const newSummaries = new Map<string, components['schemas']['ProposalSummary']>();
    summaryData.summaries.forEach(summary => {
      newSummaries.set(summary.proposal_id, summary);
    });

    update(s => ({
      ...s,
      proposalSummaries: newSummaries
    }));
  }
}
```

**Add after line 71 (after setting allProposals):**
```typescript
// Load agent decisions for proposals and filter proposals
await loadDecisions();
```

#### 4. Add New loadDecisions() Function

**Add new function after loadProposals():**

```typescript
/**
 * Loads agent voting decisions from API and filters proposals to only show those with decisions
 */
async function loadDecisions(): Promise<void> {
  console.assert(typeof apiClient.GET === 'function', 'API client should have GET method');

  try {
    update(state => ({
      ...state,
      decisionsLoading: true,
      decisionsError: null
    }));

    const { data, error: apiError } = await apiClient.GET("/agent-run/decisions", {
      params: {
        query: {
          limit: 100  // Fetch enough to cover all proposals
        }
      }
    });

    if (apiError) {
      const errorMessage = extractApiErrorMessage(apiError);
      update(state => ({
        ...state,
        decisionsError: errorMessage,
        decisionsLoading: false
      }));
      return;
    }

    if (data?.decisions) {
      // Create Map for O(1) lookup by proposal_id
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      data.decisions.forEach(decision => {
        decisionsMap.set(decision.proposal_id, decision);
      });

      // Filter proposals to only show those with voting decisions
      let currentState: DashboardState;
      const unsubscribe = subscribe(s => { currentState = s; });
      unsubscribe();

      const proposalsWithDecisions = currentState!.allProposals.filter(proposal =>
        decisionsMap.has(proposal.id)
      );

      update(state => ({
        ...state,
        allProposals: proposalsWithDecisions,  // Update with filtered list
        agentDecisions: decisionsMap,
        decisionsLoading: false
      }));
    }
  } catch (err) {
    console.error('Failed to load decisions:', err);
    update(state => ({
      ...state,
      decisionsError: 'Failed to load voting decisions',
      decisionsLoading: false
    }));
  }
}
```

#### 5. Add Type Import

**Line 4:** Add AgentDecisionResponse import

**Old:**
```typescript
import type { components } from '$lib/api/client';
```

**New:**
```typescript
import type { components } from '$lib/api/client';
// Type already available via components['schemas']['AgentDecisionResponse']
```

#### 6. Export loadDecisions Method

**Lines 143-149:** Update return object

**Old:**
```typescript
return {
  subscribe,
  loadProposals,
  changeSpace,
  updateProposalFilters
};
```

**New:**
```typescript
return {
  subscribe,
  loadProposals,
  loadDecisions,  // ADD
  changeSpace,
  updateProposalFilters
};
```

### Success Criteria

#### Automated Verification:
- [ ] TypeScript compiles without errors: `cd frontend && npm run check`
- [ ] Frontend linting passes: `cd frontend && npm run lint` (if available)
- [ ] No unused import warnings for ProposalSummary
- [ ] Store can be instantiated without errors

#### Manual Verification:
- [ ] Dashboard loads without console errors
- [ ] Network tab shows `GET /agent-run/decisions` request (not `POST /proposals/summarize`)
- [ ] Decisions are fetched and stored in state
- [ ] Console logging shows decisions Map populated correctly
- [ ] Only proposals with voting decisions are displayed (proposals without decisions are filtered out)
- [ ] Proposal count matches number of proposals with decisions

---

## Phase 3: ProposalCard Enhancement - Add Expandable Agent Decision

### Overview
Transform ProposalCard into an expandable component that displays agent voting decisions. Remove summary and risk badge display. Add expand/collapse functionality with keyboard accessibility.

### Changes Required

#### 1. Update Props Interface

**File:** `frontend/src/lib/components/dashboard/ProposalCard.svelte`

**Lines 7-13:**

**Old:**
```typescript
interface Props {
  proposal: components['schemas']['Proposal'];
  summary?: components['schemas']['ProposalSummary'];  // REMOVE
  fullProposal?: ExtendedProposal;
  variant?: 'compact' | 'detailed';  // KEEP but repurpose
  onClick?: () => void;  // REMOVE (no navigation)
}
```

**New:**
```typescript
interface Props {
  proposal: components['schemas']['Proposal'];
  decision?: components['schemas']['AgentDecisionResponse'];  // ADD
  fullProposal?: ExtendedProposal;
}
```

**Note:** Remove `variant` and `onClick` props as we're replacing with expand/collapse behavior.

#### 2. Update Props Destructuring and State

**Lines 15-16:**

**Old:**
```typescript
let { proposal, summary, fullProposal, variant = 'compact', onClick }: Props = $props();
```

**New:**
```typescript
let { proposal, decision, fullProposal }: Props = $props();

// Add expandable state
let isExpanded = $state(false);
```

#### 3. Remove Summary Parsing Logic

**Lines 51-57:** Delete

**Delete:**
```typescript
const parsedProposal = summary ? {
  summary: summary.summary,
  key_points: summary.key_points,
  risk_level: summary.risk_assessment || 'MEDIUM',
  recommendation: summary.recommendation || 'REVIEW',
  confidence_score: summary.confidence
} : parseProposalSummary(proposal);
```

#### 4. Remove Unnecessary Imports

**Lines 2, 3:**

**Old:**
```typescript
import { parseProposalSummary, cleanProposalTitle } from '$lib/utils/proposals.js';
import VotingIndicator from './VotingIndicator.svelte';
```

**New:**
```typescript
import { cleanProposalTitle } from '$lib/utils/proposals.js';
// Keep VotingIndicator if still needed, otherwise remove
```

#### 5. Add Toggle Handler

**Add after validateProps() function:**

```typescript
/**
 * Toggles card expansion state
 */
const handleToggle = () => {
  isExpanded = !isExpanded;
};

/**
 * Handles keyboard navigation for accessibility
 */
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    handleToggle();
  } else if (event.key === 'Escape' && isExpanded) {
    isExpanded = false;
  }
};

/**
 * Gets vote badge CSS classes based on vote type
 */
function getVoteBadgeClasses(vote: string): string {
  console.assert(typeof vote === 'string', 'Vote must be a string');

  const voteClasses: Record<string, string> = {
    'FOR': 'bg-green-50 text-green-700 border-green-200',
    'AGAINST': 'bg-red-50 text-red-700 border-red-200',
    'ABSTAIN': 'bg-gray-50 text-gray-700 border-gray-200'
  };
  return voteClasses[vote] || voteClasses['ABSTAIN'];
}
```

#### 6. Update Template Structure

**Lines 61-148:** Complete template replacement

**New Template:**
```svelte
<div
  class="group relative"
  role="button"
  tabindex="0"
  onclick={handleToggle}
  onkeydown={handleKeydown}
  aria-expanded={isExpanded}
>
  <div class="relative bg-white border border-secondary-200 rounded-lg p-5 hover:border-primary-300 hover:shadow-md transition-all duration-200 cursor-pointer">

    <!-- Header with title and decision badge -->
    <div class="flex items-start justify-between mb-3">
      <div class="flex-1">
        <h5 class="font-semibold text-secondary-900 text-base leading-tight pr-4">
          {cleanProposalTitle(proposal.title)}
        </h5>
        {#if fullProposal}
          <div class="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>{fullProposal?.dao_name || ''}</span>
            <span>•</span>
            <span>Created {formatDate(fullProposal?.created_at || proposal.created)}</span>
          </div>
        {/if}
      </div>

      <!-- Agent Vote Badge -->
      <!-- Note: We can simplify this since all proposals have decisions (filtered in Phase 2) -->
      <div class="flex items-center gap-2 flex-shrink-0">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border {getVoteBadgeClasses(decision.vote)}">
          {decision.vote}
        </span>

        <!-- Expand/Collapse Chevron -->
        <svg
          class="w-4 h-4 text-gray-400 transition-transform duration-200 {isExpanded ? 'rotate-90' : 'rotate-0'}"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </div>

    <!-- Expandable Agent Decision Details -->
    <!-- Note: All proposals have decisions (filtered in Phase 2), so no need for else case -->
    {#if isExpanded}
      <div class="mt-4 pt-4 border-t border-secondary-100 space-y-3">

        <!-- Reasoning -->
        <div>
          <h6 class="text-xs font-medium text-secondary-700 mb-2">Agent Reasoning</h6>
          <p class="text-sm text-secondary-600 leading-relaxed whitespace-pre-wrap">
            {decision.reasoning}
          </p>
        </div>

        <!-- Metadata Grid -->
        <div class="grid grid-cols-2 gap-3 pt-3">
          <div>
            <span class="text-xs text-secondary-500">Confidence</span>
            <p class="text-sm font-medium text-secondary-900">
              {(decision.confidence * 100).toFixed(0)}%
            </p>
          </div>
          <div>
            <span class="text-xs text-secondary-500">Strategy</span>
            <p class="text-sm font-medium text-secondary-900 capitalize">
              {decision.strategy_used}
            </p>
          </div>
        </div>

        <!-- Timestamp -->
        <div class="pt-2 text-xs text-secondary-500">
          Voted: {new Date(decision.timestamp).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </div>
      </div>
    {/if}

  </div>
</div>
```

#### 7. Remove Old Functions

**Delete these functions entirely:**
- `getRiskLevelClasses()` (lines 22-32) - no longer needed
- Any references to `parsedProposal` variable

### Success Criteria

#### Automated Verification:
- [ ] Component renders without errors: `cd frontend && npm run test`
- [ ] TypeScript type checking passes: `cd frontend && npm run check`
- [ ] Frontend linting passes: `cd frontend && npm run lint` (if available)
- [ ] No console warnings about unused props

#### Manual Verification:
- [ ] Card displays proposal title and agent vote badge
- [ ] Clicking card expands to show reasoning
- [ ] Clicking again collapses the card
- [ ] Keyboard navigation works (Enter/Space to toggle, Escape to collapse)
- [ ] Chevron icon rotates smoothly when expanding/collapsing
- [ ] All displayed proposals have voting decisions (no "No Vote" badges should appear since we filter)
- [ ] Confidence displays as percentage correctly
- [ ] Strategy displays with proper capitalization
- [ ] Timestamp formats correctly

---

## Phase 4: Dashboard Updates - Show All Proposals with Decisions

### Overview
Update RecentProposals to display all proposals with voting decisions (not just top 3) and pass agent decisions to each ProposalCard. Remove navigation props from component chain. Note: Proposals are already filtered to only include those with decisions from Phase 2.

### Changes Required

#### 1. Update RecentProposals Props

**File:** `frontend/src/lib/components/dashboard/RecentProposals.svelte`

**Lines 5-9:**

**Old:**
```typescript
interface Props {
  proposals: components['schemas']['Proposal'][];
  proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;
  onProposalClick: (proposalId: string) => void;
}
```

**New:**
```typescript
interface Props {
  proposals: components['schemas']['Proposal'][];
  agentDecisions: Map<string, components['schemas']['AgentDecisionResponse']>;
}
```

#### 2. Update Props Destructuring

**Line 11:**

**Old:**
```typescript
let { proposals, proposalSummaries, onProposalClick }: Props = $props();
```

**New:**
```typescript
let { proposals, agentDecisions }: Props = $props();
```

#### 3. Update Validation

**Lines 15-16:**

**Old:**
```typescript
console.assert(proposalSummaries instanceof Map, 'Proposal summaries should be a Map');
```

**New:**
```typescript
console.assert(agentDecisions instanceof Map, 'Agent decisions should be a Map');
```

#### 4. Update Display Logic to Show All Proposals

**Lines 24-29:**

**Old:**
```typescript
function getDisplayProposals() {
  console.assert(hasProposals(), 'Should have proposals when calling getDisplayProposals');
  console.assert(Array.isArray(proposals), 'Proposals should be an array');

  return proposals.slice(0, 3);  // Only show 3
}
```

**New:**
```typescript
function getDisplayProposals() {
  console.assert(hasProposals(), 'Should have proposals when calling getDisplayProposals');
  console.assert(Array.isArray(proposals), 'Proposals should be an array');

  return proposals;  // Show all proposals
}
```

#### 5. Update Template

**Lines 34-51:**

**Old:**
```svelte
{#if hasProposals()}
  <div class="bg-white rounded-lg shadow p-6 lg:col-span-2">
    <div class="mb-6">
      <h3 class="text-base font-medium text-gray-900">Recent Proposals</h3>
    </div>

    <div class="space-y-4">
      {#each getDisplayProposals() as proposal}
        <ProposalCard
          {proposal}
          summary={proposalSummaries.get(proposal.id)}
          onClick={() => onProposalClick(proposal.id)}
          variant="compact"
        />
      {/each}
    </div>
  </div>
{/if}
```

**New:**
```svelte
{#if hasProposals()}
  <div class="bg-white rounded-lg shadow p-6 lg:col-span-2">
    <div class="mb-6">
      <h3 class="text-base font-medium text-gray-900">All Proposals</h3>
      <p class="text-sm text-gray-500 mt-1">
        {proposals.length} {proposals.length === 1 ? 'proposal' : 'proposals'}
      </p>
    </div>

    <div class="space-y-4">
      {#each getDisplayProposals() as proposal}
        <ProposalCard
          {proposal}
          decision={agentDecisions.get(proposal.id)}
        />
      {/each}
    </div>
  </div>
{/if}
```

#### 6. Update DashboardContent Component

**File:** `frontend/src/lib/components/dashboard/DashboardContent.svelte`

**Lines 15, 19, 22:** Remove onProposalClick prop

**Old:**
```typescript
interface Props {
  // ... other props
  onProposalClick: (proposalId: string) => void;
}

let { /* ... */, onProposalClick }: Props = $props();

console.assert(typeof onProposalClick === 'function', 'onProposalClick must be a function');
```

**New:**
```typescript
interface Props {
  // ... other props (remove onProposalClick)
}

let { /* ... */ }: Props = $props();

// Remove assertion for onProposalClick
```

**Line 81:** Update RecentProposals usage

**Old:**
```svelte
<RecentProposals
  proposals={$dashboardStore.allProposals}
  proposalSummaries={$dashboardStore.proposalSummaries}
  {onProposalClick}
/>
```

**New:**
```svelte
<RecentProposals
  proposals={$dashboardStore.allProposals}
  agentDecisions={$dashboardStore.agentDecisions}
/>
```

#### 7. Update Root Page Component

**File:** `frontend/src/routes/+page.svelte`

**Line 2:** Remove goto import

**Old:**
```typescript
import { goto } from "$app/navigation";
```

**New:**
```typescript
// Remove this import entirely
```

**Lines 79-84:** Remove handleProposalClick function

**Delete:**
```typescript
function handleProposalClick(proposalId: string): void {
  console.assert(typeof proposalId === 'string', 'Proposal ID must be a string');
  console.assert(proposalId.length > 0, 'Proposal ID should not be empty');
  goto(`/proposals/${proposalId}`);
}
```

**Line 129:** Remove onProposalClick prop

**Old:**
```svelte
<DashboardContent
  {selectedOrganization}
  {currentSpaceId}
  {spaces}
  organizations={$organizations}
  onOrganizationChange={handleOrganizationChange}
  onProposalClick={handleProposalClick}
/>
```

**New:**
```svelte
<DashboardContent
  {selectedOrganization}
  {currentSpaceId}
  {spaces}
  organizations={$organizations}
  onOrganizationChange={handleOrganizationChange}
/>
```

### Success Criteria

#### Automated Verification:
- [ ] TypeScript compiles: `cd frontend && npm run check`
- [ ] Frontend linting passes: `cd frontend && npm run lint` (if available)
- [ ] No unused variable warnings
- [ ] Component tests pass (after writing tests in Phase 6)

#### Manual Verification:
- [ ] Dashboard displays all proposals with voting decisions (not just 3)
- [ ] Only proposals with decisions are shown (filtered in Phase 2)
- [ ] Proposal count displays correctly in header (matches filtered count)
- [ ] Each card shows appropriate vote badge (FOR/AGAINST/ABSTAIN)
- [ ] No "No Vote" badges appear (all proposals have decisions)
- [ ] Cards can be expanded/collapsed individually
- [ ] No navigation occurs when clicking cards
- [ ] No console errors about missing props

---

## Phase 5: Navigation Cleanup - Remove Proposal Detail Page

### Overview
Delete the proposal detail page route and clean up all references to it in the codebase.

### Changes Required

#### 1. Delete Proposal Detail Route

**Directory to delete:** `frontend/src/routes/proposals/`

**Command:**
```bash
rm -rf frontend/src/routes/proposals
```

This removes:
- `frontend/src/routes/proposals/[id]/+page.svelte`
- Any other files in the proposals route directory

#### 2. Verify No Remaining References

**Search for references:**
```bash
# Search for route references
cd frontend && grep -r "/proposals/" src/

# Search for navigation to proposals
cd frontend && grep -r "goto.*proposals" src/

# Search for href to proposals
cd frontend && grep -r 'href="/proposals' src/
```

**Expected result:** No matches (all references removed in previous phases)

#### 3. Update API Client Types (If Needed)

**File:** `frontend/src/lib/api/client.ts`

**Note:** The API endpoint types are typically auto-generated. If they reference `/proposals/{proposal_id}`, they can stay as the backend endpoint still exists (used programmatically, just not by frontend UI).

**Verification:** Ensure no TypeScript errors about missing route types

### Success Criteria

#### Automated Verification:
- [ ] Directory does not exist: `ls frontend/src/routes/proposals/` returns error
- [ ] TypeScript compiles: `cd frontend && npm run check`
- [ ] Frontend linting passes: `cd frontend && npm run lint` (if available)
- [ ] No broken imports or missing route errors
- [ ] Search for `/proposals/` in frontend returns no UI references

#### Manual Verification:
- [ ] Navigating to `/proposals/any-id` in browser shows 404 page
- [ ] No console errors about missing routes
- [ ] No broken links in UI
- [ ] Dashboard functions normally without proposal detail page

---

## Phase 6: Testing & Validation

### Overview
Add comprehensive tests for modified components and validate the entire feature works end-to-end.

### Changes Required

#### 1. Create ProposalCard Tests

**File to create:** `frontend/src/lib/components/dashboard/ProposalCard.test.ts`

**Test cases:**
```typescript
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import ProposalCard from './ProposalCard.svelte';
import type { components } from '$lib/api/client';

describe('ProposalCard', () => {
  const mockProposal: components['schemas']['Proposal'] = {
    id: 'test-proposal-1',
    title: 'Test Proposal Title',
    created: 1234567890,
    state: 'active'
  };

  const mockDecision: components['schemas']['AgentDecisionResponse'] = {
    proposal_id: 'test-proposal-1',
    vote: 'FOR',
    confidence: 0.85,
    reasoning: 'This proposal aligns with our strategic objectives.',
    strategy_used: 'balanced',
    timestamp: '2024-01-15T10:30:00Z',
    proposal_title: 'Test Proposal Title'
  };

  it('renders proposal title correctly', () => {
    render(ProposalCard, {
      props: { proposal: mockProposal }
    });

    expect(screen.getByText(/Test Proposal Title/i)).toBeInTheDocument();
  });

  it('displays vote badge when decision is provided', () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    expect(screen.getByText('FOR')).toBeInTheDocument();
  });

  // Note: We don't test "No Vote" case since proposals without decisions are filtered out in Phase 2

  it('expands to show reasoning when clicked', async () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    // Initially reasoning should not be visible
    expect(screen.queryByText(/This proposal aligns/i)).not.toBeInTheDocument();

    // Click to expand
    const card = screen.getByRole('button');
    await fireEvent.click(card);

    // Reasoning should now be visible
    expect(screen.getByText(/This proposal aligns/i)).toBeInTheDocument();
  });

  it('collapses when clicked again', async () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    const card = screen.getByRole('button');

    // Expand
    await fireEvent.click(card);
    expect(screen.getByText(/This proposal aligns/i)).toBeInTheDocument();

    // Collapse
    await fireEvent.click(card);
    expect(screen.queryByText(/This proposal aligns/i)).not.toBeInTheDocument();
  });

  it('supports keyboard navigation with Enter key', async () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    const card = screen.getByRole('button');

    // Press Enter to expand
    await fireEvent.keyDown(card, { key: 'Enter' });
    expect(screen.getByText(/This proposal aligns/i)).toBeInTheDocument();
  });

  it('supports keyboard navigation with Space key', async () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    const card = screen.getByRole('button');

    // Press Space to expand
    await fireEvent.keyDown(card, { key: ' ' });
    expect(screen.getByText(/This proposal aligns/i)).toBeInTheDocument();
  });

  it('collapses with Escape key when expanded', async () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    const card = screen.getByRole('button');

    // Expand first
    await fireEvent.click(card);
    expect(screen.getByText(/This proposal aligns/i)).toBeInTheDocument();

    // Press Escape to collapse
    await fireEvent.keyDown(card, { key: 'Escape' });
    expect(screen.queryByText(/This proposal aligns/i)).not.toBeInTheDocument();
  });

  it('displays confidence as percentage', async () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    const card = screen.getByRole('button');
    await fireEvent.click(card);

    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('displays strategy with proper capitalization', async () => {
    render(ProposalCard, {
      props: {
        proposal: mockProposal,
        decision: mockDecision
      }
    });

    const card = screen.getByRole('button');
    await fireEvent.click(card);

    expect(screen.getByText('Balanced')).toBeInTheDocument();
  });

  // Note: We don't test the "no decision" message case since proposals without decisions are filtered out
});
```

#### 2. Create RecentProposals Tests

**File to create:** `frontend/src/lib/components/dashboard/RecentProposals.test.ts`

**Test cases:**
```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import RecentProposals from './RecentProposals.svelte';
import type { components } from '$lib/api/client';

describe('RecentProposals', () => {
  const mockProposals: components['schemas']['Proposal'][] = [
    { id: '1', title: 'Proposal 1', created: 1234567890, state: 'active' },
    { id: '2', title: 'Proposal 2', created: 1234567891, state: 'active' },
    { id: '3', title: 'Proposal 3', created: 1234567892, state: 'active' },
    { id: '4', title: 'Proposal 4', created: 1234567893, state: 'active' }
  ];

  const mockDecisions = new Map();

  it('renders all proposals', () => {
    render(RecentProposals, {
      props: {
        proposals: mockProposals,
        agentDecisions: mockDecisions
      }
    });

    expect(screen.getByText(/Proposal 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Proposal 2/i)).toBeInTheDocument();
    expect(screen.getByText(/Proposal 3/i)).toBeInTheDocument();
    expect(screen.getByText(/Proposal 4/i)).toBeInTheDocument();
  });

  it('displays correct proposal count', () => {
    render(RecentProposals, {
      props: {
        proposals: mockProposals,
        agentDecisions: mockDecisions
      }
    });

    expect(screen.getByText('4 proposals')).toBeInTheDocument();
  });

  it('displays singular "proposal" for single item', () => {
    render(RecentProposals, {
      props: {
        proposals: [mockProposals[0]],
        agentDecisions: mockDecisions
      }
    });

    expect(screen.getByText('1 proposal')).toBeInTheDocument();
  });

  it('does not render when no proposals', () => {
    const { container } = render(RecentProposals, {
      props: {
        proposals: [],
        agentDecisions: mockDecisions
      }
    });

    expect(container.firstChild).toBeNull();
  });
});
```

#### 3. Create useDashboardData Tests

**File to create:** `frontend/src/lib/hooks/useDashboardData.test.ts`

**Test cases:**
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { createDashboardStore } from './useDashboardData';
import apiClient from '$lib/api';

// Mock API client
vi.mock('$lib/api', () => ({
  default: {
    GET: vi.fn()
  }
}));

describe('useDashboardData', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with correct default state', () => {
    const store = createDashboardStore();
    const state = get(store);

    expect(state.loading).toBe(true);
    expect(state.currentSpaceId).toBe('quorum-ai.eth');
    expect(state.allProposals).toEqual([]);
    expect(state.agentDecisions).toBeInstanceOf(Map);
    expect(state.agentDecisions.size).toBe(0);
  });

  it('loads proposals and decisions successfully and filters proposals', async () => {
    const mockProposals = [
      { id: '1', title: 'Proposal 1', created: 1234567890, state: 'active' },
      { id: '2', title: 'Proposal 2', created: 1234567891, state: 'active' }
    ];

    const mockDecisions = [
      {
        proposal_id: '1',
        vote: 'FOR',
        confidence: 0.9,
        reasoning: 'Good proposal',
        strategy_used: 'balanced',
        timestamp: '2024-01-15T10:30:00Z',
        proposal_title: 'Proposal 1'
      }
      // Note: No decision for proposal 2
    ];

    vi.mocked(apiClient.GET).mockImplementation(async (path: string) => {
      if (path === '/proposals') {
        return { data: { proposals: mockProposals }, error: null };
      }
      if (path === '/agent-run/decisions') {
        return { data: { decisions: mockDecisions }, error: null };
      }
      return { data: null, error: null };
    });

    const store = createDashboardStore();
    await store.loadProposals();

    const state = get(store);
    // Should only include proposal 1 (has decision), not proposal 2 (no decision)
    expect(state.allProposals).toEqual([mockProposals[0]]);
    expect(state.allProposals.length).toBe(1);
    expect(state.agentDecisions.get('1')).toEqual(mockDecisions[0]);
    expect(state.loading).toBe(false);
  });

  it('handles API errors gracefully', async () => {
    vi.mocked(apiClient.GET).mockResolvedValue({
      data: null,
      error: { message: 'API Error' }
    });

    const store = createDashboardStore();
    await store.loadProposals();

    const state = get(store);
    expect(state.error).toBeTruthy();
    expect(state.loading).toBe(false);
  });

  it('creates decision map correctly', async () => {
    const mockDecisions = [
      { proposal_id: '1', vote: 'FOR', confidence: 0.9, reasoning: 'Good', strategy_used: 'balanced', timestamp: '2024-01-15T10:30:00Z', proposal_title: 'P1' },
      { proposal_id: '2', vote: 'AGAINST', confidence: 0.8, reasoning: 'Bad', strategy_used: 'conservative', timestamp: '2024-01-15T11:30:00Z', proposal_title: 'P2' }
    ];

    vi.mocked(apiClient.GET).mockImplementation(async (path: string) => {
      if (path === '/proposals') {
        return { data: { proposals: [] }, error: null };
      }
      if (path === '/agent-run/decisions') {
        return { data: { decisions: mockDecisions }, error: null };
      }
      return { data: null, error: null };
    });

    const store = createDashboardStore();
    await store.loadProposals();

    const state = get(store);
    expect(state.agentDecisions.size).toBe(2);
    expect(state.agentDecisions.get('1')?.vote).toBe('FOR');
    expect(state.agentDecisions.get('2')?.vote).toBe('AGAINST');
  });
});
```

#### 4. Update Existing Tests

**Files to check and update:**
- `frontend/src/lib/components/dashboard/DashboardContent.test.ts` (if exists)
- `frontend/src/routes/+page.test.ts` (if exists)

**Changes needed:**
- Remove any tests that reference `handleProposalClick`
- Update any snapshot tests to reflect new component structure
- Add tests for decision display if not covered above

#### 5. Backend Test Validation

**Run existing backend tests:**
```bash
cd backend && uv run pytest tests/ -v
```

**Expected:** All tests pass (none should break from removing summarization)

**If tests fail:**
- Check for tests that explicitly test summarization endpoint
- Remove or update those specific tests
- Ensure no other tests depended on summarization

### Success Criteria

#### Automated Verification:
- [ ] All frontend tests pass: `cd frontend && npm run test`
- [ ] All backend tests pass: `cd backend && uv run pytest tests/ -v`
- [ ] TypeScript type checking passes: `cd frontend && npm run check`
- [ ] Frontend linting passes: `cd frontend && npm run lint` (if available)
- [ ] Backend linting passes: `cd backend && ruff check .` (or applicable linter)
- [ ] Test coverage for ProposalCard includes expandable functionality
- [ ] Test coverage for RecentProposals includes decision passing
- [ ] Test coverage for useDashboardData includes decision fetching and filtering

#### Manual Verification:
- [ ] Dashboard loads without errors
- [ ] Only proposals with voting decisions are displayed (no proposals without decisions)
- [ ] All proposals display with correct vote badges (FOR/AGAINST/ABSTAIN)
- [ ] No "No Vote" badges appear (all proposals filtered to have decisions)
- [ ] Clicking proposals expands them inline (no navigation)
- [ ] Agent reasoning displays correctly when expanded
- [ ] Confidence displays as percentage (0-100%)
- [ ] Strategy displays with correct capitalization
- [ ] Timestamp formats correctly
- [ ] Keyboard navigation works (Enter, Space, Escape)
- [ ] Chevron icon rotates smoothly
- [ ] Multiple proposals can be expanded simultaneously
- [ ] No console errors or warnings
- [ ] Network tab shows only /proposals and /agent-run/decisions requests (no summarize)
- [ ] Backend starts and runs without errors
- [ ] API docs no longer show /proposals/summarize endpoint

---

## Testing Strategy

### Unit Tests

**Backend:**
- No new tests required (only removing functionality)
- Verify existing tests still pass after removing summarization

**Frontend:**
- **ProposalCard**: Rendering, expansion, keyboard navigation, decision display
- **RecentProposals**: Proposal list rendering, count display, decision passing
- **useDashboardData**: State management, API calls, decision map creation

### Integration Tests

**Manual Testing Flows:**

1. **Dashboard Load Flow:**
   - Navigate to dashboard
   - Verify proposals load
   - Verify decisions load
   - Verify cards display correctly

2. **Expansion Flow:**
   - Click a proposal card
   - Verify it expands inline
   - Verify reasoning displays
   - Click again to collapse
   - Verify it collapses

3. **Keyboard Navigation Flow:**
   - Tab to a proposal card
   - Press Enter to expand
   - Press Escape to collapse
   - Verify focus management

4. **Decision States Flow:**
   - View proposal with decision (FOR/AGAINST/ABSTAIN)
   - View proposal without decision
   - Verify appropriate badges and messages

5. **Error Handling Flow:**
   - Stop backend server
   - Verify dashboard shows error message
   - Restart backend
   - Verify dashboard recovers

### Manual Testing Steps

**Setup:**
```bash
# Terminal 1: Start backend
cd backend
export $(cat ../.env | xargs)
export SAFE_CONTRACT_ADDRESSES='{"base": "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"}'
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

**Test Checklist:**

1. **Visual Verification:**
   - [ ] Dashboard displays "All Proposals" heading
   - [ ] Proposal count displays correctly (e.g., "5 proposals")
   - [ ] Each card shows proposal title
   - [ ] Each card shows vote badge (FOR/AGAINST/ABSTAIN/No Vote)
   - [ ] Chevron icon appears on each card
   - [ ] Cards have hover effect

2. **Interaction Verification:**
   - [ ] Clicking card expands it
   - [ ] Reasoning text displays
   - [ ] Confidence displays as percentage
   - [ ] Strategy displays capitalized
   - [ ] Timestamp displays correctly formatted
   - [ ] Clicking again collapses card
   - [ ] Multiple cards can be expanded at once

3. **Keyboard Verification:**
   - [ ] Tab navigates between cards
   - [ ] Enter key expands focused card
   - [ ] Space key expands focused card
   - [ ] Escape key collapses expanded card
   - [ ] Focus indicator visible

4. **Edge Cases:**
   - [ ] Proposals without decisions are not displayed (filtered out)
   - [ ] Very long reasoning text displays properly (scrollable/wrapped)
   - [ ] Empty proposal list handled (shouldn't crash)
   - [ ] Dashboard shows appropriate message when no proposals have decisions yet

5. **Network Verification:**
   - [ ] Open DevTools Network tab
   - [ ] Reload dashboard
   - [ ] Verify `GET /proposals` request
   - [ ] Verify `GET /agent-run/decisions` request
   - [ ] Verify NO `POST /proposals/summarize` request
   - [ ] Check backend logs for clean requests

6. **Navigation Verification:**
   - [ ] No "View Details" links appear
   - [ ] Clicking cards doesn't navigate away
   - [ ] Browser URL stays on dashboard
   - [ ] Navigating to `/proposals/any-id` shows 404


## Migration Notes

**No data migration required** - all changes are to frontend UI and backend API endpoints. No database schema changes.

**Deployment strategy:**
1. Deploy backend changes first (remove summarization endpoint)
2. Deploy frontend changes second (no longer calls removed endpoint)
3. Verify dashboard loads correctly
4. Monitor error logs for any issues

**Rollback strategy:**
- Backend rollback: Re-deploy previous version (summarization endpoint returns)
- Frontend rollback: Re-deploy previous version (calls summarization endpoint again)
- No data loss risk - decision files remain unchanged

**User impact:**
- Improved UX: Faster loading (fewer API calls), no navigation required
- All information accessible on one page
- Better mobile experience (no multi-page navigation)

## References

### Research Documents
- Original exploration: Research tasks completed in this session
- Decision API analysis: `backend/main.py:715-768`
- Decision service: `backend/services/agent_run_service.py:1372-1443`
- Decision models: `backend/models.py:387-455`

### Similar Implementations
- OrganizationDropdown: Expandable pattern reference (`frontend/src/lib/components/OrganizationDropdown.svelte`)
- VotingIndicator: Vote display component (`frontend/src/lib/components/dashboard/VotingIndicator.svelte`)
- AgentStatusWidget: Dashboard widget pattern (`frontend/src/lib/components/dashboard/AgentStatusWidget.svelte`)

### Documentation
- Component guidelines: `frontend/src/lib/components/CLAUDE.md`
- API specification: `specs/api.md`
- Frontend specification: `specs/frontend.md`

### Key Files Modified
- Backend: `main.py`, `ai_service.py`, `models.py`
- Frontend hooks: `useDashboardData.ts`
- Frontend components: `ProposalCard.svelte`, `RecentProposals.svelte`, `DashboardContent.svelte`
- Frontend routes: `+page.svelte`, delete `proposals/[id]/+page.svelte`

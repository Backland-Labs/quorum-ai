# Frontend Specification

## Overview

The Quorum AI frontend is a modern SvelteKit application providing a user interface for DAO proposal management and autonomous voting. It uses TypeScript for type safety, TailwindCSS v4 for styling, and integrates with the backend via OpenAPI-generated clients.

## Architecture

### Technology Stack
- **Framework**: SvelteKit with Svelte 5 runes
- **Language**: TypeScript with strict type checking
- **Styling**: TailwindCSS v4.x with PostCSS
- **Build Tool**: Vite
- **Testing**: Vitest with Testing Library
- **API Client**: OpenAPI-generated TypeScript client (openapi-fetch)

### Project Structure
```
frontend/
├── src/
│   ├── lib/
│   │   ├── api/          # OpenAPI client and API utilities
│   │   ├── components/   # Reusable UI components
│   │   ├── hooks/        # Custom stores and state management
│   │   ├── types/        # TypeScript type definitions
│   │   └── utils/        # Utility functions
│   ├── routes/           # SvelteKit file-based routing
│   └── app.css          # Global styles
├── static/              # Static assets
└── tests/               # Test files
```

## Component Organization

### Component Principles
1. **Single Responsibility**: Each component serves one clear purpose
2. **Composition**: Build complex UI from simple, reusable components
3. **Props Interface**: Well-defined TypeScript interfaces for all props
4. **Event Handling**: Consistent `handle*` naming convention

### Component Categories
- **Base Components**: `LoadingSkeleton`, `MetricCard`, `TabNavigation`
- **Dashboard Components**: `DashboardHeader`, `ProposalCard`, `VotingIndicator`
- **Agent Dashboard Components**: `AgentStatusWidget`, `AgentDecisionsPanel`, `AgentStatistics`, `AgentQuickActions`
- **Feature Components**: `OrganizationDropdown`, `TopVoters`, `OverviewTab`
- **State Components**: `LoadingState`, `ErrorState`, `EmptyState`

## State Management

### Store-based Architecture
- **Svelte Stores**: Writable stores for reactive state management
- **Custom Hooks**: `createDashboardStore()` pattern for complex state logic
- **State Structure**: Centralized dashboard state with clear data flow
- **Runes Integration**: Uses Svelte 5's `$state` for local component state

### State Flow
```typescript
// Example: Dashboard state management
interface DashboardState {
  organizationsWithProposals: OrganizationWithProposals[];
  loading: boolean;
  error: string | null;
  activeTab: TabType;
  selectedOrganization: Organization | null;
  allProposals: Proposal[];
  proposalSummaries: Map<string, ProposalSummary>;
}
```

## API Integration

### OpenAPI Workflow
1. Backend exposes OpenAPI schema at `/openapi.json`
2. Generate TypeScript client: `npm run generate-api`
3. Type-safe API calls with full autocompletion
4. Environment-aware base URL configuration

### API Client Pattern
```typescript
import createClient from "openapi-fetch";
import type { paths } from "./client";

const apiClient = createClient<paths>({
  baseUrl: browser ? "http://localhost:8000" : "http://backend:8000"
});

// Type-safe API calls
const { data, error } = await apiClient.GET("/proposals", {
  params: { query: { space_id: "example.eth" } }
});
```

## Agent Dashboard Components

### Overview
The Agent Dashboard provides real-time visibility into the autonomous voting agent's status, decisions, and performance. These components are integrated into the main dashboard's Overview tab.

### Component Details

#### AgentStatusWidget
**Purpose**: Display real-time agent status and activity indicator
**Location**: `src/lib/components/dashboard/AgentStatusWidget.svelte`
**Features**:
- Polls `/agent-run/status` endpoint every 30 seconds
- Shows current state (idle, fetching_proposals, analyzing, voting, error)
- Displays last run timestamp in human-readable format
- Visual activity indicator (green dot when active)

#### AgentDecisionsPanel
**Purpose**: Show recent voting decisions made by the agent
**Location**: `src/lib/components/dashboard/AgentDecisionsPanel.svelte`
**Features**:
- Fetches last 5 decisions from `/agent-run/decisions`
- Displays proposal title, vote choice (FOR/AGAINST), and confidence score
- Links to proposal detail pages
- Handles empty state gracefully

#### AgentStatistics
**Purpose**: Display aggregated performance metrics
**Location**: `src/lib/components/dashboard/AgentStatistics.svelte`
**Features**:
- Shows total runs, proposals reviewed, votes cast
- Does not include average confidence or success rate (removed as of 2025-09-05)
- Updates when dashboard refreshes
- Responsive grid layout for metrics

#### AgentQuickActions
**Purpose**: Provide manual control over agent execution
**Location**: `src/lib/components/dashboard/AgentQuickActions.svelte`
**Features**:
- "Run Now" button to trigger agent execution
- Disabled state when agent is already active
- Loading state during API calls
- Success/error feedback messages

### Integration Pattern
```typescript
// In OverviewTab.svelte
<script lang="ts">
  import AgentStatusWidget from '$lib/components/dashboard/AgentStatusWidget.svelte';
  import AgentDecisionsPanel from '$lib/components/dashboard/AgentDecisionsPanel.svelte';
  import AgentStatistics from '$lib/components/dashboard/AgentStatistics.svelte';
  import AgentQuickActions from '$lib/components/dashboard/AgentQuickActions.svelte';

  // Props
  let currentSpaceId = $props<string>();
</script>

<div class="agent-dashboard">
  <AgentStatusWidget />
  <AgentStatistics />
  <AgentQuickActions {currentSpaceId} />
  <AgentDecisionsPanel />
</div>
```

### State Management
- Components use Svelte 5 runes (`$state`, `$effect`)
- Local state for loading, error, and data
- No global store dependency (except currentSpaceId)
- Auto-refresh via polling or parent refresh

### API Integration
All components use the OpenAPI-generated client:
```typescript
import { apiClient } from '$lib/api';

// Get status
const { data } = await apiClient.GET('/agent-run/status');

// Trigger run
const { data } = await apiClient.POST('/agent-run', {
  body: { space_id: currentSpaceId, dry_run: false }
});
```

## Testing Approach

### Testing Stack
- **Framework**: Vitest with jsdom/happy-dom environment
- **Component Testing**: @testing-library/svelte for Svelte 5
- **Setup**: Global test setup with jest-dom matchers
- **Coverage**: Component behavior and integration tests

### Testing Patterns
```typescript
// Component test example
import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import Component from './Component.svelte';

describe('Component', () => {
  it('renders with expected content', () => {
    render(Component, { props: { title: 'Test' } });
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

### Test Organization
- Colocated with components (`.test.ts` files)
- Test utilities in `lib/test-utils.ts`
- Mock API responses for isolated testing
- Focus on user interactions and behavior

## Best Practices

1. **Type Safety**: Leverage TypeScript and OpenAPI types throughout
2. **Accessibility**: Proper ARIA labels and keyboard navigation
3. **Performance**: Use Svelte's reactivity efficiently
4. **Code Style**: Consistent formatting with Prettier
5. **Error Handling**: Graceful degradation with clear error states
6. **Responsive Design**: Mobile-first approach with TailwindCSS

## Troubleshooting Guide

### Agent Dashboard Issues

#### Status Widget Not Updating
**Problem**: Agent status remains stuck or doesn't refresh
**Solutions**:
1. Check browser console for API errors
2. Verify backend is running on port 8716
3. Ensure `/agent-run/status` endpoint is accessible
4. Check for CORS issues if frontend/backend on different ports

#### "Run Now" Button Disabled
**Problem**: Cannot trigger agent run manually
**Causes**:
- Agent is already running (check status widget)
- No space ID selected in dashboard
- API connection issues

**Solutions**:
1. Wait for current run to complete
2. Select a valid space from the dropdown
3. Check network tab for failed API calls

#### Empty Decisions Panel
**Problem**: No voting decisions displayed
**Causes**:
- Agent hasn't run yet
- No proposals met voting criteria
- Checkpoint files missing or corrupted

**Solutions**:
1. Trigger an agent run first
2. Check agent logs for filtering reasons
3. Verify checkpoint files exist in backend

#### Statistics Show Zeros
**Problem**: All metrics display as 0
**Causes**:
- No agent runs completed
- Checkpoint aggregation failing
- API endpoint error

**Debug Steps**:
```bash
# Check for checkpoint files
ls backend/agent_checkpoint_*.json

# Test API endpoint
curl http://localhost:8716/agent-run/statistics

# Check backend logs
tail -f backend/log.txt
```

#### Component Build Errors
**Problem**: TypeScript errors after adding components
**Solutions**:
1. Regenerate API client: `npm run generate-api`
2. Ensure all imports use correct paths
3. Update TypeScript types if API changed
4. Clear build cache: `rm -rf .svelte-kit`

#### Polling Performance Issues
**Problem**: Browser becomes slow with polling
**Solutions**:
1. Increase polling interval (default 30s)
2. Implement visibility API to pause when hidden
3. Add cleanup in component unmount
4. Check for memory leaks in dev tools

### Common Error Messages

#### "Failed to fetch agent status"
- Backend not running
- Incorrect API base URL
- Network connectivity issues

#### "No space selected"
- User must select a DAO space first
- Pass currentSpaceId prop correctly

#### "Agent run failed"
- Check user preferences configuration
- Verify wallet connection
- Review backend error logs

### Development Tips

1. **Hot Module Replacement**: If HMR breaks, restart dev server
2. **Type Generation**: Run `npm run generate-api` after backend changes
3. **Component Testing**: Mock API responses for reliable tests
4. **State Debugging**: Use Svelte DevTools browser extension
5. **Performance**: Profile with Chrome DevTools Performance tab

This specification ensures a maintainable, type-safe, and performant frontend that integrates seamlessly with the FastAPI backend while providing an excellent user experience for DAO proposal management.

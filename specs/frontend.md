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

This specification ensures a maintainable, type-safe, and performant frontend that integrates seamlessly with the FastAPI backend while providing an excellent user experience for DAO proposal management.
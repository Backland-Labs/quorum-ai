# Component Development Guide

This file provides specific guidance for working with Svelte components in this Quorum AI application. All components follow Svelte 5 patterns with TypeScript and TailwindCSS v4 styling.

## Component Architecture Patterns

### Props Interface Definition
All components use explicit TypeScript interfaces for props:

```typescript
interface Props {
  requiredProp: string;
  optionalProp?: boolean;
  callbackProp?: (data: Type) => void;
}

let { requiredProp, optionalProp = false, callbackProp }: Props = $props();
```

### Component Organization
Components are organized by feature domains:
- `/dashboard/` - Dashboard-specific components (panels, cards, widgets)
- `/setup/` - User configuration and preference components
- Root level - Shared/reusable components (loading, metrics, dropdowns)

## Svelte 5 Runes Usage

### State Management
- Use `$state()` for local component state
- Use `$derived()` for computed values
- Use `$props()` for component props with destructuring

```typescript
// Local state
let isOpen = $state(false);
let formData = $state({ name: '', email: '' });

// Computed values
let displayName = $derived(user?.name || 'Anonymous');
let isValid = $derived(formData.name.length > 0 && formData.email.length > 0);

// Props destructuring
let { items, selectedItem, onSelect }: Props = $props();
```

### Event Handling
- Prefix all event handlers with "handle" (e.g., `handleClick`, `handleSubmit`)
- Use function expressions for handlers
- Support keyboard accessibility (Enter, Space, Escape)

```typescript
const handleToggle = () => {
  if (!loading) {
    isOpen = !isOpen;
  }
};

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    handleToggle();
  } else if (event.key === 'Escape') {
    isOpen = false;
  }
};
```

## TailwindCSS v4 Styling Conventions

### Component Base Classes
- Use semantic color classes: `text-secondary-600`, `bg-white`, `border-secondary-200`
- Apply consistent spacing: `p-4`, `space-y-4`, `gap-3`
- Use responsive breakpoints: `sm:text-base`, `sm:p-6`, `sm:flex-row`

### Interactive States
- Hover states: `hover:bg-secondary-50`, `hover:shadow-md`
- Focus states: `focus:outline-none focus:ring-2 focus:ring-primary-500`
- Disabled states: `disabled:opacity-50 disabled:cursor-not-allowed`
- Loading states: `animate-pulse`

### Color System
- Primary: `primary-500`, `primary-600` (interactive elements)
- Secondary: `secondary-600`, `secondary-900` (text), `secondary-200` (borders)
- Status colors: `text-green-600` (success), `text-red-600` (error), `text-yellow-600` (warning)

### Layout Patterns
```css
/* Card pattern */
class="bg-white border border-secondary-200 rounded-lg p-5 hover:border-primary-300 hover:shadow-md transition-all duration-200"

/* Button pattern */
class="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md transition-colors duration-200"

/* Dropdown pattern */
class="absolute z-50 w-full mt-1 bg-white border border-secondary-300 rounded-md shadow-lg max-h-60 overflow-auto"
```

## Component Composition Patterns

### Conditional Rendering
Use `class:` directive instead of ternary operators when possible:

```svelte
<!-- Preferred -->
<div class="base-class" class:active={isActive} class:disabled={isDisabled}>

<!-- Avoid -->
<div class="base-class {isActive ? 'active' : ''} {isDisabled ? 'disabled' : ''}">
```

### Data Validation and Constants
Define constants at the top of the script block:

```typescript
// Constants
const ADDRESS_TRUNCATE_LENGTH = 10;
const MIN_CONFIDENCE_THRESHOLD = 0;
const MAX_CONFIDENCE_THRESHOLD = 1;

// Validation functions
function validateInput(value: string): boolean {
  return value.length >= MIN_LENGTH && value.length <= MAX_LENGTH;
}
```

### Utility Functions
Keep utility functions within components for component-specific logic:

```typescript
function formatTimestamp(timestamp: string | null): string {
  if (!timestamp) return 'Never';
  // formatting logic
}

function getRiskLevelClasses(riskLevel: string): string {
  const riskClasses: Record<string, string> = {
    'LOW': 'bg-green-50 text-green-700',
    'MEDIUM': 'bg-yellow-50 text-yellow-700',
    'HIGH': 'bg-red-50 text-red-700'
  };
  return riskClasses[riskLevel] || riskClasses['MEDIUM'];
}
```

## Accessibility Requirements

### ARIA Attributes
- Use semantic HTML elements where possible
- Add `role` attributes for interactive elements
- Include `aria-label`, `aria-expanded`, `aria-controls` for complex components
- Use `aria-selected` for selectable items

```svelte
<button
  role="combobox"
  aria-haspopup="listbox"
  aria-expanded={isOpen}
  aria-controls="options-listbox"
  aria-label="Select organization"
>

<div role="listbox" id="options-listbox">
  <button role="option" aria-selected={isSelected}>
```

### Keyboard Navigation
- Support Tab navigation with proper `tabindex`
- Handle Enter, Space, Escape keys appropriately
- Provide focus indicators with `focus:` classes

### Screen Reader Support
- Use descriptive text for loading states: `aria-label="Loading content"`
- Provide context for list items: `aria-label="Voter 1 of 10"`
- Include status announcements with `role="status"`

## Testing Approaches

### Test Structure
- Use descriptive test names that explain the behavior being tested
- Include comments explaining the purpose and importance of each test
- Group related tests in `describe` blocks by functionality

```typescript
describe('MetricCard', () => {
  test('renders metric with title and value', () => {
    // Tests basic rendering functionality to ensure component displays correctly
    render(MetricCard, {
      props: { title: 'Total Proposals', value: '150' }
    });
    
    expect(screen.getByText('Total Proposals')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });
});
```

### Testing Patterns
- Use `data-testid` attributes for reliable element selection
- Test both positive and negative cases
- Mock external dependencies (stores, API clients)
- Test keyboard interactions and accessibility

### Responsive Testing
- Create separate `.responsive.test.ts` files for components requiring responsive behavior testing
- Test viewport-specific functionality and breakpoint behavior

## API Integration Patterns

### Type Safety
Import and use generated API types:

```typescript
import type { components } from '$lib/api/client';

type ProposalVoter = components['schemas']['ProposalVoter'];
type VoteType = components['schemas']['VoteType'];
```

### Store Integration
For components that need reactive data, use Svelte stores:

```typescript
import { agentStatusStore } from '$lib/stores/agentStatus';

// Subscribe to store state
const storeState = $state($agentStatusStore);
```

## Error Handling and Validation

### Runtime Assertions
Include runtime assertions for critical component methods:

```typescript
function validateProps(): void {
  console.assert(proposal !== null, 'Proposal should not be null');
  console.assert(proposal !== undefined, 'Proposal should not be undefined');
}

function getRiskLevelClasses(riskLevel: string): string {
  console.assert(typeof riskLevel === 'string', 'Risk level must be a string');
  console.assert(riskLevel.length > 0, 'Risk level should not be empty');
  // implementation
}
```

### Form Validation
For form components, implement validation with clear error states:

```typescript
// Validation state
let confidenceError = $state('');
let isSubmitting = $state(false);

// Validation functions
const validateConfidence = () => {
  if (confidenceThreshold < MIN_THRESHOLD || confidenceThreshold > MAX_THRESHOLD) {
    confidenceError = `Confidence must be between ${MIN_THRESHOLD} and ${MAX_THRESHOLD}`;
  } else {
    confidenceError = '';
  }
};

// Apply error styling conditionally
<input
  class="base-input-class"
  class:border-red-500={confidenceError}
  onblur={validateConfidence}
/>
```

## Performance Considerations

### Loading States
Implement loading states for components that fetch data:

```svelte
{#if loading}
  <LoadingSkeleton height="h-6" count={3} />
{:else if error}
  <div class="text-red-600 text-sm">{error}</div>
{:else}
  <!-- Component content -->
{/if}
```

### Component Variants
Support different display variants when components need flexibility:

```typescript
interface Props {
  variant?: 'compact' | 'detailed';
}

// Apply variant-specific rendering
{#if variant === 'detailed'}
  <!-- Detailed view with more information -->
{:else}
  <!-- Compact view with essential information only -->
{/if}
```

## Code Organization Best Practices

### Method Length
- Keep component methods under 60 lines
- Extract complex logic into separate utility functions
- Break down large components into smaller, focused components

### Naming Conventions
- Use descriptive, self-documenting component and prop names
- Prefix boolean props with "is", "has", "can" (e.g., `isActive`, `hasError`, `canEdit`)
- Use consistent naming for similar functionality across components

### Import Organization
Order imports consistently:
1. Svelte/SvelteKit imports
2. Third-party library imports
3. Local utility imports
4. Type imports
5. Component imports

```typescript
import { tick } from 'svelte';
import type { components } from '$lib/api/client';
import { formatTimestamp } from '$lib/utils/time';
import type { ExtendedProposal } from '$lib/types/dashboard';
import VotingIndicator from './VotingIndicator.svelte';
```
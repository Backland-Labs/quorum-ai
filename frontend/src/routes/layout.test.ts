import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import Layout from './+layout.svelte';

// Purpose: Ensure top nav uses "Dashboard" label instead of "Organizations"

describe('Top Navigation', () => {
  it('shows Dashboard link and not Organizations', () => {
    render(Layout);

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Organizations')).not.toBeInTheDocument();
  });

  // Purpose: Verify an Instructions tab is visible and correctly linked
  it('shows Instructions link in navigation with correct href', () => {
    render(Layout);

    const link = screen.getByRole('link', { name: 'Instructions' });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/instructions');
  });
});

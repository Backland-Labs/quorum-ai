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
});

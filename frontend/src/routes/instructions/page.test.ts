import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import Page from './+page.svelte';

// Purpose: Ensure Instructions page clearly explains usage, required setup, and voting power requirements

describe('Instructions Page', () => {
  it('renders the page title and key sections', () => {
    render(Page);

    // H1 title
    expect(screen.getByRole('heading', { level: 1, name: /instructions/i })).toBeInTheDocument();

    // Section headings
    expect(screen.getByText(/getting started/i)).toBeInTheDocument();
    expect(screen.getByText(/required setup/i)).toBeInTheDocument();
    expect(screen.getByText(/voting power/i)).toBeInTheDocument();
  });

  it('sets a descriptive document title', () => {
    render(Page);
    expect(document.title.toLowerCase()).toContain('instructions');
  });
});

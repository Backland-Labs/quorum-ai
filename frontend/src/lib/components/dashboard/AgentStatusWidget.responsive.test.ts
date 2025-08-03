import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import AgentStatusWidget from './AgentStatusWidget.svelte';

// Mock the API client
vi.mock('$lib/api', () => ({
  apiClient: {
    GET: vi.fn()
  }
}));

describe('AgentStatusWidget - Responsive Design', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display in mobile-friendly layout on small screens', () => {
    // Test that the component uses responsive classes for mobile
    const { container } = render(AgentStatusWidget);

    // Check for mobile-first responsive classes
    const widget = container.querySelector('[data-testid="agent-status-widget"]');
    expect(widget?.classList.contains('w-full')).toBe(true);
    expect(widget?.classList.contains('sm:w-auto')).toBe(true);
  });

  it('should stack elements vertically on mobile', () => {
    // Test that status and timestamp stack on mobile
    const { container } = render(AgentStatusWidget);

    const contentWrapper = container.querySelector('[data-testid="status-content"]');
    expect(contentWrapper?.classList.contains('flex')).toBe(true);
    expect(contentWrapper?.classList.contains('flex-col')).toBe(true);
    expect(contentWrapper?.classList.contains('sm:flex-row')).toBe(true);
  });

  it('should use appropriate text sizes for mobile', () => {
    // Test responsive text sizing
    const { container } = render(AgentStatusWidget);

    const title = container.querySelector('[data-testid="widget-title"]');
    expect(title?.classList.contains('text-sm')).toBe(true);
    expect(title?.classList.contains('sm:text-base')).toBe(true);

    const status = container.querySelector('[data-testid="agent-state"]');
    expect(status?.classList.contains('text-xs')).toBe(true);
    expect(status?.classList.contains('sm:text-sm')).toBe(true);
  });

  it('should have touch-friendly spacing on mobile', () => {
    // Test that padding and spacing is appropriate for touch
    const { container } = render(AgentStatusWidget);

    const widget = container.querySelector('[data-testid="agent-status-widget"]');
    expect(widget?.classList.contains('p-3')).toBe(true);
    expect(widget?.classList.contains('sm:p-4')).toBe(true);
  });

  it('should be accessible with proper ARIA labels', () => {
    // Test accessibility features
    render(AgentStatusWidget);

    const widget = screen.getByRole('region', { name: /agent status/i });
    expect(widget).toBeInTheDocument();

    // Check for status announcement region
    const status = screen.getByRole('status');
    expect(status).toBeInTheDocument();
  });

  it('should handle viewport changes gracefully', () => {
    // Test that component responds to viewport changes
    const { container } = render(AgentStatusWidget);

    // Check that responsive utilities are in place
    const elements = container.querySelectorAll('[class*="sm:"], [class*="md:"], [class*="lg:"]');
    expect(elements.length).toBeGreaterThan(0);
  });
});

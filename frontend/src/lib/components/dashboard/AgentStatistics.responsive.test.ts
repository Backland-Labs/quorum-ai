import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import AgentStatistics from './AgentStatistics.svelte';

// Mock the API client
vi.mock('$lib/api', () => ({
  apiClient: {
    GET: vi.fn()
  }
}));

describe('AgentStatistics - Responsive Design', () => {
  const mockStatistics = {
    total_runs: 42,
    total_proposals_reviewed: 156,
    total_votes_cast: 89,
    average_confidence: 0.875,
    success_rate: 0.95
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.GET.mockResolvedValue({
      data: mockStatistics,
      error: undefined
    });
  });

  it('should use responsive grid layout for statistics', async () => {
    const { container } = render(AgentStatistics);
    
    await screen.findByText('42'); // Wait for data to load
    
    const grid = container.querySelector('[data-testid="statistics-grid"]');
    expect(grid?.classList.contains('grid')).toBe(true);
    expect(grid?.classList.contains('grid-cols-1')).toBe(true);
    expect(grid?.classList.contains('sm:grid-cols-2')).toBe(true);
    expect(grid?.classList.contains('lg:grid-cols-3')).toBe(true);
    expect(grid?.classList.contains('gap-3')).toBe(true);
    expect(grid?.classList.contains('sm:gap-4')).toBe(true);
  });

  it('should display stat cards with appropriate mobile sizing', async () => {
    const { container } = render(AgentStatistics);
    
    await screen.findByText('42');
    
    const statCards = container.querySelectorAll('[data-testid="stat-card"]');
    expect(statCards.length).toBe(5); // All 5 statistics
    
    statCards.forEach(card => {
      // Mobile-first sizing
      expect(card.classList.contains('p-3')).toBe(true);
      expect(card.classList.contains('sm:p-4')).toBe(true);
      
      // Full width on mobile
      expect(card.classList.contains('w-full')).toBe(true);
    });
  });

  it('should use responsive text sizes for statistics', async () => {
    const { container } = render(AgentStatistics);
    
    await screen.findByText('42');
    
    // Component title
    const title = container.querySelector('[data-testid="statistics-title"]');
    expect(title?.classList.contains('text-base')).toBe(true);
    expect(title?.classList.contains('sm:text-lg')).toBe(true);
    
    // Stat labels
    const labels = container.querySelectorAll('[data-testid="stat-label"]');
    labels.forEach(label => {
      expect(label.classList.contains('text-xs')).toBe(true);
      expect(label.classList.contains('sm:text-sm')).toBe(true);
    });
    
    // Stat values
    const values = container.querySelectorAll('[data-testid="stat-value"]');
    values.forEach(value => {
      expect(value.classList.contains('text-lg')).toBe(true);
      expect(value.classList.contains('sm:text-xl')).toBe(true);
      expect(value.classList.contains('lg:text-2xl')).toBe(true);
    });
  });

  it('should handle percentage display in a mobile-friendly way', async () => {
    const { container } = render(AgentStatistics);
    
    await screen.findByText('87.5%'); // Average confidence
    await screen.findByText('95%'); // Success rate
    
    const percentages = container.querySelectorAll('[data-testid="percentage-value"]');
    percentages.forEach(pct => {
      // Ensure percentages don't overflow on small screens
      expect(pct.classList.contains('tabular-nums')).toBe(true);
      expect(pct.classList.contains('font-mono')).toBe(true);
    });
  });

  it('should stack elements appropriately on mobile', async () => {
    const { container } = render(AgentStatistics);
    
    await screen.findByText('42');
    
    const statContents = container.querySelectorAll('[data-testid="stat-content"]');
    statContents.forEach(content => {
      expect(content.classList.contains('flex')).toBe(true);
      expect(content.classList.contains('flex-col')).toBe(true);
      expect(content.classList.contains('space-y-1')).toBe(true);
    });
  });

  it('should be accessible with proper ARIA labels', async () => {
    render(AgentStatistics);
    
    await screen.findByText('42');
    
    // Check for section landmark
    const section = screen.getByRole('region', { name: /agent statistics/i });
    expect(section).toBeInTheDocument();
    
    // Check for described statistics
    const stats = screen.getAllByRole('group');
    expect(stats.length).toBeGreaterThan(0);
    
    // Each stat should have a label
    stats.forEach(stat => {
      expect(stat).toHaveAccessibleName();
    });
  });

  it('should display loading state in a mobile-friendly way', () => {
    const { apiClient } = vi.mocked(vi.mocked(import('$lib/api')));
    apiClient.GET.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    const { container } = render(AgentStatistics);
    
    const loading = container.querySelector('[data-testid="loading-state"]');
    expect(loading?.classList.contains('text-center')).toBe(true);
    expect(loading?.classList.contains('p-4')).toBe(true);
    expect(loading?.classList.contains('sm:p-6')).toBe(true);
  });

  it('should handle error state responsively', async () => {
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.GET.mockResolvedValue({
      data: undefined,
      error: { message: 'Failed to load statistics' }
    });
    
    const { container } = render(AgentStatistics);
    
    await screen.findByText(/error loading/i);
    
    const errorState = container.querySelector('[data-testid="error-state"]');
    expect(errorState?.classList.contains('text-center')).toBe(true);
    expect(errorState?.classList.contains('p-4')).toBe(true);
    expect(errorState?.classList.contains('sm:p-6')).toBe(true);
    expect(errorState?.classList.contains('text-sm')).toBe(true);
    expect(errorState?.classList.contains('sm:text-base')).toBe(true);
  });

  it('should use appropriate icon sizing for mobile', async () => {
    const { container } = render(AgentStatistics);
    
    await screen.findByText('42');
    
    const icons = container.querySelectorAll('[data-testid="stat-icon"]');
    icons.forEach(icon => {
      expect(icon.classList.contains('w-4')).toBe(true);
      expect(icon.classList.contains('h-4')).toBe(true);
      expect(icon.classList.contains('sm:w-5')).toBe(true);
      expect(icon.classList.contains('sm:h-5')).toBe(true);
    });
  });
});
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import AgentDecisionsPanel from './AgentDecisionsPanel.svelte';

// Mock the API client
vi.mock('$lib/api', () => ({
  apiClient: {
    GET: vi.fn()
  }
}));

describe('AgentDecisionsPanel - Responsive Design', () => {
  const mockDecisions = [
    {
      proposal_id: '0x123',
      proposal_title: 'Test Proposal 1',
      vote: 'FOR',
      confidence_score: 0.85,
      timestamp: '2025-01-30T10:00:00Z',
      reason: 'Test reason'
    },
    {
      proposal_id: '0x456',
      proposal_title: 'Test Proposal 2 with a very long title that should wrap on mobile devices',
      vote: 'AGAINST',
      confidence_score: 0.92,
      timestamp: '2025-01-30T11:00:00Z',
      reason: 'Test reason'
    }
  ];

  beforeEach(async () => {
    vi.clearAllMocks();
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.GET.mockResolvedValue({
      data: { decisions: mockDecisions },
      error: undefined
    });
  });

  it('should use responsive container sizing', () => {
    const { container } = render(AgentDecisionsPanel);

    const panel = container.querySelector('[data-testid="decisions-panel"]');
    expect(panel?.classList.contains('w-full')).toBe(true);
    expect(panel?.classList.contains('max-w-full')).toBe(true);
    expect(panel?.classList.contains('sm:max-w-2xl')).toBe(true);
  });

  it('should display decisions in a mobile-friendly card layout', async () => {
    const { container } = render(AgentDecisionsPanel);

    // Wait for decisions to load
    await screen.findByText('Test Proposal 1');

    const decisionCards = container.querySelectorAll('[data-testid="decision-card"]');
    decisionCards.forEach(card => {
      // Cards should stack on mobile
      expect(card.classList.contains('flex')).toBe(true);
      expect(card.classList.contains('flex-col')).toBe(true);
      expect(card.classList.contains('sm:flex-row')).toBe(true);

      // Proper spacing for touch
      expect(card.classList.contains('p-3')).toBe(true);
      expect(card.classList.contains('sm:p-4')).toBe(true);
    });
  });

  it('should handle long proposal titles with proper text wrapping', async () => {
    const { container } = render(AgentDecisionsPanel);

    await screen.findByText(/Test Proposal 2/);

    const titles = container.querySelectorAll('[data-testid="proposal-title"]');
    titles.forEach(title => {
      expect(title.classList.contains('break-words')).toBe(true);
      expect(title.classList.contains('line-clamp-2')).toBe(true);
      expect(title.classList.contains('sm:line-clamp-none')).toBe(true);
    });
  });

  it('should use responsive text sizes', async () => {
    const { container } = render(AgentDecisionsPanel);

    await screen.findByText('Test Proposal 1');

    // Panel title
    const title = container.querySelector('[data-testid="panel-title"]');
    expect(title?.classList.contains('text-base')).toBe(true);
    expect(title?.classList.contains('sm:text-lg')).toBe(true);

    // Proposal titles
    const proposalTitles = container.querySelectorAll('[data-testid="proposal-title"]');
    proposalTitles.forEach(title => {
      expect(title.classList.contains('text-sm')).toBe(true);
      expect(title.classList.contains('sm:text-base')).toBe(true);
    });

    // Vote badges and confidence scores
    const badges = container.querySelectorAll('[data-testid="vote-badge"], [data-testid="confidence-score"]');
    badges.forEach(badge => {
      expect(badge.classList.contains('text-xs')).toBe(true);
      expect(badge.classList.contains('sm:text-sm')).toBe(true);
    });
  });

  it('should have touch-friendly clickable areas', async () => {
    const { container } = render(AgentDecisionsPanel);

    await screen.findByText('Test Proposal 1');

    const links = container.querySelectorAll('a[href*="/proposals/"]');
    links.forEach(link => {
      // Ensure links have minimum touch target size
      expect(link.classList.contains('min-h-[44px]')).toBe(true);
      expect(link.classList.contains('flex')).toBe(true);
      expect(link.classList.contains('items-center')).toBe(true);
    });
  });

  it('should be accessible with proper ARIA labels', async () => {
    render(AgentDecisionsPanel);

    await screen.findByText('Test Proposal 1');

    // Check for section landmark
    const panel = screen.getByRole('region', { name: /recent decisions/i });
    expect(panel).toBeInTheDocument();

    // Check for list semantics
    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();

    // Check for proper link labels
    const links = screen.getAllByRole('link');
    links.forEach(link => {
      expect(link).toHaveAccessibleName();
    });
  });

  it('should display empty state in a mobile-friendly way', async () => {
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.GET.mockResolvedValue({
      data: { decisions: [] },
      error: undefined
    });

    const { container } = render(AgentDecisionsPanel);

    await screen.findByText(/no voting decisions/i);

    const emptyState = container.querySelector('[data-testid="empty-state"]');
    expect(emptyState?.classList.contains('text-center')).toBe(true);
    expect(emptyState?.classList.contains('p-4')).toBe(true);
    expect(emptyState?.classList.contains('sm:p-6')).toBe(true);
  });

  it('should use responsive grid layout for vote info', async () => {
    const { container } = render(AgentDecisionsPanel);

    await screen.findByText('Test Proposal 1');

    const voteInfo = container.querySelectorAll('[data-testid="vote-info"]');
    voteInfo.forEach(info => {
      expect(info.classList.contains('grid')).toBe(true);
      expect(info.classList.contains('grid-cols-2')).toBe(true);
      expect(info.classList.contains('gap-2')).toBe(true);
      expect(info.classList.contains('sm:flex')).toBe(true);
      expect(info.classList.contains('sm:gap-4')).toBe(true);
    });
  });
});

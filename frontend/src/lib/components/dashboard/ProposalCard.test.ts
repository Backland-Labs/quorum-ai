import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import ProposalCard from './ProposalCard.svelte';
import type { components } from '$lib/api/client';

// Mock the proposal utils
vi.mock('$lib/utils/proposals.js', () => ({
  parseProposalSummary: vi.fn((proposal) => ({
    summary: 'Test summary',
    key_points: ['Point 1', 'Point 2', 'Point 3', 'Point 4'],
    risk_level: 'MEDIUM',
    recommendation: 'REVIEW',
    confidence_score: 0.75
  })),
  cleanProposalTitle: vi.fn((title) => title.replace(/^#\s*/, ''))
}));

// Test data
const mockProposal: components['schemas']['Proposal'] = {
  id: 'test-proposal-1',
  title: '# Test Proposal Title',
  created: 1700000000,
  start: 1700000000,
  end: 1700100000,
  snapshot: '12345',
  state: 'active',
  author: '0x123',
  space: { id: 'test-space', name: 'Test Space' },
  choices: ['For', 'Against', 'Abstain'],
  scores: [100, 50, 25],
  scores_total: 175,
  votes: 50,
  type: 'single-choice',
  body: 'Test proposal body'
};

const mockDecision: components['schemas']['AgentDecisionResponse'] = {
  vote: 'FOR',
  reasoning: 'This proposal aligns with our strategic goals and has strong community support.',
  confidence: 0.85,
  strategy_used: 'balanced'
};

describe('ProposalCard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders proposal title without hash prefix', () => {
      /**
       * Why: Proposal titles from Snapshot often have hash prefixes that should be cleaned for display.
       * What: Verifies that the component renders cleaned proposal title without hash prefix.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          variant: 'compact'
        }
      });

      expect(screen.getByText('Test Proposal Title')).toBeInTheDocument();
    });

    it('renders without decision prop', () => {
      /**
       * Why: ProposalCard should gracefully handle cases where no decision has been made yet.
       * What: Verifies component renders basic proposal info without showing decision-specific elements.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          variant: 'compact'
        }
      });

      expect(screen.getByText('Test Proposal Title')).toBeInTheDocument();
      expect(screen.queryByText('FOR')).not.toBeInTheDocument();
      expect(screen.queryByText('AGAINST')).not.toBeInTheDocument();
      expect(screen.queryByText('ABSTAIN')).not.toBeInTheDocument();
    });

    it('renders with decision prop', () => {
      /**
       * Why: When agent has made a decision, it should be prominently displayed.
       * What: Verifies that decision badge and details are rendered when decision prop is provided.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          variant: 'compact',
          decision: mockDecision
        }
      });

      expect(screen.getByText('Test Proposal Title')).toBeInTheDocument();
      expect(screen.getByText('FOR')).toBeInTheDocument();
    });
  });

  describe('Vote Badge Display', () => {
    it('displays FOR vote badge with green styling', () => {
      /**
       * Why: Vote badges must be visually distinct to quickly communicate agent decisions.
       * What: Verifies FOR vote displays with correct text and green color styling.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      const badge = screen.getByText('FOR');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-green-100', 'text-green-700');
    });

    it('displays AGAINST vote badge with red styling', () => {
      /**
       * Why: AGAINST votes should use red styling to indicate opposition.
       * What: Verifies AGAINST vote displays with correct text and red color styling.
       */
      const againstDecision = { ...mockDecision, vote: 'AGAINST' as const };
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: againstDecision
        }
      });

      const badge = screen.getByText('AGAINST');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-red-100', 'text-red-700');
    });

    it('displays ABSTAIN vote badge with gray styling', () => {
      /**
       * Why: ABSTAIN votes should use neutral gray styling.
       * What: Verifies ABSTAIN vote displays with correct text and gray color styling.
       */
      const abstainDecision = { ...mockDecision, vote: 'ABSTAIN' as const };
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: abstainDecision
        }
      });

      const badge = screen.getByText('ABSTAIN');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveClass('bg-gray-100', 'text-gray-700');
    });
  });

  describe('Expand/Collapse Functionality', () => {
    it('starts in collapsed state', () => {
      /**
       * Why: Cards should default to collapsed to save space and improve scanability.
       * What: Verifies that decision details are not visible initially.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      expect(screen.queryByText('Reasoning')).not.toBeInTheDocument();
      expect(screen.queryByText('Confidence')).not.toBeInTheDocument();
    });

    it('expands to show decision details on click', async () => {
      /**
       * Why: Users need to view detailed decision information on demand.
       * What: Verifies that clicking the card toggles expansion to show reasoning and confidence.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      const toggleButton = screen.getByRole('button');
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false');

      await fireEvent.click(toggleButton);

      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByText('Reasoning')).toBeInTheDocument();
      expect(screen.getByText('Confidence')).toBeInTheDocument();
      expect(screen.getByText('Strategy')).toBeInTheDocument();
    });

    it('collapses when clicked again', async () => {
      /**
       * Why: Users should be able to collapse expanded cards to reduce clutter.
       * What: Verifies toggle behavior works both ways.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      const toggleButton = screen.getByRole('button');

      // Expand
      await fireEvent.click(toggleButton);
      expect(screen.getByText('Reasoning')).toBeInTheDocument();

      // Collapse
      await fireEvent.click(toggleButton);
      expect(screen.queryByText('Reasoning')).not.toBeInTheDocument();
    });

    it('does not show expandable content without decision', async () => {
      /**
       * Why: Expansion should only be relevant when there's decision data to show.
       * What: Verifies that clicking card without decision doesn't show decision details.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal
        }
      });

      const toggleButton = screen.getByRole('button');
      await fireEvent.click(toggleButton);

      expect(screen.queryByText('Reasoning')).not.toBeInTheDocument();
      expect(screen.queryByText('Confidence')).not.toBeInTheDocument();
    });
  });

  describe('Keyboard Accessibility', () => {
    it('expands on Enter key press', async () => {
      /**
       * Why: Keyboard users must be able to interact with all interactive elements.
       * What: Verifies Enter key toggles expansion state.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      const toggleButton = screen.getByRole('button');
      await fireEvent.keyDown(toggleButton, { key: 'Enter' });

      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByText('Reasoning')).toBeInTheDocument();
    });

    it('expands on Space key press', async () => {
      /**
       * Why: Space is standard keyboard activation for buttons alongside Enter.
       * What: Verifies Space key toggles expansion state.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      const toggleButton = screen.getByRole('button');
      await fireEvent.keyDown(toggleButton, { key: ' ' });

      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByText('Reasoning')).toBeInTheDocument();
    });

    it('collapses on Escape key press', async () => {
      /**
       * Why: Escape key is a common pattern for closing expanded UI elements.
       * What: Verifies Escape key collapses expanded card.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      const toggleButton = screen.getByRole('button');

      // First expand
      await fireEvent.click(toggleButton);
      expect(screen.getByText('Reasoning')).toBeInTheDocument();

      // Then collapse with Escape
      await fireEvent.keyDown(toggleButton, { key: 'Escape' });
      expect(screen.queryByText('Reasoning')).not.toBeInTheDocument();
    });

    it('has proper ARIA attributes', () => {
      /**
       * Why: Screen readers need semantic information about interactive elements.
       * What: Verifies component has required ARIA attributes for accessibility.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      const toggleButton = screen.getByRole('button');
      expect(toggleButton).toHaveAttribute('aria-expanded');
      expect(toggleButton).toHaveAttribute('aria-controls', `proposal-details-${mockProposal.id}`);
      expect(toggleButton).toHaveAttribute('tabindex', '0');
    });
  });

  describe('Decision Details Display', () => {
    it('displays reasoning text when expanded', async () => {
      /**
       * Why: The AI reasoning is critical context for understanding decisions.
       * What: Verifies reasoning text is displayed in expanded state.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      await fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('Reasoning')).toBeInTheDocument();
      expect(screen.getByText(mockDecision.reasoning)).toBeInTheDocument();
    });

    it('displays confidence percentage correctly', async () => {
      /**
       * Why: Confidence score helps users assess how certain the AI is about its decision.
       * What: Verifies confidence is converted to percentage and displayed with progress bar.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      await fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('Confidence')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    it('displays strategy used', async () => {
      /**
       * Why: Strategy context helps understand which voting approach was applied.
       * What: Verifies strategy_used field is displayed in expanded view.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: mockDecision
        }
      });

      await fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('Strategy')).toBeInTheDocument();
      expect(screen.getByText('balanced')).toBeInTheDocument();
    });

    it('handles missing confidence gracefully', async () => {
      /**
       * Why: Decision data may be incomplete; component should not crash.
       * What: Verifies component handles missing confidence field without errors.
       */
      const incompleteDecision = {
        vote: 'FOR' as const,
        reasoning: 'Test reasoning',
        confidence: 0,
        strategy_used: 'balanced'
      };

      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: incompleteDecision
        }
      });

      await fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('Confidence')).toBeInTheDocument();
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('handles missing reasoning gracefully', async () => {
      /**
       * Why: Decision data may be incomplete; component should show fallback text.
       * What: Verifies component displays fallback when reasoning is missing.
       */
      const incompleteDecision = {
        vote: 'FOR' as const,
        reasoning: '',
        confidence: 0.85,
        strategy_used: 'balanced'
      };

      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: incompleteDecision
        }
      });

      await fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('No reasoning provided')).toBeInTheDocument();
    });

    it('handles missing strategy gracefully', async () => {
      /**
       * Why: Strategy field may be optional or missing.
       * What: Verifies component displays fallback when strategy_used is missing.
       */
      const incompleteDecision = {
        vote: 'FOR' as const,
        reasoning: 'Test reasoning',
        confidence: 0.85,
        strategy_used: undefined as any
      };

      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          decision: incompleteDecision
        }
      });

      await fireEvent.click(screen.getByRole('button'));

      expect(screen.getByText('Unknown')).toBeInTheDocument();
    });
  });

  describe('Variant Rendering', () => {
    it('renders compact variant without voting indicator', () => {
      /**
       * Why: Compact variant should show minimal information for list views.
       * What: Verifies voting indicator is not shown in compact variant.
       */
      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          variant: 'compact'
        }
      });

      // VotingIndicator should not be rendered in compact mode
      expect(screen.queryByText(/votes for/i)).not.toBeInTheDocument();
    });

    it('renders detailed variant with voting indicator when fullProposal provided', () => {
      /**
       * Why: Detailed variant should show comprehensive proposal information.
       * What: Verifies voting indicator appears in detailed variant with fullProposal data.
       */
      const mockFullProposal = {
        ...mockProposal,
        dao_name: 'Test DAO',
        created_at: 1700000000,
        votes_for: '100',
        votes_against: '50',
        votes_abstain: '25',
        state: 'active',
        end_block: 12345678
      };

      render(ProposalCard, {
        props: {
          proposal: mockProposal,
          fullProposal: mockFullProposal,
          variant: 'detailed'
        }
      });

      // Should render VotingIndicator component
      expect(screen.getByText('Test DAO')).toBeInTheDocument();
    });
  });
});

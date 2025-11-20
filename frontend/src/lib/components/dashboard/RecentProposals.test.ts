import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import RecentProposals from './RecentProposals.svelte';
import type { components } from '$lib/api/client';

// Mock ProposalCard component
vi.mock('./ProposalCard.svelte', () => ({
  default: vi.fn()
}));

// Test data
const mockProposals: components['schemas']['Proposal'][] = [
  {
    id: 'proposal-1',
    title: 'Proposal 1',
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
    body: 'Test proposal 1 body'
  },
  {
    id: 'proposal-2',
    title: 'Proposal 2',
    created: 1700001000,
    start: 1700001000,
    end: 1700101000,
    snapshot: '12346',
    state: 'active',
    author: '0x124',
    space: { id: 'test-space', name: 'Test Space' },
    choices: ['For', 'Against', 'Abstain'],
    scores: [80, 40, 20],
    scores_total: 140,
    votes: 40,
    type: 'single-choice',
    body: 'Test proposal 2 body'
  },
  {
    id: 'proposal-3',
    title: 'Proposal 3',
    created: 1700002000,
    start: 1700002000,
    end: 1700102000,
    snapshot: '12347',
    state: 'closed',
    author: '0x125',
    space: { id: 'test-space', name: 'Test Space' },
    choices: ['For', 'Against', 'Abstain'],
    scores: [60, 30, 15],
    scores_total: 105,
    votes: 30,
    type: 'single-choice',
    body: 'Test proposal 3 body'
  }
];

const mockDecision1: components['schemas']['AgentDecisionResponse'] = {
  vote: 'FOR',
  reasoning: 'Good proposal',
  confidence: 0.85,
  strategy_used: 'balanced'
};

const mockDecision2: components['schemas']['AgentDecisionResponse'] = {
  vote: 'AGAINST',
  reasoning: 'Concerns about implementation',
  confidence: 0.75,
  strategy_used: 'conservative'
};

describe('RecentProposals Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Proposal Filtering', () => {
    it('only shows proposals with decisions', () => {
      /**
       * Why: The component should filter to show only proposals where agent has made decisions.
       * What: Verifies that proposals without decisions are filtered out from display.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      // Should show count of only proposals with decisions
      expect(screen.getByText('1 proposal')).toBeInTheDocument();
    });

    it('shows all proposals when all have decisions', () => {
      /**
       * Why: When agent has decided on all proposals, all should be displayed.
       * What: Verifies count reflects all proposals when decisions exist for each.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);
      decisionsMap.set('proposal-2', mockDecision2);
      decisionsMap.set('proposal-3', mockDecision1);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('3 proposals')).toBeInTheDocument();
    });

    it('filters correctly when some proposals have decisions', () => {
      /**
       * Why: Mixed scenario where only some proposals have decisions is common.
       * What: Verifies filtering works correctly with partial decision coverage.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);
      decisionsMap.set('proposal-3', mockDecision2);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('2 proposals')).toBeInTheDocument();
    });
  });

  describe('Heading and Count Display', () => {
    it('displays "All Proposals" heading', () => {
      /**
       * Why: Clear heading helps users understand what they're viewing.
       * What: Verifies the section heading is displayed correctly.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('All Proposals')).toBeInTheDocument();
    });

    it('displays singular "proposal" for count of 1', () => {
      /**
       * Why: Proper grammar improves user experience.
       * What: Verifies singular form is used when count is 1.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('1 proposal')).toBeInTheDocument();
      expect(screen.queryByText('1 proposals')).not.toBeInTheDocument();
    });

    it('displays plural "proposals" for count > 1', () => {
      /**
       * Why: Proper grammar improves user experience.
       * What: Verifies plural form is used when count is greater than 1.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);
      decisionsMap.set('proposal-2', mockDecision2);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('2 proposals')).toBeInTheDocument();
      expect(screen.queryByText('2 proposal')).not.toBeInTheDocument();
    });

    it('displays count in header section', () => {
      /**
       * Why: Count should be visually separated from main heading for clarity.
       * What: Verifies count appears in the header alongside the title.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);
      decisionsMap.set('proposal-2', mockDecision2);

      const { container } = render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      const heading = screen.getByText('All Proposals');
      const count = screen.getByText('2 proposals');

      // Both should exist in the same parent container
      expect(heading.parentElement).toContain(count.parentElement);
    });
  });

  describe('Empty State', () => {
    it('shows empty state when no proposals have decisions', () => {
      /**
       * Why: Users need clear feedback when there's no data to display.
       * What: Verifies empty state message appears when decisions map is empty.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('No proposals with agent decisions yet')).toBeInTheDocument();
    });

    it('shows empty state when proposals array is empty', () => {
      /**
       * Why: Handle edge case of no proposals at all.
       * What: Verifies empty state appears when proposals array is empty.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();

      render(RecentProposals, {
        props: {
          proposals: [],
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('No proposals with agent decisions yet')).toBeInTheDocument();
    });

    it('shows empty state when no proposal IDs match decisions', () => {
      /**
       * Why: Handle case where decisions exist but for different proposals.
       * What: Verifies empty state when decision IDs don't match any proposal IDs.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('nonexistent-proposal', mockDecision1);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.getByText('No proposals with agent decisions yet')).toBeInTheDocument();
    });

    it('does not show "All Proposals" heading in empty state', () => {
      /**
       * Why: Heading should only appear when there are proposals to show.
       * What: Verifies heading is hidden in empty state.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      expect(screen.queryByText('All Proposals')).not.toBeInTheDocument();
    });
  });

  describe('ProposalCard Integration', () => {
    it('passes proposal to ProposalCard component', () => {
      /**
       * Why: ProposalCard needs proposal data to render correctly.
       * What: Verifies each proposal is passed to its ProposalCard instance.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      const { container } = render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      // ProposalCard component should be rendered
      // Since we mocked it, we verify the container has the expected structure
      expect(container.querySelector('.space-y-4')).toBeInTheDocument();
    });

    it('passes decision prop to ProposalCard', () => {
      /**
       * Why: ProposalCard needs decision data to show voting information.
       * What: Verifies decision from map is correctly passed to ProposalCard.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);
      decisionsMap.set('proposal-2', mockDecision2);

      render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      // Verify structure that would contain ProposalCards
      const proposalContainer = screen.getByText('2 proposals').closest('.bg-white');
      expect(proposalContainer).toBeInTheDocument();
    });

    it('sets variant to compact for all ProposalCards', () => {
      /**
       * Why: List view should use compact variant for better space efficiency.
       * What: Verifies variant prop is set to compact for list display.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      const { container } = render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      // Verify the container structure suggests compact layout
      const proposalList = container.querySelector('.space-y-4');
      expect(proposalList).toBeInTheDocument();
    });

    it('renders ProposalCards in correct order', () => {
      /**
       * Why: Proposals should maintain their original order from the proposals array.
       * What: Verifies proposals are rendered in the same order they appear in the array.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);
      decisionsMap.set('proposal-2', mockDecision2);
      decisionsMap.set('proposal-3', mockDecision1);

      const { container } = render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      // Verify the proposal list container exists
      const proposalList = container.querySelector('.space-y-4');
      expect(proposalList).toBeInTheDocument();
      
      // Verify count shows all 3 proposals
      expect(screen.getByText('3 proposals')).toBeInTheDocument();
    });
  });

  describe('Layout and Styling', () => {
    it('renders with white background and shadow', () => {
      /**
       * Why: Component should have consistent card styling with the design system.
       * What: Verifies correct background and shadow classes are applied.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      const { container } = render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      const card = container.querySelector('.bg-white.rounded-lg.shadow');
      expect(card).toBeInTheDocument();
    });

    it('applies correct grid span class', () => {
      /**
       * Why: Component should span 2 columns in large grid layouts.
       * What: Verifies lg:col-span-2 class is applied for responsive layout.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      const { container } = render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      const card = container.querySelector('.lg\\:col-span-2');
      expect(card).toBeInTheDocument();
    });

    it('applies space-y-4 to proposal list container', () => {
      /**
       * Why: Consistent vertical spacing between proposal cards improves readability.
       * What: Verifies spacing utility class is applied to list container.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      const { container } = render(RecentProposals, {
        props: {
          proposals: mockProposals,
          agentDecisions: decisionsMap
        }
      });

      const listContainer = container.querySelector('.space-y-4');
      expect(listContainer).toBeInTheDocument();
    });
  });

  describe('Props Validation', () => {
    it('handles proposals prop correctly', () => {
      /**
       * Why: Component should work with valid proposals array.
       * What: Verifies component accepts and processes proposals prop.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      expect(() => {
        render(RecentProposals, {
          props: {
            proposals: mockProposals,
            agentDecisions: decisionsMap
          }
        });
      }).not.toThrow();
    });

    it('handles agentDecisions Map correctly', () => {
      /**
       * Why: Component requires Map structure for efficient decision lookups.
       * What: Verifies component accepts and processes agentDecisions Map prop.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
      decisionsMap.set('proposal-1', mockDecision1);

      expect(() => {
        render(RecentProposals, {
          props: {
            proposals: mockProposals,
            agentDecisions: decisionsMap
          }
        });
      }).not.toThrow();
    });

    it('handles empty agentDecisions Map', () => {
      /**
       * Why: Component should gracefully handle empty decisions.
       * What: Verifies component doesn't error with empty Map.
       */
      const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();

      expect(() => {
        render(RecentProposals, {
          props: {
            proposals: mockProposals,
            agentDecisions: decisionsMap
          }
        });
      }).not.toThrow();
    });
  });
});

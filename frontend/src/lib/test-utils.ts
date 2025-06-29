// Test utilities for Svelte components
import { render } from '@testing-library/svelte';
import type { ComponentProps, SvelteComponent } from 'svelte';

export function renderComponent<T extends SvelteComponent>(
  component: any,
  props?: any
) {
  return render(component, props);
}

// Mock API response for organizations
export const mockOrganizationsResponse = {
  organizations: [
    {
      organization: {
        id: "1",
        name: "Compound",
        slug: "compound",
        chain_ids: ["eip155:1"],
        token_ids: ["eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888"],
        governor_ids: ["eip155:1:0x309a862bbC1A00e45506cB8A802D1ff10004c8C0"],
        metadata: null,
        creator: null,
        has_active_proposals: true,
        proposals_count: 408,
        delegates_count: 14248,
        delegates_votes_count: "2740594070519955495931154",
        token_owners_count: 218778,
        endorsement_service: null
      },
      proposals: [
        {
          proposal_id: "prop1",
          title: "Test Proposal 1",
          summary: "This is a test proposal summary",
          key_points: ["Point 1", "Point 2"],
          risk_level: "LOW",
          recommendation: "APPROVE",
          confidence_score: 0.9
        }
      ]
    },
    {
      organization: {
        id: "2", 
        name: "Nouns DAO",
        slug: "nounsdao",
        chain_ids: ["eip155:1"],
        token_ids: [],
        governor_ids: [],
        metadata: null,
        creator: null,
        has_active_proposals: true,
        proposals_count: 823,
        delegates_count: 5000,
        delegates_votes_count: "1000000000000000000000",
        token_owners_count: 10000,
        endorsement_service: null
      },
      proposals: []
    }
  ],
  processing_time: 1.5,
  model_used: "anthropic/claude-3.5-sonnet"
};
import { writable } from 'svelte/store';
import apiClient from '$lib/api';
import { extractApiErrorMessage, selectDefaultOrganization } from '$lib/utils/api.js';
import type { components } from '$lib/api/client';

interface DashboardState {
  loading: boolean;
  error: string | null;
  currentSpaceId: string;
  allProposals: components['schemas']['Proposal'][];
  proposalsLoading: boolean;
  proposalsError: string | null;
  proposalFilters: {
    state?: string;
  };
  agentDecisions: Map<string, components['schemas']['AgentDecisionResponse']>;
}

/**
 * Creates dashboard data management hook
 * @returns Dashboard state and actions
 */
export function createDashboardStore() {
  const initialState: DashboardState = {
    loading: true,
    error: null,
    currentSpaceId: 'quorum-ai.eth', // Default Snapshot space - can be made configurable
    allProposals: [],
    proposalsLoading: false,
    proposalsError: null,
    proposalFilters: {},
    agentDecisions: new Map()
  };

  const { subscribe, set, update } = writable(initialState);

  /**
   * Loads proposals from API
   */
  async function loadProposals(): Promise<void> {
    console.assert(typeof apiClient.GET === 'function', 'API client should have GET method');

    try {
      update(state => ({ ...state, loading: true, error: null }));

      let currentState: DashboardState = initialState;
      const unsubscribe = subscribe(s => { currentState = s; });
      unsubscribe();

      const { data, error: apiError } = await apiClient.GET("/proposals", {
        params: {
          query: {
            space_id: currentState.currentSpaceId,
            state: currentState.proposalFilters.state,
            limit: 20
          }
        }
      });

      if (apiError) {
        const errorMessage = extractApiErrorMessage(apiError);
        update(state => ({ ...state, error: errorMessage, loading: false }));
        return;
      }

      if (data) {
        // @ts-ignore - API response type is unknown but we know the structure
        const proposals = data.proposals || [];
        update(state => ({
          ...state,
          allProposals: proposals,
          loading: false
        }));

        // Load agent decisions for the proposals
        await loadAgentDecisions();
      }
    } catch (err) {
      console.error('Failed to load proposals:', err);
      update(state => ({
        ...state,
        error: 'Failed to load proposals',
        loading: false
      }));
    }
  }

  /**
   * Loads agent decisions from API
   */
  async function loadAgentDecisions(): Promise<void> {
    console.assert(typeof apiClient.GET === 'function', 'API client should have GET method');

    try {
      const { data, error: apiError } = await apiClient.GET("/agent-run/decisions", {
        params: {
          query: {
            limit: 100
          }
        }
      });

      if (apiError) {
        console.error('Failed to load agent decisions:', apiError);
        return;
      }

      if (data?.decisions) {
        // Build a Map keyed by proposal_id, keeping the latest decision per proposal
        const decisionsMap = new Map<string, components['schemas']['AgentDecisionResponse']>();
        
        for (const decision of data.decisions) {
          const proposalId = decision.proposal_id;
          const existing = decisionsMap.get(proposalId);
          
          // Keep the latest decision (assuming array is ordered, or compare timestamps)
          if (!existing || !decision.timestamp || !existing.timestamp || 
              new Date(decision.timestamp) > new Date(existing.timestamp)) {
            decisionsMap.set(proposalId, decision);
          }
        }

        update(state => ({
          ...state,
          agentDecisions: decisionsMap
        }));
      }
    } catch (err) {
      console.error('Failed to load agent decisions:', err);
    }
  }



  /**
   * Changes Snapshot space
   * @param spaceId - New Snapshot space ID
   */
  function changeSpace(spaceId: string): void {
    console.assert(spaceId !== null, 'Space ID should not be null');
    console.assert(typeof spaceId === 'string', 'Space ID should be a string');

    update(state => ({
      ...state,
      currentSpaceId: spaceId,
      allProposals: []
    }));

    loadProposals();
  }


  /**
   * Updates proposal filters
   * @param filters - New filter values
   */
  function updateProposalFilters(filters: Partial<DashboardState['proposalFilters']>): void {
    console.assert(typeof filters === 'object', 'Filters must be an object');

    update(state => ({
      ...state,
      proposalFilters: { ...state.proposalFilters, ...filters },
      allProposals: []
    }));

    loadProposals();
  }

  return {
    subscribe,
    loadProposals,
    changeSpace,
    updateProposalFilters
  };
}

import { writable } from 'svelte/store';
import apiClient from '$lib/api';
import type { TabType } from '$lib/types/dashboard.js';
import { extractApiErrorMessage, selectDefaultOrganization } from '$lib/utils/api.js';
import type { components } from '$lib/api/client';

interface DashboardState {
  loading: boolean;
  error: string | null;
  activeTab: TabType;
  currentSpaceId: string;
  allProposals: components['schemas']['Proposal'][];
  proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;
  proposalsLoading: boolean;
  proposalsError: string | null;
  proposalFilters: {
    state?: components['schemas']['ProposalState'];
  };
}

/**
 * Creates dashboard data management hook
 * @returns Dashboard state and actions
 */
export function createDashboardStore() {
  const initialState: DashboardState = {
    loading: true,
    error: null,
    activeTab: 'overview',
    currentSpaceId: 'uniswapgovernance.eth', // Default Snapshot space - can be made configurable
    allProposals: [],
    proposalSummaries: new Map(),
    proposalsLoading: false,
    proposalsError: null,
    proposalFilters: {}
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
        update(state => ({
          ...state,
          allProposals: data.proposals,
          loading: false
        }));

        // Load summaries for proposals
        const proposalIds = data.proposals.map(p => p.id);
        if (proposalIds.length > 0) {
          const { data: summaryData } = await apiClient.POST("/proposals/summarize", {
            body: {
              proposal_ids: proposalIds,
              include_risk_assessment: true,
              include_recommendations: true
            }
          });

          if (summaryData) {
            const newSummaries = new Map<string, components['schemas']['ProposalSummary']>();
            summaryData.summaries.forEach(summary => {
              newSummaries.set(summary.proposal_id, summary);
            });

            update(s => ({
              ...s,
              proposalSummaries: newSummaries
            }));
          }
        }
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
   * Changes active tab
   * @param tabId - New tab identifier
   */
  function changeTab(tabId: TabType): void {
    console.assert(typeof tabId === 'string', 'Tab ID must be a string');
    console.assert(['overview'].includes(tabId), 'Tab ID must be valid');

    update(state => ({ ...state, activeTab: tabId }));
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
    changeTab,
    changeSpace,
    updateProposalFilters
  };
}

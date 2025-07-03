import { writable } from 'svelte/store';
import apiClient from '$lib/api';
import type { OrganizationWithProposals, Organization, TabType, ProposalDetails } from '$lib/types/dashboard.js';
import { extractApiErrorMessage, selectDefaultOrganization } from '$lib/utils/api.js';
import type { components } from '$lib/api/client';

interface DashboardState {
  organizationsWithProposals: OrganizationWithProposals[];
  loading: boolean;
  error: string | null;
  activeTab: TabType;
  selectedOrganization: Organization | null;
  allProposals: components['schemas']['Proposal'][];
  proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;
  proposalsLoading: boolean;
  proposalsError: string | null;
  proposalsCursor: string | null;
  proposalFilters: {
    state?: components['schemas']['ProposalState'];
    sortBy: components['schemas']['SortCriteria'];
    sortOrder: components['schemas']['SortOrder'];
  };
}

/**
 * Creates dashboard data management hook
 * @returns Dashboard state and actions
 */
export function createDashboardStore() {
  const initialState: DashboardState = {
    organizationsWithProposals: [],
    loading: true,
    error: null,
    activeTab: 'overview',
    selectedOrganization: null,
    allProposals: [],
    proposalSummaries: new Map(),
    proposalsLoading: false,
    proposalsError: null,
    proposalsCursor: null,
    proposalFilters: {
      sortBy: 'created_date',
      sortOrder: 'desc'
    }
  };

  const { subscribe, set, update } = writable(initialState);

  /**
   * Loads organizations from API
   */
  async function loadOrganizations(): Promise<void> {
    console.assert(typeof apiClient.GET === 'function', 'API client should have GET method');

    try {
      update(state => ({ ...state, loading: true, error: null }));

      const { data, error: apiError } = await apiClient.GET("/organizations");

      if (apiError) {
        const errorMessage = extractApiErrorMessage(apiError);
        update(state => ({ ...state, error: errorMessage, loading: false }));
        return;
      }

      if (data) {
        const organizations = data.organizations;
        const defaultOrg = selectDefaultOrganization(organizations);

        update(state => ({
          ...state,
          organizationsWithProposals: organizations,
          selectedOrganization: state.selectedOrganization || defaultOrg,
          loading: false
        }));
      }
    } catch (err) {
      console.error('Failed to load organizations:', err);
      update(state => ({
        ...state,
        error: 'Failed to load organizations',
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
    console.assert(['overview', 'proposals', 'activity'].includes(tabId), 'Tab ID must be valid');

    update(state => ({ ...state, activeTab: tabId }));
  }

  /**
   * Changes selected organization
   * @param organization - New organization
   */
  function changeOrganization(organization: Organization): void {
    console.assert(organization !== null, 'Organization should not be null');
    console.assert(typeof organization === 'object', 'Organization should be an object');

    update(state => ({
      ...state,
      selectedOrganization: organization,
      allProposals: [],
      proposalsCursor: null
    }));

    if (organization) {
      loadProposals(true);
    }
  }

  /**
   * Loads all proposals for selected organization
   * @param refresh - Whether to refresh from first page
   */
  async function loadProposals(refresh = false): Promise<void> {
    let state: DashboardState = initialState;

    const unsubscribe = subscribe(s => { state = s; });
    unsubscribe();

    if (!state.selectedOrganization) return;

    console.assert(state.selectedOrganization.id, 'Organization should have an ID');

    try {
      update(s => ({ ...s, proposalsLoading: true, proposalsError: null }));

      const cursor = refresh ? undefined : state.proposalsCursor;

      const { data, error: apiError } = await apiClient.GET(
        "/organizations/{org_id}/proposals",
        {
          params: {
            path: { org_id: state.selectedOrganization.id },
            query: {
              state: state.proposalFilters.state,
              sort_by: state.proposalFilters.sortBy,
              sort_order: state.proposalFilters.sortOrder,
              limit: 20,
              after_cursor: cursor || undefined
            }
          }
        }
      );

      if (apiError) {
        const errorMessage = extractApiErrorMessage(apiError);
        update(s => ({ ...s, proposalsError: errorMessage, proposalsLoading: false }));
        return;
      }

      if (data) {
        const proposals = refresh ? data.proposals : [...state.allProposals, ...data.proposals];

        const proposalIds = data.proposals
          .filter(p => !state.proposalSummaries.has(p.id))
          .map(p => p.id);

        if (proposalIds.length > 0) {
          const { data: summaryData } = await apiClient.POST("/proposals/summarize", {
            body: {
              proposal_ids: proposalIds,
              include_risk_assessment: true,
              include_recommendations: true
            }
          });

          if (summaryData) {
            const newSummaries = new Map(state.proposalSummaries);
            summaryData.summaries.forEach(summary => {
              newSummaries.set(summary.proposal_id, summary);
            });

            update(s => ({
              ...s,
              proposalSummaries: newSummaries
            }));
          }
        }

        update(s => ({
          ...s,
          allProposals: proposals,
          proposalsCursor: data.next_cursor || null,
          proposalsLoading: false
        }));
      }
    } catch (err) {
      console.error('Failed to load proposals:', err);
      update(s => ({
        ...s,
        proposalsError: 'Failed to load proposals',
        proposalsLoading: false
      }));
    }
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
      allProposals: [],
      proposalsCursor: null
    }));

    loadProposals(true);
  }

  return {
    subscribe,
    loadOrganizations,
    changeTab,
    changeOrganization,
    loadProposals,
    updateProposalFilters
  };
}

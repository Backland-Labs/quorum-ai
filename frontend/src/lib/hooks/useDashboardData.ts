import { writable } from 'svelte/store';
import apiClient from '$lib/api';
import type { OrganizationWithProposals, Organization, TabType } from '$lib/types/dashboard.js';
import { extractApiErrorMessage, selectDefaultOrganization } from '$lib/utils/api.js';

interface DashboardState {
  organizationsWithProposals: OrganizationWithProposals[];
  loading: boolean;
  error: string | null;
  activeTab: TabType;
  selectedOrganization: Organization | null;
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
    selectedOrganization: null
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
    
    update(state => ({ ...state, selectedOrganization: organization }));
  }

  return {
    subscribe,
    loadOrganizations,
    changeTab,
    changeOrganization
  };
}
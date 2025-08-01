import { writable, derived, get, type Writable } from 'svelte/store';
import { apiClient } from '$lib/api';
import type { AgentRunStatus, AgentDecisionResponse, AgentRunStatistics } from '$lib/api/client';

export interface AgentDashboardState {
  status: AgentRunStatus | null;
  decisions: AgentDecisionResponse[];
  statistics: AgentRunStatistics | null;
  loading: {
    status: boolean;
    decisions: boolean;
    statistics: boolean;
  };
  errors: {
    status: string | null;
    decisions: string | null;
    statistics: string | null;
  };
  lastRefresh: Date | null;
  currentSpaceId: string | null;
}

const initialState: AgentDashboardState = {
  status: null,
  decisions: [],
  statistics: null,
  loading: {
    status: false,
    decisions: false,
    statistics: false
  },
  errors: {
    status: null,
    decisions: null,
    statistics: null
  },
  lastRefresh: null,
  currentSpaceId: null
};

export function createAgentStatusStore() {
  const { subscribe, set, update }: Writable<AgentDashboardState> = writable(initialState);

  let pollInterval: NodeJS.Timeout | null = null;

  const fetchStatus = async () => {
    update(state => ({
      ...state,
      loading: { ...state.loading, status: true },
      errors: { ...state.errors, status: null }
    }));

    try {
      const { data, error } = await apiClient.GET('/agent-run/status');

      if (error) {
        throw new Error(error.message || 'Failed to fetch status');
      }

      update(state => ({
        ...state,
        status: data,
        loading: { ...state.loading, status: false }
      }));
    } catch (error) {
      update(state => ({
        ...state,
        loading: { ...state.loading, status: false },
        errors: { ...state.errors, status: error instanceof Error ? error.message : 'Unknown error' }
      }));
    }
  };

  const fetchDecisions = async () => {
    update(state => ({
      ...state,
      loading: { ...state.loading, decisions: true },
      errors: { ...state.errors, decisions: null }
    }));

    try {
      let params: any = {
        query: {
          limit: 5
        }
      };

      // Include space_id if set
      let currentState: AgentDashboardState;
      update(state => {
        currentState = state;
        return state;
      });
      if (currentState!.currentSpaceId) {
        params.query.space_id = currentState!.currentSpaceId;
      }

      const { data, error } = await apiClient.GET('/agent-run/decisions', { params });

      if (error) {
        throw new Error(error.message || 'Failed to fetch decisions');
      }

      update(state => ({
        ...state,
        decisions: data?.decisions || [],
        loading: { ...state.loading, decisions: false }
      }));
    } catch (error) {
      update(state => ({
        ...state,
        loading: { ...state.loading, decisions: false },
        errors: { ...state.errors, decisions: error instanceof Error ? error.message : 'Unknown error' }
      }));
    }
  };

  const fetchStatistics = async () => {
    update(state => ({
      ...state,
      loading: { ...state.loading, statistics: true },
      errors: { ...state.errors, statistics: null }
    }));

    try {
      const { data, error } = await apiClient.GET('/agent-run/statistics');

      if (error) {
        throw new Error(error.message || 'Failed to fetch statistics');
      }

      update(state => ({
        ...state,
        statistics: data,
        loading: { ...state.loading, statistics: false }
      }));
    } catch (error) {
      update(state => ({
        ...state,
        loading: { ...state.loading, statistics: false },
        errors: { ...state.errors, statistics: error instanceof Error ? error.message : 'Unknown error' }
      }));
    }
  };

  const fetchAll = async () => {
    await Promise.all([
      fetchStatus(),
      fetchDecisions(),
      fetchStatistics()
    ]);

    update(state => ({ ...state, lastRefresh: new Date() }));
  };

  const startPolling = (interval: number = 30000) => {
    // Stop any existing polling
    stopPolling();

    // Fetch immediately
    fetchAll();

    // Set up interval
    pollInterval = setInterval(() => {
      fetchAll();
    }, interval);
  };

  const stopPolling = () => {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  };

  const setCurrentSpaceId = (spaceId: string) => {
    update(state => ({ ...state, currentSpaceId: spaceId }));
  };


  const store = {
    subscribe,
    fetchStatus,
    fetchDecisions,
    fetchStatistics,
    fetchAll,
    startPolling,
    stopPolling,
    setCurrentSpaceId,
    isAgentActive: derived({ subscribe }, $state => $state.status?.is_active || false)
  };

  return store;
}

// Create a singleton instance
export const agentStatusStore = createAgentStatusStore();

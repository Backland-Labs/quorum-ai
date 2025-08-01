import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';
import { createAgentStatusStore, type AgentDashboardState } from './agentStatus';
import type { AgentRunStatus, AgentDecisionResponse, AgentRunStatistics } from '$lib/api/client';

// Mock the API client
vi.mock('$lib/api', () => ({
  apiClient: {
    GET: vi.fn()
  }
}));

describe('AgentStatusStore', () => {
  let store: ReturnType<typeof createAgentStatusStore>;
  let mockApiClient: any;

  beforeEach(async () => {
    vi.clearAllMocks();
    // Reset modules to ensure fresh mocks
    vi.resetModules();
    const apiModule = await import('$lib/api');
    mockApiClient = vi.mocked(apiModule.apiClient);
    store = createAgentStatusStore();
  });

  afterEach(() => {
    // Clean up any active polling
    store.stopPolling();
  });

  describe('Initialization', () => {
    it('test_agent_store_initializes_with_default_state', () => {
      /**
       * Tests that the store initializes with the correct default state.
       * This is important to ensure components have predictable initial values
       * and can handle the loading state properly.
       */
      const state = get(store);

      expect(state).toEqual({
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
      });
    });
  });

  describe('API Data Updates', () => {
    it('test_agent_store_updates_from_api_response', async () => {
      /**
       * Tests that the store correctly updates when API data is fetched.
       * This ensures that components subscribing to the store will receive
       * the latest data from the backend.
       */
      const mockStatus: AgentRunStatus = {
        current_state: 'idle',
        last_run_timestamp: '2025-07-30T10:00:00Z',
        is_active: false,
        current_space_id: 'test.eth'
      };

      mockApiClient.GET.mockResolvedValueOnce({
        data: mockStatus,
        error: null
      });

      await store.fetchStatus();

      const state = get(store);
      expect(state.status).toEqual(mockStatus);
      expect(state.loading.status).toBe(false);
      expect(state.errors.status).toBeNull();
    });

    it('test_agent_store_updates_decisions_from_api', async () => {
      /**
       * Tests that the store correctly fetches and stores voting decisions.
       * This is critical for displaying the agent's decision history.
       */
      const mockDecisions: AgentDecisionResponse[] = [
        {
          proposal_id: '1',
          proposal_title: 'Test Proposal',
          vote: 'FOR',
          confidence: 0.85,
          timestamp: '2025-07-30T09:00:00Z',
          reasoning: 'Test reasoning'
        }
      ];

      mockApiClient.GET.mockResolvedValueOnce({
        data: { decisions: mockDecisions },
        error: null
      });

      await store.fetchDecisions();

      const state = get(store);
      expect(state.decisions).toEqual(mockDecisions);
      expect(state.loading.decisions).toBe(false);
      expect(state.errors.decisions).toBeNull();
    });

    it('test_agent_store_updates_statistics_from_api', async () => {
      /**
       * Tests that the store correctly fetches and stores performance statistics.
       * This ensures the statistics panel displays accurate metrics.
       */
      const mockStatistics: AgentRunStatistics = {
        total_runs: 10,
        total_proposals_reviewed: 50,
        total_votes_cast: 8,
        average_confidence: 0.75,
        success_rate: 0.9
      };

      mockApiClient.GET.mockResolvedValueOnce({
        data: mockStatistics,
        error: null
      });

      await store.fetchStatistics();

      const state = get(store);
      expect(state.statistics).toEqual(mockStatistics);
      expect(state.loading.statistics).toBe(false);
      expect(state.errors.statistics).toBeNull();
    });
  });

  describe('Error Handling', () => {
    it('test_agent_store_handles_polling_errors', async () => {
      /**
       * Tests that the store properly handles API errors and updates error states.
       * This is crucial for components to display appropriate error messages.
       */
      const errorMessage = 'Network error';
      mockApiClient.GET.mockRejectedValueOnce(new Error(errorMessage));

      await store.fetchStatus();

      const state = get(store);
      expect(state.status).toBeNull();
      expect(state.loading.status).toBe(false);
      expect(state.errors.status).toBe(errorMessage);
    });

    it('test_store_handles_partial_fetch_failures', async () => {
      /**
       * Tests that if one API call fails, others can still succeed.
       * This ensures the dashboard remains partially functional even with errors.
       */
      const mockStatus: AgentRunStatus = {
        current_state: 'idle',
        last_run_timestamp: '2025-07-30T10:00:00Z',
        is_active: false,
        current_space_id: 'test.eth'
      };

      // Status succeeds
      mockApiClient.GET.mockResolvedValueOnce({
        data: mockStatus,
        error: null
      });

      // Decisions fails
      mockApiClient.GET.mockRejectedValueOnce(new Error('Decisions error'));

      // Statistics succeeds
      mockApiClient.GET.mockResolvedValueOnce({
        data: { total_runs: 5 },
        error: null
      });

      await store.fetchAll();

      const state = get(store);
      expect(state.status).toEqual(mockStatus);
      expect(state.errors.status).toBeNull();
      expect(state.errors.decisions).toBe('Decisions error');
      expect(state.statistics).toEqual({ total_runs: 5 });
    });
  });

  describe('Polling Behavior', () => {
    it('test_store_starts_and_stops_polling', async () => {
      /**
       * Tests that polling can be started and stopped correctly.
       * This prevents memory leaks and ensures proper cleanup.
       */
      // Clear any previous mock calls
      mockApiClient.GET.mockClear();

      const mockData = {
        status: { current_state: 'idle', last_run_timestamp: '2025-07-30T10:00:00Z', is_active: false, current_space_id: 'test.eth' },
        decisions: { decisions: [] },
        statistics: { total_runs: 0 }
      };

      // Track calls manually
      let callCount = 0;
      mockApiClient.GET.mockImplementation((path: string) => {
        callCount++;
        if (path === '/agent-run/status') return Promise.resolve({ data: mockData.status, error: null });
        if (path === '/agent-run/decisions') return Promise.resolve({ data: mockData.decisions, error: null });
        if (path === '/agent-run/statistics') return Promise.resolve({ data: mockData.statistics, error: null });
        return Promise.resolve({ data: null, error: null });
      });

      // Test that polling starts
      const initialCount = callCount;
      store.startPolling(100); // Short interval for testing

      // Wait for initial fetch
      await new Promise(resolve => setTimeout(resolve, 50));
      expect(callCount).toBe(initialCount + 3); // 3 API calls made

      // Wait for one more polling cycle
      await new Promise(resolve => setTimeout(resolve, 150));
      expect(callCount).toBeGreaterThanOrEqual(initialCount + 6); // At least 6 calls

      // Stop polling
      store.stopPolling();
      const countAfterStop = callCount;

      // Wait and verify no new calls
      await new Promise(resolve => setTimeout(resolve, 200));
      expect(callCount).toBe(countAfterStop); // No new calls after stop
    });
  });

  describe('Space ID Management', () => {
    it('test_store_updates_space_id', () => {
      /**
       * Tests that the current space ID can be updated.
       * This is important for filtering data by the active space.
       */
      store.setCurrentSpaceId('test.eth');

      const state = get(store);
      expect(state.currentSpaceId).toBe('test.eth');
    });

    it('test_store_includes_space_id_in_api_calls', async () => {
      /**
       * Tests that API calls include the current space ID when set.
       * This ensures data is filtered to the correct DAO space.
       */
      store.setCurrentSpaceId('test.eth');

      mockApiClient.GET.mockResolvedValue({
        data: { decisions: [] },
        error: null
      });

      await store.fetchDecisions();

      expect(mockApiClient.GET).toHaveBeenCalledWith(
        '/agent-run/decisions',
        expect.objectContaining({
          params: expect.objectContaining({
            query: expect.objectContaining({
              space_id: 'test.eth'
            })
          })
        })
      );
    });
  });

  describe('Reactive Updates', () => {
    it('test_components_react_to_store_changes', async () => {
      /**
       * Tests that store subscribers are notified of state changes.
       * This verifies the reactive nature of Svelte stores.
       */
      const stateChanges: AgentDashboardState[] = [];

      // Subscribe to store changes
      const unsubscribe = store.subscribe(state => {
        stateChanges.push({ ...state });
      });

      // Initial state
      expect(stateChanges).toHaveLength(1);

      // Update status
      mockApiClient.GET.mockResolvedValueOnce({
        data: {
          current_state: 'voting',
          last_run_timestamp: '2025-07-30T10:00:00Z',
          is_active: true,
          current_space_id: 'test.eth'
        },
        error: null
      });
      await store.fetchStatus();

      expect(stateChanges).toHaveLength(3); // loading=true, then data update
      expect(stateChanges[2].status?.current_state).toBe('voting');

      unsubscribe();
    });
  });

  describe('Loading States', () => {
    it('test_store_manages_individual_loading_states', async () => {
      /**
       * Tests that loading states are managed independently for each data type.
       * This allows components to show appropriate loading indicators.
       */
      // Create a promise we can control
      let resolveStatus: (value: any) => void;
      const statusPromise = new Promise(resolve => {
        resolveStatus = resolve;
      });

      mockApiClient.GET.mockReturnValueOnce(statusPromise);

      // Start fetching (don't await)
      const fetchPromise = store.fetchStatus();

      // Check loading state is true
      let state = get(store);
      expect(state.loading.status).toBe(true);
      expect(state.loading.decisions).toBe(false);
      expect(state.loading.statistics).toBe(false);

      // Resolve the promise
      resolveStatus!({ data: { current_state: 'idle' }, error: null });
      await fetchPromise;

      // Check loading state is false
      state = get(store);
      expect(state.loading.status).toBe(false);
    });
  });

  describe('Manual Refresh', () => {
    it('test_store_updates_last_refresh_timestamp', async () => {
      /**
       * Tests that the lastRefresh timestamp is updated after fetching data.
       * This helps users know when data was last updated.
       */
      const beforeRefresh = new Date();

      mockApiClient.GET.mockResolvedValue({
        data: {},
        error: null
      });

      await store.fetchAll();

      const state = get(store);
      expect(state.lastRefresh).toBeTruthy();
      expect(state.lastRefresh!.getTime()).toBeGreaterThanOrEqual(beforeRefresh.getTime());
    });
  });

  describe('Derived State', () => {
    it('test_is_agent_active_derived_from_status', async () => {
      /**
       * Tests that the store provides a derived isAgentActive value.
       * This is used by AgentQuickActions to disable the "Run Now" button.
       */
      // Initially should be false
      expect(get(store.isAgentActive)).toBe(false);

      // Update status to active
      mockApiClient.GET.mockResolvedValueOnce({
        data: {
          current_state: 'voting',
          is_active: true,
          last_run_timestamp: '2025-07-30T10:00:00Z',
          current_space_id: 'test.eth'
        },
        error: null
      });

      await store.fetchStatus();

      // Check that isAgentActive is now true
      expect(get(store.isAgentActive)).toBe(true);
    });
  });
});

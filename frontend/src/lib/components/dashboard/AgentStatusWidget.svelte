<script lang="ts">
  import { apiClient } from '$lib/api';
  import { browser } from '$app/environment';
  
  interface Props {
    // Allow override for testing
    testMode?: boolean;
  }
  
  let { testMode = false }: Props = $props();

  // Component state
  let loading = $state(true);
  let error = $state<string | null>(null);
  let agentStatus = $state<{
    current_state: string;
    last_run_timestamp: string | null;
    is_active: boolean;
    current_space_id: string | null;
  } | null>(null);

  let intervalId: ReturnType<typeof setInterval> | null = null;

  // Format timestamp to human-readable format
  function formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return 'Never';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    return `${days} day${days > 1 ? 's' : ''} ago`;
  }

  // Format state to human-readable format
  function formatState(state: string): string {
    const stateMap: Record<string, string> = {
      'idle': 'Idle',
      'fetching_proposals': 'Fetching Proposals',
      'analyzing_proposals': 'Analyzing Proposals',
      'executing_votes': 'Executing Votes',
      'completed': 'Completed'
    };
    return stateMap[state] || state;
  }

  // Fetch agent status from API
  async function fetchStatus() {
    try {
      // TODO: Update after regenerating OpenAPI client with new endpoint
      const response = await apiClient.GET('/agent-run/status' as any);
      
      if (response.error) {
        error = 'Unable to load agent status';
        agentStatus = null;
      } else {
        error = null;
        agentStatus = response.data;
      }
    } catch (e) {
      error = 'Unable to load agent status';
      agentStatus = null;
    } finally {
      loading = false;
    }
  }

  // Initialize component
  function initialize() {
    if (!browser && !testMode) return;
    
    // Initial fetch
    fetchStatus();
    
    // Set up polling interval (30 seconds)
    intervalId = setInterval(fetchStatus, 30000);
  }

  // Cleanup function
  function cleanup() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }

  // Use $effect for lifecycle management in Svelte 5
  if (browser || testMode) {
    // Initialize immediately
    initialize();
    
    // Register cleanup on unmount
    $effect(() => {
      return cleanup;
    });
  }
</script>

<div class="bg-white shadow rounded-lg p-6">
  <h3 class="text-lg font-medium text-gray-900 mb-4">Agent Status</h3>
  
  {#if loading}
    <div data-testid="loading-state" class="text-gray-500">
      Loading agent status...
    </div>
  {:else if error}
    <div data-testid="error-state" class="text-red-600">
      {error}
    </div>
  {:else if agentStatus}
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm text-gray-500">Current State</p>
          <p data-testid="agent-state" class="text-lg font-medium text-gray-900">
            {formatState(agentStatus.current_state)}
          </p>
        </div>
        {#if agentStatus.is_active}
          <div data-testid="active-indicator" class="flex items-center">
            <div class="h-3 w-3 bg-green-500 rounded-full animate-pulse"></div>
            <span class="ml-2 text-sm text-green-600">Active</span>
          </div>
        {/if}
      </div>
      
      <div>
        <p class="text-sm text-gray-500">Last Run</p>
        <p data-testid="last-run-timestamp" class="text-lg font-medium text-gray-900">
          {formatTimestamp(agentStatus.last_run_timestamp)}
        </p>
      </div>
      
      {#if agentStatus.current_space_id}
        <div>
          <p class="text-sm text-gray-500">Space ID</p>
          <p class="text-sm font-mono text-gray-700">{agentStatus.current_space_id}</p>
        </div>
      {/if}
    </div>
  {/if}
</div>
<script lang="ts">
  import { agentStatusStore } from '$lib/stores/agentStatus';
  
  interface Props {
    // Allow override for testing
    testMode?: boolean;
  }
  
  let { testMode = false }: Props = $props();

  // Subscribe to the store
  const storeState = $state($agentStatusStore);

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
</script>

<div 
  data-testid="agent-status-widget"
  role="region"
  aria-label="Agent Status"
  class="bg-white shadow rounded-lg p-3 sm:p-4 w-full sm:w-auto"
>
  <h3 data-testid="widget-title" class="text-sm sm:text-base font-medium text-gray-900 mb-4">Agent Status</h3>
  
  {#if storeState.loading.status}
    <div data-testid="loading-state" class="text-gray-500 text-sm">
      Loading agent status...
    </div>
  {:else if storeState.errors.status}
    <div data-testid="error-state" class="text-red-600 text-sm">
      {storeState.errors.status}
    </div>
  {:else if storeState.status}
    <div role="status" class="space-y-4">
      <div data-testid="status-content" class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <p class="text-xs sm:text-sm text-gray-500">Current State</p>
          <p data-testid="agent-state" class="text-xs sm:text-sm font-medium text-gray-900">
            {formatState(storeState.status.current_state)}
          </p>
        </div>
        {#if storeState.status.is_active}
          <div data-testid="active-indicator" class="flex items-center">
            <div class="h-3 w-3 bg-green-500 rounded-full animate-pulse"></div>
            <span class="ml-2 text-xs sm:text-sm text-green-600">Active</span>
          </div>
        {/if}
      </div>
      
      <div>
        <p class="text-xs sm:text-sm text-gray-500">Last Run</p>
        <p data-testid="last-run-timestamp" class="text-xs sm:text-sm font-medium text-gray-900">
          {formatTimestamp(storeState.status.last_run_timestamp)}
        </p>
      </div>
      
      {#if storeState.status.current_space_id}
        <div>
          <p class="text-xs sm:text-sm text-gray-500">Space ID</p>
          <p class="text-xs sm:text-sm font-mono text-gray-700 break-all">{storeState.status.current_space_id}</p>
        </div>
      {/if}
    </div>
  {/if}
</div>
<script lang="ts">
  import { agentStatusStore } from '$lib/stores/agentStatus';

  interface Props {
    // Allow override for testing
    testMode?: boolean;
  }

  let { testMode = false }: Props = $props();

  // Subscribe to the store
  const storeState = $state($agentStatusStore);

  // Calculate time to next checkpoint (24 hours from last run)
  function formatTimeToCheckpoint(timestamp: string | null): string {
    if (!timestamp) return 'Unknown';

    const lastRun = new Date(timestamp);
    const now = new Date();
    const nextCheckpoint = new Date(lastRun.getTime() + 24 * 60 * 60 * 1000); // 24 hours later
    const diff = nextCheckpoint.getTime() - now.getTime();

    // If checkpoint is overdue
    if (diff < 0) return 'Overdue';

    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);

    return `${hours}h ${minutes}m`;
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
      <div>
        <p class="text-xs sm:text-sm text-gray-500">Current State</p>
        <p data-testid="agent-state" class="text-base sm:text-lg font-semibold text-gray-900">
          {formatState(storeState.status.current_state)}
        </p>
      </div>

      <div>
        <p class="text-xs sm:text-sm text-gray-500">Time to Checkpoint</p>
        <p data-testid="time-to-checkpoint" class="text-base sm:text-lg font-semibold text-gray-900">
          {formatTimeToCheckpoint(storeState.status.last_run_timestamp)}
        </p>
      </div>
    </div>
  {/if}
</div>

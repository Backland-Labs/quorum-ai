<script lang="ts">
  import { agentStatusStore } from '$lib/stores/agentStatus';
  import { onMount } from 'svelte';

  interface Props {
    // Allow override for testing
    testMode?: boolean;
  }

  let { testMode = false }: Props = $props();

  // Subscribe to the store for last_run_timestamp
  const storeState = $derived($agentStatusStore);

  // State for staking KPI
  let isStakingKpiMet = $state<boolean | null>(null);
  let healthcheckLoading = $state(true);

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

  // Fetch staking KPI status from healthcheck
  async function fetchHealthcheck() {
    try {
      const response = await fetch('/healthcheck');
      const data = await response.json();
      isStakingKpiMet = data.agent_health?.is_staking_kpi_met ?? null;
    } catch (error) {
      console.error('Failed to fetch healthcheck:', error);
      isStakingKpiMet = null;
    } finally {
      healthcheckLoading = false;
    }
  }

  onMount(() => {
    fetchHealthcheck();
    // Refresh every 30 minutes
    const interval = setInterval(fetchHealthcheck, 30 * 60 * 1000);
    return () => clearInterval(interval);
  });
</script>

<div
  data-testid="agent-status-widget"
  role="region"
  aria-label="Agent Status"
  class="bg-white shadow rounded-lg p-3 sm:p-4 w-full sm:w-auto"
>
  <h3 data-testid="widget-title" class="text-sm sm:text-base font-medium text-gray-900 mb-4">Agent Status</h3>

  {#if storeState.loading.status || healthcheckLoading}
    <div data-testid="loading-state" class="text-gray-500 text-sm">
      Loading agent status...
    </div>
  {:else if storeState.errors.status}
    <div data-testid="error-state" class="text-gray-500 text-sm italic">
      Backend unavailable - agent status unknown
    </div>
  {:else if storeState.status}
    <div role="status" class="space-y-4">
      <div>
        <p class="text-xs sm:text-sm text-gray-500">Current Status</p>
        <p
          data-testid="activity-threshold"
          class="text-base sm:text-lg font-semibold {isStakingKpiMet ? 'text-green-600' : 'text-yellow-600'}"
        >
          {isStakingKpiMet !== null
            ? (isStakingKpiMet ? 'Meeting Activity Threshold' : 'Not Meeting Activity Threshold')
            : 'Unknown'}
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

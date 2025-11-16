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

  // State for checkpoint data
  let blockchainTime = $state<number | null>(null);
  let nextCheckpointTimestamp = $state<number | null>(null);
  let checkpointLoading = $state(true);

  // Reactive "now" timestamp that updates every minute to trigger time recalculation
  let now = $state(Date.now());


  // Calculate time to next checkpoint using timestamp from staking contract
  function formatTimeToCheckpoint(nextTimestamp: number | null): string {
    if (checkpointLoading) return 'Loading...';

    // If no timestamp provided, estimate 24 hours from now
    if (!nextTimestamp) {
      return '~24h 0m (estimated)';
    }

    const nextCheckpointMs = nextTimestamp * 1000; // Convert unix timestamp to ms
    // Use blockchain time if available (for Anvil time-shifted chains), otherwise system time
    // Add 'now' as dependency to make this reactive to time changes
    const nowMs = blockchainTime ? blockchainTime * 1000 : now;

    const diff = nextCheckpointMs - nowMs;

    // If checkpoint is overdue
    if (diff < 0) return 'Overdue';

    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);

    return `${hours}h ${minutes}m`;
  }

  // Fetch checkpoint data from staking endpoint
  async function fetchCheckpointData() {
    try {
      const response = await fetch('/staking/checkpoints');
      const data = await response.json();

      // Always use blockchain time and checkpoint data if available
      blockchainTime = data.current_blockchain_time || null;
      nextCheckpointTimestamp = data.next_checkpoint_timestamp || null;
    } catch (error) {
      console.error('Failed to fetch checkpoint data:', error);
      blockchainTime = null;
      nextCheckpointTimestamp = null;
    } finally {
      checkpointLoading = false;
    }
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
    fetchCheckpointData();
    // Refresh every 30 minutes
    const healthInterval = setInterval(fetchHealthcheck, 30 * 60 * 1000);
    const checkpointInterval = setInterval(fetchCheckpointData, 30 * 60 * 1000);
    // Update "now" every minute to trigger time recalculation
    const clockInterval = setInterval(() => {
      now = Date.now();
    }, 60 * 1000);
    return () => {
      clearInterval(healthInterval);
      clearInterval(checkpointInterval);
      clearInterval(clockInterval);
    };
  });
</script>

<div
  data-testid="agent-status-widget"
  role="region"
  aria-label="Agent Status"
  class="bg-white shadow rounded-lg p-3 sm:p-4 w-full sm:w-auto"
>
  <h3 data-testid="widget-title" class="text-sm sm:text-base font-medium text-gray-900 mb-4">Agent Status</h3>

  {#if healthcheckLoading || checkpointLoading}
    <div data-testid="loading-state" class="text-gray-500 text-sm">
      Loading agent status...
    </div>
  {:else}
    <div role="status" class="space-y-4">
      <div>
        <p class="text-xs sm:text-sm text-gray-500">Current Status</p>
        <p
          data-testid="activity-threshold"
          class="text-base sm:text-lg font-semibold {isStakingKpiMet === null ? 'text-gray-500' : isStakingKpiMet ? 'text-green-600' : 'text-yellow-600'}"
        >
          {isStakingKpiMet !== null
            ? (isStakingKpiMet ? 'Meeting Activity Threshold' : 'Not Meeting Activity Threshold')
            : (healthcheckLoading ? 'Loading...' : 'Activity Tracking Unavailable')}
        </p>
      </div>

      
      <div>
        <p class="text-xs sm:text-sm text-gray-500">Time to Next Checkpoint</p>
        <p data-testid="time-to-checkpoint" class="text-base sm:text-lg font-semibold text-gray-900">
          {formatTimeToCheckpoint(nextCheckpointTimestamp)}
        </p>
      </div>
    </div>
  {/if}
</div>

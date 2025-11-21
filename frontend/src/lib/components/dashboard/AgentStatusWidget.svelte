<script lang="ts">
  import { agentStatusStore } from '$lib/stores/agentStatus';
  import { onMount } from 'svelte';
  import apiClient from '$lib/api';

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
  let checkpointLoading = $state(false);
  let checkpointError = $state<string | null>(null);

  // State for service ID
  let serviceId = $state<number | null>(null);

  // Reactive "now" timestamp that updates every minute to trigger time recalculation
  let now = $state(Date.now());


  // Calculate time to next checkpoint using timestamp from staking contract
  function formatTimeToCheckpoint(nextTimestamp: number | null): string {
    // Better null handling for nextCheckpointTimestamp
    if (!nextTimestamp) {
      return '~24h 0m (estimated)';
    }

    const nextCheckpointMs = nextTimestamp * 1000; // Convert unix timestamp to ms
    // Use blockchain time if available (for Anvil time-shifted chains), otherwise system time
    // Add 'now' as dependency to make this reactive to time changes
    const nowMs = blockchainTime ? blockchainTime * 1000 : now;

    const timeRemaining = nextCheckpointMs - nowMs;

    // Show "Checkpoint imminent" when timeRemaining <= 0
    if (timeRemaining <= 0) return 'Checkpoint imminent';

    const hours = Math.floor(timeRemaining / 3600000);
    const minutes = Math.floor((timeRemaining % 3600000) / 60000);

    return `${hours}h ${minutes}m`;
  }

  // Fetch checkpoint data from staking endpoint
  async function fetchCheckpointData() {
    checkpointLoading = true;
    checkpointError = null;

    try {
      const response = await fetch('/staking/checkpoints');
      const data = await response.json();

      // Check if response contains an error
      if (data.error) {
        checkpointError = data.error;
        blockchainTime = null;
        nextCheckpointTimestamp = null;
        return;
      }

      // Always use blockchain time and checkpoint data if available
      blockchainTime = data.current_blockchain_time || null;
      nextCheckpointTimestamp = data.next_checkpoint_timestamp || null;
    } catch (error) {
      console.error('Failed to fetch checkpoint data:', error);
      checkpointError = 'Unable to fetch checkpoint data. Please try again.';
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

  // Fetch service ID from discovery endpoint
  async function fetchServiceId() {
    try {
      const { data: responseData, error: responseError } = await apiClient.GET('/api/status/discovery');

      if (!responseError && responseData) {
        serviceId = responseData.service_id ?? null;
      }
    } catch (error) {
      console.error('Failed to fetch service ID:', error);
    }
  }

  onMount(() => {
    fetchHealthcheck();
    fetchCheckpointData();
    fetchServiceId();
    // Refresh every 30 minutes
    const healthInterval = setInterval(fetchHealthcheck, 30 * 60 * 1000);
    const checkpointInterval = setInterval(fetchCheckpointData, 30 * 60 * 1000);
    const serviceIdInterval = setInterval(fetchServiceId, 30 * 60 * 1000);
    // Update "now" every minute to trigger time recalculation
    const clockInterval = setInterval(() => {
      now = Date.now();
    }, 60 * 1000);
    return () => {
      clearInterval(healthInterval);
      clearInterval(checkpointInterval);
      clearInterval(serviceIdInterval);
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
  <div class="flex items-center justify-between mb-4">
    <h3 data-testid="widget-title" class="text-sm sm:text-base font-medium text-gray-900">Agent Status</h3>
    {#if serviceId}
      <span class="text-xs font-mono text-secondary-500 bg-secondary-100 px-2 py-1 rounded">
        ID: {serviceId}
      </span>
    {/if}
  </div>

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
        {#if checkpointLoading}
          <p data-testid="checkpoint-loading" class="text-base sm:text-lg font-semibold text-gray-500">
            Loading checkpoint info...
          </p>
        {:else if checkpointError}
          <div data-testid="checkpoint-error">
            <p class="text-base sm:text-lg font-semibold text-red-500">
              {checkpointError}
            </p>
            <button
              onclick={fetchCheckpointData}
              class="text-sm text-blue-500 underline mt-1 hover:text-blue-700"
              data-testid="retry-button"
            >
              Retry
            </button>
          </div>
        {:else}
          <p data-testid="time-to-checkpoint" class="text-base sm:text-lg font-semibold text-gray-900">
            {formatTimeToCheckpoint(nextCheckpointTimestamp)}
          </p>
        {/if}
      </div>
    </div>
  {/if}
</div>

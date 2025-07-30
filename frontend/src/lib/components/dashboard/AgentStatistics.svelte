<script lang="ts">
  import { onMount } from 'svelte';
  import { apiClient } from '$lib/api';

  // Constants
  const ERROR_MESSAGE = 'Failed to load statistics';
  const RETRY_MESSAGE = 'Please try again later';
  const NO_DATA_TEXT = 'No data';

  // Types
  interface Statistics {
    total_runs: number;
    total_proposals_reviewed: number;
    total_votes_cast: number;
    average_confidence_score: number;
    success_rate: number;
  }

  // State management with Svelte 5 runes
  let loading = $state(true);
  let error = $state<string | null>(null);
  let statistics = $state<Statistics | null>(null);

  // Fetch statistics from the API
  const fetchStatistics = async (): Promise<void> => {
    try {
      loading = true;
      error = null;

      const response = await apiClient.GET('/agent-run/statistics');

      if (response.error) {
        error = ERROR_MESSAGE;
      } else if (response.data) {
        statistics = response.data;
      }
    } catch (err) {
      console.error('Error fetching agent statistics:', err);
      error = ERROR_MESSAGE;
    } finally {
      loading = false;
    }
  };

  // Format percentage values for display
  const formatPercentage = (value: number, hasData: boolean): string => {
    if (!hasData) return NO_DATA_TEXT;
    return `${Math.round(value * 100)}%`;
  };

  // Determine if we have meaningful data
  const hasData = (stats: Statistics | null): boolean => {
    return stats !== null && stats.total_runs > 0;
  };

  onMount(() => {
    fetchStatistics();
  });
</script>

<section class="bg-white dark:bg-gray-800 shadow rounded-lg p-6" aria-labelledby="statistics-heading">
  <h3 id="statistics-heading" class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
    Agent Statistics
  </h3>
  
  {#if loading}
    <div class="text-center py-8" role="status" aria-live="polite">
      <p class="text-gray-500 dark:text-gray-400">Loading statistics...</p>
    </div>
  {:else if error}
    <div class="text-center py-8" role="alert" aria-live="assertive">
      <p class="text-red-600 dark:text-red-400">{error}</p>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">{RETRY_MESSAGE}</p>
    </div>
  {:else if statistics}
    <dl class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4" aria-label="Agent performance metrics">
      <!-- Total Runs -->
      <div class="text-center">
        <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Runs</dt>
        <dd class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100" aria-label="Total runs: {statistics.total_runs}">
          {statistics.total_runs}
        </dd>
      </div>

      <!-- Proposals Reviewed -->
      <div class="text-center">
        <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Proposals Reviewed</dt>
        <dd class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100" aria-label="Proposals reviewed: {statistics.total_proposals_reviewed}">
          {statistics.total_proposals_reviewed}
        </dd>
      </div>

      <!-- Votes Cast -->
      <div class="text-center">
        <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Votes Cast</dt>
        <dd class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100" aria-label="Votes cast: {statistics.total_votes_cast}">
          {statistics.total_votes_cast}
        </dd>
      </div>

      <!-- Average Confidence -->
      <div class="text-center">
        <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Avg Confidence</dt>
        <dd class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100" aria-label="Average confidence: {formatPercentage(statistics.average_confidence_score, hasData(statistics))}">
          {formatPercentage(statistics.average_confidence_score, hasData(statistics))}
        </dd>
      </div>

      <!-- Success Rate -->
      <div class="text-center">
        <dt class="text-sm font-medium text-gray-500 dark:text-gray-400">Success Rate</dt>
        <dd class="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100" aria-label="Success rate: {formatPercentage(statistics.success_rate, hasData(statistics))}">
          {formatPercentage(statistics.success_rate, hasData(statistics))}
        </dd>
      </div>
    </dl>
  {/if}
</section>
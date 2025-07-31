<script lang="ts">
  import { agentStatusStore } from '$lib/stores/agentStatus';

  // Constants
  const ERROR_MESSAGE = 'Failed to load statistics';
  const RETRY_MESSAGE = 'Please try again later';
  const NO_DATA_TEXT = 'No data';

  // Get data from the store
  const storeState = $state($agentStatusStore);

  // Format percentage values for display
  const formatPercentage = (value: number, hasData: boolean): string => {
    if (!hasData) return NO_DATA_TEXT;
    return `${Math.round(value * 100)}%`;
  };

  // Determine if we have meaningful data
  const hasData = (stats: typeof storeState.statistics): boolean => {
    return stats !== null && stats.total_runs > 0;
  };
</script>

<section 
  class="bg-white dark:bg-gray-800 shadow rounded-lg p-3 sm:p-4" 
  aria-labelledby="statistics-heading"
  role="region"
  aria-label="Agent Statistics"
>
  <h3 id="statistics-heading" data-testid="statistics-title" class="text-base sm:text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
    Agent Statistics
  </h3>
  
  {#if storeState.loading.statistics}
    <div data-testid="loading-state" class="text-center p-4 sm:p-6" role="status" aria-live="polite">
      <p class="text-gray-500 dark:text-gray-400 text-sm">Loading statistics...</p>
    </div>
  {:else if storeState.errors.statistics}
    <div data-testid="error-state" class="text-center p-4 sm:p-6" role="alert" aria-live="assertive">
      <p class="text-red-600 dark:text-red-400 text-sm sm:text-base">{storeState.errors.statistics}</p>
      <p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-2">{RETRY_MESSAGE}</p>
    </div>
  {:else if storeState.statistics}
    <dl data-testid="statistics-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4" aria-label="Agent performance metrics">
      <!-- Total Runs -->
      <div data-testid="stat-card" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 sm:p-4 w-full" role="group" aria-label="Total runs">
        <div data-testid="stat-content" class="flex flex-col space-y-1">
          <dt data-testid="stat-label" class="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">Total Runs</dt>
          <dd data-testid="stat-value" class="text-lg sm:text-xl lg:text-2xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums" aria-label="Total runs: {storeState.statistics.total_runs}">
            {storeState.statistics.total_runs}
          </dd>
        </div>
      </div>

      <!-- Proposals Reviewed -->
      <div data-testid="stat-card" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 sm:p-4 w-full" role="group" aria-label="Proposals reviewed">
        <div data-testid="stat-content" class="flex flex-col space-y-1">
          <dt data-testid="stat-label" class="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">Proposals Reviewed</dt>
          <dd data-testid="stat-value" class="text-lg sm:text-xl lg:text-2xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums" aria-label="Proposals reviewed: {storeState.statistics.total_proposals_reviewed}">
            {storeState.statistics.total_proposals_reviewed}
          </dd>
        </div>
      </div>

      <!-- Votes Cast -->
      <div data-testid="stat-card" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 sm:p-4 w-full" role="group" aria-label="Votes cast">
        <div data-testid="stat-content" class="flex flex-col space-y-1">
          <dt data-testid="stat-label" class="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">Votes Cast</dt>
          <dd data-testid="stat-value" class="text-lg sm:text-xl lg:text-2xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums" aria-label="Votes cast: {storeState.statistics.total_votes_cast}">
            {storeState.statistics.total_votes_cast}
          </dd>
        </div>
      </div>

      <!-- Average Confidence -->
      <div data-testid="stat-card" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 sm:p-4 w-full" role="group" aria-label="Average confidence">
        <div data-testid="stat-content" class="flex flex-col space-y-1">
          <dt data-testid="stat-label" class="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">Avg Confidence</dt>
          <dd data-testid="stat-value percentage-value" class="text-lg sm:text-xl lg:text-2xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums font-mono" aria-label="Average confidence: {formatPercentage(storeState.statistics.average_confidence, hasData(storeState.statistics))}">
            {formatPercentage(storeState.statistics.average_confidence, hasData(storeState.statistics))}
          </dd>
        </div>
      </div>

      <!-- Success Rate -->
      <div data-testid="stat-card" class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 sm:p-4 w-full" role="group" aria-label="Success rate">
        <div data-testid="stat-content" class="flex flex-col space-y-1">
          <dt data-testid="stat-label" class="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">Success Rate</dt>
          <dd data-testid="stat-value percentage-value" class="text-lg sm:text-xl lg:text-2xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums font-mono" aria-label="Success rate: {formatPercentage(storeState.statistics.success_rate, hasData(storeState.statistics))}">
            {formatPercentage(storeState.statistics.success_rate, hasData(storeState.statistics))}
          </dd>
        </div>
      </div>
    </dl>
  {/if}
</section>
<script lang="ts">
  import { agentStatusStore } from '$lib/stores/agentStatus';

  // Constants
  const ERROR_MESSAGE = 'Failed to load statistics';
  const RETRY_MESSAGE = 'Please try again later';

  // Get data from the store
  const storeState = $state($agentStatusStore);

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
    <dl data-testid="statistics-grid" class="grid grid-cols-2 gap-6" aria-label="Agent performance metrics">
      <!-- Reconsider Proposals -->
      <div data-testid="stat-card" class="w-full" role="group" aria-label="Reconsider proposals">
        <div data-testid="stat-content" class="flex flex-col space-y-1">
          <dt data-testid="stat-label" class="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">Reconsider Proposals</dt>
          <dd data-testid="stat-value" class="text-3xl sm:text-4xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums" aria-label="Reconsider proposals: {storeState.statistics.total_proposals_evaluated}">
            {storeState.statistics.total_proposals_evaluated}
          </dd>
        </div>
      </div>

      <!-- Votes Cast -->
      <div data-testid="stat-card" class="w-full" role="group" aria-label="Votes cast">
        <div data-testid="stat-content" class="flex flex-col space-y-1">
          <dt data-testid="stat-label" class="text-xs sm:text-sm font-medium text-gray-500 dark:text-gray-400">Votes Cast</dt>
          <dd data-testid="stat-value" class="text-3xl sm:text-4xl font-semibold text-gray-900 dark:text-gray-100 tabular-nums" aria-label="Votes cast: {storeState.statistics.total_votes_cast}">
            {storeState.statistics.total_votes_cast}
          </dd>
        </div>
      </div>
    </dl>
  {/if}
</section>

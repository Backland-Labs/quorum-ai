<script lang="ts">
  import { onMount } from 'svelte';
  import { apiClient } from '$lib/api';
  
  // Temporary types until OpenAPI client is regenerated
  interface AgentDecisionResponse {
    proposal_id: string;
    proposal_title: string;
    vote: 'FOR' | 'AGAINST' | 'ABSTAIN';
    confidence_score: number;
    voting_power: string;
    timestamp: string;
    reasoning: string;
  }
  
  interface AgentDecisionsResponse {
    decisions: AgentDecisionResponse[];
    total_count: number;
  }
  
  // Component state
  let decisions: AgentDecisionResponse[] = $state([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  
  // Constants
  const DECISIONS_LIMIT = 5;
  const CONFIDENCE_THRESHOLDS = {
    HIGH: 0.8,
    MEDIUM: 0.6
  };
  
  const VOTE_COLORS = {
    FOR: 'text-emerald-600',
    AGAINST: 'text-rose-600',
    ABSTAIN: 'text-gray-600'
  } as const;
  
  const CONFIDENCE_COLORS = {
    HIGH: 'text-emerald-600',
    MEDIUM: 'text-amber-600',
    LOW: 'text-rose-600'
  } as const;
  
  // Utility functions
  function formatTimestamp(timestamp: string | null): string {
    if (!timestamp) return 'Never';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffDays > 0) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    if (diffHours > 0) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffMins > 0) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    return 'Just now';
  }
  
  function getVoteColorClass(vote: string): string {
    return VOTE_COLORS[vote as keyof typeof VOTE_COLORS] || VOTE_COLORS.ABSTAIN;
  }
  
  function getConfidenceColorClass(confidence: number): string {
    if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) return CONFIDENCE_COLORS.HIGH;
    if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) return CONFIDENCE_COLORS.MEDIUM;
    return CONFIDENCE_COLORS.LOW;
  }
  
  function formatConfidencePercentage(confidence: number): string {
    return `${Math.round(confidence * 100)}%`;
  }
  
  // API functions
  async function fetchDecisions(): Promise<void> {
    try {
      loading = true;
      error = null;
      
      // @ts-ignore - endpoint will be typed after OpenAPI client regeneration
      const response = await apiClient.GET('/agent-run/decisions' as any, {
        params: { query: { limit: DECISIONS_LIMIT } }
      });
      
      if (response.error) {
        error = 'Unable to load decisions';
        return;
      }
      
      decisions = response.data?.decisions || [];
    } catch (err) {
      error = 'Unable to load decisions';
      console.error('Failed to fetch decisions:', err);
    } finally {
      loading = false;
    }
  }
  
  // Lifecycle
  onMount(() => {
    fetchDecisions();
  });
</script>

<div 
  data-testid="decisions-panel"
  class="bg-white rounded-lg shadow p-3 sm:p-4 w-full max-w-full sm:max-w-2xl" 
  role="region" 
  aria-labelledby="decisions-heading"
>
  <h2 id="decisions-heading" data-testid="panel-title" class="text-base sm:text-lg font-semibold mb-4">Recent Voting Decisions</h2>
  
  {#if loading}
    <div data-testid="loading-state" class="text-gray-500 text-sm p-4 sm:p-6 text-center">
      Loading decisions...
    </div>
  {:else if error}
    <div data-testid="error-state" class="text-red-600 text-sm p-4 sm:p-6 text-center">
      {error}
    </div>
  {:else if decisions.length === 0}
    <div data-testid="empty-state" class="text-gray-500 text-sm p-4 sm:p-6 text-center">
      No voting decisions yet
    </div>
  {:else}
    <ul data-testid="decisions-list" class="space-y-3 sm:space-y-4" role="list">
      {#each decisions as decision}
        <li data-testid="decision-item" class="border-b pb-3 sm:pb-4 last:border-b-0" role="listitem">
          <div data-testid="decision-card" class="flex flex-col sm:flex-row gap-3 p-3 sm:p-4">
            <div class="flex-1">
              <a 
                href="/proposals/{decision.proposal_id}"
                data-testid="proposal-link"
                class="text-blue-600 hover:text-blue-800 font-medium min-h-[44px] flex items-center"
                aria-label="View proposal: {decision.proposal_title}"
              >
                <span data-testid="proposal-title" class="text-sm sm:text-base break-words line-clamp-2 sm:line-clamp-none">
                  {decision.proposal_title}
                </span>
              </a>
              <div data-testid="vote-info" class="mt-2 grid grid-cols-2 gap-2 sm:flex sm:gap-4">
                <span class="flex items-center gap-1">
                  <span class="text-gray-500 text-xs sm:text-sm">Vote:</span>
                  <span 
                    data-testid="vote-badge" 
                    class={`font-medium text-xs sm:text-sm ${getVoteColorClass(decision.vote)}`}
                  >
                    {decision.vote}
                  </span>
                </span>
                <span class="flex items-center gap-1">
                  <span class="text-gray-500 text-xs sm:text-sm">Confidence:</span>
                  <span 
                    data-testid="confidence-score"
                    class={`font-medium text-xs sm:text-sm ${getConfidenceColorClass(decision.confidence_score)}`}
                  >
                    {formatConfidencePercentage(decision.confidence_score)}
                  </span>
                </span>
                <span 
                  data-testid="decision-timestamp"
                  class="text-gray-500 text-xs sm:text-sm col-span-2 sm:col-span-1"
                >
                  {formatTimestamp(decision.timestamp)}
                </span>
              </div>
            </div>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
</div>
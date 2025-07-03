<script lang="ts">
  import LoadingSkeleton from './LoadingSkeleton.svelte';
  import type { components } from '$lib/api/client.js';

  // Constants
  const DEFAULT_LIMIT = 10;
  const ADDRESS_TRUNCATE_LENGTH = 10;
  const ADDRESS_START_CHARS = 6;
  const ADDRESS_END_CHARS = 4;
  const LARGE_AMOUNT_THRESHOLD = 1e21;
  const WEI_CONVERSION_FACTOR = 1e18;
  const EXPONENTIAL_NOTATION_PRECISION = 2;
  const LOADING_SKELETON_COUNT = 5;

  interface Props {
    proposalId: string;
    limit?: number;
  }

  let { proposalId, limit = DEFAULT_LIMIT }: Props = $props();

  type ProposalTopVoters = components['schemas']['ProposalTopVoters'];
  type ProposalVoter = components['schemas']['ProposalVoter'];
  type VoteType = components['schemas']['VoteType'];

  // Component state
  let loading = $state(true);
  let error = $state<string | null>(null);
  let voters = $state<ProposalVoter[]>([]);
  let retryCount = $state(0);

  // Computed properties for template state management
  let hasVoters = $derived(voters.length > 0);
  let isEmptyState = $derived(!loading && !error && !hasVoters);
  let isErrorState = $derived(!loading && error !== null);
  let isLoadingState = $derived(loading);
  let isVotersState = $derived(!loading && !error && hasVoters);

  // Utility functions
  function truncateAddress(address: string): string {
    console.assert(typeof address === 'string', 'Address must be a string');
    console.assert(address.length > 0, 'Address cannot be empty');
    
    if (address.length <= ADDRESS_TRUNCATE_LENGTH) return address;
    return `${address.slice(0, ADDRESS_START_CHARS)}...${address.slice(-ADDRESS_END_CHARS)}`;
  }

  function formatVotingPower(amount: string): string {
    console.assert(typeof amount === 'string', 'Amount must be a string');
    console.assert(amount.length > 0, 'Amount cannot be empty');

    try {
      const num = parseFloat(amount);
      if (num >= LARGE_AMOUNT_THRESHOLD) {
        return (num / WEI_CONVERSION_FACTOR).toExponential(EXPONENTIAL_NOTATION_PRECISION);
      }
      return new Intl.NumberFormat('en-US').format(num / WEI_CONVERSION_FACTOR);
    } catch {
      return amount;
    }
  }

  function getVoteBadgeClasses(voteType: VoteType): string {
    console.assert(typeof voteType === 'string', 'Vote type must be a string');
    console.assert(['FOR', 'AGAINST', 'ABSTAIN'].includes(voteType), 'Vote type must be valid');

    const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
    
    switch (voteType) {
      case 'FOR':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'AGAINST':
        return `${baseClasses} bg-red-100 text-red-800`;
      case 'ABSTAIN':
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  }

  async function fetchTopVoters(): Promise<void> {
    console.assert(typeof proposalId === 'string', 'Proposal ID must be a string');
    console.assert(proposalId.length > 0, 'Proposal ID cannot be empty');

    loading = true;
    error = null;

    try {
      // Use real backend API endpoint
      const response = await fetch(`http://localhost:8000/proposals/${proposalId}/top-voters?limit=${limit}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch top voters: ${response.status}`);
      }

      const data: ProposalTopVoters = await response.json();
      voters = data.voters || [];
      
    } catch (err) {
      console.error('Error fetching top voters:', err);
      error = err instanceof Error ? err.message : 'Failed to load top voters';
    } finally {
      loading = false;
    }
  }

  function handleRetry(): void {
    console.assert(typeof retryCount === 'number', 'Retry count must be a number');
    
    retryCount += 1;
    fetchTopVoters();
  }

  $effect(() => {
    fetchTopVoters();
  });
</script>

<div class="space-y-4" data-testid="top-voters-container">
  <h3 class="text-lg font-semibold text-gray-900">Top Voters</h3>
  
  {#if isLoadingState}
    <div class="space-y-3" data-testid="loading-state" aria-label="Loading top voters">
      <LoadingSkeleton count={LOADING_SKELETON_COUNT} height="h-12" />
    </div>
  {:else if isErrorState}
    <div class="text-center py-8" data-testid="error-state">
      <div class="text-red-600 mb-4">
        <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      </div>
      <p class="text-gray-600 mb-4">{error}</p>
      <button
        type="button"
        onclick={handleRetry}
        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        data-testid="retry-button"
        aria-label="Retry loading top voters"
      >
        Try Again
      </button>
    </div>
  {:else if isEmptyState}
    <div class="text-center py-8" data-testid="empty-state">
      <div class="text-gray-400 mb-4">
        <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
        </svg>
      </div>
      <p class="text-gray-600">No voters found for this proposal</p>
    </div>
  {:else}
    <div class="space-y-3" data-testid="voters-list">
      {#each voters as voter, index (voter.address)}
        <div 
          class="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
          data-testid="voter-item"
          role="listitem"
          aria-label="Voter {index + 1} of {voters.length}"
        >
          <div class="flex items-center space-x-4">
            <div class="flex-shrink-0">
              <div class="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
                <span class="text-sm font-medium text-gray-600">
                  {index + 1}
                </span>
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate" data-testid="voter-address">
                {truncateAddress(voter.address)}
              </p>
              <p class="text-sm text-gray-500" data-testid="voting-power">
                {formatVotingPower(voter.amount)} votes
              </p>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <span 
              class={getVoteBadgeClasses(voter.vote_type)}
              data-testid="vote-badge"
              aria-label="Vote: {voter.vote_type}"
            >
              {voter.vote_type}
            </span>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
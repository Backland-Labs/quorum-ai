<script lang="ts">
  import type { Proposal } from '$lib/types/dashboard';
  
  interface VotingIndicatorProps {
    votesFor: string;
    votesAgainst: string;
    votesAbstain: string;
    state: string;
    endBlock?: number;
    currentBlock?: number;
  }
  
  const { votesFor, votesAgainst, votesAbstain, state, endBlock, currentBlock }: VotingIndicatorProps = $props();
  
  const totalVotes = $derived(
    BigInt(votesFor || '0') + BigInt(votesAgainst || '0') + BigInt(votesAbstain || '0')
  );
  
  const forPercentage = $derived(
    totalVotes > 0n ? Number((BigInt(votesFor || '0') * 100n) / totalVotes) : 0
  );
  
  const againstPercentage = $derived(
    totalVotes > 0n ? Number((BigInt(votesAgainst || '0') * 100n) / totalVotes) : 0
  );
  
  const abstainPercentage = $derived(
    totalVotes > 0n ? Number((BigInt(votesAbstain || '0') * 100n) / totalVotes) : 0
  );
  
  const stateConfig = $derived(() => {
    switch (state) {
      case 'ACTIVE':
        return { label: 'Active', class: 'bg-emerald-500 text-white' };
      case 'SUCCEEDED':
        return { label: 'Succeeded', class: 'bg-green-500 text-white' };
      case 'DEFEATED':
        return { label: 'Defeated', class: 'bg-red-500 text-white' };
      case 'EXECUTED':
        return { label: 'Executed', class: 'bg-blue-500 text-white' };
      case 'QUEUED':
        return { label: 'Queued', class: 'bg-yellow-500 text-white' };
      case 'CANCELED':
        return { label: 'Canceled', class: 'bg-gray-500 text-white' };
      case 'EXPIRED':
        return { label: 'Expired', class: 'bg-orange-500 text-white' };
      case 'PENDING':
        return { label: 'Pending', class: 'bg-indigo-500 text-white' };
      default:
        return { label: state, class: 'bg-gray-400 text-white' };
    }
  });
  
  const formatVotes = (votes: string): string => {
    const num = BigInt(votes || '0');
    if (num >= 1000000000000000000n) {
      return `${Number(num / 1000000000000000000n).toLocaleString()}`;
    }
    return num.toString();
  };
</script>

<div class="space-y-3">
  <div class="flex items-center justify-between">
    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Voting Status</span>
    <span class={`px-2.5 py-1 text-xs font-medium rounded-full ${stateConfig().class}`}>
      {stateConfig().label}
    </span>
  </div>
  
  {#if totalVotes > 0n}
    <div class="space-y-2">
      <div class="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400">
        <span>Total Votes</span>
        <span class="font-medium">{formatVotes(totalVotes.toString())}</span>
      </div>
      
      <div class="space-y-1.5">
        <div class="flex items-center justify-between text-xs">
          <span class="text-green-600 dark:text-green-400">For</span>
          <span class="text-gray-700 dark:text-gray-300">{forPercentage}%</span>
        </div>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
          <div class="bg-green-500 h-2 rounded-full transition-all duration-300" style="width: {forPercentage}%"></div>
        </div>
        
        <div class="flex items-center justify-between text-xs">
          <span class="text-red-600 dark:text-red-400">Against</span>
          <span class="text-gray-700 dark:text-gray-300">{againstPercentage}%</span>
        </div>
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
          <div class="bg-red-500 h-2 rounded-full transition-all duration-300" style="width: {againstPercentage}%"></div>
        </div>
        
        {#if abstainPercentage > 0}
          <div class="flex items-center justify-between text-xs">
            <span class="text-gray-600 dark:text-gray-400">Abstain</span>
            <span class="text-gray-700 dark:text-gray-300">{abstainPercentage}%</span>
          </div>
          <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
            <div class="bg-gray-400 h-2 rounded-full transition-all duration-300" style="width: {abstainPercentage}%"></div>
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <p class="text-xs text-gray-500 dark:text-gray-400">No votes cast yet</p>
  {/if}
</div>
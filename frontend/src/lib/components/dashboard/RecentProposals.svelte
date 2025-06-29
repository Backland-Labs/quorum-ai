<script lang="ts">
  import type { OrganizationWithProposals } from '$lib/types/dashboard.js';
  import ProposalCard from './ProposalCard.svelte';
  
  interface Props {
    organizationData: OrganizationWithProposals;
    onViewAllProposals: () => void;
  }
  
  let { organizationData, onViewAllProposals }: Props = $props();
  
  function validateProps(): void {
    console.assert(organizationData !== null, 'Organization data should not be null');
    console.assert(typeof organizationData === 'object', 'Organization data should be an object');
  }
  
  function hasProposals(): boolean {
    console.assert(organizationData !== null, 'Organization data should not be null');
    console.assert(typeof organizationData === 'object', 'Organization data should be an object');
    
    return organizationData.proposals && organizationData.proposals.length > 0;
  }
  
  function getDisplayProposals() {
    console.assert(hasProposals(), 'Should have proposals when calling getDisplayProposals');
    console.assert(Array.isArray(organizationData.proposals), 'Proposals should be an array');
    
    return organizationData.proposals.slice(0, 3);
  }
  
  validateProps();
</script>

{#if hasProposals()}
  <div class="card lg:col-span-2">
    <div class="flex items-center justify-between mb-6">
      <h4 class="text-lg font-semibold text-secondary-900">Recent Proposals</h4>
      <span class="text-sm text-secondary-500">{organizationData.proposals.length} total</span>
    </div>
    
    <div class="space-y-6">
      {#each getDisplayProposals() as proposal}
        <ProposalCard {proposal} variant="detailed" />
      {/each}
    </div>
    
    <!-- View All Link -->
    <div class="mt-6 text-center">
      <button
        onclick={onViewAllProposals}
        class="inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors duration-200"
      >
        View all {organizationData.proposals.length} proposals
        <svg class="ml-1 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  </div>
{/if}
<script lang="ts">
  import type { components } from '$lib/api/client';
  import ProposalCard from './ProposalCard.svelte';

  interface Props {
    proposals: components['schemas']['Proposal'][];
    proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;
    onProposalClick: (proposalId: string) => void;
  }

  let { proposals, proposalSummaries, onProposalClick }: Props = $props();

  function validateProps(): void {
    console.assert(Array.isArray(proposals), 'Proposals should be an array');
    console.assert(proposalSummaries instanceof Map, 'Proposal summaries should be a Map');
  }

  function hasProposals(): boolean {
    console.assert(Array.isArray(proposals), 'Proposals should be an array');

    return proposals.length > 0;
  }

  function getDisplayProposals() {
    console.assert(hasProposals(), 'Should have proposals when calling getDisplayProposals');
    console.assert(Array.isArray(proposals), 'Proposals should be an array');

    return proposals.slice(0, 3);
  }

  validateProps();
</script>

{#if hasProposals()}
  <div class="bg-white rounded-lg shadow p-6 lg:col-span-2">
    <div class="mb-6">
      <h3 class="text-base font-medium text-gray-900">Recent Proposals</h3>
    </div>

    <div class="space-y-4">
      {#each getDisplayProposals() as proposal}
        <ProposalCard
          {proposal}
          summary={proposalSummaries.get(proposal.id)}
          onClick={() => onProposalClick(proposal.id)}
          variant="compact"
        />
      {/each}
    </div>
  </div>
{/if}

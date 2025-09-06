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
  <div class="card lg:col-span-2">
    <div class="flex items-center justify-between mb-6">
      <h4 class="text-lg font-semibold text-secondary-900">Recent Proposals</h4>
      <span class="text-sm text-secondary-500">{proposals.length} total</span>
    </div>

    <div class="space-y-6">
      {#each getDisplayProposals() as proposal}
        <ProposalCard
          {proposal}
          summary={proposalSummaries.get(proposal.id)}
          onClick={() => onProposalClick(proposal.id)}
          variant="detailed"
        />
      {/each}
    </div>

  </div>
{/if}

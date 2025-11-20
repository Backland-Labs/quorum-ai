<script lang="ts">
  import type { components } from '$lib/api/client';
  import ProposalCard from './ProposalCard.svelte';

  interface Props {
    proposals: components['schemas']['Proposal'][];
    agentDecisions: Map<string, components['schemas']['AgentDecisionResponse']>;
  }

  let { proposals, agentDecisions }: Props = $props();

  function validateProps(): void {
    console.assert(Array.isArray(proposals), 'Proposals should be an array');
    console.assert(agentDecisions instanceof Map, 'Agent decisions should be a Map');
  }

  function getDisplayProposals() {
    console.assert(Array.isArray(proposals), 'Proposals should be an array');
    console.assert(agentDecisions instanceof Map, 'Agent decisions should be a Map');

    // Filter proposals to only show those with decisions
    return proposals.filter(p => agentDecisions.has(p.id));
  }

  const displayProposals = $derived(getDisplayProposals());
  const hasProposals = $derived(displayProposals.length > 0);

  validateProps();
</script>

{#if hasProposals}
  <div class="bg-white rounded-lg shadow p-6 lg:col-span-2">
    <div class="mb-6 flex items-center justify-between">
      <h3 class="text-base font-medium text-gray-900">All Proposals</h3>
      <span class="text-sm text-gray-500">
        {displayProposals.length} {displayProposals.length === 1 ? 'proposal' : 'proposals'}
      </span>
    </div>

    <div class="space-y-4">
      {#each displayProposals as proposal}
        <ProposalCard
          {proposal}
          variant="compact"
          decision={agentDecisions.get(proposal.id)}
        />
      {/each}
    </div>
  </div>
{:else}
  <div class="bg-white rounded-lg shadow p-6 lg:col-span-2">
    <div class="text-center py-8">
      <p class="text-gray-500 text-sm">No proposals with agent decisions yet</p>
    </div>
  </div>
{/if}

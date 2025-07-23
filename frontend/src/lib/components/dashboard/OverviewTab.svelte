<script lang="ts">
  import type { components } from '$lib/api/client';
  import ProposalStats from './ProposalStats.svelte';
  import RecentProposals from './RecentProposals.svelte';
  import EmptyState from './EmptyState.svelte';

  interface Props {
    proposals: components['schemas']['Proposal'][];
    proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;
    onProposalClick: (proposalId: string) => void;
    onViewAllProposals: () => void;
  }

  let { proposals, proposalSummaries, onProposalClick, onViewAllProposals }: Props = $props();

  function validateProps(): void {
    console.assert(typeof onProposalClick === 'function', 'onProposalClick must be a function');
    console.assert(typeof onViewAllProposals === 'function', 'onViewAllProposals must be a function');
  }

  function hasProposals(): boolean {
    console.assert(Array.isArray(proposals), 'Proposals should be an array');

    return proposals.length > 0;
  }

  validateProps();
</script>

<div id="tab-panel-overview" role="tabpanel" aria-labelledby="tab-overview">
  {#if hasProposals()}
    <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <ProposalStats
        {proposals}
        onViewDetails={onViewAllProposals}
      />

      <RecentProposals
        {proposals}
        {proposalSummaries}
        {onProposalClick}
        {onViewAllProposals}
      />
    </div>
  {:else}
    <EmptyState
      title="No proposals found"
      description="This Snapshot space doesn't have any proposals yet."
      icon="document"
    />
  {/if}
</div>

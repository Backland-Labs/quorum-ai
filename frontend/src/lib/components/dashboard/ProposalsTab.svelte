<script lang="ts">
  import type { components } from '$lib/api/client';
  import ProposalCard from './ProposalCard.svelte';
  import EmptyState from './EmptyState.svelte';
  import LoadingSkeleton from '../LoadingSkeleton.svelte';
  import { onMount } from 'svelte';

  interface Props {
    proposals: components['schemas']['Proposal'][];
    proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;
    dashboardStore: any;
  }

  let { proposals, proposalSummaries, dashboardStore }: Props = $props();

  let proposalsLoading = $derived($dashboardStore.proposalsLoading);
  let proposalsError = $derived($dashboardStore.proposalsError);
  let proposalFilters = $derived($dashboardStore.proposalFilters);
  let currentSpaceId = $derived($dashboardStore.currentSpaceId);

  const proposalStates: Array<{ value: components['schemas']['ProposalState'] | undefined; label: string }> = [
    { value: undefined, label: 'All States' },
    { value: 'active', label: 'Active' },
    { value: 'closed', label: 'Closed' },
    { value: 'pending', label: 'Pending' }
  ];


  onMount(() => {
    console.assert(dashboardStore, 'Dashboard store should be provided');
    console.assert(typeof dashboardStore.loadProposals === 'function', 'Dashboard store should have loadProposals method');

    if (currentSpaceId && proposals.length === 0) {
      dashboardStore.loadProposals();
    }
  });

  function handleFilterChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const state = target.value as components['schemas']['ProposalState'] | undefined;

    console.assert(dashboardStore, 'Dashboard store should be available');

    dashboardStore.updateProposalFilters({ state: state || undefined });
  }



  function getProposalWithSummary(proposal: components['schemas']['Proposal']) {
    const summary = proposalSummaries.get(proposal.id);

    return summary ? {
      ...proposal,
      proposal_id: proposal.id,
      summary: summary.summary,
      key_points: summary.key_points,
      risk_level: summary.risk_level,
      recommendation: summary.recommendation,
      confidence_score: summary.confidence_score
    } : null;
  }
</script>

<div id="tab-panel-proposals" role="tabpanel" aria-labelledby="tab-proposals">
  {#if currentSpaceId}
    <div class="card">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-6 gap-4">
        <h3 class="text-lg font-semibold text-secondary-900">
          Proposals for {currentSpaceId}
        </h3>

        <div class="flex flex-col sm:flex-row gap-3">
          <select
            class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            value={proposalFilters.state}
            onchange={handleFilterChange}
          >
            {#each proposalStates as state}
              <option value={state.value}>{state.label}</option>
            {/each}
          </select>

        </div>
      </div>

      {#if proposalsError}
        <EmptyState
          title="Error loading proposals"
          description={proposalsError}
          icon="error"
        />
      {:else if proposalsLoading && proposals.length === 0}
        <div class="space-y-4">
          <LoadingSkeleton count={3} height="h-32" className="mb-4" />
        </div>
      {:else if proposals.length > 0}
        <div class="space-y-4">
          {#each proposals as proposal}
            {@const proposalWithSummary = getProposalWithSummary(proposal)}
            {#if proposalWithSummary}
              <ProposalCard
                proposal={proposalWithSummary}
                fullProposal={proposal}
                variant="detailed"
              />
            {:else}
              <div class="p-4 border border-gray-200 rounded-lg">
                <h4 class="font-medium text-gray-900 mb-2">{proposal.title}</h4>
                <p class="text-sm text-gray-500">Loading summary...</p>
              </div>
            {/if}
          {/each}
        </div>

      {:else}
        <EmptyState
          title="No proposals found"
          description="No proposals match your current filters."
          icon="proposals"
        />
      {/if}
    </div>
  {:else}
    <EmptyState
      title="No space selected"
      description="Choose a Snapshot space from the dropdown to view its proposals."
      icon="document"
    />
  {/if}
</div>

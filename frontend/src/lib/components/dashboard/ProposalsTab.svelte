<script lang="ts">
  import type { OrganizationWithProposals } from '$lib/types/dashboard.js';
  import type { components } from '$lib/api/client';
  import ProposalCard from './ProposalCard.svelte';
  import EmptyState from './EmptyState.svelte';
  import LoadingSkeleton from '../LoadingSkeleton.svelte';
  import { onMount } from 'svelte';

  interface Props {
    currentOrgData: OrganizationWithProposals | null;
    dashboardStore: any;
  }

  let { currentOrgData, dashboardStore }: Props = $props();

  let allProposals = $derived($dashboardStore.allProposals);
  let proposalSummaries = $derived($dashboardStore.proposalSummaries);
  let proposalsLoading = $derived($dashboardStore.proposalsLoading);
  let proposalsError = $derived($dashboardStore.proposalsError);
  let proposalsCursor = $derived($dashboardStore.proposalsCursor);
  let proposalFilters = $derived($dashboardStore.proposalFilters);
  let selectedOrganization = $derived($dashboardStore.selectedOrganization);

  const proposalStates: Array<{ value: components['schemas']['ProposalState'] | undefined; label: string }> = [
    { value: undefined, label: 'All States' },
    { value: 'ACTIVE', label: 'Active' },
    { value: 'SUCCEEDED', label: 'Succeeded' },
    { value: 'DEFEATED', label: 'Defeated' },
    { value: 'EXECUTED', label: 'Executed' },
    { value: 'QUEUED', label: 'Queued' },
    { value: 'PENDING', label: 'Pending' },
    { value: 'CANCELED', label: 'Canceled' },
    { value: 'EXPIRED', label: 'Expired' }
  ];

  const sortOptions: Array<{ value: components['schemas']['SortCriteria']; label: string }> = [
    { value: 'created_date', label: 'Date Created' },
    { value: 'vote_count', label: 'Vote Count' },
    { value: 'state', label: 'Status' },
    { value: 'title', label: 'Title' }
  ];

  onMount(() => {
    console.assert(dashboardStore, 'Dashboard store should be provided');
    console.assert(typeof dashboardStore.loadProposals === 'function', 'Dashboard store should have loadProposals method');

    if (selectedOrganization && allProposals.length === 0) {
      dashboardStore.loadProposals(true);
    }
  });

  function handleFilterChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const state = target.value as components['schemas']['ProposalState'] | undefined;

    console.assert(dashboardStore, 'Dashboard store should be available');

    dashboardStore.updateProposalFilters({ state: state || undefined });
  }

  function handleSortChange(event: Event): void {
    const target = event.target as HTMLSelectElement;
    const sortBy = target.value as components['schemas']['SortCriteria'];

    console.assert(dashboardStore, 'Dashboard store should be available');

    dashboardStore.updateProposalFilters({ sortBy });
  }

  function handleSortOrderToggle(): void {
    console.assert(dashboardStore, 'Dashboard store should be available');

    const newOrder = proposalFilters.sortOrder === 'asc' ? 'desc' : 'asc';
    dashboardStore.updateProposalFilters({ sortOrder: newOrder });
  }

  function handleLoadMore(): void {
    console.assert(dashboardStore, 'Dashboard store should be available');
    console.assert(proposalsCursor, 'Should have cursor for loading more');

    dashboardStore.loadProposals(false);
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
  {#if selectedOrganization}
    <div class="card">
      <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between mb-6 gap-4">
        <h3 class="text-lg font-semibold text-secondary-900">
          Proposals for {selectedOrganization.name}
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

          <div class="flex items-center gap-2">
            <select
              class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              value={proposalFilters.sortBy}
              onchange={handleSortChange}
            >
              {#each sortOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>

            <button
              onclick={handleSortOrderToggle}
              class="p-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              aria-label={`Sort ${proposalFilters.sortOrder === 'asc' ? 'descending' : 'ascending'}`}
            >
              {#if proposalFilters.sortOrder === 'asc'}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11l5-5m0 0l5 5m-5-5v12" />
                </svg>
              {:else}
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 13l-5 5m0 0l-5-5m5 5V6" />
                </svg>
              {/if}
            </button>
          </div>
        </div>
      </div>

      {#if proposalsError}
        <EmptyState
          title="Error loading proposals"
          description={proposalsError}
          icon="error"
        />
      {:else if proposalsLoading && allProposals.length === 0}
        <div class="space-y-4">
          <LoadingSkeleton count={3} height="h-32" className="mb-4" />
        </div>
      {:else if allProposals.length > 0}
        <div class="space-y-4">
          {#each allProposals as proposal}
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

        {#if proposalsCursor}
          <div class="mt-6 flex justify-center">
            <button
              onclick={handleLoadMore}
              disabled={proposalsLoading}
              class="px-4 py-2 text-sm font-medium text-primary-600 bg-white border border-primary-600 rounded-lg hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {proposalsLoading ? 'Loading...' : 'Load More'}
            </button>
          </div>
        {/if}
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
      title="No organization selected"
      description="Choose an organization from the dropdown to view its proposals."
      icon="organization"
    />
  {/if}
</div>

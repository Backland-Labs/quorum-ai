<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import apiClient from '$lib/api';
  import type { components } from '$lib/api/client';

  let proposals: components["schemas"]["Proposal"][] = [];
  let organization: components["schemas"]["Organization"] | null = null;
  let loading = true;
  let error: string | null = null;

  $: orgId = $page.params.id;

  onMount(async () => {
    if (!orgId) return;

    try {
      // TODO: Uncomment when the proposals endpoint is available
      // const { data: proposalsData, error: proposalsError } = await apiClient.GET("/organizations/{org_id}/proposals", {
      //   params: {
      //     path: { org_id: orgId },
      //     query: { limit: 50 }
      //   }
      // });

      // if (proposalsError) {
      //   error = proposalsError && typeof proposalsError === 'object' && 'message' in proposalsError 
      //     ? String((proposalsError as any).message) 
      //     : "Failed to load proposals";
      // } else if (proposalsData) {
      //   proposals = proposalsData;
      // }

      // For now, using empty proposals array since API endpoint is not yet available
      proposals = [];

      // For now, we'll create a mock organization object since we don't have an endpoint for single org
      // In a real implementation, you'd have a separate endpoint
      organization = {
        id: orgId,
        name: "DAO Organization", // This would come from API
        slug: `dao-org-${orgId}`,
        proposals_count: proposals.length,
        chain_ids: ["ethereum", "polygon"],
        token_ids: [],
        governor_ids: [],
        metadata: null,
        endorsement_service: null,
        has_active_proposals: false,
        delegates_count: 0,
        delegates_votes_count: "0",
        token_owners_count: 0
      };

    } catch (err) {
      error = err instanceof Error ? err.message : "An unknown error occurred";
    } finally {
      loading = false;
    }
  });

  const getStatusColor = (state: string) => {
    switch (state) {
      case 'ACTIVE': return 'bg-green-100 text-green-800';
      case 'SUCCEEDED': return 'bg-blue-100 text-blue-800';
      case 'EXECUTED': return 'bg-blue-100 text-blue-800';
      case 'DEFEATED': return 'bg-red-100 text-red-800';
      case 'CANCELED': return 'bg-red-100 text-red-800';
      case 'PENDING': return 'bg-yellow-100 text-yellow-800';
      case 'QUEUED': return 'bg-yellow-100 text-yellow-800';
      case 'EXPIRED': return 'bg-secondary-100 text-secondary-800';
      default: return 'bg-secondary-100 text-secondary-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const calculateVotePercentage = (votesForStr: string, votesAgainstStr: string) => {
    const votesFor = parseInt(votesForStr) || 0;
    const votesAgainst = parseInt(votesAgainstStr) || 0;
    const total = votesFor + votesAgainst;
    if (total === 0) return { for: 0, against: 0 };
    return {
      for: Math.round((votesFor / total) * 100),
      against: Math.round((votesAgainst / total) * 100)
    };
  };
</script>

<svelte:head>
  <title>Quorum AI - {organization?.name || 'Organization'} Proposals</title>
  <meta name="description" content="View and participate in {organization?.name || 'organization'} governance proposals" />
</svelte:head>

<div class="space-y-6">
  <!-- Back Navigation -->
  <div>
    <a href="/" class="inline-flex items-center text-secondary-600 hover:text-primary-600 transition-colors duration-200">
      <svg class="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back to Organizations
    </a>
  </div>

  {#if loading}
    <div class="flex justify-center items-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      <span class="ml-3 text-secondary-600">Loading proposals...</span>
    </div>

  {:else if error}
    <div class="card bg-red-50 border-red-200">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800">Failed to load proposals</h3>
          <p class="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    </div>

  {:else}
    <!-- Organization Header -->
    {#if organization}
      <div class="card">
        <div class="flex items-start justify-between">
          <div>
            <h1 class="text-2xl font-bold text-secondary-900">{organization.name}</h1>
            {#if organization.slug}
              <p class="text-secondary-600 mt-1">@{organization.slug}</p>
            {/if}
            <div class="flex items-center space-x-6 mt-4 text-sm text-secondary-500">
              <div class="flex items-center">
                <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {organization.proposals_count} proposals
              </div>
              {#if organization.chain_ids && organization.chain_ids.length > 0}
                <div class="flex items-center">
                  <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  {organization.chain_ids.length} {organization.chain_ids.length === 1 ? 'chain' : 'chains'}
                </div>
              {/if}
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Proposals Section -->
    <div>
      <h2 class="text-xl font-semibold text-secondary-900 mb-4">Active Proposals</h2>
      
      {#if proposals.length === 0}
        <div class="card text-center py-12">
          <svg class="mx-auto h-12 w-12 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-secondary-900">No proposals</h3>
          <p class="mt-1 text-sm text-secondary-500">This organization doesn't have any proposals yet.</p>
        </div>
      {:else}
        <div class="space-y-4">
          {#each proposals as proposal}
            <div class="card hover:shadow-md transition-shadow duration-200">
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center space-x-3 mb-2">
                    <h3 class="text-lg font-medium text-secondary-900">{proposal.title}</h3>
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusColor(proposal.state)}">
                      {proposal.state}
                    </span>
                  </div>
                  
                  <p class="text-secondary-600 text-sm mb-4">{proposal.description}</p>
                  
                  <!-- Voting Progress -->
                  {#if proposal.votes_for && proposal.votes_against && (parseInt(proposal.votes_for) > 0 || parseInt(proposal.votes_against) > 0)}
                    {@const percentages = calculateVotePercentage(proposal.votes_for, proposal.votes_against)}
                    {@const votesFor = parseInt(proposal.votes_for) || 0}
                    {@const votesAgainst = parseInt(proposal.votes_against) || 0}
                    <div class="space-y-2">
                      <div class="flex justify-between items-center text-sm">
                        <span class="text-green-700">For: {votesFor} ({percentages.for}%)</span>
                        <span class="text-red-700">Against: {votesAgainst} ({percentages.against}%)</span>
                      </div>
                      <div class="w-full bg-secondary-200 rounded-full h-2">
                        <div class="bg-green-500 h-2 rounded-l-full" style="width: {percentages.for}%"></div>
                        <div class="bg-red-500 h-2 rounded-r-full -mt-2 ml-auto" style="width: {percentages.against}%"></div>
                      </div>
                    </div>
                  {:else}
                    <p class="text-sm text-secondary-500">No votes yet</p>
                  {/if}
                  
                  <div class="flex items-center justify-between mt-4 text-xs text-secondary-500">
                    <span>Created: {formatDate(proposal.created_at)}</span>
                    <span>End Block: {proposal.end_block}</span>
                  </div>
                </div>
                
                <!-- Action Buttons -->
                <div class="ml-6 flex space-x-2">
                  {#if proposal.state === 'ACTIVE'}
                    <button class="btn-primary text-sm">Vote For</button>
                    <button class="btn-secondary text-sm">Vote Against</button>
                  {/if}
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
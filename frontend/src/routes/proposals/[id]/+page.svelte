<script lang="ts">
  import { page } from '$app/stores';
  import apiClient from '$lib/api/index.js';
  import { cleanProposalTitle } from '$lib/utils/proposals.js';
  import type { components } from '$lib/api/client.js';
  import type { ExtendedProposal } from '$lib/types/dashboard.js';

  let proposalId = $page.params.id;

  // Ensure proposalId is available
  if (!proposalId) {
    throw new Error('Proposal ID is required');
  }
  let proposal = $state<ExtendedProposal | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let decision = $state<components['schemas']['AgentDecisionResponse'] | null>(null);
  let decisionLoading = $state(false);

  async function fetchProposal() {
    // Runtime assertions for fetchProposal
    console.assert(typeof proposalId === 'string', 'proposalId must be a string');
    console.assert(proposalId.length > 0, 'proposalId cannot be empty');

    loading = true;
    error = null;

    try {
      const { data, error: fetchError } = await apiClient.GET('/proposals/{proposal_id}', {
        params: {
          path: { proposal_id: proposalId! }
        }
      });

      if (fetchError) {
        const errorMessage = typeof fetchError === 'string' ? fetchError : 'Failed to fetch proposal';
        throw new Error(errorMessage);
      }

      proposal = data as ExtendedProposal;
    } catch (err) {
      console.error('Error fetching proposal:', err);
      error = err instanceof Error ? err.message : 'Failed to load proposal';
    } finally {
      loading = false;
    }
  }

  async function fetchDecisionForProposal() {
    // Runtime assertions for fetchDecisionForProposal
    console.assert(typeof proposalId === 'string', 'proposalId must be a string');
    console.assert(proposalId.length > 0, 'proposalId cannot be empty');

    decisionLoading = true;

    try {
      // Fetch recent decisions with a reasonable limit to find our proposal
      const { data, error: fetchError } = await apiClient.GET('/agent-run/decisions', {
        params: {
          query: { limit: 50 }  // Increase limit to improve chances of finding the decision
        }
      });

      if (fetchError) {
        console.warn('Failed to fetch decisions:', fetchError);
        decision = null;
        return;
      }

      // Find the decision for this specific proposal
      const proposalDecision = data?.decisions?.find(
        (d: components['schemas']['AgentDecisionResponse']) => d.proposal_id === proposalId!
      );

      decision = proposalDecision || null;
    } catch (err) {
      console.warn('Error fetching decision for proposal:', err);
      decision = null;
    } finally {
      decisionLoading = false;
    }
  }

  $effect(() => {
    fetchProposal();
    fetchDecisionForProposal();
  });
</script>

<svelte:head>
  <title>{proposal ? cleanProposalTitle(proposal.title) : 'Proposal Details'} - Quorum AI</title>
</svelte:head>

<div class="min-h-screen bg-gray-50">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    {#if loading}
      <div class="animate-pulse">
        <div class="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div class="h-4 bg-gray-200 rounded w-1/2 mb-8"></div>
        <div class="bg-white rounded-lg shadow p-6">
          <div class="h-4 bg-gray-200 rounded mb-4"></div>
          <div class="h-4 bg-gray-200 rounded mb-4"></div>
          <div class="h-4 bg-gray-200 rounded w-2/3"></div>
        </div>
      </div>
    {:else if error}
      <div class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
        <div class="flex items-start">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">Backend Unavailable</h3>
            <p class="mt-1 text-sm text-red-700">{error}</p>
            <p class="mt-1 text-sm text-red-600">Start the backend to load proposal details.</p>
          </div>
        </div>
      </div>

      <!-- Show empty proposal details structure -->
      <div class="mb-8">
        <nav class="flex mb-6" aria-label="Breadcrumb">
          <ol class="flex items-center space-x-2 text-sm">
            <li>
              <a href="/" class="text-gray-600 hover:text-gray-900">Dashboard</a>
            </li>
            <li>
              <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
              </svg>
            </li>
            <li>
              <span class="text-gray-600">Proposal Details</span>
            </li>
          </ol>
        </nav>

        <h1 class="text-4xl font-bold text-gray-900">
          Proposal #{proposalId}
        </h1>
      </div>

      <!-- Empty voting results card -->
      <div class="bg-white rounded-lg border border-gray-200 p-8">
        <h2 class="text-xl font-semibold text-gray-900 mb-6">Voting Results</h2>
        <p class="text-gray-500 italic">No voting decision available - backend unavailable</p>
      </div>
    {:else if proposal}
      <!-- Header -->
      <div class="mb-8">
        <nav class="flex mb-6" aria-label="Breadcrumb">
          <ol class="flex items-center space-x-2 text-sm">
            <li>
              <a href="/" class="text-gray-600 hover:text-gray-900">Dashboard</a>
            </li>
            <li>
              <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
              </svg>
            </li>
            <li>
              <span class="text-gray-600">Proposal Details</span>
            </li>
          </ol>
        </nav>

        <h1 class="text-4xl font-bold text-gray-900">
          {cleanProposalTitle(proposal.title)}
        </h1>
      </div>

      <!-- Main Content -->
      <div class="bg-white rounded-lg border border-gray-200 p-8">
        <h2 class="text-xl font-semibold text-gray-900 mb-6">Voting Results</h2>

        {#if decisionLoading}
          <div class="animate-pulse space-y-4">
            <div class="h-4 bg-gray-200 rounded w-20"></div>
            <div class="h-8 bg-gray-200 rounded w-24"></div>
            <div class="h-4 bg-gray-200 rounded w-32 mt-6"></div>
            <div class="h-4 bg-gray-200 rounded"></div>
            <div class="h-4 bg-gray-200 rounded"></div>
            <div class="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        {:else if decision}
          <!-- Vote -->
          <div class="mb-6">
            <div class="text-sm font-normal text-gray-900 mb-2">Vote</div>
            <span class="inline-flex items-center px-3 py-1 rounded text-sm font-medium {decision.vote === 'FOR' ? 'bg-green-100 text-green-800' : decision.vote === 'AGAINST' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}">
              {decision.vote}
            </span>
          </div>

          <!-- Reasoning -->
          <div>
            <div class="text-sm font-normal text-gray-900 mb-2">Reasoning</div>
            <div class="text-gray-700 leading-relaxed">
              {#if Array.isArray(decision.reasoning)}
                <p>{decision.reasoning.join(' ')}</p>
              {:else}
                <p>{decision.reasoning}</p>
              {/if}
            </div>
          </div>
        {:else}
          <p class="text-gray-500 italic">No voting decision available for this proposal yet.</p>
        {/if}
      </div>
    {/if}
  </div>
</div>

<script lang="ts">
  import { page } from '$app/stores';
  import apiClient from '$lib/api/index.js';
  import TopVoters from '$lib/components/TopVoters.svelte';
  import VotingIndicator from '$lib/components/dashboard/VotingIndicator.svelte';
  import { parseProposalSummary, cleanProposalTitle } from '$lib/utils/proposals.js';
  import type { components } from '$lib/api/client.js';
  import type { ExtendedProposal } from '$lib/types/dashboard.js';

  // Constants
  const TOP_VOTERS_LIMIT = 10;
  const DATE_FORMAT_OPTIONS = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  } as const;

  // CSS Classes
  const RISK_LEVEL_CLASSES = {
    LOW: 'bg-green-50 text-green-700 border-green-200',
    MEDIUM: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    HIGH: 'bg-red-50 text-red-700 border-red-200'
  } as const;

  const RECOMMENDATION_CLASSES = {
    APPROVE: 'bg-green-100 text-green-800',
    REJECT: 'bg-red-100 text-red-800',
    DEFAULT: 'bg-gray-100 text-gray-800'
  } as const;

  type Proposal = components['schemas']['Proposal'];

  let proposalId = $page.params.id;
  let proposal = $state<ExtendedProposal | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  async function fetchProposal() {
    // Runtime assertions for fetchProposal
    console.assert(typeof proposalId === 'string', 'proposalId must be a string');
    console.assert(proposalId.length > 0, 'proposalId cannot be empty');

    loading = true;
    error = null;

    try {
      const { data, error: fetchError } = await apiClient.GET('/proposals/{proposal_id}', {
        params: {
          path: { proposal_id: proposalId }
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

  function formatDate(dateInput: string | number): string {
    // Runtime assertions for formatDate
    console.assert(typeof dateInput === 'string' || typeof dateInput === 'number', 'dateInput must be a string or number');

    let date: Date;
    if (typeof dateInput === 'number') {
      // Assume timestamp is in seconds, convert to milliseconds if needed
      date = new Date(dateInput > 1e10 ? dateInput : dateInput * 1000);
    } else {
      console.assert(dateInput.length > 0, 'dateString cannot be empty');
      date = new Date(dateInput);
    }

    return date.toLocaleDateString('en-US', DATE_FORMAT_OPTIONS);
  }

  function getRiskLevelClasses(riskLevel: string): string {
    // Runtime assertions for getRiskLevelClasses
    console.assert(typeof riskLevel === 'string', 'riskLevel must be a string');
    console.assert(riskLevel.length > 0, 'riskLevel cannot be empty');

    return RISK_LEVEL_CLASSES[riskLevel as keyof typeof RISK_LEVEL_CLASSES] || RISK_LEVEL_CLASSES.MEDIUM;
  }

  function getRecommendationClasses(recommendation: string): string {
    // Runtime assertions for getRecommendationClasses
    console.assert(typeof recommendation === 'string', 'recommendation must be a string');
    console.assert(recommendation.length > 0, 'recommendation cannot be empty');

    return RECOMMENDATION_CLASSES[recommendation as keyof typeof RECOMMENDATION_CLASSES] || RECOMMENDATION_CLASSES.DEFAULT;
  }

  $effect(() => {
    fetchProposal();
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
      <div class="text-center py-12">
        <div class="text-red-600 mb-4">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-900 mb-2">Failed to load proposal</h2>
        <p class="text-gray-600 mb-4">{error}</p>
        <button
          type="button"
          onclick={fetchProposal}
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Try Again
        </button>
      </div>
    {:else if proposal}
      {@const parsedProposal = parseProposalSummary(proposal)}

      <!-- Header -->
      <div class="mb-8">
        <nav class="flex mb-4" aria-label="Breadcrumb">
          <ol class="flex items-center space-x-4">
            <li>
              <a href="/" class="text-gray-500 hover:text-gray-700">Dashboard</a>
            </li>
            <li>
              <svg class="flex-shrink-0 h-5 w-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
              </svg>
            </li>
            <li>
              <span class="text-gray-500">Proposal Details</span>
            </li>
          </ol>
        </nav>

        <div class="flex items-start justify-between">
          <div class="flex-1">
            <h1 class="text-3xl font-bold text-gray-900 mb-2">
              {cleanProposalTitle(proposal.title)}
            </h1>
            <div class="flex items-center gap-4 text-sm text-gray-500 mb-4">
              {#if proposal.dao_name}
                <span>{proposal.dao_name}</span>
                <span>•</span>
              {/if}
              <span>Created {formatDate(proposal.created_at || proposal.created)}</span>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border {getRiskLevelClasses(parsedProposal.risk_level)}">
              {parsedProposal.risk_level} Risk
            </span>
            <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium {getRecommendationClasses(parsedProposal.recommendation)}">
              {parsedProposal.recommendation}
            </span>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Left Column - Proposal Details -->
        <div class="lg:col-span-2 space-y-6">
          <!-- Summary -->
          <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">Summary</h2>
            <p class="text-gray-700 leading-relaxed">{parsedProposal.summary}</p>
          </div>

          <!-- Key Points -->
          {#if parsedProposal.key_points && parsedProposal.key_points.length > 0}
            <div class="bg-white rounded-lg shadow p-6">
              <h2 class="text-lg font-semibold text-gray-900 mb-4">Key Points</h2>
              <ul class="space-y-3">
                {#each parsedProposal.key_points as point}
                  <li class="flex items-start">
                    <div class="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3"></div>
                    <span class="text-gray-700">{point}</span>
                  </li>
                {/each}
              </ul>
            </div>
          {/if}

          <!-- Voting Results -->
          <div class="bg-white rounded-lg shadow p-6">
            <h2 class="text-lg font-semibold text-gray-900 mb-4">Voting Results</h2>
            <VotingIndicator
              votesFor={proposal.votes_for || '0'}
              votesAgainst={proposal.votes_against || '0'}
              votesAbstain={proposal.votes_abstain || '0'}
              state={proposal.state}
              endBlock={proposal.end_block}
            />
          </div>

          <!-- External Link -->
          {#if proposal.url}
            <div class="bg-white rounded-lg shadow p-6">
              <h2 class="text-lg font-semibold text-gray-900 mb-4">External Link</h2>
              <a
                href={proposal.url}
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                View on {proposal.dao_name || 'Snapshot'}
                <svg class="ml-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          {/if}
        </div>

        <!-- Right Column - Top Voters -->
        <div class="bg-white rounded-lg shadow p-6">
          <TopVoters proposalId={proposalId} limit={TOP_VOTERS_LIMIT} />
        </div>
      </div>
    {/if}
  </div>
</div>

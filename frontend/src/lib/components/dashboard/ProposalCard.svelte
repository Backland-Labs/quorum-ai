<script lang="ts">
  import { parseProposalSummary, cleanProposalTitle } from '$lib/utils/proposals.js';
  import VotingIndicator from './VotingIndicator.svelte';
  import type { components } from '$lib/api/client';
  import type { ExtendedProposal } from '$lib/types/dashboard';

  interface Props {
    proposal: components['schemas']['Proposal'];
    fullProposal?: ExtendedProposal;
    variant?: 'compact' | 'detailed';
    decision?: components['schemas']['AgentDecisionResponse'];
  }

  let { proposal, fullProposal, variant = 'compact', decision }: Props = $props();

  let isExpanded = $state(false);

  const handleToggle = () => {
    isExpanded = !isExpanded;
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleToggle();
    } else if (event.key === 'Escape') {
      isExpanded = false;
    }
  };

  function validateProps(): void {
    console.assert(proposal !== null, 'Proposal should not be null');
    console.assert(proposal !== undefined, 'Proposal should not be undefined');
  }

  
  function formatDate(dateInput: string | number): string {
    let date: Date;
    if (typeof dateInput === 'number') {
      // Assume timestamp is in seconds, convert to milliseconds if needed
      date = new Date(dateInput > 1e10 ? dateInput : dateInput * 1000);
    } else {
      date = new Date(dateInput);
    }

    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  const parsedProposal = parseProposalSummary(proposal);
  validateProps();
</script>

<div class="group relative">
  <div class="relative bg-white border border-secondary-200 rounded-lg p-5 hover:border-primary-300 hover:shadow-md transition-all duration-200">
    <!-- Header with title and badges -->
    <div 
      class="flex items-start justify-between mb-3 cursor-pointer"
      role="button"
      tabindex="0"
      aria-expanded={isExpanded}
      aria-controls="proposal-details-{proposal.id}"
      onclick={handleToggle}
      onkeydown={handleKeyDown}
    >
      <div class="flex-1">
        <h5 class="font-semibold text-secondary-900 text-base leading-tight pr-4">
          {cleanProposalTitle(proposal.title)}
        </h5>
        {#if fullProposal}
          <div class="flex items-center gap-3 mt-1 text-xs text-gray-500">
            <span>{fullProposal?.dao_name || ''}</span>
            <span>•</span>
            <span>Created {formatDate(fullProposal?.created_at || proposal.created)}</span>
          </div>
        {/if}
      </div>
      {#if decision}
        {@const voteColors = {
          FOR: 'bg-green-100 text-green-700',
          AGAINST: 'bg-red-100 text-red-700',
          ABSTAIN: 'bg-gray-100 text-gray-700'
        }}
        <div class="ml-4">
          <span class="px-2.5 py-1 text-xs font-medium rounded-full {voteColors[decision.vote]}">
            {decision.vote}
          </span>
        </div>
      {/if}
    </div>

    <!-- Voting Indicator for detailed variant -->
    {#if variant === 'detailed' && fullProposal}
      <div class="mb-4 p-4 bg-gray-50 rounded-lg">
        <VotingIndicator
          votesFor={fullProposal.votes_for || '0'}
          votesAgainst={fullProposal.votes_against || '0'}
          votesAbstain={fullProposal.votes_abstain || '0'}
          state={fullProposal.state}
          endBlock={fullProposal.end_block}
        />
      </div>
    {/if}

    <!-- Key Points (if available and detailed variant) -->
    {#if variant === 'detailed' && parsedProposal.key_points && parsedProposal.key_points.length > 0}
      <div class="mb-4">
        <h6 class="text-xs font-medium text-secondary-700 mb-2">Key Highlights</h6>
        <div class="space-y-1">
          {#each parsedProposal.key_points.slice(0, 3) as point}
            <div class="flex items-start text-xs text-secondary-600">
              <div class="flex-shrink-0 w-1.5 h-1.5 bg-primary-400 rounded-full mt-1.5 mr-2"></div>
              <span class="leading-relaxed">{point}</span>
            </div>
          {/each}
          {#if parsedProposal.key_points.length > 3}
            <div class="text-xs text-secondary-500 ml-3.5">
              +{parsedProposal.key_points.length - 3} more points
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Expandable Decision Section -->
    {#if decision && isExpanded}
      <div 
        id="proposal-details-{proposal.id}"
        class="mt-4 pt-4 border-t border-secondary-100 space-y-3 animate-in slide-in-from-top-2 duration-200"
      >
        <div>
          <h6 class="text-xs font-semibold text-secondary-700 mb-1">Reasoning</h6>
          <p class="text-sm text-secondary-600 leading-relaxed">{decision.reasoning || 'No reasoning provided'}</p>
        </div>

        {#if variant === 'detailed'}
          <div class="grid grid-cols-2 gap-3">
            <div>
              <h6 class="text-xs font-semibold text-secondary-700 mb-1">Confidence</h6>
              <div class="flex items-center gap-2">
                <div class="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    class="bg-primary-500 h-2 rounded-full transition-all duration-300"
                    style="width: {(decision.confidence * 100).toFixed(0)}%"
                  ></div>
                </div>
                <span class="text-sm font-medium text-secondary-900">{(decision.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>

            <div>
              <h6 class="text-xs font-semibold text-secondary-700 mb-1">Strategy</h6>
              <span class="inline-block px-2 py-1 text-xs font-medium bg-primary-50 text-primary-700 rounded">
                {decision.strategy_used || 'Unknown'}
              </span>
            </div>
          </div>
        {:else}
          <div>
            <h6 class="text-xs font-semibold text-secondary-700 mb-1">Strategy</h6>
            <span class="inline-block px-2 py-1 text-xs font-medium bg-primary-50 text-primary-700 rounded">
              {decision.strategy_used || 'Unknown'}
            </span>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

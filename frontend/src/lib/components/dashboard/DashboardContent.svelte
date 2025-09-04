<script lang="ts">
  import type { components } from '$lib/api/client';
  import ProposalStats from './ProposalStats.svelte';
  import RecentProposals from './RecentProposals.svelte';
  import EmptyState from './EmptyState.svelte';
  import AgentStatusWidget from './AgentStatusWidget.svelte';
  import AgentDecisionsPanel from './AgentDecisionsPanel.svelte';
  import AgentStatistics from './AgentStatistics.svelte';
  import AgentQuickActions from './AgentQuickActions.svelte';
  import { agentStatusStore } from '$lib/stores/agentStatus';
  import { onMount, onDestroy } from 'svelte';

  interface Props {
    proposals: components['schemas']['Proposal'][];
    proposalSummaries: Map<string, components['schemas']['ProposalSummary']>;
    onProposalClick: (proposalId: string) => void;
    currentSpaceId?: string | null;
  }

  let { proposals, proposalSummaries, onProposalClick, currentSpaceId = null }: Props = $props();

  function validateProps(): void {
    console.assert(typeof onProposalClick === 'function', 'onProposalClick must be a function');
  }

  function hasProposals(): boolean {
    console.assert(Array.isArray(proposals), 'Proposals should be an array');

    return proposals.length > 0;
  }

  validateProps();

  // Update store with current space ID when it changes
  $effect(() => {
    if (currentSpaceId) {
      agentStatusStore.setCurrentSpaceId(currentSpaceId);
    }
  });

  // Start polling when component mounts
  onMount(() => {
    agentStatusStore.startPolling(30000); // 30 second interval
  });

  // Stop polling when component unmounts
  onDestroy(() => {
    agentStatusStore.stopPolling();
  });
</script>

<div>
  <!-- Autonomous Voting Agent Section -->
  <div class="mb-8">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Autonomous Voting Agent</h2>

    <!-- Agent Status and Statistics Row -->
    <div class="grid gap-6 mb-6 lg:grid-cols-2">
      <AgentStatusWidget />
      <AgentStatistics />
    </div>

    <!-- Agent Quick Actions -->
    <div class="mb-6">
      <AgentQuickActions />
    </div>

    <!-- Agent Decisions Panel -->
    <div class="mb-6">
      <AgentDecisionsPanel />
    </div>
  </div>

  <!-- Proposals Section -->
  <div>
    <h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">Proposals Overview</h2>

    {#if hasProposals()}
      <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <ProposalStats
          {proposals}
        />

        <RecentProposals
          {proposals}
          {proposalSummaries}
          {onProposalClick}
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
</div>

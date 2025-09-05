<script lang="ts">
  import { goto } from "$app/navigation";
  import DashboardHeader from "$lib/components/dashboard/DashboardHeader.svelte";
  import LoadingState from "$lib/components/dashboard/LoadingState.svelte";
  import ErrorState from "$lib/components/dashboard/ErrorState.svelte";
  import DashboardContent from "$lib/components/dashboard/DashboardContent.svelte";
  import { createDashboardStore } from "$lib/hooks/useDashboardData.js";
  import apiClient from "$lib/api";

  interface Space {
    id: string;
    name: string;
  }

  const dashboardStore = createDashboardStore();
  const dashboardState = $state(dashboardStore);

  let mounted = $state(false);
  let spaces = $state<Space[]>([]);
  let spacesLoading = $state(true);

  // Fallback spaces for when API is unavailable
  const FALLBACK_SPACES: Space[] = [
    { id: 'quorum-ai.eth', name: 'Quorum AI' },
    { id: 'aave.eth', name: 'Aave' },
    { id: 'compound-governance.eth', name: 'Compound Governance' },
    { id: 'ens.eth', name: 'Ens' },
    { id: 'nounsdao.eth', name: 'Nounsdao' },
    { id: 'arbitrum-odyssey.eth', name: 'Arbitrum Odyssey' },
    { id: 'balancer.eth', name: 'Balancer' },
    { id: 'gitcoindao.eth', name: 'Gitcoindao' }
  ];

  $effect(() => {
    if (!mounted) {
      mounted = true;
      initializeDashboard();
    }
  });

  async function fetchMonitoredDaos(): Promise<void> {
    try {
      spacesLoading = true;
      const { data, error } = await apiClient.GET("/config/monitored-daos");

      if (error || !data) {
        console.error('Failed to fetch monitored DAOs:', error);
        spaces = FALLBACK_SPACES;
      } else {
        // @ts-ignore - The response type is unknown but we know the structure
        spaces = data.spaces || FALLBACK_SPACES;
      }
    } catch (err) {
      console.error('Error fetching monitored DAOs:', err);
      spaces = FALLBACK_SPACES;
    } finally {
      spacesLoading = false;
    }
  }

  async function initializeDashboard(): Promise<void> {
    console.assert(typeof dashboardStore.loadProposals === 'function', 'Dashboard store should have loadProposals method');
    console.assert(!mounted, 'Dashboard should only initialize once');

    // Fetch spaces and proposals in parallel
    await Promise.all([
      fetchMonitoredDaos(),
      dashboardStore.loadProposals()
    ]);
  }

  function handleSpaceChange(spaceId: string): void {
    console.assert(spaceId !== null, 'Space ID should not be null');
    console.assert(typeof spaceId === 'string', 'Space ID should be a string');

    dashboardStore.changeSpace(spaceId);
  }

  function handleProposalClick(proposalId: string): void {
    console.assert(typeof proposalId === 'string', 'Proposal ID must be a string');
    console.assert(proposalId.length > 0, 'Proposal ID should not be empty');

    goto(`/proposals/${proposalId}`);
  }

  // Derived values from store
  const proposals = $derived($dashboardState.allProposals);
  const currentSpaceId = $derived($dashboardState.currentSpaceId);
</script>

<svelte:head>
  <title>Dashboard - Quorum AI</title>
  <meta name="description" content="DAO governance overview, agent status, and key insights" />
</svelte:head>

<div class="space-y-6">
  <DashboardHeader
    spaceId={currentSpaceId}
    loading={$dashboardState.loading || spacesLoading}
    spaces={spaces}
    onSpaceChange={handleSpaceChange}
  />

  {#if $dashboardState.loading}
    <LoadingState />
  {:else if $dashboardState.error}
    <ErrorState error={$dashboardState.error} />
  {:else}
    <div class="mt-6">
      <DashboardContent
        {proposals}
        proposalSummaries={$dashboardState.proposalSummaries}
        onProposalClick={handleProposalClick}
        {currentSpaceId}
      />
    </div>
  {/if}
</div>

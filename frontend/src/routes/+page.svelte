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
  {:else}
    <!-- Show error banner if backend is unavailable, but still render the dashboard -->
    {#if $dashboardState.error}
      <div class="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
        <div class="flex items-start">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">Backend Unavailable</h3>
            <p class="mt-1 text-sm text-red-700">{$dashboardState.error}</p>
            <p class="mt-1 text-sm text-red-600">The dashboard will load with empty data. Start the backend to see live proposals.</p>
          </div>
        </div>
      </div>
    {/if}

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

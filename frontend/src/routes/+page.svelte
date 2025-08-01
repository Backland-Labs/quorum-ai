<script lang="ts">
  import { goto } from "$app/navigation";
  import TabNavigation from "$lib/components/TabNavigation.svelte";
  import DashboardHeader from "$lib/components/dashboard/DashboardHeader.svelte";
  import LoadingState from "$lib/components/dashboard/LoadingState.svelte";
  import ErrorState from "$lib/components/dashboard/ErrorState.svelte";
  import OverviewTab from "$lib/components/dashboard/OverviewTab.svelte";
  import ProposalsTab from "$lib/components/dashboard/ProposalsTab.svelte";
  import ActivityTab from "$lib/components/dashboard/ActivityTab.svelte";
  import { createDashboardStore } from "$lib/hooks/useDashboardData.js";
  import type { TabType, Tab } from "$lib/types/dashboard.js";

  const dashboardStore = createDashboardStore();
  const dashboardState = $state(dashboardStore);

  const tabs: Tab[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'proposals', label: 'Proposals' },
    { id: 'activity', label: 'Activity' }
  ];

  let mounted = $state(false);

  $effect(() => {
    if (!mounted) {
      mounted = true;
      initializeDashboard();
    }
  });

  function initializeDashboard(): void {
    console.assert(typeof dashboardStore.loadProposals === 'function', 'Dashboard store should have loadProposals method');
    console.assert(!mounted, 'Dashboard should only initialize once');

    dashboardStore.loadProposals();
  }

  function handleTabChange(tabId: TabType): void {
    console.assert(typeof tabId === 'string', 'Tab ID must be a string');
    console.assert(['overview', 'proposals', 'activity'].includes(tabId), 'Tab ID must be valid');

    dashboardStore.changeTab(tabId);
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

  function handleViewAllProposals(): void {
    console.assert(typeof dashboardStore.changeTab === 'function', 'Dashboard store should have changeTab method');

    dashboardStore.changeTab('proposals');
  }

  // Derived values from store
  const proposals = $derived($dashboardState.allProposals);
  const currentSpaceId = $derived($dashboardState.currentSpaceId);
</script>

<svelte:head>
  <title>Dashboard - Quorum AI</title>
  <meta name="description" content="DAO governance dashboard with proposals, activity, and analytics" />
</svelte:head>

<div class="space-y-6">
  <DashboardHeader
    spaceId={currentSpaceId}
    loading={$dashboardState.loading}
    onSpaceChange={handleSpaceChange}
  />

  {#if $dashboardState.loading}
    <LoadingState />
  {:else if $dashboardState.error}
    <ErrorState error={$dashboardState.error} />
  {:else}
    <TabNavigation
      {tabs}
      activeTab={$dashboardState.activeTab}
      onTabChange={handleTabChange}
    />

    <div class="mt-6">
      {#if $dashboardState.activeTab === 'overview'}
        <OverviewTab
          {proposals}
          proposalSummaries={$dashboardState.proposalSummaries}
          onProposalClick={handleProposalClick}
          onViewAllProposals={handleViewAllProposals}
          {currentSpaceId}
        />
      {:else if $dashboardState.activeTab === 'proposals'}
        <ProposalsTab
          {proposals}
          proposalSummaries={$dashboardState.proposalSummaries}
          {dashboardStore}
        />
      {:else if $dashboardState.activeTab === 'activity'}
        <ActivityTab />
      {/if}
    </div>
  {/if}
</div>

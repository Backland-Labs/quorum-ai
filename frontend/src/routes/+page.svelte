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
    console.assert(typeof dashboardStore.loadOrganizations === 'function', 'Dashboard store should have loadOrganizations method');
    console.assert(!mounted, 'Dashboard should only initialize once');
    
    dashboardStore.loadOrganizations();
  }

  function handleTabChange(tabId: TabType): void {
    console.assert(typeof tabId === 'string', 'Tab ID must be a string');
    console.assert(['overview', 'proposals', 'activity'].includes(tabId), 'Tab ID must be valid');
    
    dashboardStore.changeTab(tabId);
  }

  function handleOrganizationChange(organization: any): void {
    console.assert(organization !== null, 'Organization should not be null');
    console.assert(typeof organization === 'object', 'Organization should be an object');
    
    dashboardStore.changeOrganization(organization);
  }

  function handleOrganizationClick(orgId: string): void {
    console.assert(typeof orgId === 'string', 'Organization ID must be a string');
    console.assert(orgId.length > 0, 'Organization ID should not be empty');
    
    goto(`/organizations/${orgId}`);
  }

  function handleViewAllProposals(): void {
    console.assert(typeof dashboardStore.changeTab === 'function', 'Dashboard store should have changeTab method');
    
    dashboardStore.changeTab('proposals');
  }

  // Derived values from store
  const currentOrgData = $derived($dashboardState.selectedOrganization 
    ? $dashboardState.organizationsWithProposals.find(org => org.organization.id === $dashboardState.selectedOrganization?.id) || null
    : null);

  const organizations = $derived($dashboardState.organizationsWithProposals.map(org => org.organization));
</script>

<svelte:head>
  <title>Dashboard - Quorum AI</title>
  <meta name="description" content="DAO governance dashboard with proposals, activity, and analytics" />
</svelte:head>

<div class="space-y-6">
  <DashboardHeader 
    {organizations}
    selectedOrganization={$dashboardState.selectedOrganization}
    loading={$dashboardState.loading}
    onOrganizationChange={handleOrganizationChange}
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
          {currentOrgData}
          onOrganizationClick={handleOrganizationClick}
          onViewAllProposals={handleViewAllProposals}
        />
      {:else if $dashboardState.activeTab === 'proposals'}
        <ProposalsTab {currentOrgData} />
      {:else if $dashboardState.activeTab === 'activity'}
        <ActivityTab />
      {/if}
    </div>
  {/if}
</div>
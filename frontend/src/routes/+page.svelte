<script lang="ts">
  import { goto } from "$app/navigation";
  import apiClient from "$lib/api";
  import OrganizationDropdown from "$lib/components/OrganizationDropdown.svelte";
  import TabNavigation from "$lib/components/TabNavigation.svelte";
  import type { TabType, Organization, OrganizationWithProposals, Tab } from "$lib/types/dashboard.js";

  let organizationsWithProposals: OrganizationWithProposals[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);
  let activeTab: TabType = $state('overview');
  let selectedOrganization: Organization | null = $state(null);

  const tabs: Tab[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'proposals', label: 'Proposals' },
    { id: 'activity', label: 'Activity' }
  ];

  const loadOrganizations = async () => {
    console.log("Loading organizations");
    const { data, error: apiError } = await apiClient.GET("/organizations");

    if (apiError) {
      error = apiError && typeof apiError === 'object' && 'message' in apiError 
        ? String((apiError as any).message)
        : "Failed to load organizations";
    } else if (data) {
      organizationsWithProposals = data.organizations;
      // Set first organization as default if none selected
      if (organizationsWithProposals.length > 0 && !selectedOrganization) {
        selectedOrganization = organizationsWithProposals[0].organization;
      }
    }
    loading = false;
  };

  let mounted = $state(false);

  $effect(() => {
    if (!mounted) {
      mounted = true;
      loadOrganizations();
    }
  });

  const handleTabChange = (tabId: TabType) => {
    activeTab = tabId;
  };

  const handleOrganizationChange = (organization: Organization) => {
    selectedOrganization = organization;
  };

  const handleOrganizationClick = (orgId: string) => {
    goto(`/organizations/${orgId}`);
  };

  // Get current organization data
  const currentOrgData = $derived(selectedOrganization 
    ? organizationsWithProposals.find(org => org.organization.id === selectedOrganization?.id)
    : null);

  // Get organizations list for dropdown
  const organizations = $derived(organizationsWithProposals.map(org => org.organization));
</script>

<svelte:head>
  <title>Dashboard - Quorum AI</title>
  <meta name="description" content="DAO governance dashboard with proposals, activity, and analytics" />
</svelte:head>

<div class="space-y-6">
  <!-- Dashboard Header -->
  <div class="flex items-center justify-between">
    <h1 class="text-3xl font-bold text-secondary-900">Dashboard</h1>
    
    <!-- Organization Dropdown -->
    <div class="flex items-center">
      {#if !loading && organizations.length > 0}
        <OrganizationDropdown 
          {organizations}
          {selectedOrganization}
          onOrganizationChange={handleOrganizationChange}
        />
      {:else if loading}
        <div class="animate-pulse bg-secondary-200 h-10 w-64 rounded-md"></div>
      {/if}
    </div>
  </div>

  <!-- Loading State -->
  {#if loading}
    <div class="flex justify-center items-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      <span class="ml-3 text-secondary-600">Loading dashboard...</span>
    </div>
  
  <!-- Error State -->
  {:else if error}
    <div class="card bg-red-50 border-red-200">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3">
          <h3 class="text-sm font-medium text-red-800">Failed to load dashboard</h3>
          <p class="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    </div>
  
  <!-- Dashboard Content -->
  {:else}
    <!-- Tab Navigation -->
    <TabNavigation 
      {tabs}
      {activeTab}
      onTabChange={handleTabChange}
    />

    <!-- Tab Content -->
    <div class="mt-6">
      {#if activeTab === 'overview'}
        <div id="tab-panel-overview" role="tabpanel" aria-labelledby="tab-overview">
          {#if currentOrgData}
            {@const org = currentOrgData.organization}
            <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              <!-- Organization Overview Card -->
              <div class="card">
                <div class="flex items-start justify-between">
                  <div class="flex-1">
                    <h3 class="text-lg font-semibold text-secondary-900">
                      {org.name}
                    </h3>
                    {#if org.slug}
                      <p class="text-secondary-600 text-sm mt-1">
                        @{org.slug}
                      </p>
                    {/if}
                  </div>
                  <button
                    class="ml-4 flex-shrink-0 text-primary-600 hover:text-primary-700"
                    onclick={() => handleOrganizationClick(org.id)}
                    aria-label="View {org.name} details"
                  >
                    <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
                
                <div class="mt-4 grid grid-cols-2 gap-4 text-sm">
                  <div class="flex items-center">
                    <svg class="h-4 w-4 mr-2 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span class="text-secondary-600">{org.proposals_count} proposals</span>
                  </div>
                  {#if org.chain_ids && org.chain_ids.length > 0}
                    <div class="flex items-center">
                      <svg class="h-4 w-4 mr-2 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                      </svg>
                      <span class="text-secondary-600">{org.chain_ids?.length || 0} {(org.chain_ids?.length || 0) === 1 ? 'chain' : 'chains'}</span>
                    </div>
                  {/if}
                  <div class="flex items-center">
                    <svg class="h-4 w-4 mr-2 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                    </svg>
                    <span class="text-secondary-600">{org.delegates_count.toLocaleString()} delegates</span>
                  </div>
                  <div class="flex items-center">
                    <svg class="h-4 w-4 mr-2 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                    <span class="text-secondary-600">{org.token_owners_count.toLocaleString()} token holders</span>
                  </div>
                </div>
              </div>

              <!-- Recent Proposals -->
              {#if currentOrgData.proposals && currentOrgData.proposals.length > 0}
                <div class="card lg:col-span-2">
                  <h4 class="text-lg font-semibold text-secondary-900 mb-4">Recent Proposals</h4>
                  <div class="space-y-4">
                    {#each currentOrgData.proposals.slice(0, 3) as proposal}
                      <div class="border-b border-secondary-200 pb-4 last:border-b-0 last:pb-0">
                        <div class="flex items-start justify-between">
                          <div class="flex-1">
                            <h5 class="font-medium text-secondary-900">{proposal.title}</h5>
                            <p class="text-sm text-secondary-600 mt-1">{proposal.summary}</p>
                            <div class="flex items-center gap-2 mt-2">
                              <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                                {proposal.risk_level === 'LOW' ? 'bg-green-100 text-green-800' : 
                                 proposal.risk_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' : 
                                 'bg-red-100 text-red-800'}">
                                {proposal.risk_level}
                              </span>
                              <span class="text-secondary-400">•</span>
                              <span class="text-sm text-secondary-600">{proposal.recommendation}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    {/each}
                  </div>
                </div>
              {/if}
            </div>
          {:else}
            <div class="text-center py-12">
              <svg class="mx-auto h-12 w-12 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <h3 class="mt-2 text-sm font-medium text-secondary-900">No organization selected</h3>
              <p class="mt-1 text-sm text-secondary-500">Choose an organization from the dropdown to view its overview.</p>
            </div>
          {/if}
        </div>
      
      {:else if activeTab === 'proposals'}
        <div id="tab-panel-proposals" role="tabpanel" aria-labelledby="tab-proposals">
          {#if currentOrgData}
            <div class="card">
              <h3 class="text-lg font-semibold text-secondary-900 mb-4">
                All Proposals for {currentOrgData.organization.name}
              </h3>
              {#if currentOrgData.proposals && currentOrgData.proposals.length > 0}
                <div class="space-y-4">
                  {#each currentOrgData.proposals as proposal}
                    <div class="border border-secondary-200 rounded-lg p-4 hover:border-primary-300 transition-colors duration-200">
                      <div class="flex items-start justify-between">
                        <div class="flex-1">
                          <h4 class="font-medium text-secondary-900">{proposal.title}</h4>
                          <p class="text-sm text-secondary-600 mt-2">{proposal.summary}</p>
                          
                          {#if proposal.key_points && proposal.key_points.length > 0}
                            <div class="mt-3">
                              <h5 class="text-xs font-medium text-secondary-700 mb-1">Key Points:</h5>
                              <ul class="text-xs text-secondary-600 space-y-1">
                                {#each proposal.key_points as point}
                                  <li class="flex items-start">
                                    <span class="text-primary-400 mr-1">•</span>
                                    {point}
                                  </li>
                                {/each}
                              </ul>
                            </div>
                          {/if}
                          
                          <div class="flex items-center gap-3 mt-3">
                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                              {proposal.risk_level === 'LOW' ? 'bg-green-100 text-green-800' : 
                               proposal.risk_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' : 
                               'bg-red-100 text-red-800'}">
                              {proposal.risk_level} Risk
                            </span>
                            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                              {proposal.recommendation === 'APPROVE' ? 'bg-green-100 text-green-800' : 
                               proposal.recommendation === 'REJECT' ? 'bg-red-100 text-red-800' : 
                               'bg-gray-100 text-gray-800'}">
                              {proposal.recommendation}
                            </span>
                            <span class="text-xs text-secondary-500">
                              Confidence: {Math.round(proposal.confidence_score * 100)}%
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              {:else}
                <div class="text-center py-8">
                  <svg class="mx-auto h-8 w-8 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p class="mt-2 text-sm text-secondary-500">No proposals available for this organization.</p>
                </div>
              {/if}
            </div>
          {:else}
            <div class="text-center py-12">
              <svg class="mx-auto h-12 w-12 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 class="mt-2 text-sm font-medium text-secondary-900">No organization selected</h3>
              <p class="mt-1 text-sm text-secondary-500">Choose an organization from the dropdown to view its proposals.</p>
            </div>
          {/if}
        </div>
      
      {:else if activeTab === 'activity'}
        <div id="tab-panel-activity" role="tabpanel" aria-labelledby="tab-activity">
          <div class="card">
            <div class="text-center py-12">
              <svg class="mx-auto h-12 w-12 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 00-2 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6a2 2 0 00-2-2H5a2 2 0 01-2-2V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2z" />
              </svg>
              <h3 class="mt-2 text-sm font-medium text-secondary-900">Activity Feed Coming Soon</h3>
              <p class="mt-1 text-sm text-secondary-500">
                We're working on bringing you real-time activity feeds for DAO governance events.
              </p>
            </div>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</div>
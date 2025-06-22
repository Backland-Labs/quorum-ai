<script lang="ts">
  import { onMount } from "svelte";
  import apiClient from "$lib/api";
  import type { components } from "$lib/api/client";

  let organizations: components["schemas"]["Organization"][] = [];
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    const { data, error: apiError } = await apiClient.GET("/organizations", {
      params: {
        query: {
          limit: 20,
        },
      },
    });

    if (apiError) {
      error = apiError && typeof apiError === 'object' && 'message' in apiError 
        ? String((apiError as any).message)
        : "Failed to load organizations";
    } else if (data) {
      organizations = data.organizations;
    }
    loading = false;
  });

  const handleOrganizationClick = (orgId: string) => {
    window.location.href = `/organizations/${orgId}`;
  };
</script>

<svelte:head>
  <title>Quorum AI - DAO Organizations</title>
  <meta name="description" content="Explore and manage decentralized autonomous organizations" />
</svelte:head>

<div class="space-y-6">
  <!-- Header Section -->
  <div class="text-center">
    <h1 class="text-3xl font-bold text-secondary-900 mb-2">DAO Organizations</h1>
    <p class="text-secondary-600 max-w-2xl mx-auto">
      Discover and participate in decentralized autonomous organizations. View proposals, cast votes, and shape the future of decentralized governance.
    </p>
  </div>

  <!-- Loading State -->
  {#if loading}
    <div class="flex justify-center items-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      <span class="ml-3 text-secondary-600">Loading organizations...</span>
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
          <h3 class="text-sm font-medium text-red-800">Failed to load organizations</h3>
          <p class="text-sm text-red-700 mt-1">{error}</p>
        </div>
      </div>
    </div>
  
  <!-- Organizations Grid -->
  {:else}
    <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {#each organizations as org}
        <div 
          class="card hover:shadow-md transition-shadow duration-200 cursor-pointer group"
          on:click={() => handleOrganizationClick(org.id)}
          on:keydown={(e) => e.key === 'Enter' && handleOrganizationClick(org.id)}
          role="button"
          tabindex="0"
          aria-label="View {org.name} organization details"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-secondary-900 group-hover:text-primary-600 transition-colors duration-200">
                {org.name}
              </h3>
              {#if org.description}
                <p class="text-secondary-600 text-sm mt-1 line-clamp-2">
                  {org.description}
                </p>
              {/if}
            </div>
            <div class="ml-4 flex-shrink-0">
              <svg class="h-5 w-5 text-secondary-400 group-hover:text-primary-500 transition-colors duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </div>
          
          <div class="mt-4 flex items-center justify-between text-sm text-secondary-500">
            <div class="flex items-center">
              <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {org.proposals_count} proposals
            </div>
            {#if org.members_count}
              <div class="flex items-center">
                <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                </svg>
                {org.members_count} members
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

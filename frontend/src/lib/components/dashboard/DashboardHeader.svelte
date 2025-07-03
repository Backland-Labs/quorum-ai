<script lang="ts">
  import type { Organization } from '$lib/types/dashboard.js';
  import OrganizationDropdown from '$lib/components/OrganizationDropdown.svelte';

  interface Props {
    organizations: Organization[];
    selectedOrganization: Organization | null;
    loading: boolean;
    onOrganizationChange: (org: Organization) => void;
  }

  let {
    organizations,
    selectedOrganization,
    loading,
    onOrganizationChange
  }: Props = $props();

  function validateProps(): void {
    console.assert(Array.isArray(organizations), 'Organizations must be an array');
    console.assert(typeof loading === 'boolean', 'Loading must be a boolean');
  }

  function shouldShowDropdown(): boolean {
    console.assert(typeof loading === 'boolean', 'Loading must be a boolean');
    console.assert(Array.isArray(organizations), 'Organizations must be an array');

    return !loading && organizations.length > 0;
  }

  validateProps();
</script>

<div class="flex items-center justify-between">
  <h1 class="text-3xl font-bold text-secondary-900">Dashboard</h1>

  <div class="flex items-center">
    {#if shouldShowDropdown()}
      <OrganizationDropdown
        {organizations}
        {selectedOrganization}
        onOrganizationChange={onOrganizationChange}
      />
    {:else if loading}
      <div class="animate-pulse bg-secondary-200 h-10 w-64 rounded-md"></div>
    {/if}
  </div>
</div>

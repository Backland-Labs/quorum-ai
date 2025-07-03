<script lang="ts">
  import type { OrganizationDropdownProps } from '../types/dashboard.js';

  interface Props extends OrganizationDropdownProps {}

  let {
    organizations,
    selectedOrganization,
    onOrganizationChange,
    loading = false
  }: Props = $props();

  let isOpen = $state(false);

  const handleToggle = () => {
    if (!loading && organizations.length > 0) {
      isOpen = !isOpen;
    }
  };

  const handleSelect = (organization: (typeof organizations)[0]) => {
    onOrganizationChange(organization);
    isOpen = false;
  };

  const handleKeydown = (event: KeyboardEvent, organization?: (typeof organizations)[0]) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (organization) {
        handleSelect(organization);
      } else {
        handleToggle();
      }
    } else if (event.key === 'Escape') {
      isOpen = false;
    }
  };
</script>

<div class="relative">
  <button
    type="button"
    class="inline-flex items-center justify-between w-64 px-4 py-2 text-sm font-medium
           text-secondary-700 bg-white border border-secondary-300 rounded-md
           hover:bg-secondary-50 focus:outline-none focus:ring-2 focus:ring-primary-500
           focus:border-primary-500 transition-colors duration-200
           {loading ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}"
    onclick={handleToggle}
    onkeydown={handleKeydown}
    aria-haspopup="listbox"
    aria-expanded={isOpen}
    aria-controls="organization-listbox"
    aria-label="Select organization"
    role="combobox"
    disabled={loading || organizations.length === 0}
  >
    <span class="truncate">
      {#if loading}
        Loading organizations...
      {:else if selectedOrganization}
        {selectedOrganization.name}
      {:else if organizations.length === 0}
        No organizations available
      {:else}
        Select organization
      {/if}
    </span>
    <svg
      class="ml-2 h-4 w-4 text-secondary-400 transition-transform duration-200
             {isOpen ? 'rotate-180' : 'rotate-0'}"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
    </svg>
  </button>

  {#if isOpen && organizations.length > 0}
    <div
      class="absolute z-50 w-full mt-1 bg-white border border-secondary-300 rounded-md shadow-lg
             max-h-60 overflow-auto"
      id="organization-listbox"
      role="listbox"
    >
      {#each organizations as organization (organization.id)}
        <button
          type="button"
          class="flex items-center justify-between w-full px-4 py-2 text-sm text-secondary-700
                 hover:bg-primary-50 hover:text-primary-600 focus:outline-none focus:bg-primary-50
                 focus:text-primary-600 transition-colors duration-200
                 {selectedOrganization?.id === organization.id ? 'bg-primary-50 text-primary-600' : ''}"
          onclick={() => handleSelect(organization)}
          onkeydown={(e) => handleKeydown(e, organization)}
          role="option"
          aria-selected={selectedOrganization?.id === organization.id}
        >
          <div class="flex flex-col items-start">
            <span class="font-medium">{organization.name}</span>
            {#if organization.slug}
              <span class="text-xs text-secondary-500">@{organization.slug}</span>
            {/if}
          </div>
          <div class="flex items-center text-xs text-secondary-500">
            <svg class="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {organization.proposals_count}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

{#if isOpen}
  <div
    class="fixed inset-0 z-40"
    onclick={() => isOpen = false}
    onkeydown={(e) => e.key === 'Escape' && (isOpen = false)}
    aria-hidden="true"
  ></div>
{/if}

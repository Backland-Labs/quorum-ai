<script lang="ts">
  import type { Organization } from '$lib/types/dashboard.js';

  interface Props {
    organization: Organization;
    onViewDetails: (orgId: string) => void;
  }

  let { organization, onViewDetails }: Props = $props();

  function validateProps(): void {
    console.assert(organization !== null, 'Organization should not be null');
    console.assert(typeof organization === 'object', 'Organization should be an object');
  }

  function formatChainCount(chainIds?: string[]): string {
    console.assert(chainIds === undefined || Array.isArray(chainIds), 'Chain IDs must be array or undefined');

    const count = chainIds?.length || 0;
    return `${count} ${count === 1 ? 'chain' : 'chains'}`;
  }

  function formatNumber(num: number): string {
    console.assert(typeof num === 'number', 'Number must be a number type');
    console.assert(num >= 0, 'Number should not be negative');

    return num.toLocaleString();
  }

  validateProps();
</script>

<div class="card">
  <div class="flex items-start justify-between">
    <div class="flex-1">
      <h3 class="text-lg font-semibold text-secondary-900">
        {organization.name}
      </h3>
      {#if organization.slug}
        <p class="text-secondary-600 text-sm mt-1">
          @{organization.slug}
        </p>
      {/if}
    </div>
    <button
      class="ml-4 flex-shrink-0 text-primary-600 hover:text-primary-700"
      onclick={() => onViewDetails(organization.id)}
      aria-label="View {organization.name} details"
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
      <span class="text-secondary-600">{organization.proposals_count} proposals</span>
    </div>

    {#if organization.chain_ids && organization.chain_ids.length > 0}
      <div class="flex items-center">
        <svg class="h-4 w-4 mr-2 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
        <span class="text-secondary-600">{formatChainCount(organization.chain_ids)}</span>
      </div>
    {/if}

    <div class="flex items-center">
      <svg class="h-4 w-4 mr-2 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
      </svg>
      <span class="text-secondary-600">{formatNumber(organization.delegates_count)} delegates</span>
    </div>

    <div class="flex items-center">
      <svg class="h-4 w-4 mr-2 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
      <span class="text-secondary-600">{formatNumber(organization.token_owners_count)} token holders</span>
    </div>
  </div>
</div>

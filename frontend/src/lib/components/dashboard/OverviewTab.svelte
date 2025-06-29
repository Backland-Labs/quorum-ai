<script lang="ts">
  import type { OrganizationWithProposals } from '$lib/types/dashboard.js';
  import OrganizationStats from './OrganizationStats.svelte';
  import RecentProposals from './RecentProposals.svelte';
  import EmptyState from './EmptyState.svelte';
  
  interface Props {
    currentOrgData: OrganizationWithProposals | null;
    onOrganizationClick: (orgId: string) => void;
    onViewAllProposals: () => void;
  }
  
  let { currentOrgData, onOrganizationClick, onViewAllProposals }: Props = $props();
  
  function validateProps(): void {
    console.assert(typeof onOrganizationClick === 'function', 'onOrganizationClick must be a function');
    console.assert(typeof onViewAllProposals === 'function', 'onViewAllProposals must be a function');
  }
  
  function hasOrganizationData(): boolean {
    console.assert(currentOrgData === null || typeof currentOrgData === 'object', 'Organization data should be null or object');
    
    return currentOrgData !== null;
  }
  
  validateProps();
</script>

<div id="tab-panel-overview" role="tabpanel" aria-labelledby="tab-overview">
  {#if hasOrganizationData() && currentOrgData}
    <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <OrganizationStats 
        organization={currentOrgData.organization}
        onViewDetails={onOrganizationClick}
      />
      
      <RecentProposals 
        organizationData={currentOrgData}
        onViewAllProposals={onViewAllProposals}
      />
    </div>
  {:else}
    <EmptyState 
      title="No organization selected"
      description="Choose an organization from the dropdown to view its overview."
      icon="organization"
    />
  {/if}
</div>
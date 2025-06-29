<script lang="ts">
  import type { OrganizationWithProposals } from '$lib/types/dashboard.js';
  import ProposalCard from './ProposalCard.svelte';
  import EmptyState from './EmptyState.svelte';
  
  interface Props {
    currentOrgData: OrganizationWithProposals | null;
  }
  
  let { currentOrgData }: Props = $props();
  
  function validateProps(): void {
    console.assert(currentOrgData === null || typeof currentOrgData === 'object', 'Organization data should be null or object');
  }
  
  function hasOrganizationData(): boolean {
    console.assert(currentOrgData === null || typeof currentOrgData === 'object', 'Organization data should be null or object');
    
    return currentOrgData !== null;
  }
  
  function hasProposals(): boolean {
    console.assert(hasOrganizationData(), 'Should have organization data when checking proposals');
    console.assert(currentOrgData !== null, 'Current org data should not be null');
    
    return currentOrgData !== null && currentOrgData.proposals && currentOrgData.proposals.length > 0;
  }
  
  validateProps();
</script>

<div id="tab-panel-proposals" role="tabpanel" aria-labelledby="tab-proposals">
  {#if hasOrganizationData() && currentOrgData}
    <div class="card">
      <h3 class="text-lg font-semibold text-secondary-900 mb-4">
        All Proposals for {currentOrgData.organization.name}
      </h3>
      
      {#if hasProposals()}
        <div class="space-y-4">
          {#each currentOrgData.proposals as proposal}
            <ProposalCard {proposal} variant="compact" />
          {/each}
        </div>
      {:else}
        <EmptyState 
          title="No proposals available"
          description="No proposals available for this organization."
          icon="proposals"
        />
      {/if}
    </div>
  {:else}
    <EmptyState 
      title="No organization selected"
      description="Choose an organization from the dropdown to view its proposals."
      icon="organization"
    />
  {/if}
</div>
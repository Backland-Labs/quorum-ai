<script lang="ts">
  interface Props {
    spaceId: string;
    loading: boolean;
    onSpaceChange: (spaceId: string) => void;
  }

  let {
    spaceId,
    loading,
    onSpaceChange
  }: Props = $props();

  // Predefined list of Snapshot spaces - extracted as configuration
  const SNAPSHOT_SPACES = [
    { id: 'uniswapgovernance.eth', name: 'Uniswap' },
    { id: 'aave.eth', name: 'Aave' },
    { id: 'compound-governance.eth', name: 'Compound' },
    { id: 'snapshot.dcl.eth', name: 'Decentraland' },
    { id: 'gitcoindao.eth', name: 'Gitcoin' }
  ] as const;

  function handleSpaceSelect(event: Event): void {
    const target = event.target as HTMLSelectElement;
    onSpaceChange(target.value);
  }
</script>

<div class="flex items-center justify-between">
  <h1 class="text-3xl font-bold text-secondary-900">Dashboard</h1>

  <div class="flex items-center gap-4">
    <label for="space-select" class="text-sm font-medium text-secondary-700">
      Snapshot Space:
    </label>
    {#if !loading}
      <select
        id="space-select"
        value={spaceId}
        onchange={handleSpaceSelect}
        class="px-4 py-2 border border-secondary-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
      >
        {#each SNAPSHOT_SPACES as space}
          <option value={space.id}>{space.name}</option>
        {/each}
      </select>
    {:else}
      <div class="animate-pulse bg-secondary-200 h-10 w-48 rounded-md"></div>
    {/if}
  </div>
</div>

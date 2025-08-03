<script lang="ts">
  interface Space {
    id: string;
    name: string;
  }

  interface Props {
    spaceId: string;
    loading: boolean;
    spaces: Space[];
    onSpaceChange: (spaceId: string) => void;
  }

  let {
    spaceId,
    loading,
    spaces,
    onSpaceChange
  }: Props = $props();

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
        {#each spaces as space}
          <option value={space.id}>{space.name}</option>
        {/each}
      </select>
    {:else}
      <div class="animate-pulse bg-secondary-200 h-10 w-48 rounded-md"></div>
    {/if}
  </div>
</div>

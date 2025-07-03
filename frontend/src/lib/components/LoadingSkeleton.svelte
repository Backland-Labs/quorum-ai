<script lang="ts">
  interface Props {
    height?: string;
    width?: string;
    rounded?: boolean;
    count?: number;
    className?: string;
  }

  let { height = 'h-4', width = 'w-full', rounded = false, count = 1, className = '' }: Props = $props();

  const baseClasses = 'bg-secondary-200 animate-pulse';
  const roundedClasses = rounded ? 'rounded-lg' : '';
  const combinedClasses = `${baseClasses} ${height} ${width} ${roundedClasses} ${className}`.trim();
</script>

{#if count === 1}
  <div
    class={combinedClasses}
    data-testid="loading-skeleton"
    aria-label="Loading content"
  ></div>
{:else}
  {#each Array(count) as _, i}
    <div
      class={combinedClasses}
      class:mb-2={i < count - 1}
      data-testid="loading-skeleton"
      aria-label="Loading content"
    ></div>
  {/each}
{/if}

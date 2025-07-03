<script lang="ts">
  interface Props {
    title: string;
    value: string;
    description?: string;
    icon?: string;
    loading?: boolean;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
  }

  let { title, value, description, icon, loading = false, trend, trendValue }: Props = $props();

  const getIconSvg = (iconName: string) => {
    switch (iconName) {
      case 'users':
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />`;
      case 'document':
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />`;
      case 'chart':
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />`;
      case 'activity':
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />`;
      default:
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />`;
    }
  };

  const getTrendIcon = (direction: 'up' | 'down' | 'neutral') => {
    switch (direction) {
      case 'up':
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 11l5-5m0 0l5 5m-5-5v12" />`;
      case 'down':
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 13l-5 5m0 0l-5-5m5 5V6" />`;
      default:
        return `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14" />`;
    }
  };

  const getTrendColor = (direction: 'up' | 'down' | 'neutral') => {
    switch (direction) {
      case 'up':
        return 'text-green-600';
      case 'down':
        return 'text-red-600';
      default:
        return 'text-secondary-600';
    }
  };
</script>

<div
  class="bg-white rounded-lg shadow-sm border border-secondary-200 p-6 transition-shadow duration-200 hover:shadow-md"
  class:animate-pulse={loading}
  data-testid="metric-card"
>
  <div class="flex items-center justify-between">
    <div class="flex-1">
      <div class="flex items-center space-x-3">
        {#if icon}
          <div class="flex-shrink-0" data-testid="metric-icon">
            <svg class="h-5 w-5 text-secondary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {@html getIconSvg(icon)}
            </svg>
          </div>
        {/if}
        <div>
          <p class="text-sm font-medium text-secondary-600">{title}</p>
          {#if description}
            <p class="text-xs text-secondary-500 mt-1">{description}</p>
          {/if}
        </div>
      </div>

      <div class="mt-3 flex items-baseline">
        <p class="text-2xl font-semibold text-secondary-900" class:bg-secondary-200={loading} class:text-transparent={loading}>
          {value}
        </p>

        {#if trend && trendValue}
          <div class="ml-2 flex items-center text-sm {getTrendColor(trend)}" data-testid="trend-indicator">
            <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {@html getTrendIcon(trend)}
            </svg>
            <span>{trendValue}</span>
          </div>
        {/if}
      </div>
    </div>
  </div>
</div>

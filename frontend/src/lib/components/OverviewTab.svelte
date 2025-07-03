<script lang="ts">
  import { onMount } from 'svelte';
  import apiClient from '$lib/api';
  import type { components } from '$lib/api/client';
  import MetricCard from './MetricCard.svelte';
  import LoadingSkeleton from './LoadingSkeleton.svelte';

  interface Props {
    organizationId: string;
  }

  let { organizationId }: Props = $props();

  type OrganizationOverviewResponse = components["schemas"]["OrganizationOverviewResponse"];

  let overviewData: OrganizationOverviewResponse | null = $state(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatPercentage = (rate: number): string => {
    return `${Math.round(rate * 100)}%`;
  };

  const getStatusDisplayName = (status: string): string => {
    const statusMap: Record<string, string> = {
      'ACTIVE': 'Active',
      'SUCCEEDED': 'Succeeded',
      'DEFEATED': 'Defeated',
      'PENDING': 'Pending',
      'EXECUTED': 'Executed',
      'CANCELED': 'Canceled',
      'EXPIRED': 'Expired',
      'QUEUED': 'Queued'
    };
    return statusMap[status] || status;
  };

  const fetchOverviewData = async (orgId: string) => {
    if (!orgId) return;

    loading = true;
    error = null;

    try {
      const { data, error: apiError } = await apiClient.GET("/organizations/{org_id}/overview", {
        params: {
          path: { org_id: orgId }
        }
      });

      if (apiError) {
        error = apiError && typeof apiError === 'object' && 'message' in apiError
          ? String((apiError as any).message)
          : "Failed to fetch organization data";
      } else if (data) {
        overviewData = data;
      }
    } catch (err) {
      error = err instanceof Error ? err.message : "An unknown error occurred";
    } finally {
      loading = false;
    }
  };

  const handleRetry = () => {
    fetchOverviewData(organizationId);
  };

  let previousOrgId: string | undefined = $state(undefined);

  $effect(() => {
    if (organizationId && organizationId !== previousOrgId) {
      previousOrgId = organizationId;
      fetchOverviewData(organizationId);
    }
  });
</script>

<div class="space-y-6">
  {#if loading}
    <!-- Loading State -->
    <div class="space-y-6">
      <div class="space-y-4">
        <LoadingSkeleton height="h-8" width="w-64" rounded={true} />
        <LoadingSkeleton height="h-4" width="w-96" rounded={true} />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {#each Array(6) as _}
          <LoadingSkeleton height="h-32" rounded={true} />
        {/each}
      </div>
    </div>

  {:else if error}
    <!-- Error State -->
    <div class="bg-red-50 border border-red-200 rounded-lg p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
          </svg>
        </div>
        <div class="ml-3 flex-1">
          <h3 class="text-sm font-medium text-red-800">Failed to load organization overview</h3>
          <p class="text-sm text-red-700 mt-1">{error}</p>
        </div>
        <div class="ml-3">
          <button
            onclick={handleRetry}
            class="bg-red-100 text-red-800 hover:bg-red-200 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200"
          >
            Retry
          </button>
        </div>
      </div>
    </div>

  {:else if overviewData}
    <!-- Success State -->
    <div class="space-y-6">
      <!-- Organization Header -->
      <div class="space-y-2">
        <h1 class="text-3xl font-bold text-secondary-900">{overviewData.organization_name}</h1>
        {#if overviewData.description}
          <p class="text-lg text-secondary-600">{overviewData.description}</p>
        {/if}
        <p class="text-sm text-secondary-500">@{overviewData.organization_slug}</p>
      </div>

      <!-- Key Metrics Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <!-- Delegates -->
        <MetricCard
          title="Delegates"
          value={formatNumber(overviewData.delegate_count)}
          description="Active voting delegates"
          icon="users"
        />

        <!-- Token Holders -->
        <MetricCard
          title="Token Holders"
          value={formatNumber(overviewData.token_holder_count)}
          description="Total token holders"
          icon="users"
        />

        <!-- Total Proposals -->
        <MetricCard
          title="Total Proposals"
          value={formatNumber(overviewData.total_proposals_count)}
          description="All time proposals"
          icon="document"
        />

        <!-- Governance Participation -->
        <MetricCard
          title="Participation Rate"
          value={formatPercentage(overviewData.governance_participation_rate)}
          description="Governance participation"
          icon="chart"
          trend={overviewData.governance_participation_rate > 0.5 ? 'up' : 'down'}
        />

        <!-- Recent Activity -->
        <MetricCard
          title="Recent Activity"
          value={formatNumber(overviewData.recent_activity_count)}
          description="Recent governance actions"
          icon="activity"
        />

        <!-- Active Proposals -->
        {#if overviewData.proposal_counts_by_status['ACTIVE']}
          <MetricCard
            title="Active Proposals"
            value={formatNumber(overviewData.proposal_counts_by_status['ACTIVE'])}
            description="Currently open for voting"
            icon="document"
            trend="up"
          />
        {/if}
      </div>

      <!-- Proposal Status Breakdown -->
      <div class="bg-white rounded-lg shadow-sm border border-secondary-200 p-6">
        <h2 class="text-xl font-semibold text-secondary-900 mb-4">Proposal Status Breakdown</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          {#each Object.entries(overviewData.proposal_counts_by_status) as [status, count]}
            {#if count > 0}
              <div class="text-center p-4 bg-secondary-50 rounded-lg">
                <div class="text-2xl font-bold text-secondary-900">{formatNumber(count)}</div>
                <div class="text-sm text-secondary-600 mt-1">{getStatusDisplayName(status)}</div>
              </div>
            {/if}
          {/each}
        </div>
      </div>
    </div>
  {/if}
</div>

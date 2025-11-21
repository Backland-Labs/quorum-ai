<script lang="ts">
  import { onMount } from 'svelte';
  import apiClient from '$lib/api';

  interface ServiceStatusData {
    service_id: number | null;
    state: string;
    status: string;
    is_live: boolean;
    message?: string;
  }

  let loading = $state(true);
  let error = $state<string | null>(null);
  let data = $state<ServiceStatusData | null>(null);

  onMount(async () => {
    try {
      const { data: responseData, error: responseError } = await apiClient.GET('/api/status/discovery');
      
      if (responseError) {
        error = 'Failed to fetch status';
        console.error(responseError);
      } else {
        data = responseData as ServiceStatusData;
      }
    } catch (err) {
      error = 'Failed to connect to service';
      console.error(err);
    } finally {
      loading = false;
    }
  });

  function getStatusColor(status: string): string {
    switch (status) {
      case 'meeting_threshold': return 'text-green-700 bg-green-50 border-green-200';
      case 'not_meeting_threshold': return 'text-red-700 bg-red-50 border-red-200';
      case 'unstaked': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    }
  }
  
  function getStatusLabel(status: string): string {
     switch (status) {
      case 'meeting_threshold': return 'Meeting Activity Threshold';
      case 'not_meeting_threshold': return 'Not Meeting Activity Threshold';
      case 'unstaked': return 'Unstaked';
      default: return 'Unknown Status';
    }
  }
</script>

<div class="bg-white rounded-xl shadow-sm border border-secondary-200 p-5 transition-all duration-200 hover:shadow-md">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-base font-semibold text-secondary-900">Service Status</h3>
    {#if data?.service_id}
      <span class="text-xs font-mono text-secondary-500 bg-secondary-100 px-2 py-1 rounded">
        ID: {data.service_id}
      </span>
    {/if}
  </div>
  
  {#if loading}
    <div class="flex flex-col items-center justify-center py-4 gap-3">
      <div class="animate-spin h-6 w-6 border-2 border-primary-500 border-t-transparent rounded-full"></div>
      <span class="text-sm text-secondary-500 animate-pulse">Discovering service...</span>
    </div>
  {:else if error}
    <div class="text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-100 flex items-start gap-2">
      <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>{error}</span>
    </div>
  {:else if data}
    <div class="space-y-4">
      <div class="flex justify-between items-center py-1">
        <span class="text-sm text-secondary-600">State</span>
        <span class="text-sm font-medium text-secondary-900 capitalize px-2 py-0.5 bg-secondary-50 rounded">
          {data.state.toLowerCase().replace('_', ' ')}
        </span>
      </div>

      <div class={`px-4 py-3 rounded-lg border text-sm font-medium flex items-center justify-center gap-2 ${getStatusColor(data.status)}`}>
        {#if data.status === 'meeting_threshold'}
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        {:else if data.status === 'not_meeting_threshold'}
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        {/if}
        {getStatusLabel(data.status)}
      </div>
    </div>
  {/if}
</div>

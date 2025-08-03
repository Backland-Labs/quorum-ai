<script lang="ts">
  import { goto } from '$app/navigation';
  import apiClient from '$lib/api';
  import PreferenceForm from '$lib/components/setup/PreferenceForm.svelte';
  import type { components } from '$lib/api/client';
  import { hasApiError, getApiErrorStatus } from '$lib/utils/api';
  import { onMount } from 'svelte';

  let preferences = $state<components['schemas']['UserPreferences'] | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let successMessage = $state<string | null>(null);

  onMount(() => {
    loadPreferences();
  });

  async function loadPreferences() {
    loading = true;
    error = null;

    try {
      const response = await apiClient.GET('/user-preferences');

      if (hasApiError(response)) {
        if (getApiErrorStatus(response) === 404) {
          // Redirect new users to setup
          await goto('/setup');
          return;
        }
        throw new Error('Failed to load preferences');
      }

      preferences = response.data || null;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load preferences';
    } finally {
      loading = false;
    }
  }

  async function handleSave(data: components['schemas']['UserPreferences']) {
    error = null;
    successMessage = null;

    try {
      const response = await apiClient.PUT('/user-preferences', {
        body: data
      });

      if (hasApiError(response)) {
        throw new Error('Failed to save preferences');
      }

      preferences = response.data || null;
      successMessage = 'Preferences saved successfully';
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save preferences';
    }
  }
</script>

<svelte:head>
  <title>Settings - Quorum AI</title>
  <meta name="description" content="Update your voting preferences and configure your autonomous voting agent" />
</svelte:head>

<div class="container mx-auto px-4 py-8 max-w-4xl">
  <h1 class="text-3xl font-bold mb-2">Settings</h1>
  <p class="text-gray-600 mb-8">Update your voting preferences and agent configuration</p>

  {#if loading}
    <div class="flex justify-center items-center min-h-[400px]">
      <div class="text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
        <p class="text-gray-600">Loading preferences...</p>
      </div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
      <h2 class="text-red-800 font-medium mb-1">Failed to load preferences</h2>
      <p class="text-red-700">{error}</p>
    </div>
  {:else if preferences}
    {#if successMessage}
      <div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
        <p class="text-green-800">{successMessage}</p>
      </div>
    {/if}

    <PreferenceForm
      initialValues={preferences}
      onSubmit={handleSave}
    />
  {/if}
</div>

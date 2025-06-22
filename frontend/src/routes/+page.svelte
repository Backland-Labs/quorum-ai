<script lang="ts">
  import { onMount } from "svelte";
  import apiClient from "$lib/api";
  import type { components } from "$lib/api/client";

  let organizations: components["schemas"]["Organization"][] = [];
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    const { data, error: apiError } = await apiClient.GET("/organizations", {
      params: {
        query: {
          limit: 20,
        },
      },
    });

    if (apiError) {
      error =
        "message" in apiError
          ? String(apiError.message)
          : "An unknown error occurred";
    } else if (data) {
      organizations = data.organizations;
    }
    loading = false;
  });
</script>

<svelte:head>
  <title>Quorum AI - Organizations</title>
</svelte:head>

<div class="container mx-auto p-8">
  <h1 class="text-3xl font-bold mb-6">DAO Organizations</h1>

  {#if loading}
    <p>Loading organizations...</p>
  {:else if error}
    <div class="text-red-500">
      <p>Failed to load organizations:</p>
      <pre>{error}</pre>
    </div>
  {:else}
    <ul class="space-y-4">
      {#each organizations as org}
        <li class="p-4 border rounded-lg shadow-sm">
          <h2 class="text-xl font-semibold">{org.name}</h2>
          <p class="text-gray-600">Proposals: {org.proposals_count}</p>
        </li>
      {/each}
    </ul>
  {/if}
</div>

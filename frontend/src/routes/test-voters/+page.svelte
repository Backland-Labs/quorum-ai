<script lang="ts">
  import TopVoters from '$lib/components/TopVoters.svelte';
</script>

<svelte:head>
  <title>Test TopVoters Component</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="bg-white shadow rounded-lg p-6">
      <h1 class="text-2xl font-bold text-gray-900 mb-8">TopVoters Component Test</h1>

      <div class="space-y-8">
        <div>
          <h2 class="text-lg font-medium text-gray-900 mb-4">Test with Mock Data (5 voters)</h2>
          <TopVoters proposalId="mock-test" limit={5} />
        </div>

        <div>
          <h2 class="text-lg font-medium text-gray-900 mb-4">Test with Empty State</h2>
          <TopVoters proposalId="empty" limit={10} />
        </div>

        <div>
          <h2 class="text-lg font-medium text-gray-900 mb-4">Test with Error State</h2>
          <TopVoters proposalId="error" limit={3} />
        </div>
      </div>
    </div>
  </div>
</div>

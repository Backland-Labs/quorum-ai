<script lang="ts">
  import type { components } from '$lib/api/client';

  interface Props {
    proposals: components['schemas']['Proposal'][];
  }

  let { proposals }: Props = $props();

  const stats = $derived({
    total: proposals.length,
    active: proposals.filter(p => p.state === 'active').length,
    closed: proposals.filter(p => p.state === 'closed').length,
    pending: proposals.filter(p => p.state === 'pending').length
  });
</script>

<div class="bg-white rounded-lg shadow p-6">
  <div class="grid grid-cols-3 gap-8">
    <div class="text-center">
      <p class="text-5xl font-semibold text-gray-900 mb-2">{stats.total}</p>
      <p class="text-sm text-gray-600">Total Proposals</p>
    </div>
    <div class="text-center">
      <p class="text-5xl font-semibold text-gray-900 mb-2">{stats.active}</p>
      <p class="text-sm text-gray-600">Active</p>
    </div>
    <div class="text-center">
      <p class="text-5xl font-semibold text-gray-900 mb-2">{stats.closed}</p>
      <p class="text-sm text-gray-600">Closed</p>
    </div>
  </div>
</div>

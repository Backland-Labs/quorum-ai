<script lang="ts">
  import type { components } from '$lib/api/client';

  interface Props {
    proposals: components['schemas']['Proposal'][];
    onViewDetails: () => void;
  }

  let { proposals, onViewDetails }: Props = $props();

  const stats = $derived({
    total: proposals.length,
    active: proposals.filter(p => p.state === 'active').length,
    closed: proposals.filter(p => p.state === 'closed').length,
    pending: proposals.filter(p => p.state === 'pending').length
  });
</script>

<div class="bg-white rounded-lg shadow p-6">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold text-secondary-900">Proposal Statistics</h3>
    <button
      onclick={onViewDetails}
      class="text-sm text-primary-600 hover:text-primary-700"
    >
      View all
    </button>
  </div>

  <div class="grid grid-cols-2 gap-4">
    <div>
      <p class="text-2xl font-bold text-secondary-900">{stats.total}</p>
      <p class="text-sm text-secondary-600">Total Proposals</p>
    </div>
    <div>
      <p class="text-2xl font-bold text-success-600">{stats.active}</p>
      <p class="text-sm text-secondary-600">Active</p>
    </div>
    <div>
      <p class="text-2xl font-bold text-secondary-500">{stats.closed}</p>
      <p class="text-sm text-secondary-600">Closed</p>
    </div>
    <div>
      <p class="text-2xl font-bold text-warning-600">{stats.pending}</p>
      <p class="text-sm text-secondary-600">Pending</p>
    </div>
  </div>
</div>

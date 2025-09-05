<script lang="ts">
  import { goto } from '$app/navigation';
</script>

<svelte:head>
  <title>Instructions • Quorum AI</title>
  <meta name="description" content="How to use Quorum AI, required setup, and voting power requirements." />
</svelte:head>

<div class="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
  <div class="max-w-3xl mx-auto">
    <button
      onclick={() => goto('/')}
      class="mb-8 inline-flex items-center text-indigo-600 hover:text-indigo-500"
      aria-label="Back to Dashboard"
    >
      <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
      </svg>
      Back to Dashboard
    </button>

    <h1 class="text-3xl font-bold text-gray-900 mb-6">Instructions</h1>
    <p class="text-gray-600 mb-8">Follow these steps to configure and use Quorum AI for autonomous Snapshot voting.</p>

    <div class="bg-white shadow rounded-lg p-6 space-y-6">
      <section>
        <h2 class="text-xl font-semibold text-gray-900 mb-3">Getting Started</h2>
        <ol class="list-decimal pl-5 space-y-2 text-gray-700">
          <li>Start the backend (FastAPI) on port 8716 and the frontend. Quick start: <code class="text-gray-900">./startup.sh</code></li>
          <li>Open the app and complete the setup wizard to save your voting preferences (<a href="/setup" class="text-indigo-600 hover:text-indigo-500 underline">/setup</a>).</li>
          <li>From the Dashboard, select the Snapshot space you want to follow and run the agent.</li>
          <li>Review recent decisions and status on the Dashboard. For detailed options, see <a href="/docs" class="text-indigo-600 hover:text-indigo-500 underline">Documentation</a>.</li>
        </ol>
      </section>

      <section class="border-t pt-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-3">Required Setup</h2>
        <ul class="list-disc pl-5 space-y-2 text-gray-700">
          <li><strong>OpenRouter API Key:</strong> Required for AI features. Set <code class="text-gray-900">OPENROUTER_API_KEY</code> in your environment/backend.</li>
          <li><strong>Backend Port:</strong> Runs on <code class="text-gray-900">8716</code> by default; API docs available at <code class="text-gray-900">/docs</code> when running.</li>
          <li><strong>Private Key for Voting:</strong> The agent uses <code class="text-gray-900">backend/ethereum_private_key.txt</code> (preferred) or <code class="text-gray-900">PRIVATE_KEY</code> in <code class="text-gray-900">.env</code>. Ensure the file exists, is valid, and has secure permissions (chmod 600).</li>
          <li><strong>API Client (optional):</strong> Generate types by running <code class="text-gray-900">npm run generate-api</code> in <code class="text-gray-900">frontend/</code> when the backend is running.</li>
        </ul>
      </section>

      <section class="border-t pt-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-3">Voting Power Requirements</h2>
        <div class="text-gray-700 space-y-2">
          <p>Snapshot will only accept votes from addresses that have voting power in the selected space (according to that space's strategies/rules).</p>
          <ul class="list-disc pl-5 space-y-2">
            <li>If you see a 400 error "no voting power" in logs, your address doesn't meet the space requirements. This is not a technical error but an eligibility rule.</li>
            <li>Verify the active address corresponds to your configured private key and holds the required tokens or delegations for that space.</li>
            <li>For test environments, use a funded/authorized test account with voting power in the test space.</li>
          </ul>
          <p class="text-xs text-gray-500">Tip: Check <code>backend/log.txt</code> for detailed Pearl-compliant logs when troubleshooting.</p>
        </div>
      </section>

      <section class="border-t pt-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-3">Troubleshooting</h2>
        <ul class="list-disc pl-5 space-y-2 text-gray-700">
          <li>Status not updating? Ensure the backend is running on port 8716 and check network errors.</li>
          <li>Agent run failed? Confirm your OpenRouter API key is set and user preferences are saved.</li>
          <li>No votes posted? Verify voting power and private key configuration as above.</li>
        </ul>
      </section>
    </div>
  </div>
</div>

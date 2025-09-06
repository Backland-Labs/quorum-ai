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

    <h1 class="text-3xl font-bold text-gray-900 mb-6">Getting Started</h1>
    <p class="text-gray-600 mb-8">Follow these steps to set up and configure Quorum AI for autonomous Snapshot voting.</p>

    <div class="bg-white shadow rounded-lg p-6 space-y-6">
      <section>
        <h2 class="text-xl font-semibold text-gray-900 mb-3">Configure Your Agent</h2>
        <div class="text-gray-700 space-y-3">
          <p>First, you'll need to sign up for OpenRouter to get an API key for AI functionality:</p>
          <ol class="list-decimal pl-5 space-y-2">
            <li>Go to <a href="https://openrouter.ai/" target="_blank" class="text-indigo-600 hover:text-indigo-500 underline">OpenRouter.ai</a></li>
            <li>Sign up for an account</li>
            <li>Navigate to your API keys section</li>
            <li>Generate a new API key</li>
            <li>Copy and save this key</li>
            <li>Go to the <a href="/settings" class="text-indigo-600 hover:text-indigo-500 underline">Settings</a> page in Quorum AI</li>
            <li>Add your OpenRouter API key in the configuration section</li>
            <li>Configure your agent's voting strategy based on your preferences</li>
            <li>Configure the confidence threshold (recommend leaving the defaults)</li>
          </ol>
        </div>
      </section>
    </div>
  </div>
</div>

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

      <section class="border-t pt-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-3">Important Note</h2>
        <div class="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium text-yellow-800">Voting Power Required</h3>
              <div class="mt-2 text-sm text-yellow-700">
                <p>In order for the agent to vote on a given proposal, your wallet address must have voting power for that specific proposal. This is determined by the DAO's voting strategies and token holdings at the proposal's snapshot block.</p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</div>

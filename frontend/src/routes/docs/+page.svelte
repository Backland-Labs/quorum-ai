<script lang="ts">
	import { goto } from '$app/navigation';
</script>

<div class="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
	<div class="max-w-3xl mx-auto">
		<button
			onclick={() => goto('/')}
			class="mb-8 inline-flex items-center text-indigo-600 hover:text-indigo-500"
		>
			<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
			</svg>
			Back to Dashboard
		</button>

		<h1 class="text-3xl font-bold text-gray-900 mb-8">Quorum AI Documentation</h1>

		<div class="bg-white shadow rounded-lg p-6 space-y-6">
			<section>
				<h2 class="text-xl font-semibold text-gray-900 mb-4">User Preferences</h2>
				<div class="prose prose-sm text-gray-700">
					<h3 class="text-lg font-medium mb-2">Voting Strategy</h3>
					<ul class="list-disc pl-5 space-y-2">
						<li><strong>Conservative:</strong> Only vote on proposals with low risk assessments. Best for users who prioritize safety.</li>
						<li><strong>Balanced:</strong> Consider both risk and potential reward. The default strategy for most users.</li>
						<li><strong>Aggressive:</strong> Vote on high-impact proposals even if they carry higher risk. For users seeking maximum participation.</li>
					</ul>

					<h3 class="text-lg font-medium mb-2 mt-6">Confidence Threshold</h3>
					<p>The minimum confidence score (0.0 to 1.0) required for the AI to cast a vote. Higher values mean the AI will only vote when it's very confident in its decision.</p>

					<h3 class="text-lg font-medium mb-2 mt-6">Maximum Proposals per Run</h3>
					<p>Limits how many proposals the agent will analyze in a single run. This helps manage gas costs and processing time.</p>

					<h3 class="text-lg font-medium mb-2 mt-6">Blacklisted Proposers</h3>
					<p>Wallet addresses whose proposals will be automatically rejected. Use this to filter out known bad actors or proposals you never want to support.</p>

					<h3 class="text-lg font-medium mb-2 mt-6">Whitelisted Proposers</h3>
					<p>Wallet addresses whose proposals receive priority consideration. The AI will still analyze these proposals but may apply a lower confidence threshold.</p>
				</div>
			</section>

			<section class="border-t pt-6">
				<h2 class="text-xl font-semibold text-gray-900 mb-4">Getting Started</h2>
				<ol class="list-decimal pl-5 space-y-2 text-gray-700">
					<li>Configure your voting preferences in the setup wizard</li>
					<li>Select a Snapshot space to monitor</li>
					<li>Run the autonomous agent to analyze and vote on proposals</li>
					<li>Review voting decisions in the dashboard</li>
				</ol>
			</section>
		</div>
	</div>
</div>

<script lang="ts">
	import type { VotingStrategy } from '$lib/types/preferences';
	
	interface Props {
		initialValues?: {
			voting_strategy: VotingStrategy;
			confidence_threshold: number;
			max_proposals_per_run: number;
			blacklisted_proposers: string[];
			whitelisted_proposers: string[];
		};
		onSubmit?: (data: {
			voting_strategy: VotingStrategy;
			confidence_threshold: number;
			max_proposals_per_run: number;
			blacklisted_proposers: string[];
			whitelisted_proposers: string[];
		}) => void | Promise<void>;
	}
	
	let { initialValues, onSubmit }: Props = $props();
	
	// Form state with defaults
	let votingStrategy = $state<VotingStrategy>(initialValues?.voting_strategy || 'balanced');
	let confidenceThreshold = $state(initialValues?.confidence_threshold || 0.7);
	let maxProposalsPerRun = $state(initialValues?.max_proposals_per_run || 5);
	let blacklistedProposers = $state(initialValues?.blacklisted_proposers?.join('\n') || '');
	let whitelistedProposers = $state(initialValues?.whitelisted_proposers?.join('\n') || '');
	
	// Form validation state
	let confidenceError = $state('');
	let maxProposalsError = $state('');
	let isSubmitting = $state(false);
	
	// Validation functions
	const validateConfidence = () => {
		if (confidenceThreshold < 0 || confidenceThreshold > 1) {
			confidenceError = 'Confidence threshold must be between 0 and 1';
		} else {
			confidenceError = '';
		}
	};
	
	const validateMaxProposals = () => {
		if (maxProposalsPerRun < 1 || maxProposalsPerRun > 10) {
			maxProposalsError = 'Maximum proposals must be between 1 and 10';
		} else {
			maxProposalsError = '';
		}
	};
	
	// Parse address lists
	const parseAddressList = (text: string): string[] => {
		return text
			.split('\n')
			.map(addr => addr.trim())
			.filter(addr => addr.length > 0);
	};
	
	// Handle form submission
	const handleSubmit = async (e: Event) => {
		e.preventDefault();
		
		// Validate all fields
		validateConfidence();
		validateMaxProposals();
		
		// Check for errors
		if (confidenceError || maxProposalsError) {
			return;
		}
		
		if (!onSubmit) return;
		
		isSubmitting = true;
		
		try {
			await onSubmit({
				voting_strategy: votingStrategy,
				confidence_threshold: confidenceThreshold,
				max_proposals_per_run: maxProposalsPerRun,
				blacklisted_proposers: parseAddressList(blacklistedProposers),
				whitelisted_proposers: parseAddressList(whitelistedProposers)
			});
		} finally {
			isSubmitting = false;
		}
	};
</script>

<form onsubmit={handleSubmit} class="space-y-6">
	<!-- Voting Strategy -->
	<div>
		<label for="voting-strategy" class="block text-sm font-medium text-gray-700 mb-2">
			Voting Strategy
		</label>
		<select
			id="voting-strategy"
			bind:value={votingStrategy}
			class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
			disabled={isSubmitting}
		>
			<option value="conservative">Conservative - Vote only on low-risk proposals</option>
			<option value="balanced">Balanced - Consider risk vs. reward</option>
			<option value="aggressive">Aggressive - Vote on high-impact proposals</option>
		</select>
		<p class="mt-1 text-sm text-gray-500">
			Determines how the agent evaluates proposal risk
		</p>
	</div>
	
	<!-- Confidence Threshold -->
	<div>
		<label for="confidence-threshold" class="block text-sm font-medium text-gray-700 mb-2">
			Confidence Threshold
		</label>
		<input
			id="confidence-threshold"
			type="number"
			step="0.1"
			min="0"
			max="1"
			bind:value={confidenceThreshold}
			onblur={validateConfidence}
			class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
			class:border-red-500={confidenceError}
			disabled={isSubmitting}
		/>
		{#if confidenceError}
			<p class="mt-1 text-sm text-red-600">{confidenceError}</p>
		{/if}
		<p class="mt-1 text-sm text-gray-500">
			Minimum confidence score (0-1) required to cast a vote
		</p>
	</div>
	
	<!-- Max Proposals -->
	<div>
		<label for="max-proposals" class="block text-sm font-medium text-gray-700 mb-2">
			Maximum Proposals per Run
		</label>
		<input
			id="max-proposals"
			type="number"
			min="1"
			max="10"
			bind:value={maxProposalsPerRun}
			onblur={validateMaxProposals}
			class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
			class:border-red-500={maxProposalsError}
			disabled={isSubmitting}
		/>
		{#if maxProposalsError}
			<p class="mt-1 text-sm text-red-600">{maxProposalsError}</p>
		{/if}
		<p class="mt-1 text-sm text-gray-500">
			How many proposals to analyze in each agent run
		</p>
	</div>
	
	<!-- Blacklisted Proposers -->
	<div>
		<label for="blacklisted-proposers" class="block text-sm font-medium text-gray-700 mb-2">
			Blacklisted Proposers
		</label>
		<textarea
			id="blacklisted-proposers"
			bind:value={blacklistedProposers}
			rows="3"
			class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
			placeholder="Enter wallet addresses, one per line"
			disabled={isSubmitting}
		></textarea>
		<p class="mt-1 text-sm text-gray-500">
			Proposals from these addresses will be automatically rejected
		</p>
	</div>
	
	<!-- Whitelisted Proposers -->
	<div>
		<label for="whitelisted-proposers" class="block text-sm font-medium text-gray-700 mb-2">
			Whitelisted Proposers
		</label>
		<textarea
			id="whitelisted-proposers"
			bind:value={whitelistedProposers}
			rows="3"
			class="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
			placeholder="Enter wallet addresses, one per line"
			disabled={isSubmitting}
		></textarea>
		<p class="mt-1 text-sm text-gray-500">
			Proposals from these addresses will receive priority consideration
		</p>
	</div>
	
	<!-- Submit Button -->
	<div class="pt-4">
		<button
			type="submit"
			disabled={isSubmitting || !!confidenceError || !!maxProposalsError}
			class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
		>
			{isSubmitting ? 'Saving...' : 'Save Preferences'}
		</button>
	</div>
</form>
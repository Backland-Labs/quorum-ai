<script lang="ts">
	import type { VotingStrategy } from '$lib/types/preferences';
	import { apiClient } from '$lib/api';
	import { onMount } from 'svelte';

	interface Props {
		initialValues?: {
			voting_strategy: VotingStrategy;
			blacklisted_proposers?: string[];
			whitelisted_proposers?: string[];
		};
		onSubmit?: (data: {
			voting_strategy: VotingStrategy;
			blacklisted_proposers: string[];
			whitelisted_proposers: string[];
		}) => void | Promise<void>;
		onSubmitAndReconsider?: (data: {
			voting_strategy: VotingStrategy;
			blacklisted_proposers: string[];
			whitelisted_proposers: string[];
		}) => void | Promise<void>;
		showApiKeyField?: boolean;
		reconsiderDisabled?: boolean;
	}

	let { initialValues, onSubmit, onSubmitAndReconsider, showApiKeyField = true, reconsiderDisabled = false }: Props = $props();

	// Default configuration values
	const DEFAULT_VOTING_STRATEGY: VotingStrategy = 'balanced';

	// Form state with defaults
	let votingStrategy = $state<VotingStrategy>(initialValues?.voting_strategy || DEFAULT_VOTING_STRATEGY);
	let blacklistedProposers = $state(initialValues?.blacklisted_proposers?.join('\n') || '');
	let whitelistedProposers = $state(initialValues?.whitelisted_proposers?.join('\n') || '');

	// Baseline snapshot for dirty-state tracking
	interface Baseline {
		votingStrategy: VotingStrategy;
		blacklistedProposers: string;
		whitelistedProposers: string;
	}
	let baseline = $state<Baseline>({
		votingStrategy: votingStrategy,
		blacklistedProposers: blacklistedProposers,
		whitelistedProposers: whitelistedProposers
	});

	// Update baseline when initialValues changes
	$effect(() => {
		if (initialValues) {
			baseline = {
				votingStrategy: initialValues.voting_strategy || DEFAULT_VOTING_STRATEGY,
				blacklistedProposers: initialValues.blacklisted_proposers?.join('\n') || '',
				whitelistedProposers: initialValues.whitelisted_proposers?.join('\n') || ''
			};
		}
	});

	// Normalize list for comparison (case-insensitive, order-insensitive)
	const normalizeList = (text: string): string[] => {
		return text
			.split('\n')
			.map(line => line.trim().toLowerCase())
			.filter(line => line.length > 0)
			.sort();
	};

	// Check if form is dirty
	const isDirty = $derived(
		votingStrategy !== baseline.votingStrategy ||
		normalizeList(blacklistedProposers).join('\n') !== normalizeList(baseline.blacklistedProposers).join('\n') ||
		normalizeList(whitelistedProposers).join('\n') !== normalizeList(baseline.whitelistedProposers).join('\n')
	);

	// API key state
	let apiKey = $state('');
	let showApiKey = $state(false);
	let apiKeyConfigured = $state(false);
	let apiKeySource = $state<string | null>(null);
	let apiKeyError = $state('');
	let apiKeySaving = $state(false);
	let apiKeySuccess = $state(false);

	// Form validation state
	let isSubmitting = $state(false);

	// Parse address lists
	const parseAddressList = (text: string): string[] => {
		return text
			.split('\n')
			.map(addr => addr.trim())
			.filter(addr => addr.length > 0);
	};

	// Load API key status on mount
	onMount(() => {
		loadApiKeyStatus();
	});

	// API key functions
	const loadApiKeyStatus = async () => {
		try {
			const response = await apiClient.GET('/config/openrouter-key');
			if (response.data && typeof response.data === 'object') {
				const data = response.data as any;
				if (data.status === 'success' && data.data) {
					apiKeyConfigured = data.data.configured || false;
					apiKeySource = data.data.source || null;
				}
			}
		} catch (error) {
			console.error('Failed to load API key status:', error);
		}
	};

	const handleSaveApiKey = async () => {
		if (!apiKey.trim() || apiKey.trim().length < 20) {
			apiKeyError = 'API key must be at least 20 characters';
			return;
		}

		apiKeySaving = true;
		apiKeyError = '';
		apiKeySuccess = false;

		try {
			const response = await apiClient.POST('/config/openrouter-key', {
				body: { api_key: apiKey.trim() }
			});

			if (response.data && typeof response.data === 'object') {
				const data = response.data as any;
				if (data.status === 'success') {
					apiKeySuccess = true;
					apiKey = ''; // Clear field after save
					await loadApiKeyStatus(); // Refresh status
					setTimeout(() => { apiKeySuccess = false; }, 3000);
				} else {
					apiKeyError = data.message || 'Failed to save API key';
				}
			} else {
				apiKeyError = 'Failed to save API key';
			}
		} catch (error) {
			apiKeyError = 'Failed to save API key';
		} finally {
			apiKeySaving = false;
		}
	};

	const handleRemoveApiKey = async () => {
		apiKeySaving = true;
		apiKeyError = '';

		try {
			const response = await apiClient.POST('/config/openrouter-key', {
				body: { api_key: '' }
			});

			if (response.data && typeof response.data === 'object') {
				const data = response.data as any;
				if (data.status === 'success') {
					apiKey = '';
					await loadApiKeyStatus();
				} else {
					apiKeyError = data.message || 'Failed to remove API key';
				}
			} else {
				apiKeyError = 'Failed to remove API key';
			}
		} catch (error) {
			apiKeyError = 'Failed to remove API key';
		} finally {
			apiKeySaving = false;
		}
	};

	// Handle form submission
	const handleSubmit = async (e: Event) => {
		e.preventDefault();

		if (!onSubmit) return;

		isSubmitting = true;

		try {
			await onSubmit({
				voting_strategy: votingStrategy,
				blacklisted_proposers: parseAddressList(blacklistedProposers),
				whitelisted_proposers: parseAddressList(whitelistedProposers)
			});
		} finally {
			isSubmitting = false;
		}
	};

	// Handle submit and reconsider
	const handleSubmitAndReconsider = async (e: Event) => {
		e.preventDefault();

		if (!onSubmitAndReconsider) return;

		isSubmitting = true;

		try {
			await onSubmitAndReconsider({
				voting_strategy: votingStrategy,
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

	<!-- API Key Configuration -->
	{#if showApiKeyField}
		<div>
			<label for="api-key" class="block text-sm font-medium text-gray-700 mb-2">
				OpenRouter API Key
			</label>
			<div class="space-y-3">
				<div class="relative">
					<input
						id="api-key"
						type={showApiKey ? 'text' : 'password'}
						bind:value={apiKey}
						placeholder="sk-or-..."
						class="block w-full pr-20 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
						class:border-red-500={apiKeyError}
						disabled={apiKeySaving}
					/>
					<button
						type="button"
						onclick={() => showApiKey = !showApiKey}
						class="absolute right-12 top-1/2 transform -translate-y-1/2 text-sm text-gray-500 hover:text-gray-700"
						disabled={apiKeySaving}
					>
						{showApiKey ? 'Hide' : 'Show'}
					</button>
					<button
						type="button"
						onclick={handleSaveApiKey}
						disabled={apiKeySaving || !apiKey.trim()}
						class="absolute right-2 top-1/2 transform -translate-y-1/2 text-sm bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
					>
						{apiKeySaving ? '...' : 'Save'}
					</button>
				</div>

				{#if apiKeySuccess}
					<p class="text-sm text-green-600">✓ API key saved successfully</p>
				{/if}

				{#if apiKeyError}
					<p class="text-sm text-red-600">{apiKeyError}</p>
				{/if}

				{#if apiKeyConfigured}
					<div class="flex items-center justify-between bg-green-50 p-3 rounded-md">
						<p class="text-sm text-green-800">
							✓ API key configured from {apiKeySource === 'user' ? 'user input' : 'environment'}
						</p>
						{#if apiKeySource === 'user'}
							<button
								type="button"
								onclick={handleRemoveApiKey}
								disabled={apiKeySaving}
								class="text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
							>
								Remove
							</button>
						{/if}
					</div>
				{/if}

				<p class="text-sm text-gray-500">
					Enter your OpenRouter API key to enable AI-powered proposal analysis
				</p>
			</div>
		</div>
	{/if}


	<!-- Conditional Action Buttons -->
	{#if isDirty}
		<div class="pt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
			<button
				type="submit"
				disabled={isSubmitting}
				class="flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{isSubmitting ? 'Saving...' : 'Save Preferences'}
			</button>
			<button
				type="button"
				onclick={handleSubmitAndReconsider}
				disabled={isSubmitting || reconsiderDisabled || !onSubmitAndReconsider}
				class="flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{isSubmitting ? 'Saving...' : 'Save Settings and Reconsider Proposals'}
			</button>
		</div>
	{/if}
</form>

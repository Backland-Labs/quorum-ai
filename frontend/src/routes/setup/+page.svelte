<script lang="ts">
	import { goto } from '$app/navigation';
	import PreferenceForm from '$lib/components/setup/PreferenceForm.svelte';
	import type { UserPreferences } from '$lib/types/preferences';
	import { extractApiErrorMessage } from '$lib/utils/api';
	import apiClient from '$lib/api';
	
	let errorMessage = $state('');
	let successMessage = $state('');
	
	const handleSubmit = async (data: UserPreferences) => {
		errorMessage = '';
		successMessage = '';
		
		try {
			// Call the API to save preferences
			const response = await apiClient.PUT('/user-preferences', {
				body: data
			});
			
			if (response.error) {
				throw new Error(response.error.message || 'Failed to save preferences');
			}
			
			successMessage = 'Preferences saved successfully! Redirecting...';
			
			// Redirect to dashboard after a short delay
			setTimeout(() => {
				goto('/');
			}, 1500);
			
		} catch (error) {
			errorMessage = extractApiErrorMessage(error);
			console.error('Failed to save preferences:', error);
		}
	};
</script>

<div class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
	<div class="sm:mx-auto sm:w-full sm:max-w-md">
		<h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
			Welcome to Quorum AI
		</h2>
		<p class="mt-2 text-center text-sm text-gray-600">
			Configure your autonomous voting preferences to get started
		</p>
	</div>
	
	<div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
		<div class="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
			{#if errorMessage}
				<div class="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
					<p class="text-sm text-red-800">{errorMessage}</p>
				</div>
			{/if}
			
			{#if successMessage}
				<div class="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
					<p class="text-sm text-green-800">{successMessage}</p>
				</div>
			{/if}
			
			<PreferenceForm onSubmit={handleSubmit} />
			
			<div class="mt-6">
				<div class="relative">
					<div class="absolute inset-0 flex items-center">
						<div class="w-full border-t border-gray-300"></div>
					</div>
					<div class="relative flex justify-center text-sm">
						<span class="px-2 bg-white text-gray-500">Need help?</span>
					</div>
				</div>
				
				<div class="mt-6 text-center">
					<a href="/docs" class="text-indigo-600 hover:text-indigo-500">
						View documentation
					</a>
				</div>
			</div>
		</div>
	</div>
</div>
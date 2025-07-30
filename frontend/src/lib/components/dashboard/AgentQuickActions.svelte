<script lang="ts">
  import { apiClient } from '$lib/api';

  interface Props {
    spaceId: string | null;
    isAgentActive?: boolean;
    onRunComplete?: () => void;
  }

  let { spaceId: currentSpaceId, isAgentActive = false, onRunComplete }: Props = $props();
  
  // Constants
  const SUCCESS_MESSAGE_DURATION = 5000;
  const API_ENDPOINT = '/agent-run';
  
  // State
  let isLoading = $state(false);
  let message = $state<{ type: 'success' | 'error'; text: string } | null>(null);
  let messageTimer: NodeJS.Timeout | null = null;

  // Derived values
  const buttonDisabled = $derived(isLoading || isAgentActive);
  const buttonText = $derived(isLoading ? 'Running...' : 'Run Now');
  const buttonTitle = $derived(isAgentActive ? 'Agent is currently active' : undefined);
  const buttonAriaLabel = $derived(isAgentActive ? 'Run agent (currently active)' : 'Run autonomous voting agent now');
  const alertClasses = $derived(
    message?.type === 'success' 
      ? 'bg-green-50 text-green-800 border-green-200' 
      : 'bg-red-50 text-red-800 border-red-200'
  );

  function clearMessageTimer(): void {
    if (messageTimer) {
      clearTimeout(messageTimer);
      messageTimer = null;
    }
  }

  function showMessage(type: 'success' | 'error', text: string): void {
    message = { type, text };
    clearMessageTimer();
    
    if (type === 'success') {
      messageTimer = setTimeout(() => {
        message = null;
      }, SUCCESS_MESSAGE_DURATION);
    }
  }

  async function triggerAgentRun(): Promise<void> {
    const { data, error } = await apiClient.POST(API_ENDPOINT, {
      body: {
        space_id: currentSpaceId,
        dry_run: false
      }
    });

    if (error) {
      showMessage('error', `Failed to trigger agent run: ${error.message || 'Unknown error'}`);
    } else {
      showMessage('success', 'Agent run triggered successfully!');
      onRunComplete?.();
    }
  }

  async function handleRunNow(): Promise<void> {
    if (!currentSpaceId) {
      showMessage('error', 'No space selected. Please select a space first.');
      return;
    }

    isLoading = true;
    message = null;

    try {
      await triggerAgentRun();
    } catch (err) {
      showMessage('error', 'Failed to trigger agent run. Please try again.');
    } finally {
      isLoading = false;
    }
  }

  function handleKeyDown(event: KeyboardEvent): void {
    const isActivationKey = event.key === 'Enter' || event.key === ' ';
    
    if (isActivationKey && !buttonDisabled) {
      event.preventDefault();
      handleRunNow();
    }
  }

  // Cleanup timer on unmount
  $effect(() => {
    return clearMessageTimer;
  });
</script>

<div data-testid="quick-actions" class="flex flex-col gap-2 w-full sm:w-auto">
  <h4 data-testid="actions-title" class="text-sm sm:text-base font-medium text-gray-900 mb-2 sm:mb-3">Quick Actions</h4>
  
  {#if message}
    <div 
      data-testid={message.type === 'success' ? 'feedback-message' : 'error-message'}
      role="alert" 
      class="px-2 sm:px-0 py-3 rounded-md text-xs sm:text-sm border {alertClasses} break-words"
    >
      {message.text}
    </div>
  {/if}

  <button
    onclick={handleRunNow}
    onkeydown={handleKeyDown}
    disabled={buttonDisabled}
    class="inline-flex items-center justify-center px-4 py-2 sm:px-6 sm:py-3 text-sm sm:text-base font-medium text-white bg-blue-600 rounded-md hover:bg-blue-600 active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 w-full sm:w-auto min-h-[44px]"
    aria-label={buttonAriaLabel}
    title={buttonTitle}
  >
    {#if isLoading}
      <svg 
        data-testid="loading-spinner"
        role="status" 
        aria-label="Loading" 
        class="w-4 h-4 sm:w-5 sm:h-5 mr-2 animate-spin"
        viewBox="0 0 24 24"
        fill="none"
      >
        <circle 
          class="opacity-25" 
          cx="12" 
          cy="12" 
          r="10" 
          stroke="currentColor" 
          stroke-width="4"
        />
        <path 
          class="opacity-75" 
          fill="currentColor" 
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    {/if}
    <span data-testid="button-text" class="text-sm sm:text-base">{buttonText}</span>
  </button>
</div>
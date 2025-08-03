import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import AgentQuickActions from './AgentQuickActions.svelte';
import { apiClient } from '$lib/api';

// Mock the API client
vi.mock('$lib/api', () => ({
  apiClient: {
    POST: vi.fn()
  }
}));

// Default test props
const defaultProps = {
  currentSpaceId: 'test-space-id',
  isAgentActive: false,
  onRunComplete: vi.fn()
};

describe('AgentQuickActions Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('displays run now button', async () => {
    /**
     * Why: Users need a clear, visible button to trigger the autonomous voting agent.
     * What: Verifies that the "Run Agent Now" button is rendered with proper text and accessibility attributes.
     */
    render(AgentQuickActions, {
      props: defaultProps
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveAttribute('aria-label', 'Run autonomous voting agent');
  });

  it('button calls api on click', async () => {
    /**
     * Why: The primary function of this component is to trigger agent runs via API.
     * What: Verifies that clicking the button makes the correct API call with proper parameters.
     */
    const mockPost = vi.mocked(apiClient.POST);
    mockPost.mockResolvedValueOnce({
      data: { status: 'Agent run triggered successfully' },
      error: null
    });

    render(AgentQuickActions, {
      props: defaultProps
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    await fireEvent.click(button);

    expect(mockPost).toHaveBeenCalledWith('/agent-run', {
      body: {
        space_id: 'test-space-id',
        dry_run: false
      }
    });
  });

  it('button disabled when agent active', async () => {
    /**
     * Why: Prevents multiple concurrent agent runs which could cause conflicts.
     * What: Verifies that the button is disabled when the agent status indicates it's already active.
     */
    render(AgentQuickActions, {
      props: {
        ...defaultProps,
        isAgentActive: true
      }
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('title', 'Agent is currently active');
  });

  it('shows loading state during request', async () => {
    /**
     * Why: Users need visual feedback that their action is being processed.
     * What: Verifies that the button shows loading state while API call is in progress.
     */
    const mockPost = vi.mocked(apiClient.POST);
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockPost.mockReturnValueOnce(promise as any);

    render(AgentQuickActions, {
      props: defaultProps
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    await fireEvent.click(button);

    // Check loading state
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/running.../i);
    expect(screen.getByRole('status', { name: /loading/i })).toBeInTheDocument();

    // Resolve the promise
    resolvePromise!({
      data: { status: 'Agent run triggered successfully' },
      error: null
    });

    // Wait for loading state to clear
    await waitFor(() => {
      expect(button).not.toBeDisabled();
      expect(button).toHaveTextContent(/run agent now/i);
    });
  });

  it('displays success message', async () => {
    /**
     * Why: Users need confirmation that their action was successful.
     * What: Verifies that a success message is displayed after successful API call.
     */
    const mockPost = vi.mocked(apiClient.POST);
    mockPost.mockResolvedValueOnce({
      data: { status: 'Agent run triggered successfully' },
      error: null
    });

    render(AgentQuickActions, {
      props: defaultProps
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    await fireEvent.click(button);

    await waitFor(() => {
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('alert-success');
      expect(alert).toHaveTextContent(/agent run triggered successfully/i);
    });

    // Success message should disappear after 5 seconds
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    }, { timeout: 6000 });
  });

  it('displays error message on failure', async () => {
    /**
     * Why: Users need to know when something goes wrong and what they can do about it.
     * What: Verifies that an error message is displayed when the API call fails.
     */
    const mockPost = vi.mocked(apiClient.POST);
    mockPost.mockResolvedValueOnce({
      data: null,
      error: {
        status: 500,
        message: 'Internal server error'
      }
    });

    render(AgentQuickActions, {
      props: defaultProps
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    await fireEvent.click(button);

    await waitFor(() => {
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('alert-error');
      expect(alert).toHaveTextContent(/failed to trigger agent run/i);
    });
  });

  it('handles missing space id gracefully', async () => {
    /**
     * Why: Component should handle edge case where no space is selected.
     * What: Verifies that appropriate error is shown when current_space_id is not available.
     */
    render(AgentQuickActions, {
      props: {
        ...defaultProps,
        currentSpaceId: null
      }
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    await fireEvent.click(button);

    await waitFor(() => {
      const alert = screen.getByRole('alert');
      expect(alert).toHaveClass('alert-error');
      expect(alert).toHaveTextContent(/no space selected/i);
    });

    // API should not be called
    expect(apiClient.POST).not.toHaveBeenCalled();
  });

  it('updates agent status after successful run', async () => {
    /**
     * Why: Dashboard components should stay synchronized after agent actions.
     * What: Verifies that the component triggers a status refresh after successful agent run.
     */
    const mockPost = vi.mocked(apiClient.POST);
    mockPost.mockResolvedValueOnce({
      data: { status: 'Agent run triggered successfully' },
      error: null
    });

    const onRunCompleteSpy = vi.fn();

    render(AgentQuickActions, {
      props: {
        ...defaultProps,
        onRunComplete: onRunCompleteSpy
      }
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    await fireEvent.click(button);

    await waitFor(() => {
      expect(onRunCompleteSpy).toHaveBeenCalled();
    });
  });

  it('respects keyboard navigation', async () => {
    /**
     * Why: Accessibility requirement - all interactive elements must be keyboard navigable.
     * What: Verifies that the button can be activated using Enter or Space keys.
     */
    const mockPost = vi.mocked(apiClient.POST);
    mockPost.mockResolvedValueOnce({
      data: { status: 'Agent run triggered successfully' },
      error: null
    });

    render(AgentQuickActions, {
      props: defaultProps
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    button.focus();

    // Test Enter key
    await fireEvent.keyDown(button, { key: 'Enter' });
    expect(mockPost).toHaveBeenCalledTimes(1);

    // Reset mock
    mockPost.mockClear();
    mockPost.mockResolvedValueOnce({
      data: { status: 'Agent run triggered successfully' },
      error: null
    });

    // Test Space key
    await fireEvent.keyDown(button, { key: ' ' });
    expect(mockPost).toHaveBeenCalledTimes(1);
  });

  it('shows tooltip on hover when disabled', async () => {
    /**
     * Why: Users need to understand why an action is unavailable.
     * What: Verifies that hovering over disabled button shows explanatory tooltip.
     */
    render(AgentQuickActions, {
      props: {
        ...defaultProps,
        isAgentActive: true
      }
    });

    const button = screen.getByRole('button', { name: /run agent now/i });
    await fireEvent.mouseEnter(button);

    expect(button).toHaveAttribute('title', 'Agent is currently active');
  });
});

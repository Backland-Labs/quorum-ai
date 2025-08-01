import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import AgentQuickActions from './AgentQuickActions.svelte';

// Mock the API client
vi.mock('$lib/api', () => ({
  apiClient: {
    POST: vi.fn()
  }
}));

describe('AgentQuickActions - Responsive Design', () => {
  const defaultProps = {
    spaceId: 'test.eth',
    isAgentActive: false
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should use responsive container sizing', () => {
    const { container } = render(AgentQuickActions, { props: defaultProps });

    const actionsContainer = container.querySelector('[data-testid="quick-actions"]');
    expect(actionsContainer?.classList.contains('w-full')).toBe(true);
    expect(actionsContainer?.classList.contains('sm:w-auto')).toBe(true);
  });

  it('should have mobile-friendly button sizing', () => {
    const { container } = render(AgentQuickActions, { props: defaultProps });

    const button = container.querySelector('button');
    // Full width on mobile, auto width on larger screens
    expect(button?.classList.contains('w-full')).toBe(true);
    expect(button?.classList.contains('sm:w-auto')).toBe(true);

    // Appropriate padding for touch targets
    expect(button?.classList.contains('px-4')).toBe(true);
    expect(button?.classList.contains('py-2')).toBe(true);
    expect(button?.classList.contains('sm:px-6')).toBe(true);
    expect(button?.classList.contains('sm:py-3')).toBe(true);

    // Minimum height for touch targets
    expect(button?.classList.contains('min-h-[44px]')).toBe(true);
  });

  it('should use responsive text sizes', () => {
    const { container } = render(AgentQuickActions, { props: defaultProps });

    const buttonText = container.querySelector('[data-testid="button-text"]');
    expect(buttonText?.classList.contains('text-sm')).toBe(true);
    expect(buttonText?.classList.contains('sm:text-base')).toBe(true);
  });

  it('should display loading state appropriately on mobile', async () => {
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.POST.mockImplementation(() => new Promise(() => {})); // Never resolves

    render(AgentQuickActions, { props: defaultProps });

    const button = screen.getByRole('button', { name: /run now/i });
    await fireEvent.click(button);

    // Check for loading spinner sizing
    const spinner = screen.getByTestId('loading-spinner');
    expect(spinner.classList.contains('w-4')).toBe(true);
    expect(spinner.classList.contains('h-4')).toBe(true);
    expect(spinner.classList.contains('sm:w-5')).toBe(true);
    expect(spinner.classList.contains('sm:h-5')).toBe(true);
  });

  it('should display feedback messages responsively', async () => {
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.POST.mockResolvedValue({
      data: { status: 'started' },
      error: undefined
    });

    const { container } = render(AgentQuickActions, { props: defaultProps });

    const button = screen.getByRole('button', { name: /run now/i });
    await fireEvent.click(button);

    await screen.findByText(/started successfully/i);

    const feedback = container.querySelector('[data-testid="feedback-message"]');
    expect(feedback?.classList.contains('text-xs')).toBe(true);
    expect(feedback?.classList.contains('sm:text-sm')).toBe(true);
    expect(feedback?.classList.contains('mt-2')).toBe(true);
    expect(feedback?.classList.contains('px-2')).toBe(true);
    expect(feedback?.classList.contains('sm:px-0')).toBe(true);
  });

  it('should handle disabled state appropriately', () => {
    const { container } = render(AgentQuickActions, {
      props: { ...defaultProps, isAgentActive: true }
    });

    const button = screen.getByRole('button');
    expect(button).toBeDisabled();

    // Visual feedback for disabled state
    expect(button.classList.contains('opacity-50')).toBe(true);
    expect(button.classList.contains('cursor-not-allowed')).toBe(true);
  });

  it('should be accessible with proper ARIA labels', () => {
    render(AgentQuickActions, { props: defaultProps });

    const button = screen.getByRole('button', { name: /run now/i });
    expect(button).toHaveAttribute('aria-label');

    // When agent is active
    const { rerender } = render(AgentQuickActions, {
      props: { ...defaultProps, isAgentActive: true }
    });

    const disabledButton = screen.getByRole('button');
    expect(disabledButton).toHaveAttribute('aria-label', expect.stringContaining('active'));
  });

  it('should handle touch events properly', async () => {
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.POST.mockResolvedValue({
      data: { status: 'started' },
      error: undefined
    });

    render(AgentQuickActions, { props: defaultProps });

    const button = screen.getByRole('button', { name: /run now/i });

    // Simulate touch event
    const touchEvent = new TouchEvent('touchstart', {
      touches: [{ clientX: 0, clientY: 0 } as Touch]
    });

    button.dispatchEvent(touchEvent);

    // Button should have visual feedback styles
    expect(button.classList.contains('hover:bg-blue-600')).toBe(true);
    expect(button.classList.contains('active:scale-95')).toBe(true);
  });

  it('should display component title responsively', () => {
    const { container } = render(AgentQuickActions, { props: defaultProps });

    const title = container.querySelector('[data-testid="actions-title"]');
    if (title) {
      expect(title.classList.contains('text-sm')).toBe(true);
      expect(title.classList.contains('sm:text-base')).toBe(true);
      expect(title.classList.contains('mb-2')).toBe(true);
      expect(title.classList.contains('sm:mb-3')).toBe(true);
    }
  });

  it('should handle error messages responsively', async () => {
    const { apiClient } = vi.mocked(await import('$lib/api'));
    apiClient.POST.mockResolvedValue({
      data: undefined,
      error: { message: 'Network error' }
    });

    const { container } = render(AgentQuickActions, { props: defaultProps });

    const button = screen.getByRole('button', { name: /run now/i });
    await fireEvent.click(button);

    await screen.findByText(/failed to start/i);

    const errorMessage = container.querySelector('[data-testid="error-message"]');
    expect(errorMessage?.classList.contains('text-xs')).toBe(true);
    expect(errorMessage?.classList.contains('sm:text-sm')).toBe(true);
    expect(errorMessage?.classList.contains('break-words')).toBe(true);
  });
});

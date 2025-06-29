import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/svelte';
import { renderComponent, mockOrganizationsResponse } from '../test-utils';
import HomePage from '../../routes/+page.svelte';

// Mock the API client
vi.mock('$lib/api', () => ({
  default: {
    GET: vi.fn()
  }
}));

// Mock the navigation
vi.mock('$app/navigation', () => ({
  goto: vi.fn()
}));

describe('Dashboard Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display organization cards with correct information', async () => {
    // Arrange: Mock successful API response
    const mockApiClient = await import('$lib/api');
    vi.mocked(mockApiClient.default.GET).mockResolvedValue({
      data: mockOrganizationsResponse,
      error: undefined,
      response: new Response()
    } as any);

    // Act: Render the component
    renderComponent(HomePage);

    // Assert: Loading state should show first
    expect(screen.getByText('Loading organizations...')).toBeInTheDocument();

    // Wait for the organizations to load
    await waitFor(() => {
      expect(screen.queryByText('Loading organizations...')).not.toBeInTheDocument();
    });

    // Assert: Organization cards should be displayed
    expect(screen.getByText('Compound')).toBeInTheDocument();
    expect(screen.getByText('@compound')).toBeInTheDocument();
    expect(screen.getByText('408 proposals')).toBeInTheDocument();
    expect(screen.getByText('1 chain')).toBeInTheDocument();

    expect(screen.getByText('Nouns DAO')).toBeInTheDocument();
    expect(screen.getByText('@nounsdao')).toBeInTheDocument();
    expect(screen.getByText('823 proposals')).toBeInTheDocument();
  });

  it('should handle API errors gracefully', async () => {
    // Arrange: Mock API error
    const mockApiClient = await import('$lib/api');
    vi.mocked(mockApiClient.default.GET).mockResolvedValue({
      data: undefined,
      error: { message: 'Failed to fetch organizations' },
      response: new Response()
    } as any);

    // Act: Render the component
    renderComponent(HomePage);

    // Assert: Wait for error state
    await waitFor(() => {
      expect(screen.getByText('Failed to load organizations')).toBeInTheDocument();
      expect(screen.getByText('Failed to fetch organizations')).toBeInTheDocument();
    });
  });

  it('should display empty state when no organizations are returned', async () => {
    // Arrange: Mock empty response
    const mockApiClient = await import('$lib/api');
    vi.mocked(mockApiClient.default.GET).mockResolvedValue({
      data: { organizations: [], processing_time: 0.1, model_used: 'test' },
      error: undefined,
      response: new Response()
    } as any);

    // Act: Render the component
    renderComponent(HomePage);

    // Assert: Wait for empty state (no cards)
    await waitFor(() => {
      expect(screen.queryByText('Loading organizations...')).not.toBeInTheDocument();
    });

    // Should not have any organization cards
    expect(screen.queryByText('Compound')).not.toBeInTheDocument();
    expect(screen.queryByText('Nouns DAO')).not.toBeInTheDocument();
  });

  it('should call the correct API endpoint', async () => {
    // Arrange: Mock API response
    const mockApiClient = await import('$lib/api');
    vi.mocked(mockApiClient.default.GET).mockResolvedValue({
      data: mockOrganizationsResponse,
      error: undefined,
      response: new Response()
    } as any);

    // Act: Render the component
    renderComponent(HomePage);

    // Assert: API should be called with correct endpoint
    await waitFor(() => {
      expect(mockApiClient.default.GET).toHaveBeenCalledWith('/organizations');
    });
  });

  it('should extract organization data from nested structure', async () => {
    // Arrange: Mock API response with nested structure
    const mockApiClient = await import('$lib/api');
    vi.mocked(mockApiClient.default.GET).mockResolvedValue({
      data: mockOrganizationsResponse,
      error: undefined,
      response: new Response()
    } as any);

    // Act: Render the component
    renderComponent(HomePage);

    // Assert: Organization data should be extracted correctly
    await waitFor(() => {
      // Verify that the organization name from nested structure is displayed
      expect(screen.getByText('Compound')).toBeInTheDocument();
      expect(screen.getByText('Nouns DAO')).toBeInTheDocument();
    });
  });

  describe('Dashboard Layout Requirements', () => {
    beforeEach(async () => {
      const mockApiClient = await import('$lib/api');
      vi.mocked(mockApiClient.default.GET).mockResolvedValue({
        data: mockOrganizationsResponse,
        error: undefined,
        response: new Response()
      } as any);
    });

    it('should display Dashboard title', async () => {
      renderComponent(HomePage);
      
      await waitFor(() => {
        expect(screen.getByText('Dashboard')).toBeInTheDocument();
      });
    });

    it('should display three tabs: Overview, Proposals, Activity', async () => {
      renderComponent(HomePage);
      
      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument();
        expect(screen.getByText('Proposals')).toBeInTheDocument();
        expect(screen.getByText('Activity')).toBeInTheDocument();
      });
    });

    it('should display organization dropdown in top-right area', async () => {
      renderComponent(HomePage);
      
      await waitFor(() => {
        expect(screen.getByRole('combobox', { name: /select organization/i })).toBeInTheDocument();
      });
    });

    it('should show Overview tab as active by default', async () => {
      renderComponent(HomePage);
      
      await waitFor(() => {
        const overviewTab = screen.getByRole('tab', { name: 'Overview' });
        expect(overviewTab).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('should switch tabs when clicked', async () => {
      renderComponent(HomePage);
      
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
      });

      const proposalsTab = screen.getByRole('tab', { name: 'Proposals' });
      await fireEvent.click(proposalsTab);

      expect(proposalsTab).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'false');
    });

    it('should maintain tab selection when switching organizations', async () => {
      renderComponent(HomePage);
      
      // Wait for initial load and switch to Proposals tab
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Proposals' })).toBeInTheDocument();
      });

      const proposalsTab = screen.getByRole('tab', { name: 'Proposals' });
      await fireEvent.click(proposalsTab);
      
      // Switch organization
      const dropdown = screen.getByRole('combobox', { name: /select organization/i });
      await fireEvent.click(dropdown);
      
      // Select a different organization (assuming dropdown options are loaded)
      const orgOption = screen.getByText('Nouns DAO');
      await fireEvent.click(orgOption);

      // Proposals tab should still be selected
      expect(screen.getByRole('tab', { name: 'Proposals' })).toHaveAttribute('aria-selected', 'true');
    });

    it('should populate organization dropdown from API', async () => {
      renderComponent(HomePage);
      
      await waitFor(() => {
        const dropdown = screen.getByRole('combobox', { name: /select organization/i });
        fireEvent.click(dropdown);
        
        expect(screen.getByText('Compound')).toBeInTheDocument();
        expect(screen.getByText('Nouns DAO')).toBeInTheDocument();
      });
    });

    it('should display organization data in Overview tab', async () => {
      renderComponent(HomePage);
      
      await waitFor(() => {
        // Should show overview content by default
        expect(screen.getByText('408 proposals')).toBeInTheDocument();
        expect(screen.getByText('1 chain')).toBeInTheDocument();
      });
    });
  });
});
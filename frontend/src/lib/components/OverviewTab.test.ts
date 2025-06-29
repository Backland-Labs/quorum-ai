import { render, screen, waitFor } from '@testing-library/svelte';
import { expect, test, describe, vi, beforeEach } from 'vitest';
import OverviewTab from './OverviewTab.svelte';
import type { components } from '$lib/api/client';

type OrganizationOverviewResponse = components["schemas"]["OrganizationOverviewResponse"];

vi.mock('$lib/api', () => ({
  default: {
    GET: vi.fn()
  }
}));

const mockOverviewData: OrganizationOverviewResponse = {
  organization_id: 'org-123',
  organization_name: 'Test DAO',
  organization_slug: 'test-dao',
  description: 'A test DAO for demonstration',
  delegate_count: 150,
  token_holder_count: 5000,
  total_proposals_count: 75,
  proposal_counts_by_status: {
    'ACTIVE': 5,
    'SUCCEEDED': 45,
    'DEFEATED': 20,
    'PENDING': 3,
    'EXECUTED': 2
  },
  recent_activity_count: 12,
  governance_participation_rate: 0.68
};

describe('OverviewTab', () => {
  let mockApiClient: any;

  beforeEach(async () => {
    vi.clearAllMocks();
    const apiModule = await import('$lib/api');
    mockApiClient = apiModule.default;
  });

  test('displays loading skeleton when data is being fetched', () => {
    mockApiClient.GET.mockImplementation(() => new Promise(() => {}));

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    expect(screen.getAllByTestId('loading-skeleton')).toHaveLength(6);
  });

  test('fetches and displays organization overview data successfully', async () => {
    mockApiClient.GET.mockResolvedValue({
      data: mockOverviewData,
      error: null
    });

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    await waitFor(() => {
      expect(screen.getByText('Test DAO')).toBeInTheDocument();
    });

    expect(screen.getByText('A test DAO for demonstration')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument(); // delegate_count
    expect(screen.getByText('5,000')).toBeInTheDocument(); // token_holder_count
    expect(screen.getByText('75')).toBeInTheDocument(); // total_proposals_count
    expect(screen.getByText('68%')).toBeInTheDocument(); // governance_participation_rate
  });

  test('displays proposal counts by status correctly', async () => {
    mockApiClient.GET.mockResolvedValue({
      data: mockOverviewData,
      error: null
    });

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument(); // ACTIVE
    });

    expect(screen.getByText('45')).toBeInTheDocument(); // SUCCEEDED
    expect(screen.getByText('20')).toBeInTheDocument(); // DEFEATED
    expect(screen.getByText('3')).toBeInTheDocument(); // PENDING
  });

  test('handles API error gracefully', async () => {
    mockApiClient.GET.mockResolvedValue({
      data: null,
      error: { message: 'Failed to fetch organization data' }
    });

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    await waitFor(() => {
      expect(screen.getByText('Failed to load organization overview')).toBeInTheDocument();
    });

    expect(screen.getByText('Failed to fetch organization data')).toBeInTheDocument();
  });

  test('displays retry button on error', async () => {
    mockApiClient.GET.mockResolvedValue({
      data: null,
      error: { message: 'Network error' }
    });

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
  });

  test('retries data fetch when retry button is clicked', async () => {
    mockApiClient.GET
      .mockResolvedValueOnce({
        data: null,
        error: { message: 'Network error' }
      })
      .mockResolvedValueOnce({
        data: mockOverviewData,
        error: null
      });

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /retry/i });
    retryButton.click();

    await waitFor(() => {
      expect(screen.getByText('Test DAO')).toBeInTheDocument();
    });

    expect(mockApiClient.GET).toHaveBeenCalledTimes(2);
  });

  test('calls API with correct organization ID', () => {
    mockApiClient.GET.mockResolvedValue({
      data: mockOverviewData,
      error: null
    });

    render(OverviewTab, {
      props: { organizationId: 'org-456' }
    });

    expect(mockApiClient.GET).toHaveBeenCalledWith('/organizations/{org_id}/overview', {
      params: {
        path: { org_id: 'org-456' }
      }
    });
  });

  test('updates data when organization ID changes', async () => {
    mockApiClient.GET.mockResolvedValue({
      data: mockOverviewData,
      error: null
    });

    const { rerender } = render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    expect(mockApiClient.GET).toHaveBeenCalledWith('/organizations/{org_id}/overview', {
      params: {
        path: { org_id: 'org-123' }
      }
    });

    rerender({ organizationId: 'org-456' });

    await waitFor(() => {
      expect(mockApiClient.GET).toHaveBeenCalledWith('/organizations/{org_id}/overview', {
        params: {
          path: { org_id: 'org-456' }
        }
      });
    });

    expect(mockApiClient.GET).toHaveBeenCalledTimes(2);
  });

  test('formats large numbers correctly', async () => {
    const largeNumberData = {
      ...mockOverviewData,
      token_holder_count: 1234567,
      delegate_count: 15000
    };

    mockApiClient.GET.mockResolvedValue({
      data: largeNumberData,
      error: null
    });

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    await waitFor(() => {
      expect(screen.getByText('1,234,567')).toBeInTheDocument();
    });

    expect(screen.getByText('15,000')).toBeInTheDocument();
  });

  test('handles missing description gracefully', async () => {
    const dataWithoutDescription = {
      ...mockOverviewData,
      description: null
    };

    mockApiClient.GET.mockResolvedValue({
      data: dataWithoutDescription,
      error: null
    });

    render(OverviewTab, {
      props: { organizationId: 'org-123' }
    });

    await waitFor(() => {
      expect(screen.getByText('Test DAO')).toBeInTheDocument();
    });

    expect(screen.queryByText('A test DAO for demonstration')).not.toBeInTheDocument();
  });
});
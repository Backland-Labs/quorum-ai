/*
 * Test suite for AgentDecisionsPanel component
 * 
 * These tests verify that the component correctly:
 * 1. Displays a loading state while fetching data
 * 2. Renders a list of voting decisions with all required information
 * 3. Shows correct data for each decision (title, vote, confidence)
 * 4. Handles empty state when no decisions exist
 * 5. Links to proposal details pages
 * 
 * Following TDD methodology - tests written before implementation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import AgentDecisionsPanel from './AgentDecisionsPanel.svelte';

// Mock the API client
vi.mock('$lib/api', () => ({
  apiClient: {
    GET: vi.fn()
  }
}));

// Mock the app environment
vi.mock('$app/environment', () => ({
  browser: true
}));

import { apiClient } from '$lib/api';

describe('AgentDecisionsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays loading state initially', () => {
    // Tests that the panel shows a loading indicator while fetching decisions
    // This ensures users see appropriate feedback during data loading
    const { container } = render(AgentDecisionsPanel);
    
    const loadingElement = container.querySelector('[data-testid="loading-state"]');
    expect(loadingElement).toBeTruthy();
    expect(loadingElement?.textContent).toContain('Loading');
  });

  it('renders a list of decisions', async () => {
    // Tests that the panel correctly renders a list of voting decisions
    // This verifies the core functionality of displaying agent decisions
    const mockDecisions = {
      decisions: [
        {
          proposal_id: 'proposal-1',
          proposal_title: 'Increase Treasury Allocation',
          vote: 'FOR',
          confidence_score: 0.85,
          voting_power: '1000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Aligns with growth objectives'
        },
        {
          proposal_id: 'proposal-2',
          proposal_title: 'Update Governance Parameters',
          vote: 'AGAINST',
          confidence_score: 0.72,
          voting_power: '1000.0',
          timestamp: '2024-01-19T15:45:00Z',
          reasoning: 'May introduce instability'
        }
      ],
      total_count: 2
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockDecisions,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const decisionsList = container.querySelector('[data-testid="decisions-list"]');
      expect(decisionsList).toBeTruthy();
      
      const decisionItems = container.querySelectorAll('[data-testid="decision-item"]');
      expect(decisionItems).toHaveLength(2);
    });
  });

  it('displays correct data for each decision', async () => {
    // Tests that each decision item shows all required information correctly
    // This ensures users can see proposal title, vote choice, and confidence
    const mockDecisions = {
      decisions: [
        {
          proposal_id: 'proposal-1',
          proposal_title: 'Test Proposal Title',
          vote: 'FOR',
          confidence_score: 0.95,
          voting_power: '5000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Strong support reasoning'
        }
      ],
      total_count: 1
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockDecisions,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      // Check proposal title
      const titleElement = container.querySelector('[data-testid="decision-title"]');
      expect(titleElement?.textContent).toBe('Test Proposal Title');
      
      // Check vote display
      const voteElement = container.querySelector('[data-testid="decision-vote"]');
      expect(voteElement?.textContent).toBe('FOR');
      expect(voteElement?.classList.toString()).toMatch(/green|emerald/); // FOR should be green
      
      // Check confidence score
      const confidenceElement = container.querySelector('[data-testid="decision-confidence"]');
      expect(confidenceElement?.textContent).toContain('95%');
    });
  });

  it('shows empty state when no decisions are available', async () => {
    // Tests that the panel displays an appropriate message when no decisions exist
    // This handles the edge case of a new installation or no voting activity
    const mockEmptyResponse = {
      decisions: [],
      total_count: 0
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockEmptyResponse,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const emptyState = container.querySelector('[data-testid="empty-state"]');
      expect(emptyState).toBeTruthy();
      expect(emptyState?.textContent).toContain('No voting decisions yet');
    });
  });

  it('handles API errors gracefully', async () => {
    // Tests that the panel displays an error message when the API fails
    // This ensures users are informed when something goes wrong
    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: null,
      error: { message: 'Failed to fetch decisions' }
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const errorElement = container.querySelector('[data-testid="error-state"]');
      expect(errorElement).toBeTruthy();
      expect(errorElement?.textContent).toContain('Unable to load decisions');
    });
  });

  it('creates links to proposal detail pages', async () => {
    // Tests that proposal titles are clickable links to detail pages
    // This enables users to view full proposal information
    const mockDecisions = {
      decisions: [
        {
          proposal_id: 'test-proposal-id',
          proposal_title: 'Clickable Proposal',
          vote: 'FOR',
          confidence_score: 0.80,
          voting_power: '1000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Test reasoning'
        }
      ],
      total_count: 1
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockDecisions,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const linkElement = container.querySelector('[data-testid="proposal-link"]');
      expect(linkElement).toBeTruthy();
      expect(linkElement?.getAttribute('href')).toBe('/proposals/test-proposal-id');
    });
  });

  it('formats timestamps in human-readable format', async () => {
    // Tests that decision timestamps are displayed in a user-friendly format
    // This improves readability by showing relative times like "2 hours ago"
    const mockDecisions = {
      decisions: [
        {
          proposal_id: 'proposal-1',
          proposal_title: 'Recent Decision',
          vote: 'FOR',
          confidence_score: 0.90,
          voting_power: '1000.0',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
          reasoning: 'Test'
        }
      ],
      total_count: 1
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockDecisions,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const timestampElement = container.querySelector('[data-testid="decision-timestamp"]');
      expect(timestampElement).toBeTruthy();
      expect(timestampElement?.textContent).toMatch(/hours? ago/);
    });
  });

  it('displays vote styling based on decision', async () => {
    // Tests that vote choices have appropriate visual styling
    // FOR votes should be green, AGAINST votes should be red
    const mockDecisions = {
      decisions: [
        {
          proposal_id: 'proposal-1',
          proposal_title: 'For Vote',
          vote: 'FOR',
          confidence_score: 0.85,
          voting_power: '1000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Support'
        },
        {
          proposal_id: 'proposal-2',
          proposal_title: 'Against Vote',
          vote: 'AGAINST',
          confidence_score: 0.75,
          voting_power: '1000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Oppose'
        }
      ],
      total_count: 2
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockDecisions,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const voteElements = container.querySelectorAll('[data-testid="decision-vote"]');
      expect(voteElements).toHaveLength(2);
      
      // First vote (FOR) should have green styling
      expect(voteElements[0]?.classList.toString()).toMatch(/green|emerald/);
      
      // Second vote (AGAINST) should have red styling
      expect(voteElements[1]?.classList.toString()).toMatch(/red|rose/);
    });
  });

  it('limits display to 5 most recent decisions', async () => {
    // Tests that only the 5 most recent decisions are displayed
    // This keeps the UI clean and focused on recent activity
    const mockDecisions = {
      decisions: Array.from({ length: 10 }, (_, i) => ({
        proposal_id: `proposal-${i}`,
        proposal_title: `Proposal ${i}`,
        vote: i % 2 === 0 ? 'FOR' : 'AGAINST',
        confidence_score: 0.80 + (i * 0.01),
        voting_power: '1000.0',
        timestamp: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
        reasoning: `Reasoning ${i}`
      })).slice(0, 5), // API should return only 5
      total_count: 10
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockDecisions,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const decisionItems = container.querySelectorAll('[data-testid="decision-item"]');
      expect(decisionItems).toHaveLength(5);
    });

    // Verify the API was called with limit parameter
    expect(apiClient.GET).toHaveBeenCalledWith('/agent-run/decisions', {
      params: { query: { limit: 5 } }
    });
  });

  it('displays confidence scores with appropriate color coding', async () => {
    // Tests that confidence scores are color-coded based on value
    // High confidence (>80%) green, medium (60-80%) yellow, low (<60%) red
    const mockDecisions = {
      decisions: [
        {
          proposal_id: 'high-conf',
          proposal_title: 'High Confidence',
          vote: 'FOR',
          confidence_score: 0.92,
          voting_power: '1000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Very confident'
        },
        {
          proposal_id: 'med-conf',
          proposal_title: 'Medium Confidence',
          vote: 'FOR',
          confidence_score: 0.70,
          voting_power: '1000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Moderately confident'
        },
        {
          proposal_id: 'low-conf',
          proposal_title: 'Low Confidence',
          vote: 'AGAINST',
          confidence_score: 0.45,
          voting_power: '1000.0',
          timestamp: '2024-01-20T10:30:00Z',
          reasoning: 'Low confidence'
        }
      ],
      total_count: 3
    };

    vi.mocked(apiClient.GET).mockResolvedValueOnce({
      data: mockDecisions,
      error: null
    });

    const { container } = render(AgentDecisionsPanel);

    await waitFor(() => {
      const confidenceElements = container.querySelectorAll('[data-testid="decision-confidence"]');
      expect(confidenceElements).toHaveLength(3);
      
      // High confidence should have green styling
      expect(confidenceElements[0]?.classList.toString()).toMatch(/green|emerald/);
      
      // Medium confidence should have yellow/amber styling
      expect(confidenceElements[1]?.classList.toString()).toMatch(/yellow|amber/);
      
      // Low confidence should have red styling
      expect(confidenceElements[2]?.classList.toString()).toMatch(/red|rose/);
    });
  });
});
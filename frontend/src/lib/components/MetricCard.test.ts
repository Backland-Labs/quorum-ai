import { render, screen } from '@testing-library/svelte';
import { expect, test, describe } from 'vitest';
import MetricCard from './MetricCard.svelte';

describe('MetricCard', () => {
  test('renders metric with title and value', () => {
    render(MetricCard, {
      props: {
        title: 'Total Proposals',
        value: '150'
      }
    });

    expect(screen.getByText('Total Proposals')).toBeInTheDocument();
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  test('renders metric with description when provided', () => {
    render(MetricCard, {
      props: {
        title: 'Active Proposals',
        value: '25',
        description: 'Currently open for voting'
      }
    });

    expect(screen.getByText('Active Proposals')).toBeInTheDocument();
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('Currently open for voting')).toBeInTheDocument();
  });

  test('renders metric with icon when provided', () => {
    render(MetricCard, {
      props: {
        title: 'Delegates',
        value: '500',
        icon: 'users'
      }
    });

    expect(screen.getByText('Delegates')).toBeInTheDocument();
    expect(screen.getByText('500')).toBeInTheDocument();
    expect(screen.getByTestId('metric-icon')).toBeInTheDocument();
  });

  test('applies loading state styling when loading prop is true', () => {
    render(MetricCard, {
      props: {
        title: 'Token Holders',
        value: '1,234',
        loading: true
      }
    });

    const card = screen.getByTestId('metric-card');
    expect(card).toHaveClass('animate-pulse');
  });

  test('renders with trend indicator when provided', () => {
    render(MetricCard, {
      props: {
        title: 'Participation Rate',
        value: '75%',
        trend: 'up',
        trendValue: '+5%'
      }
    });

    expect(screen.getByText('Participation Rate')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('+5%')).toBeInTheDocument();
    expect(screen.getByTestId('trend-indicator')).toBeInTheDocument();
  });

  test('applies correct styling for different trend directions', () => {
    const { rerender } = render(MetricCard, {
      props: {
        title: 'Test Metric',
        value: '100',
        trend: 'up',
        trendValue: '+10%'
      }
    });

    let trendElement = screen.getByTestId('trend-indicator');
    expect(trendElement).toHaveClass('text-green-600');

    rerender({
      title: 'Test Metric',
      value: '100',
      trend: 'down',
      trendValue: '-5%'
    });

    trendElement = screen.getByTestId('trend-indicator');
    expect(trendElement).toHaveClass('text-red-600');
  });

  test('handles large numbers with proper formatting', () => {
    render(MetricCard, {
      props: {
        title: 'Total Value',
        value: '1,234,567'
      }
    });

    expect(screen.getByText('Total Value')).toBeInTheDocument();
    expect(screen.getByText('1,234,567')).toBeInTheDocument();
  });
});

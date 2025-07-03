import { render, screen } from '@testing-library/svelte';
import { expect, test, describe } from 'vitest';
import LoadingSkeleton from './LoadingSkeleton.svelte';

describe('LoadingSkeleton', () => {
  test('renders skeleton with default props', () => {
    render(LoadingSkeleton);

    const skeleton = screen.getByTestId('loading-skeleton');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveClass('animate-pulse');
  });

  test('renders skeleton with custom height', () => {
    render(LoadingSkeleton, {
      props: {
        height: 'h-32'
      }
    });

    const skeleton = screen.getByTestId('loading-skeleton');
    expect(skeleton).toHaveClass('h-32');
  });

  test('renders skeleton with custom width', () => {
    render(LoadingSkeleton, {
      props: {
        width: 'w-1/2'
      }
    });

    const skeleton = screen.getByTestId('loading-skeleton');
    expect(skeleton).toHaveClass('w-1/2');
  });

  test('renders skeleton with rounded corners when specified', () => {
    render(LoadingSkeleton, {
      props: {
        rounded: true
      }
    });

    const skeleton = screen.getByTestId('loading-skeleton');
    expect(skeleton).toHaveClass('rounded-lg');
  });

  test('renders skeleton without rounded corners by default', () => {
    render(LoadingSkeleton);

    const skeleton = screen.getByTestId('loading-skeleton');
    expect(skeleton).not.toHaveClass('rounded-lg');
  });

  test('renders multiple skeleton lines when count is specified', () => {
    render(LoadingSkeleton, {
      props: {
        count: 3
      }
    });

    const skeletons = screen.getAllByTestId('loading-skeleton');
    expect(skeletons).toHaveLength(3);
    skeletons.forEach(skeleton => {
      expect(skeleton).toHaveClass('animate-pulse');
    });
  });

  test('renders skeleton with custom classes', () => {
    render(LoadingSkeleton, {
      props: {
        className: 'custom-class'
      }
    });

    const skeleton = screen.getByTestId('loading-skeleton');
    expect(skeleton).toHaveClass('custom-class');
  });

  test('combines all props correctly', () => {
    render(LoadingSkeleton, {
      props: {
        height: 'h-16',
        width: 'w-3/4',
        rounded: true,
        className: 'custom-skeleton'
      }
    });

    const skeleton = screen.getByTestId('loading-skeleton');
    expect(skeleton).toHaveClass('h-16', 'w-3/4', 'rounded-lg', 'custom-skeleton', 'animate-pulse');
  });
});

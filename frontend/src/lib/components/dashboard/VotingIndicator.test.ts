import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import VotingIndicator from './VotingIndicator.svelte';

describe('VotingIndicator', () => {
  it('renders with active state', () => {
    const { container } = render(VotingIndicator, {
      props: {
        votesFor: '1000000000000000000',
        votesAgainst: '500000000000000000',
        votesAbstain: '100000000000000000',
        state: 'ACTIVE'
      }
    });
    
    const stateSpan = container.querySelector('span.bg-emerald-500');
    expect(stateSpan).toBeTruthy();
    expect(stateSpan?.textContent).toBe('Active');
  });
  
  it('calculates vote percentages correctly', () => {
    const { container } = render(VotingIndicator, {
      props: {
        votesFor: '600',
        votesAgainst: '300',
        votesAbstain: '100',
        state: 'ACTIVE'
      }
    });
    
    const percentages = container.querySelectorAll('.text-gray-700');
    expect(percentages[1]?.textContent).toBe('60%');
    expect(percentages[2]?.textContent).toBe('30%');
    expect(percentages[3]?.textContent).toBe('10%');
  });
  
  it('shows no votes message when totalVotes is zero', () => {
    const { container } = render(VotingIndicator, {
      props: {
        votesFor: '0',
        votesAgainst: '0',
        votesAbstain: '0',
        state: 'ACTIVE'
      }
    });
    
    const noVotesMessage = container.querySelector('p.text-gray-500');
    expect(noVotesMessage).toBeTruthy();
    expect(noVotesMessage?.textContent).toBe('No votes cast yet');
  });
  
  it('renders different state badges correctly', () => {
    const states = [
      { state: 'SUCCEEDED', class: 'bg-green-500', label: 'Succeeded' },
      { state: 'DEFEATED', class: 'bg-red-500', label: 'Defeated' },
      { state: 'EXECUTED', class: 'bg-blue-500', label: 'Executed' },
      { state: 'QUEUED', class: 'bg-yellow-500', label: 'Queued' },
      { state: 'CANCELED', class: 'bg-gray-500', label: 'Canceled' },
      { state: 'EXPIRED', class: 'bg-orange-500', label: 'Expired' },
      { state: 'PENDING', class: 'bg-indigo-500', label: 'Pending' }
    ];
    
    states.forEach(({ state, class: className, label }) => {
      const { container } = render(VotingIndicator, {
        props: {
          votesFor: '100',
          votesAgainst: '50',
          votesAbstain: '10',
          state
        }
      });
      
      const stateSpan = container.querySelector(`span.${className}`);
      expect(stateSpan).toBeTruthy();
      expect(stateSpan?.textContent).toBe(label);
    });
  });
  
  it('hides abstain bar when no abstain votes', () => {
    const { container } = render(VotingIndicator, {
      props: {
        votesFor: '100',
        votesAgainst: '50',
        votesAbstain: '0',
        state: 'ACTIVE'
      }
    });
    
    const abstainText = Array.from(container.querySelectorAll('span')).find(el => 
      el.textContent === 'Abstain'
    );
    expect(abstainText).toBeFalsy();
  });
  
  it('formats large vote numbers correctly', () => {
    const { container } = render(VotingIndicator, {
      props: {
        votesFor: '5000000000000000000',
        votesAgainst: '3000000000000000000',
        votesAbstain: '0',
        state: 'ACTIVE'
      }
    });
    
    const totalVotesSpan = container.querySelector('.font-medium');
    expect(totalVotesSpan?.textContent).toBe('8');
  });
});
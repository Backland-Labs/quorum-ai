<script lang="ts">
  import type { components } from '$lib/api/client.js';

  // Constants
  const ADDRESS_TRUNCATE_LENGTH = 10;
  const ADDRESS_START_CHARS = 6;
  const ADDRESS_END_CHARS = 4;
  const LARGE_AMOUNT_THRESHOLD = 1e21;
  const WEI_CONVERSION_FACTOR = 1e18;
  const EXPONENTIAL_NOTATION_PRECISION = 2;

  type ProposalVoter = components['schemas']['ProposalVoter'];
  type VoteType = components['schemas']['VoteType'];

  interface Props {
    voter: ProposalVoter;
    index: number;
    totalVoters: number;
  }

  let { voter, index, totalVoters }: Props = $props();

  // Utility functions
  function truncateAddress(address: string): string {
    if (address.length <= ADDRESS_TRUNCATE_LENGTH) return address;
    return `${address.slice(0, ADDRESS_START_CHARS)}...${address.slice(-ADDRESS_END_CHARS)}`;
  }

  function formatVotingPower(amount: string): string {
    try {
      const num = parseFloat(amount);
      if (num >= LARGE_AMOUNT_THRESHOLD) {
        return (num / WEI_CONVERSION_FACTOR).toExponential(EXPONENTIAL_NOTATION_PRECISION);
      }
      return new Intl.NumberFormat('en-US').format(num / WEI_CONVERSION_FACTOR);
    } catch {
      return amount;
    }
  }

  function getVoteBadgeClasses(voteType: VoteType): string {
    const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium';
    
    switch (voteType) {
      case 'FOR':
        return `${baseClasses} bg-green-100 text-green-800`;
      case 'AGAINST':
        return `${baseClasses} bg-red-100 text-red-800`;
      case 'ABSTAIN':
        return `${baseClasses} bg-yellow-100 text-yellow-800`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`;
    }
  }

  // Computed properties
  let displayAddress = $derived(truncateAddress(voter.address));
  let displayVotingPower = $derived(formatVotingPower(voter.amount));
  let voteBadgeClasses = $derived(getVoteBadgeClasses(voter.vote_type));
  let voterRank = $derived(index + 1);
  let voterAriaLabel = $derived(`Voter ${voterRank} of ${totalVoters}`);
</script>

<div 
  class="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
  data-testid="voter-item"
  role="listitem"
  aria-label={voterAriaLabel}
>
  <div class="flex items-center space-x-4">
    <div class="flex-shrink-0">
      <div class="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center">
        <span class="text-sm font-medium text-gray-600">
          {voterRank}
        </span>
      </div>
    </div>
    <div class="flex-1 min-w-0">
      <p class="text-sm font-medium text-gray-900 truncate" data-testid="voter-address">
        {displayAddress}
      </p>
      <p class="text-sm text-gray-500" data-testid="voting-power">
        {displayVotingPower} votes
      </p>
    </div>
  </div>
  <div class="flex items-center space-x-2">
    <span 
      class={voteBadgeClasses}
      data-testid="vote-badge"
      aria-label="Vote: {voter.vote_type}"
    >
      {voter.vote_type}
    </span>
  </div>
</div>
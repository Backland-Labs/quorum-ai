<script lang="ts">
  import { parseProposalSummary, cleanProposalTitle, calculateConfidencePercentage } from '$lib/utils/proposals.js';
  
  interface Props {
    proposal: any;
    variant?: 'compact' | 'detailed';
  }
  
  let { proposal, variant = 'compact' }: Props = $props();
  
  function validateProps(): void {
    console.assert(proposal !== null, 'Proposal should not be null');
    console.assert(proposal !== undefined, 'Proposal should not be undefined');
  }
  
  function getRiskLevelClasses(riskLevel: string): string {
    console.assert(typeof riskLevel === 'string', 'Risk level must be a string');
    console.assert(riskLevel.length > 0, 'Risk level should not be empty');
    
    const riskClasses: Record<string, string> = {
      'LOW': 'bg-green-50 text-green-700 border-green-200',
      'MEDIUM': 'bg-yellow-50 text-yellow-700 border-yellow-200',
      'HIGH': 'bg-red-50 text-red-700 border-red-200'
    };
    return riskClasses[riskLevel] || riskClasses['MEDIUM'];
  }
  
  function getRecommendationClasses(recommendation: string): string {
    console.assert(typeof recommendation === 'string', 'Recommendation must be a string');
    console.assert(recommendation.length > 0, 'Recommendation should not be empty');
    
    const recClasses: Record<string, string> = {
      'APPROVE': 'bg-green-100 text-green-800',
      'REJECT': 'bg-red-100 text-red-800'
    };
    return recClasses[recommendation] || 'bg-gray-100 text-gray-800';
  }
  
  const parsedProposal = parseProposalSummary(proposal);
  validateProps();
</script>

<div class="group relative">
  <div class="relative bg-white border border-secondary-200 rounded-lg p-5 hover:border-primary-300 hover:shadow-md transition-all duration-200">
    <!-- Header with title and badges -->
    <div class="flex items-start justify-between mb-3">
      <h5 class="font-semibold text-secondary-900 text-base leading-tight pr-4">
        {cleanProposalTitle(proposal.title)}
      </h5>
      <div class="flex items-center gap-2 flex-shrink-0">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border {getRiskLevelClasses(parsedProposal.risk_level)}">
          {parsedProposal.risk_level} Risk
        </span>
      </div>
    </div>

    <!-- Summary -->
    <p class="text-sm text-secondary-600 leading-relaxed mb-4">
      {parsedProposal.summary}
    </p>

    <!-- Key Points (if available and detailed variant) -->
    {#if variant === 'detailed' && parsedProposal.key_points && parsedProposal.key_points.length > 0}
      <div class="mb-4">
        <h6 class="text-xs font-medium text-secondary-700 mb-2">Key Highlights</h6>
        <div class="space-y-1">
          {#each parsedProposal.key_points.slice(0, 2) as point}
            <div class="flex items-start text-xs text-secondary-600">
              <div class="flex-shrink-0 w-1.5 h-1.5 bg-primary-400 rounded-full mt-1.5 mr-2"></div>
              <span class="leading-relaxed">{point}</span>
            </div>
          {/each}
          {#if parsedProposal.key_points.length > 2}
            <div class="text-xs text-secondary-500 ml-3.5">
              +{parsedProposal.key_points.length - 2} more points
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Footer with recommendation and confidence -->
    <div class="flex items-center justify-between pt-3 border-t border-secondary-100">
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium {getRecommendationClasses(parsedProposal.recommendation)}">
          {parsedProposal.recommendation}
        </span>
      </div>
      <div class="flex items-center text-xs text-secondary-500">
        <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2a2 2 0 00-2 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2v-6a2 2 0 00-2-2H5a2 2 0 01-2-2V5a2 2 0 012-2h2a2 2 0 012 2v4a2 2 0 01-2 2h-2z" />
        </svg>
        {calculateConfidencePercentage(parsedProposal.confidence_score)}% confidence
      </div>
    </div>
  </div>
</div>
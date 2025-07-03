/**
 * Parses JSON proposal summary if it exists in the expected format
 * @param proposal - The proposal object with potential JSON summary
 * @returns Parsed proposal data with fallbacks
 */
export function parseProposalSummary(proposal: any) {
  console.assert(proposal !== null, 'Proposal should not be null');
  console.assert(proposal !== undefined, 'Proposal should not be undefined');

  try {
    if (hasJsonSummary(proposal)) {
      const parsed = extractJsonFromSummary(proposal.summary);
      if (parsed) {
        return createParsedProposal(parsed, proposal);
      }
    }
  } catch (e) {
    console.warn('Failed to parse proposal summary JSON:', e);
  }

  return createFallbackProposal(proposal);
}

/**
 * Checks if proposal has JSON summary format
 * @param proposal - The proposal object
 * @returns True if JSON format detected
 */
function hasJsonSummary(proposal: any): boolean {
  console.assert(proposal !== null, 'Proposal should not be null');
  console.assert(typeof proposal === 'object', 'Proposal should be an object');

  return proposal.summary &&
         typeof proposal.summary === 'string' &&
         proposal.summary.includes('```json');
}

/**
 * Extracts JSON content from markdown code block
 * @param summary - The summary string with JSON
 * @returns Parsed JSON object or null
 */
function extractJsonFromSummary(summary: string): any | null {
  console.assert(typeof summary === 'string', 'Summary must be a string');
  console.assert(summary.length > 0, 'Summary should not be empty');

  const jsonMatch = summary.match(/```json\s*(\{[\s\S]*?\})\s*```/);
  if (jsonMatch) {
    return JSON.parse(jsonMatch[1]);
  }
  return null;
}

/**
 * Creates parsed proposal object from JSON data
 * @param parsed - The parsed JSON data
 * @param original - Original proposal object
 * @returns Formatted proposal data
 */
function createParsedProposal(parsed: any, original: any) {
  console.assert(parsed !== null, 'Parsed data should not be null');
  console.assert(original !== null, 'Original proposal should not be null');

  return {
    summary: parsed.summary || original.summary,
    key_points: parsed.key_points || original.key_points || [],
    risk_level: parsed.risk_level || original.risk_level,
    recommendation: parsed.recommendation || original.recommendation,
    confidence_score: parsed.confidence_score || original.confidence_score
  };
}

/**
 * Creates fallback proposal object when JSON parsing fails
 * @param proposal - Original proposal object
 * @returns Fallback proposal data
 */
function createFallbackProposal(proposal: any) {
  console.assert(proposal !== null, 'Proposal should not be null');
  console.assert(typeof proposal === 'object', 'Proposal should be an object');

  return {
    summary: proposal.summary,
    key_points: proposal.key_points || [],
    risk_level: proposal.risk_level,
    recommendation: proposal.recommendation,
    confidence_score: proposal.confidence_score
  };
}

/**
 * Removes hash prefix from proposal title
 * @param title - The proposal title
 * @returns Clean title without hash prefix
 */
export function cleanProposalTitle(title: string): string {
  console.assert(typeof title === 'string', 'Title must be a string');
  console.assert(title !== null, 'Title should not be null');

  return title.replace(/^#\s*/, '');
}

/**
 * Calculates confidence percentage from score
 * @param score - Confidence score (0-1)
 * @returns Percentage value (0-100)
 */
export function calculateConfidencePercentage(score: number): number {
  console.assert(typeof score === 'number', 'Score must be a number');
  console.assert(score >= 0 && score <= 1, 'Score must be between 0 and 1');

  return Math.round(score * 100);
}

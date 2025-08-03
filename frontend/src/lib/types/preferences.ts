/**
 * Voting strategies for autonomous agent decision making
 */
export type VotingStrategy = 'conservative' | 'balanced' | 'aggressive';

/**
 * User preferences for the autonomous voting agent
 */
export interface UserPreferences {
	/**
	 * The voting strategy to use
	 */
	voting_strategy: VotingStrategy;

	/**
	 * Minimum confidence threshold (0.0 to 1.0) required to cast a vote
	 */
	confidence_threshold: number;

	/**
	 * Maximum number of proposals to analyze per agent run
	 */
	max_proposals_per_run: number;

	/**
	 * List of wallet addresses whose proposals should be automatically rejected
	 */
	blacklisted_proposers?: string[];

	/**
	 * List of wallet addresses whose proposals should receive priority consideration
	 */
	whitelisted_proposers?: string[];
}

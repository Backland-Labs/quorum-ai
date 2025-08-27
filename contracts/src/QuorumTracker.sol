// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title IQuorumTracker
 * @dev Interface for the QuorumTracker contract required by Autonolas.
 */
interface IQuorumTracker {
    /**
     * @notice Gets the voting statistics for a given multisig address.
     * @param multisig The address of the multisig to get stats for.
     * @return A 3-element array of uint256 containing the stats.
     */
    function getVotingStats(address multisig) external view returns (uint256[] memory);
}

/**
 * @title QuorumTracker
 * @dev A contract to track voting and proposal consideration activity for multisig addresses.
 * This contract is owned and can only be updated by the owner (the backend service).
 */
contract QuorumTracker is IQuorumTracker, Ownable {
    // --- Constants ---
    uint8 public constant VOTES_CAST = 0;
    uint8 public constant OPPORTUNITIES_CONSIDERED = 1;
    uint8 public constant NO_OPPORTUNITIES = 2;

    // --- State ---
    /// @dev Stores the activity stats for each multisig address.
    /// The array indices correspond to the activity types defined in the constants.
    mapping(address => uint256[3]) public stats;

    // --- Constructor ---
    /**
     * @dev Sets the initial owner of the contract.
     * @param initialOwner The address of the initial owner.
     */
    constructor(address initialOwner) Ownable(initialOwner) {}

    // --- External Functions ---
    /**
     * @notice Registers an activity for a given multisig address.
     * @dev This function can only be called by the owner of the contract.
     *      It increments the counter for the specified activity type.
     * @param multisig The address of the multisig to register activity for.
     * @param activityType The type of activity to register. Must be 0, 1, or 2.
     */
    function register(address multisig, uint8 activityType) external onlyOwner {
        require(activityType <= NO_OPPORTUNITIES, "QuorumTracker: Invalid activity type");
        stats[multisig][activityType]++;
    }

    /**
     * @notice Gets the voting statistics for a given multisig address.
     * @param multisig The address of the multisig to get stats for.
     * @return result A 3-element array of uint256 containing the stats:
     *         - Index 0: Votes cast
     *         - Index 1: Opportunities considered
     *         - Index 2: No opportunities
     */
    function getVotingStats(address multisig) external view override returns (uint256[] memory result) {
        result = new uint256[](3);
        result[VOTES_CAST] = stats[multisig][VOTES_CAST];
        result[OPPORTUNITIES_CONSIDERED] = stats[multisig][OPPORTUNITIES_CONSIDERED];
        result[NO_OPPORTUNITIES] = stats[multisig][NO_OPPORTUNITIES];
    }
}
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

// QuorumTracker interface
interface IQuorumTracker {
    function getVotingStats(address multisig) external view returns (uint256[] memory votingStats);
}

// Multisig interface
interface IMultisig {
    function nonce() external view returns (uint256);
}

/// @dev Zero address error
error ZeroAddress();

/// @title QuorumStakingTokenActivityChecker
contract QuorumStakingTokenActivityChecker {
    address public immutable quorumTracker;
    uint256 public immutable livenessRatio;

    constructor(address _quorumTracker, uint256 _livenessRatio) {
        if (_quorumTracker == address(0)) {
            revert ZeroAddress();
        }
        quorumTracker = _quorumTracker;
        livenessRatio = _livenessRatio;
    }

    function getMultisigNonces(address multisig) external view returns (uint256[] memory nonces) {
        uint256[] memory votingStats = IQuorumTracker(quorumTracker).getVotingStats(multisig);

        nonces = new uint256[](4);
        nonces[0] = IMultisig(multisig).nonce();
        nonces[1] = votingStats[0];
        nonces[2] = votingStats[1];
        nonces[3] = votingStats[2];
    }

    function isRatioPass(
        uint256[] memory curNonces,
        uint256[] memory lastNonces,
        uint256 ts
    ) external view returns (bool ratioPass) {
        if (ts > 0 && curNonces[0] > lastNonces[0]) {
            uint256 ratio;
            if (curNonces[1] > lastNonces[1]) {
                ratio = ((curNonces[1] - lastNonces[1]) * 1e18) / ts;
                ratioPass = (ratio >= livenessRatio);
            } else {
                // Staking rewards achieved if the agent places at least 2x attestations for either:
                // - Voting opportunity considered, but not voted;
                // - No voting opportunity is available
                ratio = (((curNonces[2] - lastNonces[2]) + (curNonces[3] - lastNonces[3])) * 1e18) / ts;
                // Note that livenessRatio has a coefficient of 2
                ratioPass = (ratio >= 2 * livenessRatio);
            }
        }
    }
}

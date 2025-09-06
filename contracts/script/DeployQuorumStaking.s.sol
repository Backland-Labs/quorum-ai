// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {QuorumStakingTokenActivityChecker} from "../src/QuorumStakingTokenActivityChecker.sol";

/**
 * @title DeployQuorumStakingScript
 * @dev Deployment script for the QuorumStakingTokenActivityChecker contract.
 * This script deploys the QuorumStakingTokenActivityChecker contract with proper configuration
 * for tracking multisig activity and liveness ratios.
 */
contract DeployQuorumStakingScript is Script {
    /**
     * @notice Main deployment function.
     * @dev Deploys QuorumStakingTokenActivityChecker contract with quorum tracker and liveness ratio from environment variables.
     * @return quorumStakingChecker The deployed QuorumStakingTokenActivityChecker contract instance.
     */
    function run() public returns (QuorumStakingTokenActivityChecker quorumStakingChecker) {
        // Get the deployer's private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Get the attestation tracker address from environment (serves as quorum tracker)
        address attestationTrackerAddress = vm.envAddress("ATTESTATION_TRACKER_ADDRESS");

        // Get the liveness ratio from environment, default to 1e15 if not set
        uint256 livenessRatio;
        try vm.envUint("LIVENESS_RATIO") returns (uint256 ratio) {
            livenessRatio = ratio;
        } catch {
            livenessRatio = 1e15; // Default value
            console.log("LIVENESS_RATIO not set, using default:", livenessRatio);
        }

        // Validate addresses
        require(attestationTrackerAddress != address(0), "Attestation tracker address cannot be zero");

        // Get deployer address for logging
        address deployer = vm.addr(deployerPrivateKey);

        console.log("=== QuorumStakingTokenActivityChecker Deployment ===");
        console.log("Deployer:", deployer);
        console.log("Attestation Tracker (QuorumTracker):", attestationTrackerAddress);
        console.log("Liveness Ratio:", livenessRatio);

        vm.startBroadcast(deployerPrivateKey);

        // Deploy the QuorumStakingTokenActivityChecker contract
        quorumStakingChecker = new QuorumStakingTokenActivityChecker(
            attestationTrackerAddress,
            livenessRatio
        );

        vm.stopBroadcast();

        // Log deployment information
        console.log("QuorumStakingTokenActivityChecker deployed to:", address(quorumStakingChecker));
        console.log("Deployment successful!");

        // Verify deployment
        require(address(quorumStakingChecker) != address(0), "Deployment failed");
        require(quorumStakingChecker.quorumTracker() == attestationTrackerAddress, "QuorumTracker not set correctly");
        require(quorumStakingChecker.livenessRatio() == livenessRatio, "Liveness ratio not set correctly");

        console.log("=== Deployment Verification ===");
        console.log("QuorumTracker address verified:", quorumStakingChecker.quorumTracker());
        console.log("Liveness ratio verified:", quorumStakingChecker.livenessRatio());

        return quorumStakingChecker;
    }
}

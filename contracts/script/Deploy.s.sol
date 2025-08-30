// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {AttestationTracker} from "../src/AttestationTracker.sol";

/**
 * @title DeployScript
 * @dev Deployment script for the AttestationTracker contract.
 * This script deploys the minimal attestation tracking contract with proper ownership
 * and EAS integration, following the DualStakingToken pattern.
 */
contract DeployScript is Script {
    /**
     * @notice Main deployment function.
     * @dev Deploys AttestationTracker contract with owner and EAS address from environment variables.
     * @return attestationTracker The deployed AttestationTracker contract instance.
     */
    function run() public returns (AttestationTracker attestationTracker) {
        // Get the deployer's private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");

        // Get the owner address from environment
        address owner = vm.envAddress("ATTESTATION_TRACKER_OWNER");

        // Get the EAS contract address from environment
        address easAddress = vm.envAddress("EAS_CONTRACT_ADDRESS");

        // Validate addresses
        require(owner != address(0), "Owner address cannot be zero");
        require(easAddress != address(0), "EAS address cannot be zero");

        // Get deployer address for logging
        address deployer = vm.addr(deployerPrivateKey);

        console.log("=== AttestationTracker Deployment ===");
        console.log("Deployer:", deployer);
        console.log("Contract Owner:", owner);
        console.log("EAS Address:", easAddress);

        vm.startBroadcast(deployerPrivateKey);

        // Deploy the AttestationTracker contract
        attestationTracker = new AttestationTracker(owner, easAddress);

        vm.stopBroadcast();

        // Log deployment information
        console.log("AttestationTracker deployed to:", address(attestationTracker));
        console.log("Deployment successful!");

        // Verify deployment
        require(address(attestationTracker) != address(0), "Deployment failed");
        require(attestationTracker.owner() == owner, "Owner not set correctly");
        require(attestationTracker.EAS() == easAddress, "EAS address not set correctly");

        console.log("=== Deployment Verification ===");
        console.log("Contract owner verified:", attestationTracker.owner());
        console.log("EAS address verified:", attestationTracker.EAS());

        // Test initial state
        address testMultisig = makeAddr("test");
        console.log("Initial attestation count for test address:", attestationTracker.getNumAttestations(testMultisig));

        return attestationTracker;
    }
}

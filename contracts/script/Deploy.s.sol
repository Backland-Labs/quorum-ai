// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {QuorumTracker} from "../src/QuorumTracker.sol";

/**
 * @title DeployScript
 * @dev Deployment script for the QuorumTracker contract.
 * This script deploys the contract with proper ownership and logs the deployed address.
 */
contract DeployScript is Script {
    /**
     * @notice Main deployment function.
     * @dev Deploys QuorumTracker contract with owner from environment variable.
     * @return quorumTracker The deployed QuorumTracker contract instance.
     */
    function run() public returns (QuorumTracker quorumTracker) {
        // Get the deployer's private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        // Get the owner address from environment
        address owner = vm.envAddress("QUORUM_TRACKER_OWNER");
        
        // Validate owner address
        require(owner != address(0), "Owner address cannot be zero");
        
        // Get deployer address for logging
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("=== QuorumTracker Deployment ===");
        console.log("Deployer:", deployer);
        console.log("Contract Owner:", owner);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy the QuorumTracker contract
        quorumTracker = new QuorumTracker(owner);
        
        vm.stopBroadcast();
        
        // Log deployment information
        console.log("QuorumTracker deployed to:", address(quorumTracker));
        console.log("Deployment successful!");
        
        // Verify deployment
        require(address(quorumTracker) != address(0), "Deployment failed");
        require(quorumTracker.owner() == owner, "Owner not set correctly");
        
        console.log("=== Deployment Verification ===");
        console.log("Contract owner verified:", quorumTracker.owner());
        console.log("VOTES_CAST constant:", quorumTracker.VOTES_CAST());
        console.log("OPPORTUNITIES_CONSIDERED constant:", quorumTracker.OPPORTUNITIES_CONSIDERED());
        console.log("NO_OPPORTUNITIES constant:", quorumTracker.NO_OPPORTUNITIES());
        
        return quorumTracker;
    }
}